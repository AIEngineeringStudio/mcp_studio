"""A small facade that records semantic MCP operations on either transport."""

import os
import sys
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from mcp import Client, StdioServerParameters

from mcp_lab.observability.config import Settings
from mcp_lab.wire.recorder import JsonlWireRecorder


def default_stdio_target(settings: Settings, *, wiretap: bool = True) -> StdioServerParameters:
    """Build a local stdio target, optionally routed through the raw wiretap."""

    project_root = Path(__file__).resolve().parents[3]
    server_command = [sys.executable, "-m", "mcp_lab.server"]
    if wiretap:
        args = [
            "-m",
            "mcp_lab.wire.stdio_proxy",
            "--output",
            str(settings.wire_log_path),
            "--max-bytes",
            str(settings.wire_max_body_bytes),
            "--",
            *server_command,
        ]
    else:
        args = server_command[1:]
    return StdioServerParameters(
        command=sys.executable,
        args=args,
        cwd=project_root,
        env={
            "MCP_LAB_SERVER_TRANSPORT": "stdio",
            "MCP_LAB_LOG_FORMAT": settings.log_format,
            "MCP_LAB_LOG_LEVEL": settings.log_level,
            "MCP_LAB_TRACE_EXPORTER": os.getenv("MCP_LAB_SERVER_TRACE_EXPORTER", "none"),
        },
    )


class ObservedMCPClient:
    """Transport-neutral client facade with decoded request/response recording."""

    def __init__(
        self,
        target: Any,
        *,
        transport_name: str,
        recorder: JsonlWireRecorder,
    ) -> None:
        self._client = Client(target)
        self.transport_name = transport_name
        self.recorder = recorder

    @property
    def client(self) -> Client:
        return self._client

    async def __aenter__(self) -> Self:
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._client.__aexit__(exc_type, exc, traceback)

    def _record_request(self, method: str, params: Any = None) -> None:
        self.recorder.record(
            direction="client_to_server",
            vantage_point="client_facade",
            transport=self.transport_name,
            payload={"jsonrpc": "2.0", "method": method, "params": params},
        )

    def _record_response(self, method: str, result: Any) -> None:
        self.recorder.record(
            direction="server_to_client",
            vantage_point="client_facade",
            transport=self.transport_name,
            payload={"jsonrpc": "2.0", "result": result},
            method=method,
        )

    async def list_tools(self) -> Any:
        self._record_request("tools/list")
        result = await self._client.list_tools()
        self._record_response("tools/list", result)
        return result

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        params = {"name": name, "arguments": arguments}
        self._record_request("tools/call", params)
        try:
            result = await self._client.call_tool(name, arguments)
        except Exception as exc:
            self._record_response("tools/call", {"error": exc})
            raise
        self._record_response("tools/call", result)
        return result

    async def read_resource(self, uri: str) -> Any:
        self._record_request("resources/read", {"uri": uri})
        result = await self._client.read_resource(uri)
        self._record_response("resources/read", result)
        return result
