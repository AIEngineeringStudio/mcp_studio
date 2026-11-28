"""Run focused checks against the low-level MCP SDK server."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters


def client_source(mode: str):
    if mode == "in-memory":
        from server import server

        return server
    if mode == "stdio":
        return StdioServerParameters(
            command=sys.executable,
            args=[str(Path(__file__).resolve().with_name("server.py")), "--transport", "stdio"],
        )
    if mode == "http":
        return "http://127.0.0.1:8000/mcp"
    raise ValueError(f"Unsupported mode: {mode}")


async def main(transport: str, focus: str) -> None:
    async with Client(client_source(transport)) as client:
        if focus == "discovery":
            discovery = await client.session.discover()
            print(f"Supported versions: {discovery.supported_versions}")
            print(
                "Server capabilities: ",
                sorted(discovery.capabilities.model_dump(exclude_none=True)),
            )
            return

        if focus == "tools":
            tools = (await client.list_tools()).tools
            for tool in tools:
                print(f"{tool.name}: {tool.description}")
                print(json.dumps(tool.input_schema, indent=2))
            result = await client.call_tool("get_ticket", {"ticket_id": "T-100"})
            print(json.dumps(result.structured_content, indent=2))
        elif focus == "resources":
            for resource in (await client.list_resources()).resources:
                print(f"{resource.name}: {resource.uri}")
            for template in (await client.list_resource_templates()).resource_templates:
                print(f"{template.name}: {template.uri_template}")
            for uri in ("tickets://closed", "ticket://T-100"):
                result = await client.read_resource(uri)
                print(f"{uri}: {result.contents[0].text}")
        elif focus == "prompts":
            prompts = (await client.list_prompts()).prompts
            for prompt in prompts:
                print(f"{prompt.name}: {prompt.description}")
                result = await client.get_prompt(
                    prompt.name,
                    {"ticket_id": "T-100"},
                )
                for message in result.messages:
                    print(f"{message.role}: {message.content.text}")


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
