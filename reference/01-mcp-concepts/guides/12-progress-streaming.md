# Progress, streaming, and final results

**Outcome:** Distinguish work progress from returned data, SSE framing, and model-token streaming.

**Prerequisites:** [11: Streamable HTTP](11-streamable-http.md).

## Five ideas that are easy to confuse

A long-running ticket report might send progress while it works, return one
final report, and cause a host to stream a natural-language explanation
afterwards. A dashboard might also show its own UI events. These are separate
contracts.

**MCP progress:**

> Structured status information, such as “30 of 100 records checked.” Progress
> is temporary information for a client handler; it is not the operation's
> result.

**Final tool result:**

> The completed operation's result, such as a report URI and summary. One final
> response establishes protocol completion or failure.

**Server-Sent Events (SSE):**

> Transport framing that can carry complete JSON-RPC messages in an HTTP
> response stream. SSE does not decide what those messages mean.

**Model-token streaming:**

> Words or tokens produced incrementally by a language model for a chat
> interface. This is not MCP tool progress.

**Application UI event:**

> A custom message that changes a dashboard or panel. It is an application
> contract unless a particular MCP extension defines it.

```
SSE response stream
    |
    +-- may carry an MCP progress notification
    +-- later carries the final JSON-RPC response

Host model stream --------> chat tokens
Dashboard event channel --> UI changes
```

## Trace one report

```
call report
    |
    +---- progress 10/100
    +---- progress 60/100
    +---- progress 100/100
    |
    +---- final result: report location
```

Completion is established by the operation's final response, not by guessing
from a progress percentage. Even `100%` progress does not prove success; work
may fail while producing or delivering the final result.

Protocol progress uses a progress token associated with the request. A
request can opt into progress without turning its final result into a
sequence of arbitrary application chunks. The host must have somewhere to
route those notifications.

An SSE-framed progress message has this conceptual shape:

```
data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"report-7","progress":40,"total":100}}

```

The `data` field contains one complete JSON-RPC notification. It is not a
fragment of the final report.

## Why a Python generator is insufficient

**Returning a list of progress strings:**

> The caller receives the list only as final result data. It does not observe
> progress while work is running.

**Writing an async generator:**

> `yield` produces Python values. It does not automatically define MCP
> partial-result or progress semantics.

**Adding `[DONE]`:**

> MCP completion is established by the final JSON-RPC response. `[DONE]` is not
> a standard MCP sentinel.

An HTTP streaming response emits bytes. An MCP progress API emits a
protocol-defined notification. These mechanisms can be composed, but one does
not automatically implement another.

The archive's `stream/chunk`, `elicitation/request`, and `[DONE]`
examples must be treated as custom application conventions, not copied as
standard MCP messages.

If a large report cannot fit comfortably in one result, return a bounded
summary and a resource or explicit pagination interface. A separate UI stream
can show application-specific rows if its contract and client are under your
control.

## Timing and backpressure

Backpressure means a slow consumer limits the producer's output rate. An
unbounded event queue can exhaust memory even when each update is small.
Aggregate progress, bound queue sizes, and avoid emitting one event for every
database row without a measured need.

A reverse proxy may buffer an SSE response. The server can generate events
correctly while the client receives them in a burst. Measure client arrival
times as well as server emission times.

## A useful observation

In a report design, record the moment work starts, each visible update, and
the final response. A smooth animation is not evidence that partial business
results are durable or that a retry is safe.

## Model progress separately from the final value

This standard-library example makes the two channels visible. It is a concept
model, not MCP wire code:

```python
import asyncio
from collections.abc import Callable


async def build_report(on_progress: Callable[[int], None]) -> dict:
    for percent in (25, 50, 75, 100):
        await asyncio.sleep(0.01)
        on_progress(percent)
    return {"report_id": "R-7", "status": "complete"}


async def main() -> None:
    result = await build_report(lambda value: print(f"progress={value}%"))
    print(result)


asyncio.run(main())
```

The callback reports temporary progress. The returned dictionary is the one
final result. An MCP implementation must map these ideas to the progress and
result mechanisms supported by its pinned protocol and framework versions.

The framework or SDK normally handles JSON-RPC IDs, SSE framing, progress-token
correlation, and result serialization. The tool owns its business work: when
progress is meaningful and what the final result represents.

**Professional articulation:**

> “We expose progress for responsiveness and a separate final result for
> correctness. Transport streaming does not define business completion.”

## Sources and next step

- [Archived streamable transport notes](../../../_archive/streamable/streamable-3.md)
- [Archived streaming notes](../../../_archive/streamable/streamable-4.md)
- [Archived MCP walkthrough](../../02-fast-mcp/walk-through-docs/walkthrough_doc.md)
- [Legacy progress distinctions](../elicitation/chunk-2.md)
- [Legacy pinned progress exercise](../elicitation/chunk-4.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress) — checked 2026-11-15.

Next: [Elicitation and additional user input](13-elicitation.md).

