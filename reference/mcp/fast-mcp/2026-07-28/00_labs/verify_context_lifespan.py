"""Verify application-lifetime resources and request-scoped Context access."""

import asyncio

from fastmcp import Client, Context, FastMCP
from fastmcp.server.lifespan import lifespan


lifecycle: list[str] = []


@lifespan
async def app_lifespan(_server):
    lifecycle.append("startup")
    repository = {"T-100": "open"}
    yield {"repository": repository}
    lifecycle.append("shutdown")


mcp = FastMCP("Lifespan exercise", lifespan=app_lifespan)


@mcp.tool
def ticket_status(ticket_id: str, ctx: Context) -> str:
    """Read through an application-lifetime repository dependency."""
    repository = ctx.lifespan_context["repository"]
    return repository[ticket_id]


async def main() -> None:
    async with Client(mcp) as client:
        first = await client.call_tool("ticket_status", {"ticket_id": "T-100"})
        second = await client.call_tool("ticket_status", {"ticket_id": "T-100"})
        assert first.data == second.data == "open"
        assert lifecycle == ["startup"]
    assert lifecycle == ["startup", "shutdown"]
    print("lifespan: one startup served two requests, then one shutdown ran")
    print("tool schema: ticket_id is public; repository remains internal")


if __name__ == "__main__":
    asyncio.run(main())
