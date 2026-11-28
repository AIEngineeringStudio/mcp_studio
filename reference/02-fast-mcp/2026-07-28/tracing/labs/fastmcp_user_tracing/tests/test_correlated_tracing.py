"""Offline contract tests: no FastMCP installation required.

These tests exercise JSONL, HTTPX-ASGI request/response/SSE, semantic
logging, STDIO SessionMessage object preservation, subprocess env propagation.
They are not an end-to-end FastMCP v4.2 test.
"""
from __future__ import annotations

import asyncio
import contextlib
import importlib
import json
import os
import stat
import sys
import tempfile
import types
from pathlib import Path

import anyio
import httpx

# The FastMCP 4.2 app imports httpx2, unavailable in this isolated environment.
# Substituting HTTPX tests observer behavior only, not SDK version compatibility.
sys.modules.setdefault("httpx2", httpx)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import http_protocol_trace as http_trace
import query_traces
import semantic_trace_client as semantic_client
import trace_store


async def test_http(log_dir: Path) -> None:
    session_id = trace_store.new_id()
    request_body = b'{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"get_ticket"}}'
    response_body = b'{"jsonrpc":"2.0","id":7,"result":{"status":"open"}}'
    count = 0
    seen_headers = []

    async def server(scope, receive, send):
        nonlocal count
        count += 1
        received = bytearray()
        while True:
            frame = await receive()
            if frame["type"] != "http.request":
                break
            received.extend(frame.get("body", b""))
            if not frame.get("more_body", False):
                break
        assert bytes(received) == request_body
        seen_headers.append(dict(scope["headers"]))
        assert trace_store.current_session() == session_id
        assert trace_store.current_exchange()
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": response_body[:12],
                    "more_body": True})
        await send({"type": "http.response.body", "body": response_body[12:],
                    "more_body": False})

    from functools import partial
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=http_trace.HTTPProtocolTraceMiddleware(server)),
        event_hooks={
            "request": [partial(http_trace.trace_http_request,
                                trace_session_id=session_id)],
            "response": [http_trace.trace_http_response],
        },
    ) as client:
        for _ in range(2):
            result = await client.post("http://test/mcp", content=request_body,
                                       headers={"Content-Type": "application/json"})
            assert result.content == response_body
    assert count == 2
    rows = query_traces.matching_records(log_dir, session=session_id, rpc="7")
    assert len(rows) == 8, rows
    groups = {}
    for row in rows:
        groups.setdefault(row["http_exchange_id"], set()).add(
            (row["side"], row["direction"]))
        assert row["rpc_kind"] in ("request", "response")
        assert "payload" not in row  # privacy-safe default
    assert len(groups) == 2, groups
    for directions in groups.values():
        assert directions == {
            ("CLIENT", "OUT"), ("SERVER", "IN"),
            ("SERVER", "OUT"), ("CLIENT", "IN"),
        }
    for headers in seen_headers:
        assert headers[b"x-debug-trace-session"].decode() == session_id
    print("PASS: 4 HTTP observations, 2 exchanges with repeated rpc ID, correlated")


async def test_sse(log_dir: Path) -> None:
    session_id = trace_store.new_id()
    sse = b'data: {"jsonrpc":"2.0","id":23,"result":{}}\r\n\r\n'

    async def server(scope, receive, send):
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"text/event-stream")]})
        for i, part in enumerate([sse[:8], sse[8:21], sse[21:]]):
            await send({"type": "http.response.body", "body": part,
                        "more_body": i < 2})

    from functools import partial
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=http_trace.HTTPProtocolTraceMiddleware(server)),
        event_hooks={"request": [partial(http_trace.trace_http_request,
                                         trace_session_id=session_id)],
                     "response": [http_trace.trace_http_response]},
    ) as client:
        async with client.stream("GET", "http://test/mcp") as response:
            raw = b"".join([c async for c in response.aiter_raw()])
    assert raw == sse
    rows = query_traces.matching_records(log_dir, session=session_id, rpc="23")
    assert {(r["side"], r["direction"], r["event"]) for r in rows} == {
        ("SERVER", "OUT", "sse_jsonrpc"), ("CLIENT", "IN", "sse_jsonrpc"),
    }, rows
    print("PASS: fragmented SSE events on both sides; bytes unchanged")


def test_store(log_dir: Path) -> None:
    store = trace_store.TraceStore("CLIENT", log_dir)
    record = {"jsonrpc": "2.0", "id": 8, "method": "tools/call",
              "params": {"name": "get_ticket", "password": "private"}}
    session_id = trace_store.new_id()
    store.record(direction="OUT", transport="http", event="jsonrpc",
                 trace_session_id=session_id, envelope=record)
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    first = json.loads(store.path.read_text().splitlines()[-1])
    assert "payload" not in first
    assert first["rpc_id"] == 8 and first["rpc_method"] == "tools/call"
    assert first["tool_name"] == "get_ticket"
    os.environ["MCP_TRACE_PAYLOAD"] = "1"
    try:
        store.record(direction="OUT", transport="http", event="jsonrpc",
                     trace_session_id=session_id, envelope=record)
    finally:
        os.environ.pop("MCP_TRACE_PAYLOAD", None)
        store.close()
    second = json.loads(store.path.read_text().splitlines()[-1])
    assert second["payload"]["params"]["password"] == "[REDACTED]"
    assert record["params"]["password"] == "private"  # source unchanged
    try:
        trace_store.store_for = lambda side: (_ for _ in ()).throw(OSError("no space"))
        trace_store.emit("CLIENT", direction="OUT", transport="stdio",
                         event="jsonrpc", trace_session_id=session_id)
    finally:
        del trace_store.store_for
        importlib.reload(trace_store)
    print("PASS: JSONL fields, permissions, opt-in payload and redaction, log errors")


async def test_semantic(log_dir: Path) -> None:
    session_id = trace_store.new_id()
    with trace_store.trace_scope(session=session_id):
        async def work(): return {"answer": 1}
        result = await semantic_client.trace_client(
            "tools/call", {"name": "get_ticket"}, work())
        assert result == {"answer": 1}
    rows = query_traces.matching_records(log_dir, session=session_id)
    entries = [r for r in rows if r["event"].startswith("semantic")]
    assert len(entries) == 2, entries
    assert len({r["semantic_operation_id"] for r in entries}) == 1
    assert all(r["rpc_method"] == "tools/call" for r in entries)
    print("PASS: original semantic wrapper preserved, correlated operation events")


async def test_stdio(log_dir: Path) -> None:
    # Provide only the type contracts required by the user's STDIO wrapper.
    stub_names = ["mcp", "mcp.client", "mcp.client.stdio", "mcp.shared",
                  "mcp.shared.message", "fastmcp", "fastmcp.client",
                  "fastmcp.client.transports", "fastmcp.client.transports.base",
                  "fastmcp.server", "fastmcp.server.mixins",
                  "fastmcp.server.mixins.transport"]
    for name in stub_names:
        mod = types.ModuleType(name)
        if name not in ("mcp.client.stdio", "mcp.shared.message",
                        "fastmcp.client.transports.base",
                        "fastmcp.server.mixins.transport"):
            mod.__path__ = []
        sys.modules[name] = mod

    class FakeMessage:
        def model_dump_json(self, **kwargs):
            assert kwargs == {"by_alias": True, "exclude_unset": True}
            return '{"jsonrpc":"2.0","id":17,"method":"tools/list"}'

    class SessionMessage:
        def __init__(self): self.message = FakeMessage()

    class Params:
        def __init__(self, **kwargs): self.__dict__.update(kwargs)

    class ClientTransport: pass

    class Session:
        def __init__(self, read, write, **kwargs):
            self.read = read
            self.write = write
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None

    class TransportOptions:
        session_class = Session

    sys.modules["mcp"].StdioServerParameters = Params
    sys.modules["mcp.shared.message"].SessionMessage = SessionMessage
    sys.modules["fastmcp.client.transports.base"].ClientTransport = ClientTransport
    sys.modules["fastmcp.client.transports.base"].TransportOptions = TransportOptions

    recorded_params = []

    @contextlib.asynccontextmanager
    async def stdio_client(params):
        recorded_params.append(params)
        a,b = anyio.create_memory_object_stream(1)
        c,d = anyio.create_memory_object_stream(1)
        async with a,b,c,d:
            yield b,c

    sys.modules["mcp.client.stdio"].stdio_client = stdio_client
    from stdio_protocol_trace import (
        TracedStdioTransport, TraceReceiveStream, TraceSendStream,
        install_server_stdio_trace)
    session_id = trace_store.new_id()
    original_env = os.environ.get(trace_store.TRACE_SESSION_ENV)
    transport = TracedStdioTransport("python", ["server.py"], session_id)
    async with transport.connect_session() as session:
        assert isinstance(session.read, TraceReceiveStream)
        assert isinstance(session.write, TraceSendStream)
    assert recorded_params[0].env[trace_store.TRACE_SESSION_ENV] == session_id
    child_connection = recorded_params[0].env[trace_store.STDIO_CONNECTION_ENV]
    assert trace_store.valid_id(child_connection) == child_connection
    assert os.environ.get(trace_store.TRACE_SESSION_ENV) == original_env
    assert os.environ.get(trace_store.STDIO_CONNECTION_ENV) is None

    # Retain message identity and record the transport fields.
    a,b = anyio.create_memory_object_stream(1)
    msg = SessionMessage()
    async with a,b:
        await TraceSendStream(a, "CLIENT", session_id).send(msg)
        received = await TraceReceiveStream(b, "SERVER", session_id).receive()
        assert received is msg
    rows = query_traces.matching_records(log_dir, session=session_id, rpc="17")
    assert {(row["side"],row["direction"]) for row in rows} == {
        ("CLIENT","OUT"), ("SERVER","IN")},rows
    # A fresh client/server connection has its own ID, preventing id=17 reuse
    # on reconnect from being confused within the same trace session.
    another_connection = trace_store.new_id()
    a2,b2 = anyio.create_memory_object_stream(1)
    async with a2,b2:
        await TraceSendStream(a2, "CLIENT", session_id, another_connection).send(msg)
        assert await TraceReceiveStream(b2, "SERVER", session_id,
                                        another_connection).receive() is msg
    scoped = query_traces.matching_records(log_dir, session=session_id,
                                           connection=another_connection, rpc="17")
    assert len(scoped) == 2 and all(
        r["stdio_connection_id"] == another_connection for r in scoped),scoped

    runner = sys.modules["fastmcp.server.mixins.transport"]
    @contextlib.asynccontextmanager
    async def original_stdio():
        x,y=anyio.create_memory_object_stream(1)
        a,b=anyio.create_memory_object_stream(1)
        async with x,y,a,b:
            yield y,a
    runner.stdio_server = original_stdio
    install_server_stdio_trace()
    patched = runner.stdio_server
    install_server_stdio_trace()
    assert runner.stdio_server is patched
    os.environ[trace_store.TRACE_SESSION_ENV] = session_id
    try:
        async with runner.stdio_server() as (read,write):
            assert isinstance(read, TraceReceiveStream)
            assert isinstance(write, TraceSendStream)
    finally:
        if original_env is None:
            os.environ.pop(trace_store.TRACE_SESSION_ENV,None)
        else:
            os.environ[trace_store.TRACE_SESSION_ENV]=original_env
    print("PASS: STDIO stream identity, child environment and runner wrapping")


async def main():
    with tempfile.TemporaryDirectory() as folder:
        log_dir = Path(folder)
        os.environ["MCP_TRACE_DIR"] = folder
        await test_http(log_dir)
        await test_sse(log_dir)
        await test_semantic(log_dir)
        await test_stdio(log_dir)
        test_store(log_dir)
        print("PASS: all offline correlation contracts")


if __name__ == "__main__":
    asyncio.run(main())
