"""Mount one FastMCP server and verify the namespaced client contract."""

import asyncio

from fastmcp import Client, FastMCP


child = FastMCP("Ticket child")


@child.tool
def status(ticket_id: str) -> str:
    """Return a synthetic ticket status."""
    return f"{ticket_id}:open"


parent = FastMCP("Gateway parent")


@parent.tool
def health() -> str:
    """Return the parent server health state."""
    return "ok"


parent.mount(child, namespace="tickets")


async def main() -> None:
    async with Client(parent) as client:
        names = {tool.name for tool in await client.list_tools()}
        assert names == {"health", "tickets_status"}
        result = await client.call_tool(
            "tickets_status",
            {"ticket_id": "T-100"},
        )
        assert result.data == "T-100:open"
    print("composed catalog: ['health', 'tickets_status']")
    print("client used ordinary tools/list and tools/call")


if __name__ == "__main__":
    asyncio.run(main())
