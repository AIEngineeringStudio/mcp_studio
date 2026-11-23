"""Client HTTPX hooks + server ASGI tee, with request and session correlation.

The hooks log structured JSONL rather than stderr. No live bytes are altered.
The server only observes requests on /mcp. The X-Debug-* IDs are untrusted
trace metadata: never use them as identity, session state, or authorization.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from functools import partial
from typing import Any

import httpx2 as httpx

from trace_store import (
    HTTP_EXCHANGE_HEADER,
    TRACE_SESSION_HEADER,
    new_id,
    emit,
    valid_id,
    trace_scope,
)

MAX_CAPTURE = 128 * 1024


def _media(headers: Any) -> str:
    value = headers.get("content-type", "")
    return value.split(";", 1)[0].strip().lower()


def _asgi_header(headers: list[tuple[bytes, bytes]], key: str) -> str | None:
    wanted = key.encode("ascii")
    for name, value in headers:
        if name.lower() == wanted:
            return value.decode("latin1")
    return None


class BodyObserver:
    """Parse complete JSON bodies or individual SSE events, retaining at most 128 KiB.

    It does not attempt to parse every possible binary HTTP body. Only the
    content types relevant to the MCP lab are inspected.
    """
    def __init__(self, *, side: str, direction: str, media: str,
                 trace_session_id: str | None, http_exchange_id: str | None,
                 http_method: str | None = None, path: str | None = None,
                 http_status: int | None = None):
        self.side, self.direction, self.media = side, direction, media
        self.session, self.exchange = trace_session_id, http_exchange_id
        self.method, self.path, self.status = http_method, path, http_status
        self._json = bytearray()
        self._line = bytearray()
        self._event_data: list[bytes] = []
        self._event_size = 0
        self._overflow = False
        self._event_overflow = False
        self._line_overflow = False
        self._finished = False

    def _log(self, event: str, envelope: Any = None, detail: str | None = None):
        emit(self.side, 
            direction=self.direction, transport="http", event=event,
            trace_session_id=self.session, http_exchange_id=self.exchange,
            envelope=envelope, http_method=self.method, path=self.path,
            http_status=self.status, detail=detail,
        )

    def feed(self, chunk: bytes) -> None:
        if not chunk or self._finished:
            return
        if self.media in ("application/json", "application/json-rpc"):
            if len(self._json) + len(chunk) > MAX_CAPTURE:
                self._overflow = True
                self._json.clear()
            elif not self._overflow:
                self._json.extend(chunk)
        elif self.media == "text/event-stream":
            # A chunk may contain many SSE lines, and any line may be split.
            fragments = chunk.split(b"\n")
            for idx, part in enumerate(fragments):
                if not self._line_overflow:
                    if len(self._line) + len(part) > MAX_CAPTURE:
                        self._line.clear()
                        self._line_overflow = True
                        self._event_overflow = True
                    else:
                        self._line.extend(part)
                if idx < len(fragments) - 1:
                    if not self._line_overflow:
                        self._handle_line(bytes(self._line).rstrip(b"\r"))
                    self._line.clear()
                    self._line_overflow = False

    def _handle_line(self, line: bytes) -> None:
        if not line:
            self._finish_event()
        elif line.startswith(b"data:"):
            part = line[5:]
            if part.startswith(b" "):
                part = part[1:]
            self._event_size += len(part)
            if self._event_size > MAX_CAPTURE:
                self._event_overflow = True
                self._event_data.clear()
            elif not self._event_overflow:
                self._event_data.append(part)

    def _finish_event(self) -> None:
        if self._event_overflow:
            self._log("sse_truncated")
        elif self._event_data:
            data = b"\n".join(self._event_data)
            self._log_json("sse_jsonrpc", data)
        self._event_data.clear()
        self._event_size = 0
        self._event_overflow = False

    def _log_json(self, event: str, data: bytes) -> None:
        try:
            envelope = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._log("invalid_json", detail=event)
            return
        # Most MCP messages are JSON objects. Lists are still retained as
        # transport events but do not have a single JSON-RPC ID.
        self._log(event, envelope=envelope)

    def finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        if self.media == "text/event-stream":
            if self._event_data or self._event_overflow or self._line:
                self._log("sse_incomplete")
        elif self.media in ("application/json", "application/json-rpc"):
            if self._overflow:
                self._log("json_truncated")
            elif self._json:
                self._log_json("jsonrpc", bytes(self._json))


class ObservedHTTPXStream(httpx.AsyncByteStream):
    def __init__(self, inner: httpx.AsyncByteStream, observer: BodyObserver):
        self.inner = inner
        self.observer = observer

    async def __aiter__(self) -> AsyncIterator[bytes]:
        try:
            async for chunk in self.inner:
                self.observer.feed(chunk)
                yield chunk
        finally:
            self.observer.finish()

    async def aclose(self) -> None:
        try:
            await self.inner.aclose()
        finally:
            self.observer.finish()


async def trace_http_request(request: httpx.Request, *, trace_session_id: str | None = None) -> None:
    # Unique per HTTP exchange even when one logical client issues many calls.
    exchange = new_id()
    session_id = valid_id(trace_session_id) or new_id()
    request.headers[TRACE_SESSION_HEADER] = session_id
    request.headers[HTTP_EXCHANGE_HEADER] = exchange
    request.extensions["mcp_debug_exchange_id"] = exchange
    request.extensions["mcp_debug_session_id"] = session_id
    emit("CLIENT", 
        direction="OUT", transport="http", event="http_request",
        trace_session_id=session_id,
        http_exchange_id=exchange, http_method=request.method, path=request.url.path,
    )
    media = _media(request.headers)
    if media in ("application/json", "application/json-rpc"):
        observer = BodyObserver(
            side="CLIENT", direction="OUT", media=media,
            trace_session_id=session_id, http_exchange_id=exchange,
            http_method=request.method, path=request.url.path,
        )
        try:
            content = request.content
        except httpx.RequestNotRead:
            request.stream = ObservedHTTPXStream(request.stream, observer)
        else:
            observer.feed(content)
            observer.finish()


async def trace_http_response(response: httpx.Response) -> None:
    request = response.request
    session_id = valid_id(request.extensions.get("mcp_debug_session_id"))
    exchange = request.extensions.get("mcp_debug_exchange_id")
    emit("CLIENT", 
        direction="IN", transport="http", event="http_response",
        trace_session_id=session_id,
        http_exchange_id=exchange, http_method=request.method,
        path=request.url.path, http_status=response.status_code,
    )
    media = _media(response.headers)
    if media in ("application/json", "application/json-rpc", "text/event-stream"):
        observer = BodyObserver(
            side="CLIENT", direction="IN", media=media,
            trace_session_id=session_id, http_exchange_id=exchange,
            http_method=request.method, path=request.url.path,
            http_status=response.status_code,
        )
        response.stream = ObservedHTTPXStream(response.stream, observer)


def tracing_httpx_client_factory(
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    auth: httpx.Auth | None = None,
    follow_redirects: bool = True,
    trace_session_id: str | None = None,
    **kwargs: Any,
) -> httpx.AsyncClient:
    """FastMCP 4.2 factory; one logical trace ID shared by client hooks."""
    if timeout is None:
        timeout = httpx.Timeout(30.0, read=300.0)
    session_id = valid_id(trace_session_id) or new_id()
    existing_hooks = kwargs.pop("event_hooks", {})
    request_hooks = list(existing_hooks.get("request", []))
    response_hooks = list(existing_hooks.get("response", []))
    request_hooks.append(partial(trace_http_request, trace_session_id=session_id))
    response_hooks.append(trace_http_response)
    return httpx.AsyncClient(
        headers=headers, timeout=timeout, auth=auth,
        follow_redirects=follow_redirects,
        event_hooks={"request": request_hooks, "response": response_hooks},
        **kwargs,
    )


class HTTPProtocolTraceMiddleware:
    """Pure ASGI tee: never buffers or consumes an HTTP request/response."""
    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope.get("path", "").rstrip("/") != "/mcp":
            await self.app(scope, receive, send)
            return

        method, path = scope.get("method", ""), scope.get("path", "")
        headers = scope.get("headers", [])
        # Do not trust these identifiers for authentication or application state.
        session = valid_id(_asgi_header(headers, TRACE_SESSION_HEADER))
        exchange = valid_id(_asgi_header(headers, HTTP_EXCHANGE_HEADER))
        emit("SERVER", 
            direction="IN", transport="http", event="http_request",
            trace_session_id=session, http_exchange_id=exchange,
            http_method=method, path=path,
        )
        incoming = BodyObserver(
            side="SERVER", direction="IN",
            media=(_asgi_header(headers, "content-type") or "").split(";", 1)[0].lower(),
            trace_session_id=session, http_exchange_id=exchange,
            http_method=method, path=path,
        )
        outgoing: BodyObserver | None = None

        async def traced_receive() -> Any:
            message = await receive()
            if message["type"] == "http.request":
                incoming.feed(message.get("body", b""))
                if not message.get("more_body", False):
                    incoming.finish()
            return message

        async def traced_send(message: dict[str, Any]) -> None:
            nonlocal outgoing
            if message["type"] == "http.response.start":
                status = message["status"]
                emit("SERVER", 
                    direction="OUT", transport="http", event="http_response",
                    trace_session_id=session, http_exchange_id=exchange,
                    http_method=method, path=path, http_status=status,
                )
                outgoing = BodyObserver(
                    side="SERVER", direction="OUT",
                    media=(_asgi_header(message.get("headers", []), "content-type") or "")
                          .split(";", 1)[0].lower(),
                    trace_session_id=session, http_exchange_id=exchange,
                    http_method=method, path=path, http_status=status,
                )
            elif message["type"] == "http.response.body" and outgoing is not None:
                outgoing.feed(message.get("body", b""))
                if not message.get("more_body", False):
                    outgoing.finish()
            await send(message)

        # Context follows this ASGI request into FastMCP middleware when
        # execution stays within the request's async context.
        with trace_scope(session=session, exchange=exchange):
            try:
                await self.app(scope, traced_receive, traced_send)
            except BaseException as exc:
                emit("SERVER",
                    direction="OUT", transport="http", event="http_error",
                    trace_session_id=session, http_exchange_id=exchange,
                    http_method=method, path=path, detail=type(exc).__name__,
                )
                raise
            finally:
                if outgoing is not None:
                    outgoing.finish()
                incoming.finish()
