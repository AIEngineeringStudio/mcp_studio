import asyncio
import sys

from fastmcp import Context

# Verification signals for sequential calls in this example. The in-memory
# client shares these objects; stdio/HTTP clients do not share server memory.
cancellation_seen = asyncio.Event()
cleanup_finished = asyncio.Event()


async def process_records(
        count: int, delay_seconds: float, ctx: Context
) -> str:
    """Process records while reporting monotonic progress."""
    count = max(1, min(count, 20))
    result = []
    # Reset the previous call's signals before starting this call's work.
    cancellation_seen.clear()
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
    except asyncio.CancelledError:
        # This is the server's observation, distinct from client cancellation.
        cancellation_seen.set()
        print(
            f"[CANCELLED] process_records: server caught CancelledError "
            f"({len(result)}/{count} records)",
            file=sys.stderr,
            flush=True,
        )
        raise
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
