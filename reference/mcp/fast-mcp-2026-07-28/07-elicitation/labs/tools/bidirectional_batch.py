import asyncio
import json

from fastmcp import Context

from mcp.types import (
    InputRequiredResult,
    ElicitRequest,
    ElicitRequestFormParams,
    ElicitResult,
)


async def bidirectional_batch(
        initial_batch_size: int,
        ctx: Context,
) -> str | InputRequiredResult:
    """Process batches with progress streaming and elicitation."""

    # 1. Verify protocol version

    if ctx.request_context.protocol_version != "2026-07-28":
        raise ValueError("MCP 2026-07-28 is required.")

    # 2. Initial invocation

    if ctx.request_state is None:

        batch_size = max(1, min(initial_batch_size, 10))
        total_processed = 0
        batch_number = 0

    # 3. Continuation invocation

    else:

        state = json.loads(ctx.request_state)

        total_processed = state["total_processed"]
        batch_number = state["batch_number"]

        responses = ctx.input_responses or {}
        answer = responses.get("next_batch")

        if not isinstance(answer, ElicitResult):
            raise ValueError("Missing elicitation response.")

        if answer.action != "accept":
            return f"Stopped. Total rows processed: {total_processed}"

        batch_size = (answer.content or {}).get("batch_size")

        if type(batch_size) is not int or not 0 <= batch_size <= 10:
            raise ValueError("Batch size must be between 0 and 10.")

        if batch_size == 0:
            return f"Total rows processed: {total_processed}"

    # 4. Process one batch

    batch_number += 1

    for row in range(1, batch_size + 1):
        await asyncio.sleep(0.2)

        total_processed += 1

        await ctx.report_progress(
            progress=total_processed,
            total=None,
            message=(
                f"batch {batch_number}, "
                f"row {row}/{batch_size}, "
                f"total={total_processed}"
            ),
        )

    # 5. Construct elicitation request

    elicitation = ElicitRequest(
        method="elicitation/create",
        params=ElicitRequestFormParams(
            message=(
                f"Processed {total_processed} rows. "
                "Enter the next batch size (1-10), "
                "or 0 to stop."
            ),
            requested_schema={
                "type": "object",
                "properties": {
                    "batch_size": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 10,
                    }
                },
                "required": ["batch_size"],
            },
        ),
    )

    # 6. Preserve execution state

    state = json.dumps({
        "total_processed": total_processed,
        "batch_number": batch_number,
    })

    # 7. Return intermediate result

    return InputRequiredResult(
        result_type="input_required",
        input_requests={
            "next_batch": elicitation,
        },
        request_state=state,
    )
