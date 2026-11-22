"""Demonstrate MCP 2026-07-28 discovery and request metadata separately.

Choose --example discovery to see server capabilities without tools/call.
Choose --example metadata to see client capabilities on a tools/call request.
Use --example both (default) to run both demonstrations.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult
from fastmcp.client.transports import (
    StdioTransport,
    StreamableHttpTransport,
)
from server import mcp


async def decline_elicitation(
        _message: str,
        _response_type: type[Any] | None,
        _params: Any,
        _context: Any,
) -> ElicitResult:
    """Advertise elicitation support, but decline any actual requests."""
    return ElicitResult(action="decline")


def client_source(mode: str) -> Any:
    """Use the same examples with in-memory, stdio, or HTTP transport."""
    if mode == "in-memory":
        return mcp
    if mode == "stdio":
        return StdioTransport(
            command=sys.executable,
            args=[
                str(Path(__file__).resolve().with_name("server.py")),
                "--transport",
                "stdio",
            ],
        )
    if mode == "http":
        return StreamableHttpTransport(url="http://127.0.0.1:8000/mcp")
    raise ValueError(f"Unsupported mode: {mode}")

async def show_resources(client: Client) -> None:

    # If an MCP server exposes multiple resources,
    # use list_resources() to discover them
    resources = await client.list_resources()

    print("\nEXAMPLE C: Reading resources from MCP server")
    for resource in resources:
        print(f" name: {resource.name}")
        print(f" description: {resource.description}")
        print(f" uri: {resource.uri}")

async def show_prompts(client: Client) -> None:

    # If an MCP server exposes multiple prompts,
    # use list_prompts() to discover them
    prompts = await client.list_prompts()

    print("\nEXAMPLE C: Reading prompts from MCP server")
    for prompt in prompts:
        print(f"Name: {prompt.name}")
        print(f"Description: {prompt.description}")
        print(f"Arguments: {prompt.arguments}")

    # use get_prompt() to fetch each one by name.
    # Important: This works directly for prompts that do not require arguments.
    for prompt in prompts:
        result = await client.get_prompt(prompt.name)

        print(f"\nPrinting prompt using the Pydantic objects directly:")
        print(f" Prompt: {prompt.name}")
        for message in result.messages:
            print(f" Role: {message.role}")
            if message.content.type == "text":
                print(f" Text: {message.content.text}")

    # If a prompt has required arguments, supply their values when calling get_prompt():
    # result = await client.session.get_prompt(
    #     "summarize",
    #     {"topic": "MCP architecture"}
    # )

    prompt = await client.session.get_prompt("explain_discovery")

    # To print all message fields as formatted JSON:
    print(f"\nPrint all message fields as formatted JSON:")
    messages = prompt.model_dump(by_alias=True, exclude_none=True).get(
        "messages", [])

    print(f"{json.dumps(messages, indent=2, ensure_ascii=False)}")

    # To print only the text values from messages:
    print(f"Print only the text values from messages:")
    for message in messages:
        role = message.get("role", "")
        if role:
            print(f" Role: {role}")

        content = message.get("content", {})

        if content.get("type") == "text":
            print(f" Text: {content.get("text")}")

async def show_client_request_metadata(client: Client) -> None:
    """Example B: call a custom tool to inspect this request's client metadata."""
    # This tools/call does NOT perform discovery. The server tool simply reads
    # the protocol version and client capabilities attached to this request.
    observed = (await client.call_tool("inspect_request_metadata")).data

    assert observed["protocol_version"] == "2026-07-28"
    assert "elicitation" in observed["client_capabilities"]

    print("\nEXAMPLE B: Client metadata on an ordinary tools/call request")
    print("tools/call -> inspect_request_metadata")
    print(
        "  io.modelcontextprotocol/protocolVersion: "
        f"{observed['protocol_version']}"
    )
    print("  io.modelcontextprotocol/clientCapabilities:")
    print(json.dumps(observed["client_capabilities"], indent=4))
    print("\nVerified: the client advertised optional elicitation support.")

async def show_server_discovery(client: Client) -> None:
    """Example A: read server/discover and list tools; do not call any tool."""
    # FastMCP already sent server/discover when entering `async with Client(...)`.
    # By the time execution enters async with, FastMCP has performed discovery
    # automatically by sending server/discover.

    # Calling client.session.discover() again returns the stored result
    # rather than sending another request.
    discovery = await client.session.discover()
    server_capabilities = discovery.capabilities.model_dump(
        by_alias=True,
        exclude_none=True,
    )
    print("\nEXAMPLE A: Explicit Server discovery")
    print(f"  supported versions: {discovery.supported_versions}")
    print(f"  server capabilities: {sorted(server_capabilities)}")

    # Reading discover_result does not make another MCP request.
    discovery = client.session.discover_result
    assert discovery is not None, "Expected server/discover negotiation"

    server_capabilities = discovery.capabilities.model_dump(
        by_alias=True,
        exclude_none=True,
    )

    print("\nEXAMPLE A: Reading automatic Server discovery result")
    print("server/discover response (already obtained during connection)")
    print(f"  supported versions: {discovery.supported_versions}")
    print(f"  server capabilities: {sorted(server_capabilities)}")

    # tools/list enumerates individual tools. It is not a tools/call invocation.
    tools = await client.list_tools()
    print("\ntools/list response")
    for tool in tools:
        print(f"  Name: {tool.name}")
        print(f"  Description: {tool.description}")
        print(f"  Input schema: {tool.input_schema}")

async def inspect(transport_name: str, example: str) -> None:
    async with Client(
            transport=client_source(transport_name),
            name="lesson-1-client",
            elicitation_handler=decline_elicitation,
    ) as client:
        # Automatic protocol negotiation occurs here, before either example.
        assert client.protocol_version == "2026-07-28"
        print(f"Transport: {transport_name}")

        if example in ("discovery", "all"):
            await show_server_discovery(client)
        if example in ("metadata", "all"):
            await show_client_request_metadata(client)
        if example in ("prompts", "all"):
            await show_prompts(client)
        if example in ("resources", "all"):
            await show_resources(client)


if __name__ == "__main__":
    choices = ["discovery", "metadata", "prompts", "resources", "all"],

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transport",
        choices=["in-memory", "stdio", "http"],
        required=True,
    )
    parser.add_argument(
        "--example",
        choices=["discovery", "metadata", "prompts", "resources", "all"],
        default="all",
        help="Run server discovery, client metadata inspection, or both (default).",
    )
    args = parser.parse_args()
    asyncio.run(inspect(args.transport, args.example))
