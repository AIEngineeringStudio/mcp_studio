"""Demonstrate a modern server-owned model-provider boundary without an LLM."""

import asyncio
from typing import Protocol

from fastmcp import Client, FastMCP


class SummaryProvider(Protocol):
    async def summarize(self, text: str) -> str: ...


class FakeSummaryProvider:
    """Deterministic stand-in for a provider SDK in this concept exercise."""

    async def summarize(self, text: str) -> str:
        return f"Summary: {text}"


provider: SummaryProvider = FakeSummaryProvider()
mcp = FastMCP("Server-owned inference")


@mcp.tool
async def summarize_ticket(ticket_id: str) -> str:
    """Summarize a synthetic ticket through the server-owned provider."""
    ticket_text = f"Ticket {ticket_id} is open."
    return await provider.summarize(ticket_text)


async def main() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "summarize_ticket",
            {"ticket_id": "T-100"},
        )
        assert result.data == "Summary: Ticket T-100 is open."
        assert client.session.server_capabilities is not None
        print("sampling replacement: the MCP server called its own provider")
        print("no sampling/createMessage request was sent to the client")


if __name__ == "__main__":
    asyncio.run(main())
