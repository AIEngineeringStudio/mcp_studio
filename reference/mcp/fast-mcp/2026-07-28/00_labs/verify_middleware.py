"""Verify FastMCP middleware ordering around an unchanged tool contract."""

import asyncio

from fastmcp import Client, FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext


events: list[str] = []


class AuditMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        events.append("before tools/call")
        result = await call_next(context)
        events.append("after tools/call")
        return result


mcp = FastMCP("Middleware exercise")
mcp.add_middleware(AuditMiddleware())


@mcp.tool
def get_ticket(ticket_id: str) -> dict[str, str]:
    """Return one synthetic ticket."""
    events.append("tool handler")
    return {"ticket_id": ticket_id, "status": "open"}


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        before_schema = next(tool for tool in tools if tool.name == "get_ticket")
        result = await client.call_tool("get_ticket", {"ticket_id": "T-100"})
        tools = await client.list_tools()
        after_schema = next(tool for tool in tools if tool.name == "get_ticket")

    assert result.data["status"] == "open"
    assert before_schema.input_schema == after_schema.input_schema
    assert events == ["before tools/call", "tool handler", "after tools/call"]
    print("middleware order: before -> tool handler -> after")
    print("tool schema and client call stayed unchanged")


if __name__ == "__main__":
    asyncio.run(main())
