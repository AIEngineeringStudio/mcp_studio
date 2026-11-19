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

```text
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

```text
stdio: client notification -> server cancels work
HTTP:  response stream closes -> server cancels work
```

Cancellation is cooperative. Application code must propagate cancellation to
database queries, HTTP calls, queues, and other downstream work.

## Cancellation is not rollback

If a tool has already committed a side effect, cancelling the request does not
undo it. Design mutating operations with idempotency keys, transaction
boundaries, and status lookup.

```text
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

## Hands-on checkpoint

Run the transport-independent test suite, then read the focused guides:

```bash
cd reference/mcp/labs
uv run python -m unittest -q
```

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

