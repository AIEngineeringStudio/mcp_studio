"""Run focused checks for MCP tools, resources, or prompts."""

import argparse
import asyncio

from fastmcp import Client

from server import mcp


async def verify_tools(client: Client) -> None:
    tools = await client.list_tools()
    get_ticket = next(tool for tool in tools if tool.name == "get_ticket")
    assert "ticket_id" in get_ticket.input_schema["required"]
    result = await client.call_tool("get_ticket", {"ticket_id": "T-100"})
    assert result.data["status"] == "open"
    print("tools: discovered get_ticket and called it successfully")


async def verify_resources(client: Client) -> None:
    templates = await client.list_resource_templates()
    assert any("ticket_id" in str(item.uri_template) for item in templates)
    contents = await client.read_resource("ticket://T-100")
    assert '"status": "open"' in contents[0].text
    print("resources: discovered ticket://{ticket_id} and read ticket://T-100")


async def verify_prompts(client: Client) -> None:
    prompts = await client.list_prompts()
    assert "summarize_ticket" in {prompt.name for prompt in prompts}
    result = await client.get_prompt(
        "summarize_ticket",
        {"ticket_id": "T-100"},
    )
    text = result.messages[0].content.text
    assert "T-100" in text
    print("prompts: discovered summarize_ticket and rendered its message")
    print("prompts: no model was invoked")


async def main(focus: str) -> None:
    async with Client(mcp) as client:
        if focus == "tools":
            await verify_tools(client)
        elif focus == "resources":
            await verify_resources(client)
        else:
            await verify_prompts(client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("focus", choices=["tools", "resources", "prompts"])
    asyncio.run(main(parser.parse_args().focus))
