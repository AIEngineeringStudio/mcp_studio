"""Run focused checks for MCP tools, resources, or prompts (SDK 2.3.0)."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from server import mcp


async def verify_prompts(client: Client) -> None:
    prompts = (await client.list_prompts()).prompts
    assert "summarize_ticket" in {prompt.name for prompt in prompts}
    print("\nListing prompts from MCP server")
    for prompt in prompts:
        print(f"Name: {prompt.name}")
        print(f"Description: {prompt.description}")
        print(f"Arguments: {prompt.arguments}")
        print("-------------------------------")

    for prompt in prompts:
        result = await client.get_prompt(prompt.name, {"ticket_id": "T-100"})
        print(f"\nReading prompt: {prompt.name}")
        for message in result.messages:
            print(f" Role: {message.role}")
            if message.content.type == "text":
                print(f" Text: {message.content.text}")
                print("-------------------------------")
    print("prompts: discovered summarize_ticket and rendered its message")
    print("prompts: no model was invoked")


async def verify_resources(client: Client) -> None:
    templates = (await client.list_resource_templates()).resource_templates
    assert any("ticket_id" in str(item.uri_template) for item in templates)

    print("\nListing resource templates from MCP server")
    for index, template in enumerate(templates, start=1):
        print(f" Template: {index}")
        print(f" name: {template.name}")
        print(f" description: {template.description}")
        print(f" uri: {template.uri_template}")
        print("-------------------------------")

    resources = (await client.list_resources()).resources
    print("\nListing resources from MCP server")
    for resource in resources:
        print(f" name: {resource.name}")
        print(f" description: {resource.description}")
        print(f" uri: {resource.uri}")
        print("-------------------------------")

    closed_contents = await client.read_resource("tickets://closed")
    assert '"status": "closed"' in closed_contents.contents[0].text
    closed_tickets = json.loads(closed_contents.contents[0].text)
    print("\nReading resource: tickets://closed")
    print(f" id: {closed_tickets[0]['id']}")
    print(f" title: {closed_tickets[0]['title']}")
    print(f" status: {closed_tickets[0]['status']}")
    print("-------------------------------")

    ticket_id = "T-100"
    contents = await client.read_resource(f"ticket://{ticket_id}")
    assert '"status": "open"' in contents.contents[0].text
    ticket = json.loads(contents.contents[0].text)
    print(f"\nReading resource template: ticket://{ticket['id']}")
    print(f" id: {ticket['id']}")
    print(f" title: {ticket['title']}")
    print(f" status: {ticket['status']}")
    print("-------------------------------")


async def verify_tools(client: Client) -> None:
    tools = (await client.list_tools()).tools
    get_ticket = next(tool for tool in tools if tool.name == "get_ticket")
    assert "ticket_id" in get_ticket.input_schema["required"]

    print("\nListing tools from MCP server")
    for tool in tools:
        print(f"Title: {tool.title}")
        print(f"Name: {tool.name}")
        print(f"Description: {tool.description}")
        print(f"Input Schema: {json.dumps(tool.input_schema, sort_keys=True, indent=4)}")
        print(f"\nOutput Schema: {json.dumps(tool.output_schema, sort_keys=True, indent=4)}")
        print("-------------------------------")

    result = await client.call_tool("get_ticket", {"ticket_id": "T-100"})
    assert not result.is_error
    ticket = result.structured_content.get("result", result.structured_content)
    assert ticket["status"] == "open"
    print("\nTool Result: \n", json.dumps(ticket, indent=4))
    print("tools: discovered get_ticket and called it successfully")
    print("-------------------------------")


async def show_server_discovery(client: Client) -> None:
    # The SDK performs discovery when the Client context is entered.
    discovery = await client.session.discover()
    server_capabilities = discovery.capabilities.model_dump(
        by_alias=True,
        exclude_none=True,
    )
    print("\nServer discovery")
    print(f"  supported versions: {discovery.supported_versions}")
    print(f"  server capabilities: {sorted(server_capabilities)}")

    # Reading discover_result shows the same cached negotiation result.
    discovery = client.session.discover_result
    assert discovery is not None, "Expected server/discover negotiation"
    server_capabilities = discovery.capabilities.model_dump(
        by_alias=True,
        exclude_none=True,
    )
    print("\nReading automatic server discovery result")
    print("server/discover response (already obtained during connection)")
    print(f"  supported versions: {discovery.supported_versions}")
    print(f"  server capabilities: {sorted(server_capabilities)}")

    tools = (await client.list_tools()).tools
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
        return StdioServerParameters(
            command=sys.executable,
            args=[str(Path(__file__).resolve().with_name("server.py")), "--transport", "stdio"],
        )
    if mode == "http":
        return "http://127.0.0.1:8000/mcp"
    raise ValueError(f"Unsupported mode: {mode}")


async def main(transport_name: str, focus: str) -> None:
    async with Client(client_source(transport_name)) as client:
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
    parser.add_argument("--transport", choices=["in-memory", "stdio", "http"], required=True)
    parser.add_argument(
        "--focus",
        choices=["discovery", "tools", "resources", "prompts"],
        required=True,
    )
    args = parser.parse_args()
    asyncio.run(main(args.transport, args.focus))
