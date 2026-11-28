"""Verify opaque-cursor consumption and MCP argument completion."""

import asyncio
import base64
import hashlib
import hmac

from fastmcp import Client, FastMCP
from mcp_types import PromptReference

TICKETS = ["T-100", "T-101",
           "T-200", "T-201", "T-202", "T-203", "T-204", "T-205",
           "T-300"]
CURSOR_KEY = b"lesson-only-key"


def encode_cursor(offset: int) -> str:
    payload = str(offset).encode()
    signature = hmac.new(CURSOR_KEY, payload, hashlib.sha256).digest()[:8]
    return base64.urlsafe_b64encode(payload + b"." + signature).decode()


def decode_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    raw = base64.urlsafe_b64decode(cursor.encode())
    payload, signature = raw.split(b".", maxsplit=1)
    expected = hmac.new(CURSOR_KEY, payload, hashlib.sha256).digest()[:8]
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid cursor")
    return int(payload)


def list_ticket_page(cursor: str | None, page_size: int = 2) -> dict:
    offset = decode_cursor(cursor)
    items = TICKETS[offset : offset + page_size]
    next_offset = offset + len(items)
    return {
        "items": items,
        "next_cursor": (
            encode_cursor(next_offset) if next_offset < len(TICKETS) else None
        ),
    }


mcp = FastMCP("Completion exercise")


@mcp.prompt
def triage_ticket(ticket_id: str) -> str:
    """Render a triage prompt for one ticket."""
    return f"Triage {ticket_id}."


@mcp.completion
def complete_ticket_id(ref, argument, _context):
    """Suggest authorized ticket IDs matching the typed prefix."""
    if isinstance(ref, PromptReference) and ref.name == "triage_ticket":
        if argument.name == "ticket_id":
            return [item for item in TICKETS if
                    item.startswith(argument.value)]
    return None


async def main() -> None:
    cursor = None
    collected: list[str] = []
    while True:
        page = list_ticket_page(cursor)
        collected.extend(page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert collected == TICKETS

    async with Client(mcp) as client:
        completion = await client.complete(
            PromptReference(name="triage_ticket"),
            {"name": "ticket_id", "value": "T-2"},
        )
        assert completion.values == ["T-200", "T-201", "T-202", "T-203",
                                     "T-204", "T-205"]

    print("pagination: followed opaque cursors and collected all five tickets")
    print(f"completion: T-2 -> {completion.values}")
    print("validation remains required for the final supplied argument")


if __name__ == "__main__":
    asyncio.run(main())
