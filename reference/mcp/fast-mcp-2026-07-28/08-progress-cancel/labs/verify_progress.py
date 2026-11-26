"""Run either the progress example or the cooperative cancellation example."""

import argparse
import asyncio
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport, StreamableHttpTransport

from server import mcp
from tools.process_records import cleanup_finished

SERVER_URL = "http://127.0.0.1:8000/mcp"
PROTOCOL_VERSION = "2026-07-28"
WAIT_SECONDS = 5


def client_source(mode: str) -> Any:
    """Use the same examples with in-memory, stdio, or HTTP transport."""
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
            keep_alive=False,
        )
    if mode == "http":
        return StreamableHttpTransport(url=SERVER_URL)
    raise ValueError(f"Unsupported mode: {mode}")


async def example_progress(client: Client) -> None:
    """Complete one call and verify its result and progress notifications."""
    progress_items: list[tuple[float, float | None, str | None]] = []

    async def record_progress(
            progress: float,
            total: float | None,
            message: str | None,
    ) -> None:
        progress_items.append((progress, total, message))
        print(f"[PROGRESS] {message}", flush=True)

    print("\n--- progress ---", flush=True)
    result = await client.call_tool(
        "process_records",
        {"count": 3, "delay_seconds": 0.0},
        progress_handler=record_progress,
        timeout=15,
    )
    assert result.data == "Returned full result [1, 2, 3] with 3 chunks successfully."
    assert [item[0] for item in progress_items] == [1, 2, 3]
    print(f"[RESULT] {result.data}")
    print("progress: received monotonic updates [1, 2, 3]", flush=True)


async def main(transport_name: str, example_name: str) -> None:
    async with Client(
            transport=client_source(transport_name),
            name=f"verify-{example_name}-client",
            init_timeout=10,
    ) as client:
        print(f"Transport: {transport_name}", flush=True)
        if client.protocol_version != PROTOCOL_VERSION:
            raise RuntimeError(
                f"Expected {PROTOCOL_VERSION}, "
                f"received {client.protocol_version}"
            )
        print(f"Protocol: {client.protocol_version}", flush=True)

        for tool in await client.list_tools():
            print(f"[TOOL] {tool.name}", flush=True)

        if example_name == "progress":
            await example_progress(client)
        else:
            raise ValueError(f"Unsupported example: {example_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transport",
        choices=["in-memory", "stdio", "http"],
        required=True,
    )
    parser.add_argument(
        "--example",
        choices=["progress"],
        required=True,
    )
    args = parser.parse_args()
    asyncio.run(main(args.transport, args.example))
