"""Use the same three component contracts across three execution boundaries."""
import argparse
import asyncio
from pathlib import Path
import sys
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from server import mcp


async def main(mode: str) -> None:
    if mode == "memory":
        target = mcp
    elif mode == "stdio":
        target = StdioTransport(
            command=sys.executable,
            args=[str(Path(__file__).with_name("server.py"))],
        )
    else:
        target = "http://127.0.0.1:8765/mcp"
    async with Client(target) as client:
        tools = await client.list_tools()
        assert client.protocol_version == "2026-07-28", client.protocol_version
        assert "get_ticket" in {tool.name for tool in tools}
        result = await client.call_tool("get_ticket", {"ticket_id": "T-100"})
        assert result.data["status"] == "open"
        resources = await client.read_resource("ticket://T-100")
        assert "Cannot sign in" in resources[0].text
        prompt = await client.get_prompt("summarize_ticket", {"ticket_id": "T-100"})
        assert "T-100" in prompt.messages[0].content.text
        print(f"{mode}: tool, resource, and prompt checks passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["memory", "stdio", "http"], default="memory", nargs="?")
    asyncio.run(main(parser.parse_args().mode))
