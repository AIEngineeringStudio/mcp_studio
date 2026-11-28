"""Non-mutating MCP Streamable HTTP protocol observation (FastMCP 4.2).

Captures JSON-RPC JSON POST bodies, JSON responses, SSE `data:` messages,
and HTTP response status. HTTPX client hooks and ASGI server middleware
observe streaming chunks without consuming/replacing the actual body bytes.

Educational use only: payloads may contain secrets. Logs go to stderr.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import httpx2 as httpx  # FastMCP 4.2 uses the MCP SDK v2 / httpx2

MAX_CAPTURE = 128 * 1024  # bounded memory per JSON body or SSE event


def _emit(side: str, direction: str, kind: str, **fields: Any) -> None:
    """Tracing is best-effort and must never cause an MCP request to fail."""
    try:
        item = {
            "time": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "kind": kind,
            **fields,
        }
        print(f"\n\n[******** PROTOCOL(HTTP): {side} {direction} ********]\n",
              file=sys.stderr, flush=True
        )
        print(json.dumps(item, ensure_ascii=False, default=str),
              file=sys.stderr, flush=True)
    except Exception:
        pass


def _media_type(headers: Any) -> str:
    value = headers.get("content-type", "")
    return value.split(";", 1)[0].strip().lower()


def _read_content_type(headers: list[tuple[bytes, bytes]]) -> str:
    for name, value in headers:
        if name.lower() == b"content-type":
            return value.decode("latin1").split(";", 1)[0].strip().lower()
    return ""


def _decoded(data: bytes) -> Any:
    """Keep the JSON-RPC envelope as a JSON object, not just a method name."""
    try:
        return json.loads(data)
    except (UnicodeError, json.JSONDecodeError):
        return {"invalid_json": data.decode("utf-8", errors="replace")}


class _BodyObserver:
    """Incrementally observe either one JSON body or a sequence of SSE events.

    Memory usage is limited independently of how long an SSE connection lives.
    """

    def __init__(self, side: str, direction: str, content_type: str,
                 *, method: str | None = None, path: str | None = None,
                 status: int | None = None) -> None:
        self.side, self.direction, self.content_type = side, direction, content_type
        self.info = {k: v for k, v in {"method": method, "path": path,
                                       "status": status}.items() if v is not None}
        self._body = bytearray()
        self._line = bytearray()
        self._sse_data: list[bytes] = []
        self._sse_size = 0
        self._sse_overflow = False
        self._overflow = False
        self._finished = False

    def feed(self, chunk: bytes) -> None:
        if self._finished or not chunk:
            return
        if self.content_type == "text/event-stream":
            self._feed_sse(chunk)
        elif self.content_type in ("application/json", "application/json-rpc"):
            if len(self._body) + len(chunk) > MAX_CAPTURE:
                self._overflow = True
                self._body.clear()
            elif not self._overflow:
                self._body.extend(chunk)

    def _feed_sse(self, chunk: bytes) -> None:
        # SSE lines can be split across any network chunk boundary.
        self._line.extend(chunk)
        # Do not retain a never-ending line or overlarge event.
        while True:
            i = self._line.find(b"\n")
            if i < 0:
                if len(self._line) > MAX_CAPTURE:
                    self._line.clear()
                    self._sse_overflow = True
                return
            line = bytes(self._line[:i]).rstrip(b"\r")
            del self._line[:i + 1]
            if len(line) > MAX_CAPTURE:
                self._sse_overflow = True
                continue
            if not line:
                self._dispatch_sse()
            elif line.startswith(b"data:"):
                data = line[5:]
                if data.startswith(b" "):
                    data = data[1:]
                self._sse_size += len(data)
                if self._sse_size > MAX_CAPTURE:
                    self._sse_overflow = True
                    self._sse_data.clear()
                elif not self._sse_overflow:
                    self._sse_data.append(data)

    def _dispatch_sse(self) -> None:
        if self._sse_overflow:
            _emit(self.side, self.direction, "sse_truncated", **self.info)
        elif self._sse_data:
            data = b"\n".join(self._sse_data)
            _emit(self.side, self.direction, "sse_jsonrpc",
                  payload=_decoded(data), **self.info)
        self._sse_data.clear()
        self._sse_size = 0
        self._sse_overflow = False

    def finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        if self.content_type == "text/event-stream":
            # SSE normally dispatches at the blank line. A truncated stream is
            # recorded separately rather than incorrectly treated as complete.
            if self._sse_data or self._sse_overflow:
                _emit(self.side, self.direction, "sse_incomplete", **self.info)
        elif self.content_type in ("application/json", "application/json-rpc"):
            if self._overflow:
                _emit(self.side, self.direction, "json_truncated", **self.info)
            elif self._body:
                _emit(self.side, self.direction, "jsonrpc",
                      payload=_decoded(bytes(self._body)), **self.info)


class _ObservedHTTPXStream(httpx.AsyncByteStream):
    """Pass HTTPX's original chunks through unchanged and in order."""

    def __init__(self, stream: httpx.AsyncByteStream, observer: _BodyObserver):
        self.inner = stream
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


async def trace_http_request(request: httpx.Request) -> None:
    """HTTPX request hook: attach a tee before HTTPX sends the body."""
    info = {"method": request.method, "path": request.url.path}
    _emit("CLIENT", "OUT", "http_request", **info)
    media = _media_type(request.headers)
    if media in ("application/json", "application/json-rpc"):
        observer = _BodyObserver("CLIENT", "OUT", media, **info)
        try:
            # Most MCP requests are already materialized by HTTPX. Reading
            # `.content` here is non-consuming and avoids bypassing its cache.
            content = request.content
        except httpx.RequestNotRead:
            # Only truly streaming request bodies need a non-buffering tee.
            request.stream = _ObservedHTTPXStream(request.stream, observer)
        else:
            observer.feed(content)
            observer.finish()


async def trace_http_response(response: httpx.Response) -> None:
    """HTTPX response hook: attach tee before caller consumes JSON or SSE."""
    info = {"method": response.request.method, "path": response.request.url.path,
            "status": response.status_code}
    _emit("CLIENT", "IN", "http_response", **info)
    media = _media_type(response.headers)
    if media in ("application/json", "application/json-rpc", "text/event-stream"):
        response.stream = _ObservedHTTPXStream(
            response.stream,
            _BodyObserver("CLIENT", "IN", media, **info),
        )


def tracing_httpx_client_factory(
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    auth: httpx.Auth | None = None,
    follow_redirects: bool = True,
    **kwargs: Any,
) -> httpx.AsyncClient:
    """Signature compatible with FastMCP 4.2's httpx_client_factory call."""
    if timeout is None:
        timeout = httpx.Timeout(30.0, read=300.0)
    return httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        auth=auth,
        follow_redirects=follow_redirects,
        event_hooks={"request": [trace_http_request],
                     "response": [trace_http_response]},
        **kwargs,
    )


class HTTPProtocolTraceMiddleware:
    """Pure ASGI middleware: observes http.request/http.response.body frames.

    No request-body reads ahead of the application; all ASGI messages are
    forwarded exactly as received. Lifespan and non-HTTP scopes are unchanged.
    """

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope.get("path", "").rstrip("/") != "/mcp":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")
        ctype = _read_content_type(scope.get("headers", []))
        incoming = _BodyObserver("SERVER", "IN", ctype, method=method, path=path)
        outgoing: _BodyObserver | None = None
        _emit("SERVER", "IN", "http_request", method=method, path=path)

        async def trace_receive() -> Any:
            message = await receive()
            if message["type"] == "http.request":
                incoming.feed(message.get("body", b""))
                if not message.get("more_body", False):
                    incoming.finish()
            return message

        async def trace_send(message: dict[str, Any]) -> None:
            nonlocal outgoing
            if message["type"] == "http.response.start":
                status = message["status"]
                _emit("SERVER", "OUT", "http_response", method=method,
                      path=path, status=status)
                media = _read_content_type(message.get("headers", []))
                outgoing = _BodyObserver("SERVER", "OUT", media,
                                         method=method, path=path, status=status)
            elif message["type"] == "http.response.body" and outgoing is not None:
                outgoing.feed(message.get("body", b""))
                if not message.get("more_body", False):
                    outgoing.finish()
            await send(message)

        try:
            await self.app(scope, trace_receive, trace_send)
        except BaseException as exc:
            _emit("SERVER", "OUT", "http_error", method=method,
                  path=path, error=type(exc).__name__)
            raise
        finally:
            # If a client disconnects, log as incomplete rather than missing.
            if outgoing is not None:
                outgoing.finish()
            incoming.finish()
