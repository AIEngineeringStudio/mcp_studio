"""Your STDIO SessionMessage tracing with shared JSONL correlation.

FastMCP 4.2 runner interception is version-sensitive. Instrumentation never
replaces a SessionMessage; STDIO child gets a trace-only environment variable.
"""
from __future__ import annotations

import importlib
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from anyio.abc import ObjectReceiveStream, ObjectSendStream
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.message import SessionMessage
from fastmcp.client.transports.base import ClientTransport, TransportOptions

from trace_store import (TRACE_SESSION_ENV, STDIO_CONNECTION_ENV,
                         emit, new_id, valid_id)


def _log(side: str, direction: str, item: SessionMessage | Exception,
         trace_session_id: str | None, connection_id: str | None = None) -> None:
    """Extract JSON-RPC fields; never interrupt message delivery on log failure."""
    try:
        if isinstance(item, SessionMessage):
            envelope = json.loads(item.message.model_dump_json(
                by_alias=True, exclude_unset=True))
            emit(side, direction=direction, transport="stdio", event="jsonrpc",
                 trace_session_id=trace_session_id,
                 stdio_connection_id=connection_id, envelope=envelope)
        else:
            emit(side, direction=direction, transport="stdio", event="transport_error",
                 trace_session_id=trace_session_id,
                 stdio_connection_id=connection_id, detail=type(item).__name__)
    except Exception:
        pass


class TraceReceiveStream(ObjectReceiveStream[SessionMessage | Exception]):
    """Log received messages, forwarding the identical original object."""

    def __init__(self, inner: ObjectReceiveStream[Any], side: str,
                 trace_session_id: str | None, connection_id: str | None = None):
        self._inner, self._side, self._session = inner, side, trace_session_id
        self._connection = connection_id

    async def receive(self) -> SessionMessage | Exception:
        item = await self._inner.receive()
        _log(self._side, "IN", item, self._session, self._connection)
        return item

    async def aclose(self) -> None:
        await self._inner.aclose()


class TraceSendStream(ObjectSendStream[SessionMessage]):
    """Observe attempted sends; forward the identical original object."""

    def __init__(self, inner: ObjectSendStream[SessionMessage], side: str,
                 trace_session_id: str | None, connection_id: str | None = None):
        self._inner, self._side, self._session = inner, side, trace_session_id
        self._connection = connection_id

    async def send(self, item: SessionMessage) -> None:
        _log(self._side, "OUT", item, self._session, self._connection)
        await self._inner.send(item)

    async def aclose(self) -> None:
        await self._inner.aclose()


class TracedStdioTransport(ClientTransport):
    """One subprocess per connection; same trace session ID on both sides."""

    def __init__(self, command: str, args: list[str],
                 trace_session_id: str | None = None):
        self.command = command
        self.args = args
        self.trace_session_id = valid_id(trace_session_id)

    @asynccontextmanager
    async def connect_session(
        self, *, transport_options: TransportOptions | None = None,
        **session_kwargs: Any,
    ) -> AsyncIterator[Any]:
        session_id = self.trace_session_id or new_id()
        connection_id = new_id()
        # Do not change the global environment for concurrent connections.
        child_env = {**os.environ, TRACE_SESSION_ENV: session_id,
                     STDIO_CONNECTION_ENV: connection_id}
        params = StdioServerParameters(command=self.command, args=self.args,
                                       env=child_env)
        async with stdio_client(params) as (read_stream, write_stream):
            options = transport_options or TransportOptions()
            async with options.session_class(
                TraceReceiveStream(read_stream, "CLIENT", session_id, connection_id),
                TraceSendStream(write_stream, "CLIENT", session_id, connection_id),
                **session_kwargs,
            ) as session:
                yield session


def install_server_stdio_trace() -> None:
    """Wrap the FastMCP STDIO runner's imported stdio_server context manager.

    Retains the original runner, lifecycle, and session ownership. Call before
    mcp.run(transport='stdio') in the child process only.
    """
    runner = importlib.import_module("fastmcp.server.mixins.transport")
    if getattr(runner.stdio_server, "_protocol_trace_installed", False):
        return
    original_stdio_server = runner.stdio_server

    @asynccontextmanager
    async def traced_stdio_server(*args: Any, **kwargs: Any):
        session_id = valid_id(os.environ.get(TRACE_SESSION_ENV))
        connection_id = valid_id(os.environ.get(STDIO_CONNECTION_ENV))
        async with original_stdio_server(*args, **kwargs) as streams:
            read_stream, write_stream = streams
            yield (TraceReceiveStream(read_stream, "SERVER", session_id, connection_id),
                   TraceSendStream(write_stream, "SERVER", session_id, connection_id))

    traced_stdio_server._protocol_trace_installed = True  # type: ignore[attr-defined]
    runner.stdio_server = traced_stdio_server
