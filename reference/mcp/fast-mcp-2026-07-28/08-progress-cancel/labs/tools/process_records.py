import asyncio
import sys

from fastmcp import Context

# A verification signal for sequential calls in this example.
# The in-memory client shares this object;
# stdio/HTTP clients do not share server memory.
cleanup_finished = asyncio.Event()


async def process_records(
        count: int, delay_seconds: float, ctx: Context
) -> str:
    """Process records while reporting monotonic progress."""
    count = max(1, min(count, 20))
    result = []
    # Reset the previous call's signal before starting this call's work.
    cleanup_finished.clear()
    try:
        for index in range(1, count + 1):
            await asyncio.sleep(delay_seconds)
            result.append(index)
            await ctx.report_progress(
                progress=index,
                total=count,
                message=f"update from server: fetched chunk {index}/{count}",
            )

        return f"Returned full result {result} with {count} chunks successfully."
    finally:
        # Release request-owned resources here, BEFORE signaling completion.
        # There are no real resources to release in this synthetic example.
        cleanup_finished.set()
        # stdout is reserved for MCP messages when using stdio.
        print(
            f"[CLEANUP] process_records: finally ran ({len(result)}/{count} records)",
            file=sys.stderr,
            flush=True,
        )
