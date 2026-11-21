# Lesson 8 — Progress and cancellation

## Outcome

After this lesson, you can correlate progress, cancel work correctly on stdio
and HTTP, and separate cancellation from rollback.

## Progress is opt-in and server-to-client

The client adds a unique `progressToken` to request metadata. The server may
then send `notifications/progress` for that operation.

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

The client cancels by closing the request's SSE response stream. The modern HTTP
binding does not send `notifications/cancelled`.

```
stdio: client notification -> server cancels work
HTTP:  response stream closes -> server cancels work
```

Cancellation is cooperative. Application code must propagate cancellation to
database queries, HTTP calls, queues, and other downstream work.

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

Progress belongs to one active request. Durable background work belongs to the
optional `io.modelcontextprotocol/tasks` extension. Do not confuse a progress
token with a durable task handle.

## FastMCP implementation

The client opts into progress by supplying a progress handler. FastMCP then
adds the progress token and delivers matching notifications to that handler.

```python
import asyncio

from fastmcp import Context, FastMCP

mcp = FastMCP("Progress exercise")


@mcp.tool
async def process_records(count: int, ctx: Context) -> int:
    try:
        for index in range(1, count + 1):
            await asyncio.sleep(0.01)
            await ctx.report_progress(index, count, f"processed {index}")
        return count
    finally:
        # Release request-owned resources here.
        pass
```

`finally` runs for success, failure, and cooperative cancellation. It releases
resources; it does not undo already committed business effects.

## Hands-on checkpoint

**Execution boundary:**

> In-memory MCP. It exercises real progress notifications and cancellation
> propagation without adding stdio or HTTP variables.

Run the focused progress and cancellation exercise from the repository root:

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python verify_progress.py
```

Expected output:

```
progress: received monotonic updates [1, 2, 3]
cancellation: server cleanup ran and no normal result was returned
```

The complete runnable exercise is
[`verify_progress.py`](../labs/verify_progress.py). It first completes a call
and records progress. It then cancels a second call after its first update and
verifies the handler's cleanup path.

For the transport-specific wire behavior, read:

- [`../concepts/12-progress-streaming.md`](../concepts/12-progress-streaming.md)
- [`../concepts/25-reliability.md`](../concepts/25-reliability.md)

**Say it professionally:**

> Progress is best-effort, request-scoped status reporting. Cancellation is a
> cooperative stop signal whose wire representation depends on the transport;
> it does not imply rollback of committed business effects.

## Official references

- [Progress](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)
- [Cancellation](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)
- [Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

