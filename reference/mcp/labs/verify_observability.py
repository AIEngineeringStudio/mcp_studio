"""Capture stdio-server diagnostics separately from MCP protocol messages."""

import asyncio
from pathlib import Path
import sys

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / ".uv-cache" / "lesson-09-stderr.log"


async def main() -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    LOG_PATH.write_text("")
    transport = StdioTransport(
        command=sys.executable,
        args=[str(ROOT / "logging_server.py")],
        cwd=str(ROOT),
        keep_alive=False,
        log_file=LOG_PATH,
    )
    try:
        async with Client(transport) as client:
            result = await client.call_tool("get_ticket", {"ticket_id": "T-100"})
            assert result.data["status"] == "open"
        diagnostics = LOG_PATH.read_text()
        assert "ticket_lookup_complete" in diagnostics
        assert "T-100" not in diagnostics
        print("tool result: {'ticket_id': 'T-100', 'status': 'open'}")
        print("stderr diagnostic: ticket_lookup_complete ... outcome=success")
        print("verified: diagnostics did not corrupt the stdio protocol")
    finally:
        LOG_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
