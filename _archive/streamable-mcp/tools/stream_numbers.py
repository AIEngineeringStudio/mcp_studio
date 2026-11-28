
import asyncio

from mcp.server import ServerRequestContext
from mcp.types import CallToolResult, TextContent


async def stream_numbers(
        count: int,
        ctx: ServerRequestContext,
) -> CallToolResult:
    count = max(1, min(count, 20))

    for i in range(1, count + 1):
        await ctx.session.report_progress(
            progress=i,
            total=count,
            message=f"chunk {i}/{count}",
        )

        await asyncio.sleep(0.3)

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=f"Streamed {count} chunks successfully.",
            )
        ]
    )