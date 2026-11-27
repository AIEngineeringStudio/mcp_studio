"""Run focused checks for MCP tools, resources, or prompts."""

import argparse
import asyncio
import json
import sys

from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client import StdioTransport
from fastmcp.client.transports import StreamableHttpTransport

from server import mcp


async def verify_prompts(client: Client) -> None:
    # list_prompts() - Discover resources exposed by the MCP server
    prompts = await client.list_prompts()
    assert "summarize_ticket" in {prompt.name for prompt in prompts}
    print("\nListing prompts from MCP server")
    for prompt in prompts:
        print(f"Name: {prompt.name}")
        print(f"Description: {prompt.description}")
        print(f"Arguments: {prompt.arguments}")
        print(f"-------------------------------")

    # # get_prompt() - Read a prompt by name.
    # Important: This works directly for prompts that do not require arguments.
    for prompt in prompts:
        result = await client.get_prompt(
            prompt.name,
            {"ticket_id": "T-100"}
        )
        print(f"\nReading prompt: {prompt.name}")
        for message in result.messages:
            print(f" Role: {message.role}")
            if message.content.type == "text":
                print(f" Text: {message.content.text}")
                print(f"-------------------------------")
    print("prompts: discovered summarize_ticket and rendered its message")
    print("prompts: no model was invoked")


async def verify_resources(client: Client) -> None:
    # list_resource_templates() - Discover resource templates exposed by the MCP server
    templates = await client.list_resource_templates()
    assert any("ticket_id" in str(item.uri_template) for item in templates)

    print("\nListing resource templates from MCP server")
    for index, template in enumerate(templates, start=1):
        print(f" Template: {index}")
        print(f" name: {template.name}")
        print(f" description: {template.description}")
        print(f" uri: {template.uri_template}")
        print(f"-------------------------------")

    # list_resources() - Discover resources exposed by the MCP server
    resources = await client.list_resources()

    print("\nListing resources from MCP server")
    for resource in resources:
        print(f" name: {resource.name}")
        print(f" description: {resource.description}")
        print(f" uri: {resource.uri}")
        print(f"-------------------------------")

    # read_resource() - Read a resource or resource template
    # Read a resource
    closed_tickets = await client.read_resource(f"tickets://closed")
    assert '"status": "closed"' in closed_tickets[0].text

    closed_tickets_resource = json.loads(closed_tickets[0].text)
    print(f"\nReading resource: tickets://closed")
    print(f" id: {closed_tickets_resource[0]["id"]}")
    print(f" title: {closed_tickets_resource[0]["title"]}")
    print(f" status: {closed_tickets_resource[0]["status"]}")
    print(f"-------------------------------")

    # Read resource template
    ticket_id = "T-100"
    contents = await client.read_resource(f"ticket://{ticket_id}")
    assert '"status": "open"' in contents[0].text

    ticket_resource = json.loads(contents[0].text)
    print(f"\nReading resource template: ticket://{ticket_resource["id"]}")
    print(f" id: {ticket_resource["id"]}")
    print(f" title: {ticket_resource["title"]}")
    print(f" status: {ticket_resource["status"]}")
    print(f"-------------------------------")


async def verify_tools(client: Client) -> None:
    # list_tools() - Discover tools exposed by the MCP server
    tools = await client.list_tools()

    get_ticket = next(tool for tool in tools if tool.name == "get_ticket")
    assert "ticket_id" in get_ticket.input_schema["required"]

    print("\nListing tools from MCP server")
    for tool in tools:
        print(f"Title: {tool.title}")
        print(f"Name: {tool.name}")
        print(f"Description: {tool.description}")
        print(f"Input Schema: "
              f"{json.dumps(tool.input_schema, sort_keys=True, indent=4)}")
        print(f"\nOutput Schema: "
              f"{json.dumps(tool.output_schema, sort_keys=True, indent=4)}")
        print(f"-------------------------------")

    # call_tool() - Execute tool exposed by the MCP server
    result = await client.call_tool(
        "get_ticket", {"ticket_id": "T-100"})
    assert result.data["status"] == "open"

    print("\nTool Result: \n",
          json.dumps(json.loads(result.content[0].text), indent=4))

    print("tools: discovered get_ticket and called it successfully")
    print(f"-------------------------------")


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
    print("\nExplicit Server discovery")
    print(f"  supported versions: {discovery.supported_versions}")
    print(f"  server capabilities: {sorted(server_capabilities)}")

    # Reading discover_result does not make another MCP request.
    discovery = client.session.discover_result
    assert discovery is not None, "Expected server/discover negotiation"

    server_capabilities = discovery.capabilities.model_dump(
        by_alias=True,
        exclude_none=True,
    )

    print("\nReading automatic Server discovery result")
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


def client_source(mode: str) -> Any:
    """Use the same examples with in-memory, stdio, or HTTP transport."""
    if mode == "in-memory":
        return mcp
    if mode == "stdio":
        return StdioTransport(
            command=sys.executable,
            args=[
                str(Path(__file__).resolve().resolve().with_name("server.py")),
                "--transport",
                "stdio",
            ],
        )
    if mode == "http":
        return StreamableHttpTransport(
            url="http://127.0.0.1:8000/mcp",
        )
    raise ValueError(f"Unsupported mode: {mode}")


async def main(transport_name: str, focus: str) -> None:
    async with Client(
            transport=client_source(transport_name),
            name="lesson-1-client"
    ) as client:
        if focus == "discovery":
            await show_server_discovery(client)
        elif focus == "tools":
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
        choices=["discovery", "tools", "resources", "prompts"],
        required=True,
    )
    args = parser.parse_args()
    asyncio.run(main(args.transport, args.focus))
