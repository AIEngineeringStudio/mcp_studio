from mcp import Client

from mcp_lab.observability.config import Settings
from mcp_lab.server.app import create_server
from mcp_lab.wire import JsonlWireRecorder


async def test_server_lists_and_calls_tools(tmp_path):
    settings = Settings(wire_log_enabled=True, trace_exporter="none")
    server = create_server(settings, recorder=JsonlWireRecorder(tmp_path / "server.jsonl"))

    async with Client(server, raise_exceptions=True) as client:
        listed = await client.list_tools()
        assert {tool.name for tool in listed.tools} >= {"add", "divide"}
        result = await client.call_tool("add", {"a": 7, "b": 8})

    assert result.is_error is False
    assert result.structured_content == {
        "operation": "add",
        "expression": "7.0 + 8.0",
        "result": 15.0,
    }
    assert (tmp_path / "server.jsonl").read_text().count("\n") >= 2


async def test_tool_error_is_model_visible(tmp_path):
    server = create_server(
        Settings(wire_log_enabled=False, trace_exporter="none"),
        recorder=JsonlWireRecorder(tmp_path / "unused.jsonl", enabled=False),
    )
    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool("divide", {"numerator": 1, "denominator": 0})

    assert result.is_error is True
