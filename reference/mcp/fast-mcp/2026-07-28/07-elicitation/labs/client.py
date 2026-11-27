"""Verify MRTR elicitation using MCP 2026-07-28."""

import argparse
import asyncio
import sys

from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult, ElicitRequestParams

from fastmcp.client.transports import (
    StdioTransport,
    StreamableHttpTransport,
)
from mcp.client.streamable_http import RequestContext

SERVER_URL = "http://127.0.0.1:8000/mcp"
PROTOCOL_VERSION = "2026-07-28"


# ── Transport selection ──────────────────────────

def client_source(mode: str) -> Any:
    if mode == "in-memory":
        from server import mcp

        return mcp

    if mode == "stdio":
        return StdioTransport(
            command=sys.executable,
            args=[
                str(
                    Path(__file__).resolve()
                    .with_name("server.py")
                ),
                "--transport",
                "stdio",
            ],
            keep_alive=False,
        )

    if mode == "http":
        return StreamableHttpTransport(
            url=SERVER_URL,
        )

    raise ValueError(f"Unsupported mode: {mode}")


# ── Progress handler ────────────────────────────

async def progress_handler(
        progress: float,
        total: float | None,
        message: str | None,
) -> None:
    print(f"[PROGRESS] {message}", flush=True)


# ── Elicitation handler ─────────────────────────

async def elicitation_handler(
        message: str,
        response_type: type | None,
        params: ElicitRequestParams,
        context: RequestContext
) -> ElicitResult | object:
    """
        Handle server requests for user input.

        Args:
            message: The prompt to display to the user
            response_type: Python dataclass type for form responses (None for URL requests or empty schemas)
            params: Original MCP elicitation parameters
            context: Request context with metadata

        Returns:
            - Data directly (implicitly accepts the elicitation)
            - ElicitResult for explicit control over the action
        """
    print(f"\n[ELICIT] {message}")

    # This example asks for a form with a batch_size field.
    if response_type is None:
        raise ValueError("This example expects a batch_size form.")

    while True:
        choice = await asyncio.to_thread(
            input,
            "Batch size (0-10), [d] decline, [c] dismiss: ",
        )
        choice = choice.strip().lower()

        if choice == "d":
            print("[REPLY] explicitly declined to provide a batch size")
            return ElicitResult(action="decline")

        if choice == "c":
            print("[REPLY] dismissed the question without a decision")
            return ElicitResult(action="cancel")

        try:
            batch_size = int(choice)
        except ValueError:
            print("Enter 0-10, d, or c.")
            continue

        if not 0 <= batch_size <= 10:
            print("Enter an integer between 0 and 10.")
            continue

        print(f"[REPLY] accepted batch_size={batch_size}")
        return ElicitResult(
            action="accept",
            content=response_type(batch_size=batch_size),
        )


# ── Tool invocation ─────────────────────────────

async def run_elicitation_example(
        client: Client,
) -> None:
    result = await client.call_tool(
        "bidirectional_batch",
        arguments={
            "initial_batch_size": 4,
        },
    )

    print(f"\n[RESULT] {result.content[0].text}")


# ── Main ────────────────────────────────────────

async def main(
        transport_name: str,
        example_name: str,
) -> None:
    async with Client(
            transport=client_source(transport_name),
            name=f"verify-{example_name}-client",
            mode="auto",
            init_timeout=10,
            progress_handler=progress_handler,
            elicitation_handler=elicitation_handler,
    ) as client:

        print(f"Transport: {transport_name}")

        if client.protocol_version != PROTOCOL_VERSION:
            raise RuntimeError(
                f"Expected {PROTOCOL_VERSION}, "
                f"received {client.protocol_version}"
            )

        print(f"Protocol: {client.protocol_version}")

        for tool in await client.list_tools():
            print(f"[TOOL] {tool.name}")

        if example_name == "elicitation":
            await run_elicitation_example(client)

        else:
            raise ValueError(
                f"Unsupported example: {example_name}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--transport",
        choices=["in-memory", "stdio", "http"],
        required=True,
    )

    parser.add_argument(
        "--example",
        choices=["elicitation"],
        required=True,
    )

    args = parser.parse_args()

    asyncio.run(
        main(args.transport, args.example)
    )
