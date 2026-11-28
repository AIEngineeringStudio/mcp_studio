import asyncio

from mcp import Client
from mcp.client import ClientRequestContext

from mcp.types import (
    ElicitRequestParams,
    ElicitResult,
    ElicitRequestURLParams,
)

SERVER_URL = "http://127.0.0.1:8000/mcp"
PROTOCOL_VERSION = "2026-07-28"


async def on_progress(
        progress: float,
        total: float | None,
        message: str | None,
) -> None:
    print(
        f"[PROGRESS] {message}",
        flush=True,
    )


def create_elicitation_handler():
    # Deterministic demonstration:
    # First question: continue with 3 rows.
    # Second question: stop.

    decisions = iter([3, 0])

    async def on_elicit(
            context: ClientRequestContext,
            params: ElicitRequestParams,
    ) -> ElicitResult:
        if isinstance(params, ElicitRequestURLParams):
            return ElicitResult(action="decline")

        print(f"[ELICIT] {params.message}")

        batch_size = next(decisions, 0)

        print(f"[REPLY] batch_size={batch_size}")

        return ElicitResult(
            action="accept",
            content={"batch_size": batch_size},
        )

    return on_elicit


async def main():
    async with Client(
            SERVER_URL,
            mode="auto",
            elicitation_callback=create_elicitation_handler(),
            input_required_max_rounds=10,
    ) as client:

        # Confirm the actual negotiated protocol version.

        print(f"Protocol: {client.protocol_version}")

        if client.protocol_version != PROTOCOL_VERSION:
            raise RuntimeError(
                f"Expected MCP {PROTOCOL_VERSION}, "
                f"received {client.protocol_version}"
            )

        # ── Discover tools ──

        tools = await client.list_tools()

        print(
            "Tools:",
            [tool.name for tool in tools.tools],
        )

        # ── Tool 1 ──

        print("\n--- TOOL 1: stream_numbers ---")

        result = await client.call_tool(
            "stream_numbers",
            {"count": 5},
            progress_callback=on_progress,
        )

        if result.is_error:
            raise RuntimeError(result.content)

        print("[RESULT]", result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
