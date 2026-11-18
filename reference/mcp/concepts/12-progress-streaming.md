# Progress, streaming, and final results

**Outcome:** Distinguish work progress from returned data, SSE framing, and model-token streaming.

**Prerequisites:** [11: Streamable HTTP](11-streamable-http.md).

## Four different meanings of streaming

A long-running ticket report might send progress while it works, return one
final report, and cause a host to stream a natural-language explanation
afterwards. A dashboard might also show its own UI events. These are separate
contracts.

| Information | Example | Consumer |
|---|---|---|
| Progress | 30 of 100 records checked | Client progress handler |
| Final tool result | Report URI and summary | Host/application |
| Model tokens | Words of the explanation | Chat UI |
| UI event | A panel changes state | Dashboard |

SSE is a way to carry events. It does not decide which of these meanings an
event has.

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
from a progress percentage. Work may fail after the last progress update.

Protocol progress uses a progress token associated with the request. A
request can opt into progress without turning its final result into a
sequence of arbitrary application chunks. The host must have somewhere to
route those notifications.

## Why a Python generator is insufficient

`yield` produces values in Python. An HTTP streaming response emits bytes.
An MCP progress API emits a protocol-defined notification. These mechanisms
can be composed, but one does not automatically implement another.

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

**Professional articulation:**

> “We expose progress for responsiveness and a separate final result for
> correctness. Transport streaming does not define business completion.”

## Sources and next step

- [Archive: conversations/streamable/streamable-3.md](../../conversations/streamable/streamable-3.md)
- [Archive: conversations/streamable/streamable-4.md](../../conversations/streamable/streamable-4.md)
- [Archive: _learning_resources/walkthrough_doc.md](../../_learning_resources/walkthrough_doc.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/progress) — checked 2026-11-15.

Next: [Elicitation and additional user input](13-elicitation.md).

