"""Synthetic ticket service. No LLM, external API, database, or secrets."""
import argparse
import json
from fastmcp import FastMCP

mcp = FastMCP("Ticket learning service")
TICKETS = {
    "T-100": {"id": "T-100", "title": "Cannot sign in", "status": "open"},
    "T-101": {"id": "T-101", "title": "Update contact address", "status": "closed"},
}


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true")
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=8765)
    else:
        mcp.run(transport="stdio")
