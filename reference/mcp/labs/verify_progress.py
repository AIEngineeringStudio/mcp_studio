"""Verify request-scoped progress and cooperative cancellation."""

import asyncio

from fastmcp import Client, Context, FastMCP


mcp = FastMCP("Progress exercise")
cleanup_finished = asyncio.Event()


@mcp.tool
async def process_records(count: int, delay_seconds: float, ctx: Context) -> int:
    """Process records while reporting monotonic progress."""
    try:
        for index in range(1, count + 1):
            await asyncio.sleep(delay_seconds)
            await ctx.report_progress(index, count, f"processed {index}")
        return count
    finally:
        cleanup_finished.set()


async def main() -> None:
    progress: list[tuple[float, float | None, str | None]] = []

    async def record_progress(
        current: float,
        total: float | None,
        message: str | None,
    ) -> None:
        progress.append((current, total, message))

    async with Client(mcp) as client:
        result = await client.call_tool(
            "process_records",
            {"count": 3, "delay_seconds": 0.0},
            progress_handler=record_progress,
        )
        assert result.data == 3
        assert [item[0] for item in progress] == [1, 2, 3]

        cleanup_finished.clear()
        first_progress = asyncio.Event()

        async def cancel_after_first(
            _current: float,
            _total: float | None,
            _message: str | None,
        ) -> None:
            first_progress.set()

        call = asyncio.create_task(
            client.call_tool(
                "process_records",
                {"count": 100, "delay_seconds": 0.01},
                progress_handler=cancel_after_first,
            )
        )
        await asyncio.wait_for(first_progress.wait(), timeout=2)
        call.cancel()
        try:
            await call
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("Cancelled call returned normally")
        await asyncio.wait_for(cleanup_finished.wait(), timeout=2)

    print("progress: received monotonic updates [1, 2, 3]")
    print("cancellation: server cleanup ran and no normal result was returned")


if __name__ == "__main__":
    asyncio.run(main())
