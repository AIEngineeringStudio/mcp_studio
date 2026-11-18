# MCP Server with Streamable HTTP Transport

## Chunk 7 of 8 — §§08–12. Architecture Decisions

**Version boundary:**

> All MCP behavior in this chapter refers to protocol revision `2025-11-25`.
> Examples are representative designs, not claims about named companies or
> products unless an official source explicitly documents them.

**Learning outcome:**

> Select Streamable HTTP for the right boundary, explain its trade-offs, and
> recognize common design errors before implementation.

## §08. Representative Usage

### Remote tool service

An enterprise host calls a separately deployed MCP server that provides
read-only ticket tools.

```text
AI host -- HTTPS Streamable HTTP --> ticket MCP server --> ticket API
```

Streamable HTTP is useful because the server runs independently and can report
progress for a slow search. The final tool result remains a bounded summary or
resource reference.

### Human-confirmed batch operation

A migration tool processes a preview batch, reports progress, and asks the user
whether to continue.

```text
tools/call
   +--- progress: preview completed
   +--- elicitation/create: continue?
   +--- user response
   +--- authorized transaction
   +--- final result
```

Elicitation gathers the decision. The service still verifies permissions and
protects writes with an operation ID.

### Sensitive third-party connection

A server needs the user to authorize access to a third-party service. It uses
URL-mode elicitation so credentials never pass through the MCP client.

```text
Server -> client: approved external URL
Client -> user: show domain and request consent
User -> external service: complete authorization
Server -> client: optional completion notification
```

This is not the same as authorizing the MCP client's access to the MCP server.
The MCP authorization framework handles that relationship separately.

### Large report

A tool should not stream thousands of report rows as invented partial tool
results. A better contract is:

1. report progress while generating the report;
2. store the completed artifact in an authorized location;
3. return a bounded summary and resource URI;
4. paginate any interactive record browsing.

## §09. Best Practices

### Keep protocol and business contracts separate

The MCP layer translates requests, capabilities, results, and errors. A service
layer owns business rules, authorization, transactions, and durable state.

```text
MCP transport -> MCP handler -> business service -> repository or API
```

This separation lets the same business behavior be tested without HTTP or an
LLM.

### Negotiate before using optional features

Do not send elicitation, sampling, roots, subscriptions, or change
notifications merely because the server code supports them. Use only features
advertised by the peer for the negotiated protocol revision.

### Return bounded results

Tool results must fit the host's memory and model-context constraints. Prefer:

- small structured results;
- cursor pagination;
- resources for large readable content;
- operation handles for durable long-running work;
- summaries with explicit truncation information.

### Report progress intentionally

Send progress only when the caller supplied a progress token. Keep progress
monotonic and rate-limited. Stop sending notifications after the request
finishes.

Do not use progress percentage as proof of completion. The final JSON-RPC
response establishes the result.

### Treat user interaction as untrusted input

Show which server is asking, what will happen, and which fields are required.
Let the user review form input and choose accept, decline, or cancel.

Validate the returned data again on the server. Never interpret a missing or
malformed response as approval.

### Make writes recoverable

For side-effecting tools, use an application operation ID and idempotency
strategy. Record final status durably so a client can reconcile an unknown
outcome after a disconnect.

### Test the actual boundary

Test in layers:

1. business function without MCP;
2. MCP tool through an in-memory transport;
3. Streamable HTTP on loopback;
4. reverse proxy and TLS in staging;
5. host compatibility for optional features;
6. failure injection for disconnect, timeout, cancellation, and restart.

A browser `GET /mcp` is not a complete MCP test.

## §10. Worked Architecture Case

### Requirement

A support organization wants an AI host to generate a customer-ticket report:

- search up to 50,000 tickets;
- show progress;
- ask before including archived tickets;
- return a downloadable report;
- isolate tenants;
- survive worker restarts without duplicating the report.

### Simplest correct design

```text
Host
  |
  | HTTPS Streamable HTTP
  v
MCP gateway or server
  |-- authenticate and authorize tenant
  |-- validate report request
  |-- create operation ID
  |-- elicit archive choice before dispatch
  v
Report worker ---- ticket store
  |
  +---- durable operation and artifact store
```

### Why this design

**Elicit before expensive work:**

> The archived-ticket choice changes the query. Gathering it first avoids
> wasted work and prevents partial side effects before user intent is known.

**Use durable operation state:**

> The report may outlive an HTTP connection or worker. Operation status does
> not depend on a suspended MCP request remaining in memory.

**Keep the final result small:**

> Return report metadata, a summary, and an authorized resource or download
> reference rather than all rows.

**Use progress for experience, not correctness:**

> Progress may be delivered while the request is active. The durable operation
> record remains the source of truth after a reconnect.

### Successful trace

```text
1. Host initializes and negotiates elicitation support.
2. Host calls create_ticket_report.
3. Server authorizes the tenant.
4. Server elicits whether archived tickets are included.
5. User accepts and chooses “no.”
6. Server creates operation R-104 and dispatches work.
7. Server reports progress while the request remains active.
8. Worker stores the report artifact and marks R-104 completed.
9. Tool returns a summary and report URI.
```

### Failure trace

```text
1. Operation R-104 is created.
2. The network disconnects after work starts.
3. Client does not blindly repeat create_ticket_report.
4. Client queries R-104 through a documented status tool.
5. Server returns completed status and the existing report URI.
```

The application operation ID solves recovery. SSE event replay alone would
only recover messages retained for a stream.

## §11. Transport Comparison

### Streamable HTTP versus stdio

| Concern | Streamable HTTP | stdio |
|---|---|---|
| Process boundary | Remote or local service | Server child process |
| Network security | Required for remote use | Usually inherited from host |
| Authentication | Relevant for remote endpoint | Usually environment/process based |
| Scaling | Independent deployment possible | Normally one process per host connection |
| Best fit | Shared remote service | Local tool integration |

Both are standard MCP transports. The choice changes deployment and trust
boundaries, not tool semantics.

### Streamable HTTP versus deprecated HTTP+SSE

The `2025-11-25` Streamable HTTP transport uses one MCP endpoint for client
messages. The older HTTP+SSE transport from `2024-11-05` used distinct endpoint
behavior and is retained only for compatibility.

Do not call every SSE-based implementation “Streamable HTTP.” Inspect its
initialization request and endpoint arrangement.

### Streamable HTTP versus WebSocket

WebSocket is not a standard MCP transport in `2025-11-25`. An implementation
may define it as a custom transport, but both peers must agree on framing,
security, lifecycle, and compatibility.

Streamable HTTP fits existing HTTP gateways, authorization mechanisms, and
observability. WebSocket provides a full-duplex connection but creates its own
proxy, scaling, and reconnection concerns.

### Streamable HTTP versus gRPC

gRPC is a different remote-procedure-call ecosystem. It provides typed service
definitions and streaming modes but is not the MCP wire protocol.

Use gRPC behind an MCP server when it is the right internal service boundary.
Do not label a gRPC API as MCP merely because an AI application calls it.

### Decision guide

Choose Streamable HTTP when:

- the MCP server must run independently of the host;
- remote authentication and authorization are required;
- standard HTTP infrastructure is valuable;
- the peer supports the same MCP revision and needed capabilities.

Choose stdio when:

- the server is local to the host;
- process isolation is enough;
- network deployment adds no useful capability;
- the host can manage the subprocess lifecycle.

Use a non-MCP API when the consumer does not need MCP discovery, capability
negotiation, or host interoperability.

## §12. Common Mistakes

### Mistake 1 — Treating `yield` as MCP streaming

An async generator is a Python mechanism. It does not define standard partial
tool results. Use progress notifications for progress and return one final
tool result.

### Mistake 2 — Inventing chunk messages and `[DONE]`

`stream/chunk`, arbitrary SSE objects, and `[DONE]` are not standard MCP
messages. The final JSON-RPC response completes a request.

### Mistake 3 — Inventing session routes

Paths such as `/session/{id}/message` and `/elicit/{id}` are not part of
Streamable HTTP. Use one MCP endpoint and, when the server issued one, the
`MCP-Session-Id` header.

### Mistake 4 — Assuming every session has an ID

Session IDs are optional. Code must follow the server's initialization response
and let the SDK manage the header. Do not fabricate an ID.

### Mistake 5 — Calling the MCP client the model

The host coordinates the model and creates MCP clients. The client is the
protocol component connected to one server.

### Mistake 6 — Using elicitation as authorization

An accepted form proves only that the client returned an accepted response. The
server still authenticates the caller and authorizes the business action.

### Mistake 7 — Requesting secrets in form mode

Passwords, API keys, access tokens, and payment credentials require URL mode so
the sensitive data does not pass through the MCP client.

### Mistake 8 — Retrying after every disconnect

The final outcome may be unknown. Query operation status or use an idempotency
key before repeating side effects.

### Mistake 9 — Assuming Redis resumes Python execution

Shared storage can hold explicit state. It cannot serialize and continue an
arbitrary in-flight coroutine, socket, or task group.

### Mistake 10 — Ignoring proxy buffering

The server can emit correct SSE events while the proxy delivers them in one
late burst. Measure at the client and configure only the relevant route.

## Review Checklist

- Is the protocol revision explicit?
- Are host, model, client, server, and tool roles distinct?
- Does every client message use the one MCP endpoint?
- Are optional features capability-gated?
- Are progress and final results separate?
- Is elicitation standard and safe for the data type?
- Are writes authorized, idempotent, and recoverable?
- Is protocol session state separate from durable business state?
- Are proxy, timeout, and shutdown behavior tested?
- Are examples labeled as examples rather than unsupported company claims?

## Summary

- Streamable HTTP is valuable for independently deployed MCP services.
- It is not automatically better than stdio for local integrations.
- Use standard progress, elicitation, and final-result messages.
- Large results need bounded contracts, resources, or pagination.
- Optional sessions affect routing but do not replace durable operation state.
- Compare transports by boundary and requirements, not by the word “streaming.”

**Professional articulation:**

> “We choose Streamable HTTP when MCP must cross a managed network boundary.
> We keep tool semantics independent of transport and add session affinity,
> recovery, and authorization only where the requirements justify them.”

## Official References

- [MCP `2025-11-25`: Architecture](https://modelcontextprotocol.io/specification/2025-11-25/architecture)
- [MCP `2025-11-25`: Streamable HTTP](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [MCP `2025-11-25`: Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [MCP `2025-11-25`: Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)

## Next

Continue with [chunk 8: practice and troubleshooting](chunk-8.md).
