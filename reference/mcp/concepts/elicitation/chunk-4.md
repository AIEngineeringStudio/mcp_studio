# MCP Server with Streamable HTTP Transport

## Chunk 4 of 8 — §05. Basic Python Example

**Version boundary:**

> The protocol target is MCP `2025-11-25`. The example deliberately uses the
> official Python SDK v1 maintenance line because its `ClientSession.initialize()`
> flow maps directly to that protocol revision.

**Learning outcome:**

> Run one MCP server and one MCP client over Streamable HTTP, observe progress
> notifications, and receive one final tool result.

## §05. Concept Exercise

This exercise is intentionally small. It needs no model account, database,
Docker, reverse proxy, `.env` file, or API key.

The same files and commands work on Intel and Apple Silicon Macs. They use pure
Python packages and bind only to the local loopback interface.

### Dependency choice

The example pins `mcp[cli]==1.29.1`. That is the v1 maintenance line documented
for initialization-era MCP. The current SDK major version is newer, but mixing
its different high-level API into this historical protocol lesson would obscure
the transport mechanics.

**Checked:** 2026-11-17 against the official Python SDK v1 documentation and
release history.

### Project layout

Create these three files in a new exercise directory:

```text
streamable-basic/
├── pyproject.toml
├── server.py
└── client.py
```

### `pyproject.toml`

```toml
[project]
name = "streamable-basic"
version = "0.1.0"
requires-python = ">=3.11,<3.15"
dependencies = ["mcp[cli]==1.29.1"]

[tool.uv]
package = false
```

The exact dependency pin makes the exercise reproducible. If you deliberately
migrate to SDK v2, follow its migration guide rather than changing only this
number.

### `server.py`

```python
import asyncio

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession


mcp = FastMCP("Progress learning server")


@mcp.tool()
async def process_records(
    count: int,
    ctx: Context[ServerSession, None],
) -> dict[str, int]:
    """Process synthetic records and report progress."""
    if count < 1 or count > 20:
        raise ValueError("count must be between 1 and 20")

    for completed in range(1, count + 1):
        await asyncio.sleep(0.05)
        await ctx.report_progress(
            progress=completed,
            total=count,
            message=f"Processed {completed} of {count}",
        )

    return {"processed": count}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

The tool sends protocol progress notifications. It does not `yield` partial
tool results. Its returned dictionary becomes the one final `CallToolResult`.

### `client.py`

```python
import asyncio

from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client


async def show_progress(
    progress: float,
    total: float | None,
    message: str | None,
) -> None:
    total_text = "?" if total is None else str(total)
    print(f"progress: {progress}/{total_text} — {message or ''}")


async def main() -> None:
    endpoint = "http://127.0.0.1:8000/mcp"

    async with streamable_http_client(endpoint) as (
        read_stream,
        write_stream,
        _get_session_id,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            print(f"protocol: {initialized.protocolVersion}")

            tools = await session.list_tools()
            print(f"tools: {[tool.name for tool in tools.tools]}")

            result = await session.call_tool(
                "process_records",
                arguments={"count": 5},
                progress_callback=show_progress,
            )

            if result.isError:
                raise RuntimeError("tool reported an error")

            for block in result.content:
                if isinstance(block, types.TextContent):
                    print(f"final content: {block.text}")

            print(f"structured result: {result.structuredContent}")


if __name__ == "__main__":
    asyncio.run(main())
```

Passing `progress_callback` causes the SDK to place a `progressToken` in the
tool request. The SDK routes matching `notifications/progress` messages to the
callback.

## Run the Exercise

From the `streamable-basic` directory, install the exact dependency:

```bash
uv sync
```

Start the server in terminal 1:

```bash
uv run python server.py
```

Run the client in terminal 2:

```bash
uv run python client.py
```

Stop the server with `Ctrl-C` after the client finishes.

### Expected shape of the output

Exact formatting can vary, but the important sequence is:

```text
protocol: 2025-11-25
tools: ['process_records']
progress: 1.0/5.0 — Processed 1 of 5
progress: 2.0/5.0 — Processed 2 of 5
progress: 3.0/5.0 — Processed 3 of 5
progress: 4.0/5.0 — Processed 4 of 5
progress: 5.0/5.0 — Processed 5 of 5
final content: {"processed":5}
structured result: {'processed': 5}
```

The SDK can serialize the final result in both text and structured forms. The
essential observation is that progress arrives before one final result.

## Trace the Mechanism

```text
client.py                                          server.py
   |--- initialize ----------------------------------->|
   |<-- InitializeResult: 2025-11-25 -----------------|
   |--- notifications/initialized ------------------->|
   |                                                   |
   |--- tools/list ----------------------------------->|
   |<-- process_records definition -------------------|
   |                                                   |
   |--- tools/call + progressToken ------------------->|
   |<== notifications/progress: 1/5 ==================|
   |<== notifications/progress: 2/5 ==================|
   |<== notifications/progress: 3/5 ==================|
   |<== notifications/progress: 4/5 ==================|
   |<== notifications/progress: 5/5 ==================|
   |<== one final tools/call response ================|
```

### What the SDK handles

The SDK handles:

- JSON-RPC IDs and message validation
- initialization and `notifications/initialized`
- optional session headers
- `MCP-Protocol-Version` headers
- SSE framing and parsing
- progress-token correlation
- final tool-result serialization

The tool function handles only its business logic and progress reporting.

## Deliberate Failure

Change the client argument to `{"count": 0}` and run it again. The server
rejects the invalid business input. This failure is different from:

- connection refused, where no server is listening;
- HTTP `404`, where the endpoint or session is unknown;
- a JSON-RPC protocol error, where the message itself is invalid;
- a transport interruption, where the final outcome may be unknown.

Do not automatically retry a side-effecting tool merely because the connection
failed. Application idempotency is a separate design requirement.

## What This Example Does Not Demonstrate

This concept exercise intentionally defers:

- elicitation and other server-initiated requests;
- authentication and authorization;
- TLS and reverse-proxy configuration;
- durable persistence;
- multiple workers and session affinity;
- cancellation and resumability testing;
- production configuration with `.env` and `pydantic-settings`.

Those additions solve different problems and should not be prerequisites for
understanding progress over Streamable HTTP.

## Common Incorrect Variants

**Returning a list of progress strings:**

> That sends progress only after the tool finishes. It is one final result, not
> progress notification delivery.

**Writing an async generator tool:**

> Python `yield` does not automatically define MCP partial-result semantics.
> Use `ctx.report_progress()` for protocol progress.

**Adding `[DONE]`:**

> MCP completion is the final JSON-RPC response. `[DONE]` is not part of the
> protocol.

**Setting `json_response=True`:**

> A one-object JSON response does not provide the request-scoped SSE channel
> needed for intermediate progress or server-initiated requests in this lesson.

## Summary

- The server exposes one tool through Streamable HTTP.
- The client initializes a `2025-11-25` session before normal operations.
- A progress callback opts the request into `notifications/progress`.
- Progress notifications are separate from the final tool result.
- The example uses no custom endpoints, chunk messages, or sentinels.
- The exact SDK dependency is pinned.

**Professional articulation:**

> “The tool reports progress through MCP notifications correlated by a progress
> token, then returns one final result. SSE carries those JSON-RPC messages; a
> Python generator is not the protocol contract.”

## Sources

- [Official Python SDK v1: Building servers](https://py.sdk.modelcontextprotocol.io/v1/server/)
- [Official Python SDK v1: Writing clients](https://py.sdk.modelcontextprotocol.io/v1/client/)
- [MCP `2025-11-25`: Progress](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/progress)
- [MCP `2025-11-25`: Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

## Next

Continue with [chunk 5: progress plus elicitation](chunk-5.md).
