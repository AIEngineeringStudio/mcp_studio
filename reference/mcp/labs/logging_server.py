"""Small stdio server whose diagnostics are written only to stderr."""

import logging
import sys

from fastmcp import FastMCP


logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("ticket_lab")
mcp = FastMCP("Logging exercise")


@mcp.tool
def get_ticket(ticket_id: str) -> dict[str, str]:
    """Return a synthetic ticket and emit a safe operator log."""
    logger.info("ticket_lookup_complete tool=get_ticket outcome=success")
    return {"ticket_id": ticket_id, "status": "open"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
