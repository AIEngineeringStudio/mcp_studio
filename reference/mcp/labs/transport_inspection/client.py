"""Run the same MCP 2026-07-28 inspection through three transports."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult
from fastmcp.client.transports import (
    StdioTransport,
    StreamableHttpTransport,
)
from server import mcp


async def decline_elicitation(
        _message: str,
        _response_type: type[Any] | None,
        _params: Any,
        _context: Any,
) -> ElicitResult:
    """Register elicitation support without asking for real user input."""
    return ElicitResult(action="decline")


def client_source(mode: str) -> Any:
    """Choose transport while keeping the inspection logic unchanged."""
    if mode == "in-memory":
        return mcp
    if mode == "stdio":
        return StdioTransport(
            command=sys.executable,
            args=[
                str(Path(__file__).resolve().with_name("server.py")),
                "--transport",
                "stdio",
            ],
        )
    if mode == "http":
        return StreamableHttpTransport(url="http://127.0.0.1:8000/mcp")
    raise ValueError(f"Unsupported mode: {mode}")


async def inspect(transport_name: str) -> None:
    async with Client(
            transport=client_source(transport_name),
            name="lesson-1-client",
            elicitation_handler=decline_elicitation,
    ) as client:
        assert client.protocol_version == "2026-07-28"

        discovery = client.session.discover_result
        assert discovery is not None, "Expected server/discover negotiation"

        server_capabilities = discovery.capabilities.model_dump(
            by_alias=True,
            exclude_none=True,
        )

        observed = (
            await client.call_tool("inspect_request_metadata")
        ).data

        assert observed["protocol_version"] == "2026-07-28"
        assert "elicitation" in observed["client_capabilities"]

        print(f"Transport: {transport_name}")
        print("server/discover response")
        print(f"  supported versions: {discovery.supported_versions}")
        print(f"  server capabilities: {sorted(server_capabilities)}")

        # Discover available tools
        tools = await client.list_tools()

        print("\ntools/list response")
        for tool in tools:
            print(f"  Name: {tool.name}")
            print(f"  Description: {tool.description}")
            print(f"  Input schema: {tool.input_schema}")

        print("\ntools/call metadata observed by the server")
        print(
            "  io.modelcontextprotocol/protocolVersion: "
            f"{observed['protocol_version']}"
        )
        print("  io.modelcontextprotocol/clientCapabilities:")
        print(json.dumps(observed["client_capabilities"], indent=4))

        print(
            "\nVerified: the client advertised optional elicitation support.")


if __name__ == "__main__":
    choices = ["in-memory", "stdio", "http"]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport",
        choices=choices,
        # choices restricts the value to the three supported transports.
        required=True,
        # required=True ensures the user provides --transport.
    )
    args = parser.parse_args()

    asyncio.run(inspect(args.transport))
