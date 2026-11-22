"""Inspect MCP 2026-07-28 discovery and per-request client metadata.
    FastMCP 4.2 server."""

import argparse
import json

from fastmcp import FastMCP
from semantic_trace_server import SemanticTrace

TICKETS = {
    "T-100": {"id": "T-100", "title": "Cannot sign in", "status": "open"},
    "T-101": {"id": "T-101", "title": "Update contact address",
              "status": "closed"},
}

mcp = FastMCP("Ticket learning service")

# Register server-side semantic tracing
mcp.add_middleware(SemanticTrace())


def lookup_ticket(ticket_id: str) -> dict:
    """Domain function; deliberately independent of the protocol."""
    if ticket_id not in TICKETS:
        raise ValueError("Unknown ticket")
    return dict(TICKETS[ticket_id])


@mcp.tool
def get_ticket(ticket_id: str) -> dict:
    """Read a synthetic support ticket by ID. Does not change the ticket."""
    return lookup_ticket(ticket_id)


@mcp.resource("ticket://{ticket_id}")
def ticket_resource(ticket_id: str) -> str:
    """Read a synthetic ticket as JSON text."""
    return json.dumps(lookup_ticket(ticket_id))


@mcp.prompt
def summarize_ticket(ticket_id: str) -> str:
    """Prepare instructions; fetching a prompt does not run a model."""
    return (f"Summarize ticket {ticket_id} using the provided ticket data. "
            "State its status and distinguish facts from missing information.")


if __name__ == "__main__":
    choices = ["stdio", "http"]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport",
        choices=choices,
        required=True,
        # default="stdio",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(
            transport="http",
            host="127.0.0.1",
            port=8000,
            path="/mcp",
        )
