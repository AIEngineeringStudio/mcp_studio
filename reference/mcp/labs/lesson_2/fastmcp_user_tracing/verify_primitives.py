"""Run focused checks for MCP tools, resources, or prompts."""

import argparse
import asyncio
import sys
from functools import partial

from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from server import mcp
from semantic_trace_client import trace_client
from http_protocol_trace import tracing_httpx_client_factory
from stdio_protocol_trace import TracedStdioTransport
from trace_store import new_id, trace_scope


async def verify_tools(client: Client) -> None:
    tools = await trace_client(
        "tools/list", {}, client.list_tools()
    )

    get_ticket = next(tool for tool in tools if tool.name == "get_ticket")
    assert "ticket_id" in get_ticket.input_schema["required"]

    result = await trace_client(
        "tools/call",
        {"name": "get_ticket", "arguments": {"ticket_id": "T-100"}},
        client.call_tool("get_ticket", {"ticket_id": "T-100"}),
    )
    assert result.data["status"] == "open"

    print("tools: discovered get_ticket and called it successfully")


async def verify_resources(client: Client) -> None:
    templates = await trace_client(
        "resources/templates/list",
        {},
        client.list_resource_templates(),
    )
    assert any("ticket_id" in str(item.uri_template) for item in templates)

    contents = await trace_client(
        "resources/read",
        {"uri": "ticket://T-100"},
        client.read_resource("ticket://T-100"),
    )
    assert '"status": "open"' in contents[0].text

    print("resources: discovered ticket://{ticket_id} and read ticket://T-100")


async def verify_prompts(client: Client) -> None:
    prompts = await trace_client(
        "prompts/list", {}, client.list_prompts()
    )
    assert "summarize_ticket" in {prompt.name for prompt in prompts}

    result = await trace_client(
        "prompts/get",
        {
            "name": "summarize_ticket",
            "arguments": {"ticket_id": "T-100"},
        },
        client.get_prompt(
            "summarize_ticket",
            {"ticket_id": "T-100"},
        ),
    )

    text = result.messages[0].content.text
    assert "T-100" in text

    print("prompts: discovered summarize_ticket and rendered its message")
    print("prompts: no model was invoked")


def client_source(mode: str, trace_session_id: str | None = None) -> Any:
    trace_session_id = trace_session_id or new_id()
    """Use the same examples with in-memory, stdio, or HTTP transport."""
    if mode == "in-memory":
        return mcp
    if mode == "stdio":
        return TracedStdioTransport(
            command=sys.executable,
            trace_session_id=trace_session_id,
            args=[
                str(Path(__file__).resolve().resolve().with_name("server.py")),
                "--transport",
                "stdio",
            ],
        )
    if mode == "http":
        return StreamableHttpTransport(
            url="http://127.0.0.1:8000/mcp",
            httpx_client_factory=partial(
                tracing_httpx_client_factory, trace_session_id=trace_session_id
            ),
        )
    raise ValueError(f"Unsupported mode: {mode}")


async def main(transport_name: str, focus: str) -> None:
    # One application-owned trace ID for this client connection/test run.
    session_id = new_id()
    print(f"Trace session ID: {session_id}")
    with trace_scope(session=session_id):
        async with Client(
                transport=client_source(transport_name, session_id),
                name="lesson-1-client"
        ) as client:
            if focus == "tools":
                await verify_tools(client)
            elif focus == "resources":
                await verify_resources(client)
            elif focus == "prompts":
                await verify_prompts(client)
            else:
                raise ValueError(f"Unsupported focus: {focus}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transport",
        choices=["in-memory", "stdio", "http"],
        required=True,
    )
    parser.add_argument(
        "--focus",
        choices=["tools", "resources", "prompts"],
        required=True,
    )
    args = parser.parse_args()
    asyncio.run(main(args.transport, args.focus))
