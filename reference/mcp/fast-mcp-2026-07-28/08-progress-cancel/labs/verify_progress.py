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
from tools.process_records import cancellation_seen, cleanup_finished

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


async def cancel_call(call: asyncio.Task[Any]) -> bool:
    """Cancel from an async user-action handler on the call's event loop.

    Return True if the client task ends cancelled, or False if it returns
    normally (already finished, or cancellation was suppressed). Tool failures
    propagate to the caller. This does not verify remote server cleanup.

    This function has no dependency on progress notifications or test timing.
    """
    if call.done():
        print("[CANCEL] Call already finished; observing its outcome", flush=True)
    else:
        print("[CANCEL] Cancellation requested; cancelling the call", flush=True)
        call.cancel()

    try:
        await call
    except asyncio.CancelledError:
        print("cancellation: client call raised CancelledError", flush=True)
        return True
    else:
        print("cancellation: client call returned normally", flush=True)
        return False


async def example_cancel(client: Client, transport_name: str) -> None:
    """Test cancel_call at a predictable point, then verify server cancellation.

    A real async Cancel handler invokes await cancel_call(call) directly.
    Only this test wrapper waits for progress and asserts cancellation.
    """
    # TEST SETUP: this CLIENT event selects a repeatable cancellation point.
    # Progress crosses stdio/HTTP before this callback sets the local event.
    first_progress = asyncio.Event()

    async def record_first_progress(
            current: float, total: float | None, message: str | None,
    ) -> None:
        print(f"[PROGRESS] {message}", flush=True)
        first_progress.set()

    print("\n--- cancel ---", flush=True)
    # The delay leaves time to cancel before the full call finishes.
    call = asyncio.create_task(
        client.call_tool(
            "process_records",
            {"count": 20, "delay_seconds": 0.5},
            progress_handler=record_first_progress,
            timeout=15,
        )
    )
    try:
        # TEST TRIGGER: replace this wait with a user action in an application.
        await asyncio.wait_for(first_progress.wait(), timeout=WAIT_SECONDS)
        if call.done():
            # Surface a tool failure, or report that the test missed its window.
            await call
            raise AssertionError(
                "Tool finished before cancellation could be tested")

        print("[TEST] First progress received; invoking cancel_call", flush=True)

        # SHARED ACTION: the same function an async Cancel handler would invoke.
        was_cancelled = await cancel_call(call)

        # TEST EXPECTATION: normal completion is valid in an application, but
        # means this test did not observe the cancellation it was verifying.
        if not was_cancelled:
            raise AssertionError("Cancelled call returned normally")
    except TimeoutError:
        # If the call failed before reporting progress, surface that failure.
        if call.done():
            await call
        raise
    finally:
        # TEST TEARDOWN: stop unfinished work if setup or verification failed.
        if not call.done():
            call.cancel()
            with suppress(asyncio.CancelledError):
                await call

    # TEST VERIFICATION: the client task's CancelledError does not prove that
    # the server caught cancellation. These events live in server memory.
    if transport_name == "in-memory":
        # The tool clears both signals BEFORE first progress. Their set values
        # therefore belong to this call, not a previous sequential test call.
        await asyncio.wait_for(cancellation_seen.wait(), timeout=WAIT_SECONDS)
        print("cancellation: server caught CancelledError", flush=True)
        await asyncio.wait_for(cleanup_finished.wait(), timeout=WAIT_SECONDS)
        print("cleanup: server finally block verified via shared event",
              flush=True)
    else:
        # Importing these events here does NOT share them with another process.
        print(
            "server checks: shared-event verification skipped (separate process). "
            "Look for [CANCELLED] and [CLEANUP] on server stderr; use "
            "--transport in-memory to assert both events.",
            flush=True,
        )


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
        elif example_name == "cancel":
            await example_cancel(client, transport_name)
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
        choices=["progress", "cancel"],
        required=True,
    )
    args = parser.parse_args()
    asyncio.run(main(args.transport, args.example))
