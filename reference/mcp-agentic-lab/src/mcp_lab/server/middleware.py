"""MCP-level observation middleware shared by both transports."""

from time import perf_counter
from typing import Any

from mcp.server.context import CallNext, HandlerResult, ServerMiddleware, ServerRequestContext

from mcp_lab.wire.recorder import JsonlWireRecorder


class WireRecordingMiddleware(ServerMiddleware[Any]):
    def __init__(self, recorder: JsonlWireRecorder, transport_name: str) -> None:
        self.recorder = recorder
        self.transport_name = transport_name

    async def __call__(
        self, ctx: ServerRequestContext[Any, Any], call_next: CallNext
    ) -> HandlerResult:
        started = perf_counter()
        request = {
            "jsonrpc": "2.0",
            "id": ctx.request_id,
            "method": ctx.method,
            "params": ctx.params,
        }
        self.recorder.record(
            direction="client_to_server",
            vantage_point="server_middleware",
            transport=self.transport_name,
            payload=request,
        )
        try:
            result = await call_next(ctx)
        except Exception as exc:
            self.recorder.record(
                direction="server_to_client",
                vantage_point="server_middleware",
                transport=self.transport_name,
                payload={"jsonrpc": "2.0", "id": ctx.request_id, "error": exc},
                method=ctx.method,
                duration_ms=round((perf_counter() - started) * 1000, 3),
            )
            raise
        self.recorder.record(
            direction="server_to_client",
            vantage_point="server_middleware",
            transport=self.transport_name,
            payload={"jsonrpc": "2.0", "id": ctx.request_id, "result": result},
            method=ctx.method,
            duration_ms=round((perf_counter() - started) * 1000, 3),
        )
        return result
