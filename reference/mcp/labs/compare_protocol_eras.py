"""Compare FastMCP's modern discovery path with its legacy handshake path."""

import asyncio

from fastmcp import Client, FastMCP


mcp = FastMCP("Dual-era exercise")


@mcp.tool
def echo(value: str) -> str:
    """Return the supplied value."""
    return value


async def main() -> None:
    async with Client(mcp, mode="auto") as modern:
        assert modern.protocol_version == "2026-07-28"
        assert modern.session.discover_result is not None
        assert modern.initialize_result is None
        print("modern: server/discover -> 2026-07-28; no initialize result")

    async with Client(mcp, mode="legacy") as legacy:
        assert legacy.protocol_version == "2025-11-25"
        assert legacy.session.discover_result is None
        assert legacy.initialize_result is not None
        print("legacy: initialize -> 2025-11-25; no discover result")


if __name__ == "__main__":
    asyncio.run(main())
