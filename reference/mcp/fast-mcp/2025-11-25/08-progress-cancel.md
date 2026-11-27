# Lesson 8 — Progress + Cancellation

These two features answer complementary questions:

```
PROGRESS
"Is the request still doing useful work?"

CANCELLATION
"I no longer need this request. Stop doing work."
```

They form part of MCP's **request control plane**.

```
CLIENT                                  SERVER
  │                                       │
  │──── tools/call ──────────────────────>│
  │     progressToken="job-42"            │
  │                                       │
  │<── notifications/progress ────────────│
  │<── notifications/progress ────────────│
  │<── notifications/progress ────────────│
  │                                       │
  │       ...or user cancels...           │
  │                                       │
  │──── cancellation signal ─────────────>│
  │                                       │
  │             stop work                 │
```

MCP `2026-07-28` keeps both progress and cancellation in the core protocol. Progress uses `notifications/progress`; cancellation is transport-specific: stdio uses `notifications/cancelled`, while Streamable HTTP cancels by closing that request's response stream. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)

---

## 1. First principle: requests are not always instantaneous

Until now we've mostly imagined:

```
tools/call
    │
    ▼
function
    │
    ▼
result
```

But consider:

```python
generate_report()
```

which takes 40 seconds.

Without progress:

```
0s                              40s
│                                │
request ─────────────────────── result
          ???????
```

The client cannot distinguish:

```
working normally
server hung
network stalled
deadlocked
slow upstream API
```

Progress gives the server a side-channel for status:

```
0s        10s        20s        30s       40s

request
   │
   ├── 20%
   ├──────── 45%
   ├──────────────── 75%
   └────────────────────────── result
```

Progress notifications are optional and out-of-band relative to the final result. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)

---

# 2. Progress begins with the client

This detail matters.

The server does **not** arbitrarily decide:

> “I'll start sending progress.”

The client first opts in by putting a:

```
progressToken
```

inside the request's `_meta`.

Protocol-level request:

```json
{
  "jsonrpc": "2.0",
  "id": 17,
  "method": "tools/call",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {},
      "progressToken": "inventory-import-17"
    },
    "name": "import_inventory",
    "arguments": {}
  }
}
```

A progress token must be a string or integer and must be unique across active requests. Its purpose is to correlate progress notifications with the operation that requested them. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)

---

# 3. Why not just use the JSON-RPC request ID?

Because they represent different concepts.

```
JSON-RPC request ID
        │
        └── correlates REQUEST ↔ RESPONSE


progressToken
        │
        └── correlates REQUEST ↔ PROGRESS EVENTS
```

Example:

```
request id      = 17
progress token  = "inventory-import"
```

Later:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progressToken": "inventory-import",
    "progress": 50,
    "total": 100,
    "message": "Importing warehouse records"
  }
}
```

That distinction is worth memorizing.

---

# 4. `notifications/progress`

The protocol shape is straightforward:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progressToken": "inventory-import",
    "progress": 50,
    "total": 100,
    "message": "Importing warehouse records"
  }
}
```

The fields mean:

| Field | Meaning |
|---|---|
| `progressToken` | Which operation this belongs to |
| `progress` | Work completed so far |
| `total` | Optional expected total |
| `message` | Optional human-readable status |

`progress` must increase as progress is made; both `progress` and `total` may be floating-point values. The server can omit `total` when the final amount of work is unknown. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)

---

# 5. Known vs unknown totals

There are three common progress models.

### Absolute

```
3 / 10 files
```

Protocol:

```json
{
  "progress": 3,
  "total": 10
}
```

### Percentage

```
75 / 100
```

Protocol:

```json
{
  "progress": 75,
  "total": 100
}
```

### Indeterminate

Suppose you're crawling pages and don't know how many exist:

```json
{
  "progress": 37,
  "message": "37 pages discovered"
}
```

No:

```
total
```

is necessary. FastMCP documents all three patterns explicitly. [FastMCP](https://gofastmcp.com/servers/progress)

---

# 6. Protocol rule: progress must move forward

This is bad:

```
20
30
25
40
```

Progress should increase:

```
20
30
35
40
```

The protocol requires the `progress` value to increase with each progress notification. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)

That means:

```
progress
≠
arbitrary telemetry measurement
```

If CPU usage goes:

```
40%
85%
30%
```

that is not suitable as your MCP progress value.

Use the optional message instead:

```json
{
  "progress": 4,
  "total": 10,
  "message": "CPU utilization currently 85%"
}
```

---

# 7. Progress is not Logging

Consider:

```
"Connecting to PostgreSQL"
"Query took 842 ms"
"Retrying API request"
```

Those are diagnostic events.

Compare:

```
"Processed 400 of 1,000 records"
```

That's operation progress.

```
LOGGING
"What is happening internally?"


PROGRESS
"How far through this operation are we?"
```

Don't turn your progress stream into debug logging.

We'll cover MCP Logging separately.

---

# 8. FastMCP server abstraction

Protocol-level implementation would require you to:

```
read progressToken
track it
construct notification
serialize JSON-RPC
send notification
```

FastMCP reduces that to:

```python
await ctx.report_progress(...)
```

Official FastMCP example:

```python
import asyncio

from fastmcp import Context, FastMCP


mcp = FastMCP("ProgressDemo")


@mcp.tool
async def process_items(
    items: list[str],
    ctx: Context,
) -> dict:
    total = len(items)
    results = []

    for i, item in enumerate(items, start=1):
        await asyncio.sleep(0.1)

        results.append(item.upper())

        await ctx.report_progress(
            progress=i,
            total=total,
            message=f"Processed {item}",
        )

    return {
        "processed": len(results),
        "results": results,
    }
```

FastMCP's `Context.report_progress()` maps those Python arguments onto MCP progress notifications. If the client did not provide a progress token, reporting has no effect rather than raising an error. [FastMCP](https://gofastmcp.com/servers/progress)

---

# 9. Peel the FastMCP abstraction

This:

```python
await ctx.report_progress(
    progress=3,
    total=10,
    message="Processed customer 3",
)
```

conceptually becomes:

```
ctx
 │
 ├── find current request
 │
 ├── find progressToken
 │
 └── token exists?
       │
       ├── no
       │    └── do nothing
       │
       └── yes
            │
            ▼
notifications/progress
            │
            ▼
transport
            │
            ▼
client
```

So once again:

> **`ctx.report_progress()` is protocol communication, not simply a local callback.**

---

# 10. FastMCP client abstraction

FastMCP clients register:

```python
progress_handler
```

Example:

```python
from fastmcp import Client


async def progress_handler(
    progress: float,
    total: float | None,
    message: str | None,
) -> None:

    if total is None:
        print(
            f"{progress}: "
            f"{message or ''}"
        )
        return

    percentage = progress / total * 100

    print(
        f"{percentage:.0f}% - "
        f"{message or ''}"
    )


client = Client(
    "progress_server.py",
    progress_handler=progress_handler,
)
```

FastMCP can also override the progress handler per individual tool call. [FastMCP](https://gofastmcp.com/clients/progress)

---

# 11. Complete working progress example

## `progress_server.py`

```python
import asyncio

from fastmcp import Context, FastMCP


mcp = FastMCP("BatchProcessor")


@mcp.tool
async def process_items(
    items: list[str],
    ctx: Context,
) -> dict:
    """Process strings and report progress."""

    total = len(items)
    processed = []

    for index, item in enumerate(
        items,
        start=1,
    ):
        # Pretend this is real work.
        await asyncio.sleep(0.5)

        processed.append(
            item.upper()
        )

        await ctx.report_progress(
            progress=index,
            total=total,
            message=f"Processed {item}",
        )

    return {
        "count": len(processed),
        "items": processed,
    }


if __name__ == "__main__":
    mcp.run()
```

## `progress_client.py`

```python
import asyncio

from fastmcp import Client


async def show_progress(
    progress: float,
    total: float | None,
    message: str | None,
) -> None:

    if total is None:
        print(
            f"[{progress}] "
            f"{message or ''}"
        )
        return

    percent = progress / total * 100

    print(
        f"[{percent:5.1f}%] "
        f"{message or ''}"
    )


async def main():
    client = Client(
        "progress_server.py",
        mode="auto",
        progress_handler=show_progress,
    )

    async with client:
        result = await client.call_tool(
            "process_items",
            {
                "items": [
                    "alpha",
                    "beta",
                    "gamma",
                    "delta",
                ]
            },
        )

        print("RESULT:", result.data)


asyncio.run(main())
```

Expected shape:

```
[ 25.0%] Processed alpha
[ 50.0%] Processed beta
[ 75.0%] Processed gamma
[100.0%] Processed delta
RESULT: ...
```

FastMCP's client handler supplies the progress-monitoring abstraction while the server uses `ctx.report_progress()`. [FastMCP](https://gofastmcp.com/servers/progress)

---

# 12. Now Cancellation

Imagine the same operation:

```
item 1
item 2
item 3
...
item 10,000
```

The user clicks:

```
Cancel
```

The application should not merely hide the UI.

It should attempt to stop:

```
database queries
network requests
CPU work
file operations
subprocesses
allocated resources
```

MCP defines cancellation as:

> The result is no longer wanted, so associated processing should cease. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)

---

# 13. Cancellation is request-scoped

Suppose three requests are running:

```
request #10 → import inventory
request #11 → generate report
request #12 → search customers
```

The user cancels:

```
#11
```

The server should not kill:

```
#10
#12
```

Cancellation therefore identifies the specific in-flight request.

On stdio:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/cancelled",
  "params": {
    "requestId": 11,
    "reason": "User cancelled report generation"
  }
}
```

The `requestId` must correspond to a request that the client previously issued and believes is still in progress. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)

---

# 14. Progress token vs cancellation request ID

This is an easy interview question.

```
PROGRESS
correlates via:
progressToken


CANCELLATION
correlates via:
requestId
```

Example:

```
JSON-RPC id:
17

progressToken:
"report-generation"
```

Progress:

```json
{
  "progressToken": "report-generation",
  "progress": 70
}
```

Cancellation:

```json
{
  "requestId": 17
}
```

Different jobs.

---

# 15. Cancellation differs by transport

This changed significantly in modern MCP.

## stdio

There is no independent transport stream per request.

So the client sends:

```
notifications/cancelled
``` :chatgpt-content-reference{index="11"}


## Streamable HTTP

Every request owns its HTTP/SSE response stream.

Therefore cancellation is simply:

```
CLIENT
    │
    └── closes response stream
```

The server must interpret that disconnect as cancellation.

No separate `notifications/cancelled` message is expected. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)

This is a good example of:

```
same protocol semantic
      │
      ▼
different transport mechanism
```

---

# 16. Why HTTP cancellation changed

Imagine:

```
POST /mcp   request A
    │
    └── SSE stream A


POST /mcp   request B
    │
    └── SSE stream B
```

If:

```
stream A closes
```

there is no ambiguity.

It means:

```
request A is abandoned
```

The transport itself provides correlation.

With stdio:

```
one stdin/stdout byte stream
│
├── request A
├── request B
└── notifications
```

there is no stream to close independently.

So MCP needs:

```
requestId
```

inside the cancellation notification. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)

---

# 17. Cancellation is cooperative

This is a distributed-systems principle.

Cancellation means:

```
"Please stop this work."
```

not:

```
"The work instantaneously ceased."
```

The operation might already have completed.

The request might be inside an uncancellable external API.

The cancellation signal might arrive late.

MCP therefore explicitly allows cancellation races and says servers may ignore cancellation for unknown, already-completed, or uncancellable requests. Clients should ignore a result that arrives after they cancelled it. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)

Professional term:

> **Cooperative cancellation**

---

# 18. Cancellation race condition

Example:

```
SERVER                         CLIENT

work completes
    │
    │                       click Cancel
    │                           │
response ──────────────>        │
    │                           │
    │     cancellation ────────>│
```

Depending on network timing:

```
response may arrive first

or

cancellation may arrive first
```

Neither side should malfunction.

Professional phrase:

> **“Cancellation is inherently racy because completion and cancellation can cross in flight.”**

MCP requires implementations to handle this gracefully. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)

---

# 19. Cancellation does not deserve a normal result

Suppose the client cancels:

```
request #17
```

Bad server:

```json
{
  "id": 17,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Cancelled successfully!"
      }
    ]
  }
}
```

That's conceptually wrong for protocol cancellation.

The result has already been declared:

```
unused
```

A server receiving cancellation should stop processing, free resources, and should not send the normal response for that cancelled request. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)

This differs from a domain-level operation such as:

```
cancel_order(order_id)
```

That **is a normal Tool** and should return a normal Tool result.

Important distinction:

```
PROTOCOL CANCELLATION

"Stop processing this MCP request."


DOMAIN CANCELLATION

"Change an order's status to cancelled."
```

Completely different concepts.

---

# 20. FastMCP client timeout

FastMCP's:

```python
client.call_tool(...)
```

supports a per-call:

```python
timeout=
```

Example:

```python
result = await client.call_tool(
    "process_items",
    {
        "items": [
            "alpha",
            "beta",
            "gamma",
            "delta",
        ]
    },
    timeout=2.0,
)
```

FastMCP describes this as aborting the operation if tool execution exceeds the timeout. [FastMCP](https://gofastmcp.com/clients/tools?utm_source=chatgpt.com)

Timeout is one common trigger for cancellation:

```
request starts
     │
     ▼
timeout expires
     │
     ▼
client stops waiting
     │
     ▼
transport cancellation
```

---

# 21. Working timeout/cancellation experiment

Reuse `progress_server.py`.

Now change the client:

```python
import asyncio

from fastmcp import Client


async def show_progress(
    progress: float,
    total: float | None,
    message: str | None,
) -> None:
    print(
        f"progress={progress}, "
        f"total={total}, "
        f"message={message}"
    )


async def main():
    client = Client(
        "progress_server.py",
        mode="auto",
        progress_handler=show_progress,
    )

    async with client:
        try:
            result = await client.call_tool(
                "process_items",
                {
                    "items": [
                        "alpha",
                        "beta",
                        "gamma",
                        "delta",
                        "epsilon",
                    ]
                },
                timeout=1.2,
            )

            print(result.data)

        except Exception as exc:
            # For this exercise, inspect what your installed
            # FastMCP/transport layer raises on timeout.
            print(
                type(exc).__name__,
                str(exc),
            )


asyncio.run(main())
```

The tool sleeps `0.5` seconds per item, so the timeout is deliberately shorter than full completion.

The important experiment is not the exception's spelling.

Observe:

```
1. Some progress arrives.
2. Client timeout occurs.
3. Request becomes unwanted.
4. Server should cease associated work.
```

FastMCP exposes timeout control on `call_tool()`, while the underlying cancellation semantics depend on the negotiated MCP transport. [FastMCP](https://gofastmcp.com/clients/tools?utm_source=chatgpt.com)

---

# 22. Write cancellation-safe server code

This is more important than detecting cancellation manually.

Suppose your Tool acquires resources:

```python
@mcp.tool
async def export_data(
    ctx: Context,
) -> str:

    connection = await acquire_connection()

    try:
        ...
    finally:
        await connection.close()
```

Why `finally`?

Because execution may terminate through:

```
normal completion
exception
timeout
cancellation
```

Cleanup must happen in all cases.

Professional phrase:

> **“Resource cleanup must be cancellation-safe.”**

---

# 23. Do not swallow cancellation accidentally

Conceptually dangerous:

```python
try:
    await long_operation()

except BaseException:
    return "Something went wrong"
```

That can convert cancellation-like control flow into a fake successful Tool result.

Prefer handling only failures you genuinely know how to recover from:

```python
try:
    await long_operation()

except DatabaseUnavailable as exc:
    ...
```

and let cancellation propagate through your async stack.

General principle:

```
expected business error
    → handle deliberately


cancellation
    → unwind promptly
```

---

# 24. Propagate cancellation downstream

Suppose your Tool calls:

```
Tool
 │
 ├── HTTP API
 │
 ├── database
 │
 └── subprocess
```

Cancellation is useful only if those operations can also stop.

Bad architecture:

```
MCP request cancelled
       │
       ▼
Tool coroutine stops
       │
       ▼
background subprocess
keeps running for 45 minutes
```

Better:

```
request cancellation
       │
       ▼
Tool
       │
       ├── cancel HTTP call
       ├── cancel DB operation
       └── terminate subprocess
```

Professional phrase:

> **“Cancellation should propagate through the dependency graph.”**

---

# 25. Progress and timeout interact

Suppose an operation normally takes 60 seconds.

A client has:

```
timeout = 10 seconds
```

but receives progress every 3 seconds.

There are two possible timeout policies:

### Fixed deadline

```
10 seconds total
→ cancel regardless of progress
```

### Idle timeout

```
reset timer whenever progress arrives
```

MCP permits implementations to reset a timeout after corresponding progress arrives, because progress indicates active work. However, the specification recommends still enforcing a maximum overall timeout so a misbehaving peer cannot keep a request alive forever with endless progress messages. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)

Professional terminology:

```
idle timeout
absolute deadline
maximum execution deadline
```

---

# 26. Don't use progress as a heartbeat exploit

Bad server:

```python
while True:
    await ctx.report_progress(
        progress=counter,
        message="Still working",
    )
```

with no meaningful progress.

That can prevent poorly designed clients from timing out.

Progress should communicate actual advancement.

MCP also recommends rate-limiting progress notifications to avoid flooding. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)

---

# 27. Do not report every record

Imagine processing:

```
10,000,000 records
```

Bad:

```python
for record in records:
    await ctx.report_progress(...)
```

That can produce:

```
10,000,000 protocol messages
```

Instead:

```python
REPORT_EVERY = 1000
```

```python
for index, record in enumerate(records, start=1):

    process(record)

    if index % REPORT_EVERY == 0:
        await ctx.report_progress(
            progress=index,
            total=total,
        )
```

Progress is a UX/control signal, not an event log.

---

# 28. Multi-stage progress

Suppose:

```
1. Validate
2. Export
3. Transform
4. Upload
```

Instead of resetting progress:

```
0 → 100
0 → 100
0 → 100
0 → 100
```

map each stage into one monotonic range:

```
validation   0 ───── 20
export       20 ──── 50
transform    50 ──── 80
upload       80 ─── 100
```

FastMCP recommends this style for multi-stage operations. [FastMCP](https://gofastmcp.com/servers/progress)

Example:

```python
await ctx.report_progress(
    progress=20,
    total=100,
    message="Validation complete",
)

await ctx.report_progress(
    progress=50,
    total=100,
    message="Export complete",
)

await ctx.report_progress(
    progress=80,
    total=100,
    message="Transformation complete",
)

await ctx.report_progress(
    progress=100,
    total=100,
    message="Upload complete",
)
```

---

# 29. Progress has a lifecycle

Think explicitly:

```
REQUEST STARTS
     │
     ▼
progress token becomes active
     │
     ├── progress
     ├── progress
     ├── progress
     │
     ▼
REQUEST COMPLETES / CANCELS
     │
     ▼
progress token becomes inactive
```

MCP requires progress notifications to reference active in-progress requests and to stop after completion. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)

Therefore never send:

```
100%
result
105%
```

after completion.

---

# 30. Cancellation also has a lifecycle

```
request created
      │
      ▼
in flight
      │
      ├─────────────┐
      │             │
      ▼             ▼
complete         cancelled
      │             │
      ▼             ▼
terminal         terminal
```

Once terminal, cancellation of that request has no useful effect.

This explains why unknown or already-completed cancellation notifications are normally ignored rather than treated as fatal protocol errors. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation)

---

# 31. Raw server architecture

Our naïve Lesson-1 server:

```python
for line in sys.stdin:
    handle(line)
```

is now nowhere near enough.

A realistic stdio implementation needs something like:

```
                      request registry
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   request #1          request #2          request #3
        │                   │                   │
        ▼                   ▼                   ▼
   coroutine            coroutine            coroutine
        │
        │
progress token
        │
        ▼
notifications/progress


incoming notifications/cancelled
        │
        ▼
lookup request ID
        │
        ▼
cancel corresponding operation
```

Now we need:

```
concurrent request execution
request registry
progress-token tracking
cancellation propagation
resource cleanup
race handling
```

FastMCP hides most of this infrastructure.

---

# 32. Request ID and Progress Token serve different registries

A useful implementation model:

```python
active_requests = {
    request_id: operation,
}

progress_tokens = {
    progress_token: request_id,
}
```

Then:

```
cancel request #42
        │
        ▼
active_requests[42]
        │
        ▼
cancel operation
```

while:

```
report token "abc"
        │
        ▼
progress notification
```

FastMCP manages this correlation layer for you.

---

# 33. Progress is best-effort

A server receiving a progress token:

```
MAY report progress
```

not:

```
MUST report progress
```

The token expresses:

> “I can receive progress if you have meaningful progress to provide.”

MCP explicitly allows servers to send none, choose their own frequency, and omit a total. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)

So don't design correctness around receiving progress events.

Bad:

```
"If 50% progress notification didn't arrive,
assume operation failed."
```

Wrong.

Only the final response determines request completion.

---

# 34. Progress is ephemeral; result is authoritative

Imagine:

```
progress:
"Export complete"

then:

database upload fails
```

The overall operation failed.

Therefore:

```
progress
    ≠
final outcome
```

Progress answers:

```
"What stage are we at?"
```

The final MCP response answers:

```
"What actually happened?"
```

---

# 35. Cancellation is not rollback

Another critical distinction.

Suppose:

```
Step 1: create database row
Step 2: upload file
Step 3: send notification
```

Cancellation arrives after Step 1.

Cancellation means:

```
stop remaining work
```

It does **not automatically mean**:

```
undo Step 1
```

If atomicity matters, you must design it:

```
transaction
compensation
idempotency
staging
rollback
```

Professional phrase:

> **“Cancellation terminates computation; transactional rollback is an application-level concern.”**

This distinction matters enormously for destructive Tools.

---

# 36. Design for idempotency around cancellation

Consider:

```
client sends create_invoice
        │
        ▼
server creates invoice
        │
        ▼
client cancels before response arrives
```

Did the invoice get created?

Potentially yes.

The client did not receive confirmation.

Now the user retries.

Without idempotency:

```
invoice #100
invoice #101
```

Duplicate side effect.

Therefore side-effecting operations frequently need:

```
idempotency keys
stable operation IDs
transaction records
deduplication
```

Cancellation increases the importance of these patterns.

---

# 37. Progress + Cancellation + Background Tasks

There are really two kinds of long-running operation:

```
REQUEST-SCOPED WORK

client waits for response
progress notifications
cancellable request


DURABLE BACKGROUND WORK

client receives task handle
work outlives request
poll/listen for status
task-specific cancellation
```

Do not use ordinary progress/cancellation as a substitute for durable background jobs.

FastMCP also supports protocol-native background tasks separately; we'll cover them later because they introduce a different lifecycle. [FastMCP](https://gofastmcp.com/clients/tasks?utm_source=chatgpt.com)

---

# 38. Complete protocol → FastMCP map

| MCP | FastMCP |
|---|---|
| request `_meta.progressToken` | automatically managed when progress handling is requested |
| `notifications/progress` | `ctx.report_progress()` |
| progress receiver | `progress_handler=` |
| per-operation receiver | `call_tool(..., progress_handler=...)` |
| request timeout | `timeout=` |
| stdio cancellation | framework/transport handles `notifications/cancelled` |
| HTTP cancellation | response-stream cancellation |
| request correlation | framework |
| cancellation cleanup | your application responsibility |
| rollback | your application responsibility |

FastMCP explicitly exposes progress reporting and progress handlers, and its `call_tool()` API exposes per-call timeout control. [FastMCP](https://gofastmcp.com/servers/progress)

---

# 39. Professional vocabulary

| Term | Meaning |
|---|---|
| **Progress token** | Correlation token for progress events |
| **In-flight request** | Request started but not terminal |
| **Out-of-band notification** | Message separate from final response |
| **Monotonic progress** | Progress value only moves forward |
| **Indeterminate progress** | Progress without a known total |
| **Cooperative cancellation** | Receiver is asked to stop rather than forcibly killed |
| **Cancellation propagation** | Passing stop signals through downstream work |
| **Cancellation race** | Completion and cancellation crossing concurrently |
| **Absolute deadline** | Maximum total duration |
| **Idle timeout** | Timeout based on lack of activity |
| **Resource cleanup** | Releasing resources during all exit paths |
| **Re-entrant/idempotent operation** | Operation safe against retry scenarios |
| **Compensating action** | Application operation that reverses a prior side effect |
| **Request-scoped work** | Work whose lifetime is tied to one MCP request |

A professional summary:

> **“MCP progress is opt-in and token-correlated: the client supplies a `progressToken`, and the server may emit monotonic `notifications/progress` events until the request becomes terminal. Cancellation is request-scoped and transport-specific—in modern stdio it uses `notifications/cancelled`, whereas Streamable HTTP treats closure of the request's SSE stream as the cancellation signal. FastMCP abstracts progress through `ctx.report_progress()` and client progress handlers, while timeout/cancellation propagation is handled by the client and transport layers.”** [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress)

---

# 40. Hands-on assignment

Use the example above and deliberately test:

1. **Normal completion** with five items.
2. Remove the `progress_handler` and verify the Tool still works.
3. Report without `total` to create indeterminate progress.
4. Report every 10 items instead of every item.
5. Use a short `timeout=` so the client aborts mid-operation.
6. Put resource acquisition inside `try/finally` and verify cleanup happens.
7. Add a side effect before a long sleep and observe why cancellation is **not rollback**.
8. Add an idempotency key so retrying after uncertain cancellation does not duplicate the side effect.
9. Run two long requests concurrently and verify their progress does not get confused.
10. Draw both registries:

```
request ID → request lifecycle

progressToken → progress stream
```

The key test is being able to explain why:

```
requestId
    ≠
progressToken
    ≠
timeout
    ≠
cancellation
    ≠
rollback
```

They solve different problems.

## Next lesson — Logging + Observability

Next we should cover:

```
notifications/message
log levels
FastMCP ctx.debug/info/warning/error
client log handlers
protocol logging vs server process logs
structured logging
correlation IDs
redaction
metrics and tracing
```

There is an important current-protocol wrinkle: **MCP Logging itself is deprecated in `2026-07-28`**, so we'll learn the protocol feature for compatibility, then the production observability pattern you should use for new systems. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema)