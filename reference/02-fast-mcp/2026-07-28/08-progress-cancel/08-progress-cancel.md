# Lesson 8 — Progress and cancellation

## Outcome

After this lesson, you can correlate progress, cancel work correctly on stdio
and HTTP, and separate cancellation from rollback.

## Progress is opt-in and server-to-client

The client adds a unique `progressToken` to request metadata. The server may
then send `notifications/progress` for that operation.

- One HTTP POST.
- Three progress notifications.
- One final JSON-RPC result.

```
┌─────────┐                         ┌─────────┐ 
│ CLIENT  │                         │ SERVER  │
└─────────┘                         └─────────┘ 
     |                                   |
     |--- POST: tool/call (count=5) ---->|
     |                                   | 
     |<-- SSE: progress 1/5 -------------|
     |                                   | 
     |<-- SSE: progress 2/5 -------------|
     |                                   | 
     |<-- SSE: progress 3/5 -------------|
     |                                   |
     |<-- SSE: Final tool result --------|
```

### Sample `notifications/progress`

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progressToken": "import-17",
    "progress": 50,
    "total": 100,
    "message": "Imported 50 records"
  }
}
```

In MCP `2026-07-28`, progress is **server-to-client only**. Client-to-server
progress notifications are removed.

```
JSON-RPC request ID  -> correlates request and final response
progressToken        -> correlates progress events with the operation
trace ID             -> correlates observability across services
```

Progress values must increase. `total` is optional and may change only in ways
that preserve meaningful progress. Do not use fluctuating telemetry such as CPU
percentage as the progress value.

### **How it works**

The client supplies a progress callback when calling the tool.
The SDK requests progress notifications and correlates them using a progress
token.

```python
result = await client.call_tool(
    "process_records",
    {"count": 3, "delay_seconds": 0.0},
    progress_handler=record_progress,
    timeout=15,
)
```

`ctx.report_progress()` publishes progress through the request's
response stream.

**Important distinction:** These are progress notifications, not partial tool
results. The actual tool result is returned once execution finishes.

## Progress is not streaming data

`notifications/progress` reports status. It does not replace the final result,
stream arbitrary records, or represent model-token streaming. The final result
is authoritative.

## Cancellation differs by transport

### stdio

The client sends `notifications/cancelled` with the request ID. The server
should stop cooperatively and must not send a normal response for that cancelled
request.

### Streamable HTTP

The client cancels by closing the request's SSE response stream.
The modern HTTP binding does not send `notifications/cancelled`.

```
stdio: client notification -> server cancels work
HTTP:  response stream closes -> server cancels work
```

**Cancellation is cooperative.** Application code must propagate
cancellation to `database queries`, `HTTP calls`, `queues`, and other downstream
work.

## Cancellation is not rollback

If a tool has already committed a side effect, cancelling the request does not
undo it. Design mutating operations with idempotency keys, transaction
boundaries, and status lookup.

```
request cancelled
      |
      +-- no commit yet -> stop safely
      |
      +-- commit happened -> report/lookup outcome; do not repeat blindly
```

Use `try/finally` or async context managers to release resources on success,
error, timeout, and cancellation. Do not catch cancellation and accidentally
continue as success.

## Progress and long-running tasks

Progress belongs to one active request.

Durable background work belongs to the optional `io.modelcontextprotocol/tasks`
extension. Do not confuse a progress token with a durable task handle.

## Architecture

```
Local machine
┌────────────────────┐
│ Python MCP Client  │
│                    │
│ Progress callback  │
└─────────┬──────────┘
          │
          │ Streamable HTTP
          │ POST /mcp
          │ SSE responses
          │
┌─────────┴──────────┐
│ Python MCP Server  │ :8000
│                    │
│ stream_numbers     │
└────────────────────┘
```

## FastMCP implementation

Use FastMCP for both the server and client.

```
Application
    |
FastMCP 4.x
    |
MCP Python SDK v2
    |
MCP 2026-07-28
    |
Streamable HTTP
```

### Project structure**

```
mcp-progress-cancel/
├── pyproject.toml
├── server.py
├── client.py
└── tools/
    ├── __init__.py
    └── process_records.py
```

### **pyproject.toml**

```toml
[project]
name = "mcp-progress-cancel"
version = "0.1.0"
description = "Small, synthetic examples for mcp-progress-cancel"
requires-python = ">=3.14,<3.15"

dependencies = [
    "fastmcp==4.2.0",
]

[tool.uv]
package = false
```

### MCP Tool

**tools/__init__.py**

```python
from .process_records import process_records
```

**tools/process_records.py**

```python
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
```

`finally` runs for success, failure, and cooperative cancellation. It releases
resources; it does not undo already committed business effects.

### MCP server

**server.py**

```python
import argparse

from fastmcp import FastMCP
from tools import process_records

mcp = FastMCP("Progress-exercise")

# Register tools
mcp.tool(process_records)

if __name__ == "__main__":
    choices = ["stdio", "http"]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport",
        choices=choices,
        required=True,
        # default="stdio",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(
            transport="http",
            host="127.0.0.1",
            port=8000,
            path="/mcp",
        )

```

### MCP Client

The client opts into progress by supplying a progress handler. FastMCP then
adds the progress token and delivers matching notifications to that handler.

**verify_progress.py**

```python
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
from tools import cleanup_finished

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


async def example_cancel(client: Client, transport_name: str) -> None:
    """Cancel an active call; verify cleanup through shared memory when possible."""
    # This event belongs to the CLIENT. Its callback and waiter share it even
    # with stdio/HTTP: the progress notification crosses the transport first.
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
        await asyncio.wait_for(first_progress.wait(), timeout=WAIT_SECONDS)
        if call.done():
            # Surface a tool failure, or report that cancellation was too late.
            await call
            raise AssertionError(
                "Tool finished before cancellation could be tested")

        print("[CANCEL] First progress received; cancelling the call",
              flush=True)
        call.cancel()
        try:
            await call
        except asyncio.CancelledError:
            print("cancellation: client call raised CancelledError",
                  flush=True)
        else:
            raise AssertionError("Cancelled call returned normally")
    except TimeoutError:
        # If the call failed before reporting progress, surface that failure.
        if call.done():
            await call
        raise
    finally:
        # Also stop the call if waiting for the first progress update times out.
        if not call.done():
            call.cancel()
            with suppress(asyncio.CancelledError):
                await call

    if transport_name == "in-memory":
        # The tool clears this event BEFORE sending any progress, then sets it
        # in finally. Receiving first_progress above prevents a stale-signal wait.
        await asyncio.wait_for(cleanup_finished.wait(), timeout=WAIT_SECONDS)
        print("cleanup: server finally block verified via shared event",
              flush=True)
    else:
        # Importing the event here does NOT share it with another process.
        print(
            "cleanup: shared-event check skipped (server is a separate process). "
            "Look for [CLEANUP] on server stderr; use --transport in-memory "
            "to verify cleanup with the event.",
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

```

#### Note:

| Output                            | Where it goes                 |
|-----------------------------------|-------------------------------|
| Server diagnostic prints and logs | `stderr`                      |
| Server MCP messages               | `stdout`, managed by the SDK  |
| Client diagnostic prints          | Client’s own `stdout` is fine |

The key is that **the client’s stdout and the server’s stdout are separate
streams**. The client reads MCP messages from the server’s stdout and sends MCP
messages into the server’s stdin. Ordinary text must stay out of those protocol
streams.

So your `verify_progress.py` client can use normal `print()`. Diagnostic prints
executed inside the stdio server—including its tool functions—should use
`stderr`.

## Hands-on checkpoint

The complete runnable exercise is
[`verify_progress.py`](labs/verify_progress.py). It first completes a call
and records progress. It then cancels a second call after its first update and
verifies the handler's cleanup path.

## **8. Run locally**

Run the focused progress and cancellation exercise from [labs](labs):

### Install dependencies:

```shell
uv sync
```

### Option 1: `in-memory` transport

#### Run `progress` example

```shell
uv run python verify_progress.py --transport in-memory --example progress
```

#### Run `cancel` example

```shell
uv run python verify_progress.py --transport in-memory --example cancel
```

### Option 2: `stdio` transport

#### Run `progress` example

```shell
uv run python verify_progress.py --transport stdio --example progress
```

#### Run `cancel` example

```shell
uv run python verify_progress.py --transport stdio --example cancel
```

### Option 3: `http` transport

#### Run `progress` example

**Terminal 1 — Start the server**

```shell
uv run server.py --transport http 
```

**Terminal 2 — Start the client**

```shell
uv run pythonverify_progress.py --transport http --example progress
```

#### Run `cancel` example

**Terminal 1 — Start the server**

```shell
uv run server.py --transport http 
```

**Terminal 2 — Start the client**

```shell
uv run verify_progress.py --transport stdio --example cancel
```

### **Expected output**

#### Progress

```
Transport: http
Protocol: 2026-07-28
[TOOL] process_records

--- progress ---
[PROGRESS] update from server: fetched chunk 1/3
[PROGRESS] update from server: fetched chunk 2/3
[PROGRESS] update from server: fetched chunk 3/3
[RESULT] Returned full result [1, 2, 3] with 3 chunks successfully.
progress: received monotonic updates [1, 2, 3]
```

#### Cancel

For the transport-specific wire behavior, read:

- [`12-progress-streaming.md`](../../../01-mcp-concepts/guides/12-progress-streaming.md)
- [`25-reliability.md`](../../../01-mcp-concepts/guides/25-reliability.md)

**Say it professionally:**

> Progress is best-effort, request-scoped status reporting. Cancellation is a
> cooperative stop signal whose wire representation depends on the transport;
> it does not imply rollback of committed business effects.

## Important differences

### MCP 2026-07-28 vs MCP 2025-07-25

The MCP specification released on July 28, 2026, introduces significant changes
that affect your original implementation.

| Component      | MCP 2026-07-28                   | MCP 2025-07-25    |
|----------------|----------------------------------|-------------------|
| Protocol state | Stateless protocol               | Stateful sessions |
| Initialization | `server/discover`                | `initialize()`    |
| Session ID     | N/A                              | `Mcp-Session-Id`  |
| Progress       | SSE notifications                | SSE notifications |
| HTTP routing   | `Mcp-Method`, `Mcp-Name` headers | Request body      |
| Python SDK     | v2                               | v1                |

### Low-level MCP SDK v2 vs FastMCP 4.x

| Feature           | Low-level MCP SDK v2            | FastMCP 4.x                 |
|-------------------|---------------------------------|-----------------------------|
| Server            | `Server`                        | `FastMCP`                   |
| Client            | `Client` from `mcp`             | `Client` from `fastmcp`     |
| Tool registration | Manual handlers                 | `@mcp.tool`                 |
| Input schema      | Manual JSON Schema              | Python type annotations     |
| Progress          | `ctx.session.report_progress()` | `ctx.report_progress()`     |
| MRTR              | Explicit protocol handling      | High-level MRTR APIs        |
| Streamable HTTP   | ASGI + Uvicorn                  | `mcp.run(transport="http")` |

## Official references

- [Progress](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)
- [Cancellation](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)
- [Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

