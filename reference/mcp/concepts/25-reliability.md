# Timeouts, cancellation, retries, and idempotency

**Outcome:** Design a retry policy around operation outcomes rather than connection symptoms.

**Prerequisites:** [14: Continuation state and safe reentry](14-continuation-state.md), [16: Service layers and persistence](16-service-persistence.md), [18: Uvicorn, workers, and process state](18-process-runtime.md).

## A lost response is an uncertain outcome

A client asks to close a ticket. The database commits, but the network drops
before the response arrives. The client sees failure while the business action
has succeeded.

```
request --> commit --> response lost
   |
   +---- retry?
```

Retrying blindly may duplicate audit records, notifications, or other effects.
Transport success and business completion are different observations.

## Give the operation a stable identity

Idempotency means repeating the same intended operation has the same
business effect as applying it once. Use a stable operation key, bind it to
the caller and arguments, and persist its outcome.

A JSON-RPC request ID is for one message exchange. A retry can have a new
request ID while preserving the same business operation key. Reusing an
operation key with different arguments should be rejected or handled under an
explicit contract.

The [continuation model](../labs/continuation_model.py) demonstrates sequential
result reuse. Production requires atomic claim/commit behavior and durable
storage, not only a dictionary.

## Set budgets

Use an overall operation deadline, then allocate smaller budgets to database
and upstream calls. If every nested layer independently retries for a minute,
one user request can consume several minutes and create excess load.

Retry only failures that may be transient and whose operation semantics permit
retry. Add bounded backoff and jitter to avoid synchronized bursts. Invalid
arguments and denied access usually need correction, not repetition.

## Cancellation is best effort

In modern HTTP MCP, closing a request's SSE response stream provides a
cancellation signal. Stdio uses a cancellation notification for the relevant
request. The transport rule does not roll back a completed database transaction
or recall an external email.

Cancellation handling should stop unnecessary work and release resources.
For important writes, make the outcome queryable so the host can reconcile
what happened.

## Reconnection is not replay

Modern Streamable HTTP does not retain the earlier SSE event-ID replay
mechanism. After a broken response stream, the request must be reissued under
the current rules. This makes application operation identity especially
important for side effects.

Legacy resumability, even where implemented, is about message delivery. It
does not itself establish exactly-once business execution.

## Worked response

When the close-ticket response is lost, the client queries the operation
outcome or retries with the same operation key. The service returns the
recorded result instead of closing and notifying twice.

**Professional articulation:**

> “We distinguish retryable transport failures from uncertain business
> outcomes, and reconcile writes using durable operation identities.”

## Sources and next step

- [Archive: conversations/chunks/04-mcp-chunk4.md](../../conversations/chunks/04-mcp-chunk4.md)
- [Archive: conversations/streamable/streamable-6.md](../../conversations/streamable/streamable-6.md)
- [Archive: _learning_resources/enhancements.md](../../_learning_resources/enhancements.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/cancellation) — checked 2026-11-15.

Next: [Pagination, caching, and subscriptions](26-pagination-cache.md).

