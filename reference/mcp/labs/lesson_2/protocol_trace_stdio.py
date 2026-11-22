"""Observe MCP STDIO SessionMessage objects without changing their contents.

This lesson deliberately logs complete JSON-RPC envelopes to stderr.
Do not use it with sensitive payloads unless you first add redaction.

Integration note: install_server_stdio_trace() wraps the FastMCP 4.2
server-runner's imported stdio_server symbol. This is version-sensitive.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from anyio.abc import ObjectReceiveStream, ObjectSendStream
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.message import SessionMessage

from fastmcp.client.transports.base import ClientTransport, TransportOptions


def _log(side: str, direction: str, item: SessionMessage | Exception) -> None:
    """Logging errors must never interrupt message delivery."""
    try:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        if isinstance(item, SessionMessage):
            # Same JSON-RPC model serializer used by the SDK's stdio transport.
            envelope = item.message.model_dump_json(
                by_alias=True, exclude_unset=True
            )
        else:
            envelope = f"<transport exception: {type(item).__name__}: {item}>"
        print(f"\n***[PROTOCOL]*** {timestamp} [{side} {direction}]"
              f" {envelope}",
              file=sys.stderr, flush=True)
    except Exception:
        # Instrumentation must not introduce transport failures.
        pass


class TraceReceiveStream(ObjectReceiveStream[SessionMessage | Exception]):
    """Log after receiving; forward the identical SessionMessage object."""

    def __init__(self, inner: ObjectReceiveStream[Any], side: str):
        self._inner = inner
        self._side = side

    async def receive(self) -> SessionMessage | Exception:
        item = await self._inner.receive()
        _log(self._side, "IN", item)
        return item

    async def aclose(self) -> None:
        await self._inner.aclose()


class TraceSendStream(ObjectSendStream[SessionMessage]):
    """Log send attempts; forward the identical SessionMessage object."""

    def __init__(self, inner: ObjectSendStream[SessionMessage], side: str):
        self._inner = inner
        self._side = side

    async def send(self, item: SessionMessage) -> None:
        _log(self._side, "OUT", item)
        await self._inner.send(item)

    async def aclose(self) -> None:
        await self._inner.aclose()


class TracedStdioTransport(ClientTransport):
    """FastMCP ClientTransport that observes the SDK's STDIO streams.

    The transport/session owner remains the official MCP SDK.
    This simple educational transport opens one subprocess per connection.
    """

    def __init__(self, command: str, args: list[str]):
        self.command = command
        self.args = args

    @asynccontextmanager
    async def connect_session(
        self,
        *,
        transport_options: TransportOptions | None = None,
        **session_kwargs: Any,
    ) -> AsyncIterator[Any]:
        params = StdioServerParameters(command=self.command, args=self.args)
        async with stdio_client(params) as (read_stream, write_stream):
            options = transport_options or TransportOptions()
            async with options.session_class(
                TraceReceiveStream(read_stream, "CLIENT"),
                TraceSendStream(write_stream, "CLIENT"),
                **session_kwargs,
            ) as session:
                yield session


def install_server_stdio_trace() -> None:
    """Wrap the stdio_server imported by FastMCP's STDIO runner.

    Install only in the server process, before mcp.run(transport='stdio').
    Does not affect HTTP. The original FastMCP runner keeps managing
    its own lifespan, context, and protocol options.
    """
    runner = importlib.import_module("fastmcp.server.mixins.transport")
    if getattr(runner.stdio_server, "_protocol_trace_installed", False):
        return
    original_stdio_server = runner.stdio_server

    @asynccontextmanager
    async def traced_stdio_server(*args: Any, **kwargs: Any):
        async with original_stdio_server(*args, **kwargs) as streams:
            read_stream, write_stream = streams
            yield (
                TraceReceiveStream(read_stream, "SERVER"),
                TraceSendStream(write_stream, "SERVER"),
            )

    traced_stdio_server._protocol_trace_installed = True  # type: ignore[attr-defined]
    runner.stdio_server = traced_stdio_server
