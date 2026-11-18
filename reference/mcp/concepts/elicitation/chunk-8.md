# MCP Server with Streamable HTTP Transport

## Chunk 8 of 8 — §§13–18. Practice and Troubleshooting

**Version boundary:**

> This final chapter reinforces MCP protocol revision `2025-11-25`. It does not
> mix the initialization and session model with later stateless revisions.

**Learning outcome:**

> Extend the examples safely, diagnose failures by layer, and explain the full
> Streamable HTTP interaction in professional terms.

## §13. Optional Practice

These exercises demonstrate software behavior. They are not quizzes or
assessments. Start from the runnable project in chunk 4 or 5.

### Exercise 1 — Unknown total

Change the progress tool so it does not know the final total when work starts.
Send increasing `progress` values and omit `total` until it becomes known.

**Expected behavior:**

> The client receives useful progress messages even though it cannot calculate
> a percentage. The final JSON-RPC response still determines completion.

**Design note:**

> Do not send a fake total merely to display a percentage. A truthful count and
> human-readable message are more useful.

### Exercise 2 — Decline and cancel

Run the elicitation example twice:

1. return `types.ElicitResult(action="decline")`;
2. return `types.ElicitResult(action="cancel")`.

**Expected behavior:**

> The tool returns distinct final statuses. Neither response is treated as
> approval, and neither contains form content.

### Exercise 3 — Capability missing

Remove `elicitation_callback` from the `ClientSession`, then call the tool that
requires elicitation.

**Expected behavior:**

> The client does not advertise elicitation support. The call should fail
> clearly rather than silently selecting a default answer.

### Exercise 4 — Client disconnect

Stop the client while a progress-producing tool is running.

Observe these separate questions:

- Did the HTTP connection close?
- Did the server cancel the operation?
- Did the business work continue?
- Was any durable state committed?
- Can the client determine the final outcome?

**Expected conclusion:**

> A disconnect does not itself answer the other questions. Cancellation,
> operation state, and retry safety require explicit design.

### Exercise 5 — Bounded large result

Change a tool that would return 10,000 records so it instead returns:

```json
{
  "matched": 10000,
  "returned": 100,
  "next_cursor": "opaque-cursor",
  "summary": "First page of matching records"
}
```

Alternatively, return a resource URI for a completed report.

**Expected behavior:**

> The final result remains bounded. Progress and transport streaming are not
> misused as an unbounded data API.

## §14. Mental Model

Use this compact model when reading logs or reviewing a design:

```text
Host owns model and user experience
  |
  +-- MCP client owns protocol interaction with one server
          |
          +-- Streamable HTTP carries JSON-RPC messages
                  |
                  +-- MCP server exposes tools/resources/prompts
                          |
                          +-- business service owns domain behavior
```

For one interactive tool call:

```text
initialize -> initialized -> tools/call
                     |
                     +-- progress notification, optional
                     +-- elicitation request, optional
                     +-- client response to elicitation
                     +-- one final tool response
```

### Distinctions to retain

**SSE versus MCP message:**

> SSE is transport framing. A JSON-RPC request, response, or notification is the
> protocol message carried inside it.

**Progress versus partial result:**

> Progress describes work status. It does not append data to the final tool
> result.

**MCP client versus model:**

> The host's client speaks MCP. The model may influence tool selection but is
> not normally the network protocol endpoint.

**Session versus business operation:**

> A protocol session negotiates communication. A business operation needs its
> own durable identity and recovery rules when the outcome matters.

**Elicitation versus sampling:**

> Elicitation obtains user input. Sampling asks the client to obtain model
> generation. They use different methods and capabilities.

## §15. Troubleshooting by Layer

Diagnose the first boundary that failed instead of changing every component at
once.

### Layer 1 — Process and socket

**Symptom:** connection refused.

**Meaning:**

> No process is accepting connections at the requested host and port, or a
> network policy blocks the connection.

**Check:**

- Is the server running?
- Is it bound to the expected interface and port?
- Is the client using `127.0.0.1` for a local exercise?

### Layer 2 — HTTP routing

**Symptom:** HTTP `404` before initialization.

**Meaning:**

> The request probably reached an HTTP server but not the intended MCP route.

**Check:**

- Is the URL exactly `/mcp` or the configured path?
- Did a reverse proxy remove or duplicate a path prefix?
- Did a trailing-slash redirect change origin or scheme?

An HTTP `404` with an existing `MCP-Session-Id` has another defined meaning: the
session is no longer recognized, so the client must initialize a new session.

### Layer 3 — Transport headers

**Symptom:** HTTP `400`, `403`, `405`, `406`, or `415`.

**Check:**

- `Content-Type: application/json` on JSON request bodies;
- `Accept: application/json, text/event-stream` on `POST`;
- `MCP-Protocol-Version: 2025-11-25` after initialization;
- the server-issued `MCP-Session-Id`, when one exists;
- valid `Origin` and host configuration;
- supported HTTP method.

Do not manually add a session ID that the server never issued.

### Layer 4 — Lifecycle

**Symptom:** normal requests are rejected immediately after connecting.

**Check:**

1. Was `initialize` the first interaction?
2. Did the client accept the negotiated version?
3. Did the client send `notifications/initialized`?
4. Are subsequent requests using the same optional session?

The server returns `InitializeResult`; it does not send an “initialized
response.”

### Layer 5 — Capability negotiation

**Symptom:** elicitation, sampling, roots, or a notification feature fails.

**Check:**

- Did the correct side advertise the capability?
- Does the peer support the selected mode?
- Is the client callback or host UI actually implemented?
- Is the connection using protocol revision `2025-11-25`?

A server must not send `elicitation/create` to a client that did not advertise
elicitation support.

### Layer 6 — MCP method and schema

**Symptom:** JSON-RPC method-not-found or invalid-parameters error.

**Check:**

- Is the method exactly `tools/call`, `tools/list`, or
  `elicitation/create`?
- Does `params` match the versioned schema?
- Is the tool name listed by `tools/list`?
- Do the arguments match the tool's `inputSchema`?

`stream/chunk`, `elicitation/request`, and `elicitation/result` are not standard
methods for this protocol revision.

### Layer 7 — Business execution

**Symptom:** the tool returns `isError: true` or an application error.

**Check:**

- input validation and authorization;
- downstream API or database availability;
- transaction outcome;
- timeout and cancellation handling;
- operation or idempotency record.

The transport can be healthy while the business operation fails.

### Layer 8 — Delayed progress

**Symptom:** all progress appears at once near completion.

**Check:**

- Did the caller provide a progress callback or token?
- Is the server actually sending `notifications/progress`?
- Is a reverse proxy buffering the response?
- Is synchronous work blocking the event loop?
- Are updates rate-limited too aggressively?

Observe timestamps at the server, proxy, and client to locate the delay.

### Layer 9 — Missing final result

**Symptom:** progress reached the expected total, but no final result arrived.

**Meaning:**

> The operation is not known to have completed successfully. Progress is not a
> substitute for the final JSON-RPC response.

Check server errors, cancellation, session expiry, proxy timeout, and durable
operation status before retrying.

## §16. Debugging Patterns

### Incorrect: async generator as a tool-result stream

```python
async def report():
    yield "row 1"
    yield "row 2"
```

This is only a Python generator. It does not define MCP partial results.

### Correct: progress plus one result

```python
async def report(ctx):
    await ctx.report_progress(1, 2, "row 1 processed")
    await ctx.report_progress(2, 2, "row 2 processed")
    return {"processed": 2}
```

The context type and decorator are omitted here only to focus on the contrast;
use the complete runnable example in chunk 4.

### Incorrect: custom reply endpoint

```text
POST /elicit/{session_id}
```

### Correct: JSON-RPC response to the MCP endpoint

```text
POST /mcp
MCP-Session-Id: <only when issued by the server>

{"jsonrpc":"2.0","id":"ask-1","result":{"action":"accept","content":{...}}}
```

### Incorrect: retry on transport error

```text
connection failed -> repeat write
```

### Correct: reconcile before retry

```text
connection failed
      |
      +-- query operation ID
              +-- completed -> return recorded result
              +-- not started -> retry safely
              +-- unknown -> reconcile or escalate
```

## §17. Continue Learning

The maintained MCP course separates the next topics so each can be learned
without overloading this transport guide:

1. [Progress, streaming, and final results](../12-progress-streaming.md)
2. [Elicitation and additional user input](../13-elicitation.md)
3. [Continuation state and safe reentry](../14-continuation-state.md)
4. [Async I/O and concurrent requests](../15-async-concurrency.md)
5. [Host validation, Origin, and CORS](../19-origin-cors.md)
6. [OAuth discovery and delegated access](../20-oauth-discovery.md)
7. [Timeouts, cancellation, retries, and idempotency](../25-reliability.md)
8. [Reading and migrating legacy MCP examples](../31-legacy-migration.md)

When moving to another protocol revision, start with its lifecycle and
transport specification. Do not migrate by changing only a version string or
an import path.

## §18. Final Reference

### Core vocabulary

| Term | Meaning |
|---|---|
| Host | Application that owns model integration and user experience |
| MCP client | Host-side protocol component connected to one server |
| MCP server | Provider of negotiated tools, resources, and prompts |
| Streamable HTTP | MCP JSON-RPC over one HTTP endpoint with optional SSE |
| SSE | Server-to-client event framing within an HTTP response |
| Progress token | Correlation value for progress notifications |
| Final result | JSON-RPC response that completes the tool request |
| Elicitation | `elicitation/create` request for user input |
| Session ID | Optional server-issued HTTP session header value |
| Operation ID | Application identifier for durable work and recovery |

### Final sequence

```text
1. Client POSTs initialize.
2. Server returns InitializeResult and may issue MCP-Session-Id.
3. Client POSTs notifications/initialized.
4. Client discovers tools with tools/list.
5. Client POSTs tools/call, optionally with progressToken.
6. Server may send progress notifications over SSE.
7. Server may send elicitation/create after capability negotiation.
8. Client POSTs the elicitation JSON-RPC response.
9. Server sends one final tools/call response.
10. Application records durable outcomes independently of transport state.
```

### Final rules

- One MCP endpoint; no invented session or reply routes.
- Complete JSON-RPC messages inside SSE events.
- One final result per normal tool call.
- Progress is status, not partial business output.
- Elicitation is user input, not model sampling or authorization.
- Session IDs are optional and must be treated securely.
- Disconnect is not cancellation.
- Resumability is not idempotency.
- Protocol session state is not durable business state.
- Host feature support must be verified independently of the specification.

**Professional articulation:**

> “MCP `2025-11-25` Streamable HTTP sends client messages as POST requests to
> one endpoint and can carry server messages over SSE. Optional progress and
> elicitation occur before one final tool response, while authorization,
> idempotency, and durable recovery remain application responsibilities.”

## Official References

- [MCP `2025-11-25`: Architecture](https://modelcontextprotocol.io/specification/2025-11-25/architecture)
- [MCP `2025-11-25`: Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [MCP `2025-11-25`: Streamable HTTP](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [MCP `2025-11-25`: Progress](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/progress)
- [MCP `2025-11-25`: Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [MCP `2025-11-25`: Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)

## Course Completion

All eight chunks now use the same MCP `2025-11-25` protocol model.
