"""Inspect MCP 2026-07-28 discovery and per-request client metadata.
    FastMCP 4.2 server."""

import argparse
from typing import Any

from fastmcp import Context, FastMCP

mcp = FastMCP("Lesson 1 inspection server")


@mcp.tool
def inspect_request_metadata(ctx: Context) -> dict[str, Any]:
    """Return protocol metadata that the server received on this request."""
    capabilities = ctx.session.client_capabilities

    return {
        "protocol_version": ctx.session.protocol_version,
        "client_capabilities": (
            capabilities.model_dump(by_alias=True, exclude_none=True)
            if capabilities is not None
            else {}
        ),
    }


@mcp.resource("study://lesson-1")
def lesson_resource() -> str:
    """Provide one resource so discovery can advertise resource support."""
    return "MCP 2026-07-28 uses per-request protocol metadata."


@mcp.prompt
def explain_discovery() -> str:
    """Provide one prompt so discovery can advertise prompt support."""
    return "Explain why server/discover is optional rather than a handshake."


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
