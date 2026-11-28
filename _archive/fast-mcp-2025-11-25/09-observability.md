Keeping it **protocol-first → FastMCP abstraction → production design**, with runnable examples.

# Lesson 9 — Logging + Observability

First separate four concepts that are often incorrectly lumped together:

| Concept | Question it answers |
|---|---|
| **MCP protocol logging** | “What diagnostic message does the server want to expose to this MCP client?” |
| **Application logging** | “What happened inside my server process?” |
| **Metrics** | “How often/how much is something happening?” |
| **Tracing** | “Where did this request spend time across components?” |

The most important current fact is that **MCP protocol logging is deprecated in MCP `2026-07-28`**. It still works during the compatibility period, but new systems should generally use normal logging plus OpenTelemetry for production observability. The MCP maintainers explicitly cite `stderr` and OpenTelemetry as better-established alternatives. [Model Context Protocol](https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging)

---

# 1. First principle: logs have an audience

Suppose your tool executes:

```
analyze_order("ORD-123")
```

During execution you might want to record:

```
request started
database lookup took 73 ms
customer record found
shipping API timed out
retry succeeded
request finished in 1.2 s
```

But who needs that information?

There are two very different audiences:

```
                     SERVER EVENT
                          │
              ┌───────────┴───────────┐
              │                       │
         MCP CLIENT              OPERATORS
              │                       │
       protocol logging         application logs
              │                       │
       notifications/message     stdout/stderr/file
                                      │
                                      ▼
                              observability backend
```

This distinction matters because exposing internal diagnostics to an MCP client can reveal information that should remain server-side.

---

# 2. Protocol-level MCP logging

In the older `2025-11-25` protocol, logging looked like this:

```
CLIENT                           SERVER
  │                                │
  │── logging/setLevel ───────────>│
  │      level="info"              │
  │                                │
  │────── tools/call ─────────────>│
  │                                │
  │<── notifications/message ──────│
  │<── notifications/message ──────│
  │                                │
  │<──── tool result ──────────────│
```

The server had to advertise the `logging` capability, and the client could set a session-level minimum severity with `logging/setLevel`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/logging)

Example:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "logging/setLevel",
  "params": {
    "level": "info"
  }
}
```

Then:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/message",
  "params": {
    "level": "info",
    "logger": "inventory",
    "data": {
      "message": "Loading warehouse inventory"
    }
  }
}
```

---

# 3. Modern MCP changed log-level negotiation

MCP `2026-07-28` is stateless, so:

```
logging/setLevel
```

was removed.

Instead, the client opts into logging **per request**:

```json
{
  "jsonrpc": "2.0",
  "id": 17,
  "method": "tools/call",
  "params": {
    "name": "analyze_inventory",
    "arguments": {},
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {},
      "io.modelcontextprotocol/logLevel": "info"
    }
  }
}
```

If `io.modelcontextprotocol/logLevel` is absent, a modern server **must not** send `notifications/message` for that request. Log notifications are request-scoped and travel on that request's response stream. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/logging?utm_source=chatgpt.com)

Conceptually:

```
OLD

session
 └── logging/setLevel("info")
      └── affects later requests


MODERN

request A
 └── logLevel="debug"

request B
 └── no logLevel

request C
 └── logLevel="error"
```

This follows the broader stateless architecture introduced in `2026-07-28`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic?utm_source=chatgpt.com)

---

# 4. MCP log levels

The protocol uses syslog-style severity levels:

| Level | Meaning |
|---|---|
| `debug` | detailed diagnostic information |
| `info` | normal execution information |
| `notice` | significant but normal event |
| `warning` | potentially problematic condition |
| `error` | operation failure/error condition |
| `critical` | serious component failure |
| `alert` | immediate action required |
| `emergency` | system unusable |

These are defined by MCP using the RFC 5424 severity model. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/logging)

Do not use:

```
error
```

for every event you want somebody to notice.

Severity should convey operational meaning.

---

# 5. Protocol log message shape

The wire-level notification remains:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/message",
  "params": {
    "level": "warning",
    "logger": "inventory.import",
    "data": {
      "message": "Warehouse API responded slowly",
      "latency_ms": 1820,
      "warehouse": "PHX"
    }
  }
}
```

Important fields:

```
level
    → severity

logger
    → logical source/component

data
    → arbitrary JSON-serializable payload
```

`data` is deliberately not limited to a string. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema?utm_source=chatgpt.com)

---

# 6. Structured logging beats string concatenation

Bad:

```python
await ctx.info(
    "Processing ORD-123 for customer 481 with 7 items"
)
```

Better:

```python
await ctx.info(
    "Processing order",
    extra={
        "order_id": "ORD-123",
        "item_count": 7,
    },
)
```

Why?

Because structured fields can later be:

```
filtered
aggregated
indexed
redacted
queried
```

FastMCP's `ctx.debug()`, `ctx.info()`, `ctx.warning()`, and `ctx.error()` accept an `extra` object specifically for structured data. [FastMCP](https://gofastmcp.com/servers/logging)

---

# 7. FastMCP server abstraction

For the modern examples, pin FastMCP 4 beta:

```bash
uv add "fastmcp==4.0.0b1"
```

That is currently the explicitly documented FastMCP version for modern MCP `2026-07-28`. [FastMCP](https://gofastmcp.com/getting-started/installation?utm_source=chatgpt.com)

Create `logging_server.py`:

```python
from fastmcp import Context, FastMCP


mcp = FastMCP("LoggingDemo")


@mcp.tool
async def analyze_numbers(
    values: list[float],
    ctx: Context,
) -> dict:
    await ctx.debug(
        "Starting numerical analysis",
        extra={
            "value_count": len(values),
        },
    )

    if not values:
        await ctx.warning(
            "No values supplied",
        )

        return {
            "count": 0,
            "average": None,
        }

    await ctx.info(
        "Calculating average",
        extra={
            "value_count": len(values),
        },
    )

    average = sum(values) / len(values)

    await ctx.info(
        "Analysis completed",
        extra={
            "average": average,
        },
    )

    return {
        "count": len(values),
        "average": average,
    }


if __name__ == "__main__":
    mcp.run()
```

FastMCP maps these context methods onto MCP client-visible log messages. [FastMCP](https://gofastmcp.com/servers/logging)

---

# 8. Peel the abstraction

This:

```python
await ctx.warning(
    "No values supplied",
)
```

conceptually becomes:

```
Python
ctx.warning(...)
      │
      ▼
FastMCP Context
      │
      ├── check request logging policy
      │
      ▼
MCP LoggingMessageNotification
      │
      ▼
notifications/message
      │
      ▼
client
```

FastMCP is hiding:

```
severity mapping
request context
protocol serialization
transport delivery
```

Again:

> `ctx.warning()` is not equivalent to Python's `logger.warning()`.

They have different destinations.

---

# 9. FastMCP client example

Create `logging_client.py`:

```python
import asyncio

from fastmcp import Client
from fastmcp.client.logging import LogMessage


async def handle_log(
    message: LogMessage,
) -> None:
    print(
        f"[{message.level.upper()}]"
        f"[{message.logger or 'server'}]"
        f" {message.data}"
    )


async def main():
    client = Client(
        "logging_server.py",
        log_handler=handle_log,
    )

    async with client:
        result = await client.call_tool(
            "analyze_numbers",
            {
                "values": [
                    10,
                    20,
                    30,
                ]
            },
        )

        print(
            "RESULT:",
            result.data,
        )


asyncio.run(main())
```

FastMCP clients accept a `log_handler` callback receiving `LogMessage` objects with `level`, optional `logger`, and arbitrary `data`. Without a custom handler, FastMCP forwards server logs through Python logging using corresponding severity levels. [FastMCP](https://gofastmcp.com/llms-full.txt)

Expected conceptual output:

```
[INFO][server] {'msg': 'Calculating average', ...}
[INFO][server] {'msg': 'Analysis completed', ...}

RESULT: {'count': 3, 'average': 20.0}
```

---

# 10. MCP logging vs Python logging

Now compare this:

```python
await ctx.info(
    "Customer lookup started"
)
```

with:

```python
logger.info(
    "Customer lookup started"
)
```

They should be mentally separated:

| Code | Destination |
|---|---|
| `ctx.info(...)` | MCP client |
| `logger.info(...)` | server's own logging infrastructure |

FastMCP's documentation explicitly distinguishes client-visible MCP logs from ordinary server-side logging and recommends Python logging or `fastmcp.utilities.logging.get_logger()` for the latter. [FastMCP](https://gofastmcp.com/servers/logging)

---

# 11. Why this distinction matters

Suppose:

```python
logger.debug(
    "Connecting to postgres-prod-7.internal:5432"
)
```

may be acceptable in a tightly controlled operations environment.

But:

```python
await ctx.debug(
    "Connecting to postgres-prod-7.internal:5432"
)
```

sends that information to the MCP client.

Now you've potentially leaked:

```
internal hostname
network topology
database architecture
```

The current MCP logging specification explicitly says logs must not expose credentials, secrets, PII, or internal information that could assist attacks. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/logging?utm_source=chatgpt.com)

So:

```
SERVER LOG
can contain operational detail
subject to your logging policy


MCP CLIENT LOG
must be treated as externally visible data
```

---

# 12. `stderr` matters for stdio

Recall our very first server:

```
stdin  → MCP messages in
stdout → MCP messages out
```

That means this is dangerous:

```python
print("Database connected!")
```

because `print()` normally writes to stdout.

On stdio, stdout belongs to the MCP protocol.

The protocol explicitly permits servers to write diagnostic strings to `stderr`, while stdout must contain only valid MCP messages. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports?utm_source=chatgpt.com)

So:

```python
import sys

print(
    "Database connected",
    file=sys.stderr,
)
```

is safe from a transport-framing perspective.

Professional phrasing:

> **“On stdio, stdout is the protocol channel; stderr is the diagnostic channel.”**

---

# 13. Logging is not Progress

Compare:

```python
await ctx.info(
    "Database query completed in 82 ms"
)
```

with:

```python
await ctx.report_progress(
    progress=50,
    total=100,
    message="50 records processed",
)
```

They answer different questions:

```
LOG

"What happened?"


PROGRESS

"How far through the operation are we?"
```

Do not create:

```
DEBUG: processed item 1
DEBUG: processed item 2
DEBUG: processed item 3
...
```

just to implement a progress bar.

Use the actual progress mechanism.

---

# 14. Logs are also not Tool results

Bad design:

```python
await ctx.info(
    "Customer balance is $400"
)

return "done"
```

if `$400` is required output.

The result should contain authoritative business data:

```python
return {
    "customer_id": customer_id,
    "balance": 400,
}
```

The log may additionally say:

```
Customer lookup completed.
```

Think:

```
RESULT
= contractual output


LOG
= diagnostic information
```

Clients are free to discard logs.

Therefore application correctness must never depend on them.

---

# 15. Why MCP Logging was deprecated

The protocol designers gave two main reasons:

```
existing logging infrastructure already solves this well

+

the protocol complexity was high relative to adoption/value
```

The accepted deprecation proposal specifically calls out ordinary `stderr` logging and OpenTelemetry as mature alternatives. [Model Context Protocol](https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging)

Therefore for a **new production MCP system**, think:

```
                    OBSERVABILITY

        ┌──────────────┼──────────────┐
        │              │              │
       logs          metrics        traces
        │              │              │
   application       counters       spans
     logger          gauges      distributed flow
        │              │              │
        └──────────── OpenTelemetry ──┘
```

Protocol logging should generally be treated as compatibility/client-UX functionality, not the foundation of your observability architecture.

---

# 16. Logs vs Metrics vs Traces

Suppose:

```
tool:
search_orders
```

A log might say:

```json
{
  "event": "order_search_completed",
  "result_count": 17
}
```

A metric might record:

```
mcp_tool_calls_total{
    tool="search_orders",
    status="success"
} += 1
```

A trace might represent:

```
tools/call search_orders          420 ms
│
├── auth check                     8 ms
│
├── postgres query               290 ms
│
└── serialization                 13 ms
```

Three different observability dimensions.

---

# 17. First principle of tracing: a request is a tree

Imagine:

```
MCP client
   │
   ▼
MCP server
   │
   ├── database
   │
   ├── inventory API
   │
   └── payment API
```

Tracing represents this as:

```
TRACE abc123

MCP tools/call                    980 ms
│
├── validate request               4 ms
│
├── database lookup              120 ms
│
├── inventory API                300 ms
│
└── payment API                  490 ms
```

Each unit is a:

> **span**

The collection of causally related spans is a:

> **trace**

---

# 18. MCP now standardizes trace-context propagation

MCP `2026-07-28` reserves:

```
traceparent
tracestate
baggage
```

inside `_meta` for OpenTelemetry/W3C trace-context propagation. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic?utm_source=chatgpt.com)

Example:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_inventory",
    "arguments": {
      "sku": "ABC-1001"
    },
    "_meta": {
      "traceparent":
        "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01"
    }
  }
}
```

This is not the trace itself.

It is **trace context** that allows independently instrumented processes to join the same distributed trace.

---

# 19. Trace ID vs Span ID

A W3C `traceparent` conceptually contains:

```
version
trace-id
parent-span-id
flags
```

Think:

```
TRACE

request through entire distributed system
│
└── trace_id


SPAN

one operation within that trace
│
└── span_id
```

Example:

```
trace_id
0af7651916cd43dd8448eb211c80319c


client span
1111111111111111

server span
2222222222222222

database span
3333333333333333
```

Same trace.

Different spans.

---

# 20. FastMCP OpenTelemetry abstraction

Current FastMCP includes native OpenTelemetry instrumentation for server and client operations. Its instrumentation API is enabled by default but becomes effectively a no-op if you have not configured an OpenTelemetry SDK/exporter. [FastMCP](https://gofastmcp.com/servers/telemetry?utm_source=chatgpt.com)

So:

```
FastMCP operation
      │
      ▼
OpenTelemetry API
      │
      ├── no SDK configured
      │       └── effectively no-op
      │
      └── SDK configured
              │
              ▼
            spans
              │
              ▼
           exporter
              │
              ▼
     observability backend
```

FastMCP documents automatic spans for tools, prompts, resources, templates, task operations, and related request handling. [FastMCP](https://gofastmcp.com/servers/telemetry?utm_source=chatgpt.com)

---

# 21. Enable tracing

Install:

```bash
pip install \
  opentelemetry-distro \
  opentelemetry-exporter-otlp
```

Then:

```bash
opentelemetry-bootstrap -a install
```

Configure:

```bash
export OTEL_SERVICE_NAME=inventory-mcp
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

Run:

```bash
opentelemetry-instrument \
  fastmcp run server.py
```

This is the FastMCP-documented route for exporting its native OpenTelemetry spans. [FastMCP](https://gofastmcp.com/servers/telemetry?utm_source=chatgpt.com)

---

# 22. The production mental model

Imagine your Tool:

```python
@mcp.tool
async def checkout(...):
```

You want:

```
TRACE

MCP tools/call
│
├── auth
│
├── inventory lookup
│
├── tax calculation
│
└── payment provider
```

And separately:

```
LOGS

"payment retry"
"inventory mismatch"


METRICS

mcp_tool_latency
mcp_tool_errors
payment_retries
```

The trace tells you:

> **where the request went.**

Logs tell you:

> **what notable things occurred.**

Metrics tell you:

> **how the system behaves over time.**

---

# 23. Correlation is the important part

Suppose production logs contain:

```
09:01 request started
09:01 database timeout
09:01 database timeout
09:01 request completed
```

With 5,000 concurrent requests, this is nearly useless.

Instead:

```json
{
  "event": "database_timeout",
  "trace_id": "abc123",
  "tool": "search_orders"
}
```

Now:

```
incident
   │
   ▼
trace_id=abc123
   │
   ├── logs
   ├── spans
   └── downstream requests
```

This is **correlation**.

---

# 24. FastMCP middleware is useful for audit records

Sometimes you don't want normal debug logs.

You want exactly one durable record for each tool invocation:

```
tool
caller
duration
status
redacted input shape
```

FastMCP middleware can intercept `on_call_tool`, inspect the request/result, and emit a structured audit record. FastMCP explicitly recommends OpenTelemetry for tracing and middleware-style records when you need a self-contained audit trail. [FastMCP](https://gofastmcp.com/servers/middleware?utm_source=chatgpt.com)

Conceptually:

```
request
   │
   ▼
AuditMiddleware
   │
   ├── record start
   │
   ▼
Tool
   │
   ▼
AuditMiddleware
   │
   └── record result/duration
```

---

# 25. A practical audit middleware

```python
import json
import time

from fastmcp import FastMCP
from fastmcp.server.middleware import (
    Middleware,
    MiddlewareContext,
)


mcp = FastMCP("AuditedServer")


class AuditMiddleware(Middleware):

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next,
    ):
        started = time.perf_counter()

        record = {
            "event": "tool_call",
            "tool": context.message.name,
            "argument_names": sorted(
                context.message.arguments or {}
            ),
        }

        try:
            result = await call_next(context)

        except Exception as exc:
            record["status"] = "failed"
            record["error_type"] = type(exc).__name__
            raise

        else:
            record["status"] = (
                "tool_error"
                if result.is_error
                else "success"
            )

            return result

        finally:
            record["duration_ms"] = round(
                (
                    time.perf_counter()
                    - started
                )
                * 1000,
                2,
            )

            print(
                json.dumps(record),
            )


mcp.add_middleware(
    AuditMiddleware()
)
```

Notice what we deliberately stored:

```
argument_names
```

rather than:

```
argument values
```

FastMCP's own middleware guidance similarly recommends redacted audit records rather than blindly storing raw payloads. [FastMCP](https://gofastmcp.com/servers/middleware?utm_source=chatgpt.com)

---

# 26. Logging raw Tool arguments is usually a bad default

Suppose:

```python
send_email(
    recipient="...",
    body="..."
)
```

Logging:

```json
{
  "arguments": {
    "recipient": "...",
    "body": "..."
  }
}
```

could persist:

```
personal information
customer data
legal information
secrets embedded in prompts
credentials accidentally supplied by users
```

A better default is:

```json
{
  "tool": "send_email",
  "argument_names": [
    "recipient",
    "body"
  ],
  "status": "success",
  "duration_ms": 183
}
```

Then explicitly whitelist fields when operationally necessary.

---

# 27. Avoid logging model content by default

An MCP system may handle:

```
prompts
documents
email
customer records
source code
API responses
```

Dumping them into logs creates a shadow data store.

That makes:

```
retention
access control
redaction
data deletion
incident response
```

much harder.

Professional phrase:

> **“Observability should capture execution metadata by default, not raw application payloads.”**

---

# 28. Errors need classification

Suppose:

```python
except Exception as exc:
    logger.error(str(exc))
```

You now have an unstructured string.

Better operational metadata:

```json
{
  "event": "tool_failure",
  "tool": "check_inventory",
  "error_type": "UpstreamTimeout",
  "retryable": true,
  "duration_ms": 3012
}
```

Then optionally record the stack trace server-side.

This lets you query:

```
all retryable upstream failures

all check_inventory failures

p95 latency for failed calls
```

rather than grepping arbitrary strings.

---

# 29. Tool error, log error, and span error are three things

This is a useful professional distinction.

Suppose:

```
payment provider times out
```

You may have:

```
MCP ToolResult
    │
    └── isError=true


server log
    │
    └── level=ERROR


OpenTelemetry span
    │
    └── status=ERROR
```

They overlap, but serve different consumers:

```
Tool result
→ model/client behavior

Log
→ operator debugging

Span
→ distributed request analysis
```

Do not assume setting one automatically gives you all three.

---

# 30. Your production observability stack

For new MCP systems, a clean architecture is:

```
                        MCP SERVER

                           Tool
                            │
             ┌──────────────┼──────────────┐
             │              │              │
          Python logs      Metrics       OTEL spans
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                      Observability
                        backend


OPTIONALLY

Tool
 │
 └── ctx.info(...)
      │
      ▼
MCP client-visible diagnostics
```

Protocol logging is optional compatibility/UI functionality.

OpenTelemetry + normal application logging should carry production observability. This direction matches the MCP logging deprecation rationale, and FastMCP provides native OpenTelemetry support. [Model Context Protocol](https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging)

---

# 31. Complete abstraction map

| Layer | Primitive |
|---|---|
| MCP client-visible log | `notifications/message` |
| Modern logging opt-in | `_meta["io.modelcontextprotocol/logLevel"]` |
| Legacy logging configuration | `logging/setLevel` |
| FastMCP server API | `ctx.debug/info/warning/error()` |
| FastMCP client API | `log_handler=` |
| Server-local logging | Python `logging` |
| stdio diagnostics | `stderr` |
| Distributed correlation | `traceparent` / `tracestate` |
| Distributed tracing | OpenTelemetry |
| Cross-cutting audit policy | FastMCP middleware |

---

# 32. Vocabulary checkpoint

A professional description should distinguish **structured logging** (machine-queryable fields), **severity level** (importance), **logger name** (logical source), **correlation ID** (ties events to an operation), **trace** (end-to-end request execution), **span** (one timed operation), **trace context propagation** (carrying trace identity across boundaries), **instrumentation** (code producing telemetry), **exporter** (sends telemetry elsewhere), **redaction** (removes sensitive fields), **cardinality** (number of unique metric-label values), and an **audit trail** (durable record of security/business-relevant activity).

A strong explanation is:

> **“MCP logging is client-visible diagnostic messaging, not the server's observability system. In `2026-07-28`, clients opt into deprecated protocol logs per request with `io.modelcontextprotocol/logLevel`, and servers emit `notifications/message`. FastMCP abstracts this with `ctx.info()` and `log_handler`. For production observability, I would use structured server logs and OpenTelemetry, propagating W3C trace context through MCP `_meta`, rather than making protocol logging the primary telemetry channel.”** [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/logging?utm_source=chatgpt.com)

---

# Hands-on exercise

Take the `analyze_numbers` example and implement these changes:

```
1. Send ctx.debug(), ctx.info(), ctx.warning() and ctx.error().
2. Add structured extra fields.
3. Capture them with FastMCP log_handler.
4. Add ordinary Python server logging.
5. Verify the two streams are conceptually separate.
6. Run over stdio and ensure diagnostics never pollute stdout.
7. Add AuditMiddleware with redacted arguments.
8. Enable OpenTelemetry.
9. Inspect one tool trace and locate the SERVER span.
10. Add one custom span around an artificial downstream API call.
```

The test for understanding is being able to explain:

```
ctx.info(...)
       ≠
logger.info(...)
       ≠
progress notification
       ≠
ToolResult
       ≠
OpenTelemetry span
```

They solve different problems.

## Next lesson — Pagination + Completion

Next we should cover two smaller but important protocol utilities together:

```
Pagination
    → how MCP enumerates large Tool/Resource/Prompt collections safely

Completion
    → how clients autocomplete Prompt arguments
      and Resource Template parameters
```

That lesson will introduce **opaque cursors, stable ordering, cache behavior, argument references, completion context, and FastMCP's `@mcp.completion` abstraction**.