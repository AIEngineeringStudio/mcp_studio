"""Ticket learning service implemented with the official MCP Python SDK 2.3.0."""

import argparse
import json

from mcp.server import MCPServer

TICKETS = {
    "T-100": {"id": "T-100", "title": "Cannot sign in", "status": "open"},
    "T-101": {
        "id": "T-101",
        "title": "Update contact address",
        "status": "closed",
    },
}

mcp = MCPServer("Ticket learning service")


def lookup_ticket(ticket_id: str) -> dict:
    """Domain function; deliberately independent of the protocol."""
    if ticket_id not in TICKETS:
        raise ValueError("Unknown ticket")
    return dict(TICKETS[ticket_id])


@mcp.tool()
def get_ticket(ticket_id: str) -> dict:
    """Read a synthetic support ticket by ID. Does not change the ticket."""
    return lookup_ticket(ticket_id)


@mcp.resource("tickets://closed")
def closed_tickets_resource() -> list[dict]:
    """Provide one resource so discovery can advertise resource support."""
    return [TICKETS["T-101"]]


@mcp.resource("ticket://{ticket_id}")
def ticket_resource_template(ticket_id: str) -> str:
    """Read a synthetic ticket as JSON text."""
    return json.dumps(lookup_ticket(ticket_id))


@mcp.prompt()
def summarize_ticket(ticket_id: str) -> str:
    """Prepare instructions; fetching a prompt does not run a model."""
    return (
        f"Summarize ticket {ticket_id} using the provided ticket data. "
        "State its status and distinguish facts from missing information."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "http"], required=True)
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(
            transport="streamable-http",
            host="127.0.0.1",
            port=8000,
            path="/mcp",
        )
