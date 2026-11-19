"""ASGI middleware that records Streamable HTTP request and response bodies."""

import json
from typing import Any, cast

from mcp_lab.wire.recorder import JsonlWireRecorder


def _decode_body(body: bytes, max_bytes: int) -> Any:
    sample = body[:max_bytes]
    try:
        return json.loads(sample.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"raw": sample.decode("utf-8", errors="replace")}


class JsonRpcHTTPRecorderMiddleware:
    """Record HTTP bodies without consuming them before the MCP application."""

    def __init__(self, app: Any, recorder: JsonlWireRecorder, max_bytes: int = 65_536) -> None:
        self.app = app
        self.recorder = recorder
        self.max_bytes = max_bytes

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_parts: list[bytes] = []
        response_parts: list[bytes] = []
        status = 0

        async def observed_receive() -> dict[str, Any]:
            message = cast(dict[str, Any], await receive())
            if message["type"] == "http.request":
                request_parts.append(message.get("body", b""))
            return message

        async def observed_send(message: dict[str, Any]) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            elif message["type"] == "http.response.body":
                response_parts.append(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, observed_receive, observed_send)
        finally:
            request_body = b"".join(request_parts)
            response_body = b"".join(response_parts)
            common = {"http_method": scope["method"], "path": scope["path"]}
            if request_body:
                self.recorder.record(
                    direction="client_to_server",
                    vantage_point="http_server",
                    transport="streamable-http",
                    payload=_decode_body(request_body, self.max_bytes),
                    byte_length=len(request_body),
                    truncated=len(request_body) > self.max_bytes,
                    **common,
                )
            if response_body:
                self.recorder.record(
                    direction="server_to_client",
                    vantage_point="http_server",
                    transport="streamable-http",
                    payload=_decode_body(response_body, self.max_bytes),
                    byte_length=len(response_body),
                    truncated=len(response_body) > self.max_bytes,
                    status_code=status,
                    **common,
                )
