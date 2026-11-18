# MCP Server with Streamable HTTP Transport

## Chunk 6 of 8 — §07. Production Concerns

**Version boundary:**

> This chapter applies production reasoning to MCP `2025-11-25`. Its optional
> HTTP sessions and server-initiated requests create deployment constraints that
> are different from later stateless protocol revisions.

**Learning outcome:**

> Design the security, scaling, reliability, configuration, and observability
> boundaries around a Streamable HTTP server without confusing them with MCP
> message semantics.

## §07. Move from a Concept Exercise to a Service

The concept exercise proved one client/server interaction. Production adds
untrusted networks, multiple users, failures, process restarts, proxies, and
parallel workers.

```text
MCP host
   |
   | HTTPS + authorization
   v
reverse proxy or gateway
   |
   | validated MCP traffic
   v
MCP server workers ---- durable database
   |                    audit and operation state
   +---- session/event infrastructure, when required
```

Each boundary solves a different problem. TLS does not authorize a tool call.
A session store does not make a business operation idempotent. An SSE stream
does not make a result durable.

## 7.1 Transport Security

### Validate `Origin`

Streamable HTTP servers must validate the HTTP `Origin` header when it is
present. This protects locally running servers from DNS rebinding attacks.

For local development, bind to `127.0.0.1`, not `0.0.0.0`, unless remote access
is an explicit and secured requirement.

```text
Untrusted web page
       |
       | forged browser request
       v
Origin validation ---- reject with HTTP 403
       |
       +------------- valid request to MCP endpoint
```

`Origin` validation is not authentication. It answers whether a browser origin
is allowed to reach the endpoint, not which user is making the request.

### CORS is not access control

Cross-Origin Resource Sharing (CORS) controls browser behavior. Non-browser
clients are not constrained by it. Configure a narrow origin allowlist for
browser-based hosts, expose only required headers, and enforce authentication
and authorization independently.

If a browser client must read the optional session header, expose
`MCP-Session-Id`. Do not use `*` with credentials in production.

### Authenticate the connection

Remote MCP servers should use the MCP authorization framework rather than an
invented token exchange. Validate bearer tokens for the MCP resource, including
issuer, audience, signature, expiry, and required scopes.

Do not accept tokens intended for another service. Do not forward a client's
MCP access token to an unrelated downstream API.

### Authorize every operation

Tool discovery and tool execution are separate decisions. A tool being visible
does not grant permission to invoke it, and a successful elicitation response
does not grant business authorization.

Check at least:

- authenticated subject;
- tenant or organization boundary;
- operation-specific scope or role;
- ownership of the target record;
- side-effect sensitivity;
- current business state.

### Treat inputs and metadata as untrusted

Validate tool arguments against both their JSON Schema and domain rules. Bound
request bodies, string lengths, collection sizes, page sizes, and concurrency.

Treat tool annotations, resource contents, prompt text, URLs, icons, and custom
metadata as untrusted. Do not interpolate them into commands, SQL, HTML, logs,
or model instructions without the appropriate validation or escaping.

### Elicitation safety

Form-mode elicitation must not request passwords, API keys, access tokens, or
payment credentials. Use URL mode for sensitive out-of-band workflows and show
the user the target domain before navigation.

Bind user-related state to authenticated identity, not only to an
`MCP-Session-Id`. A session ID is a routing and protocol value, not proof of
identity.

## 7.2 Session and State Design

### Optional protocol sessions

In `2025-11-25`, a Streamable HTTP server may issue an `MCP-Session-Id` during
initialization. If it does, later requests with that ID must reach server state
that recognizes the session.

```text
Initialize -> worker A creates session S
Request S  -> worker A, or infrastructure that can recover S
```

A load balancer can satisfy this in several ways:

- session affinity routes the session to the same worker;
- shared session infrastructure lets multiple workers locate protocol state;
- a gateway owns the client session and delegates business work downstream.

These are implementation patterns, not MCP requirements.

### Do not serialize suspended coroutines

Putting a session dictionary in Redis does not preserve a suspended Python
stack, an open socket, an async task, or an in-flight elicitation callback.

For recoverable interactive workflows, store explicit continuation data such
as:

- operation ID;
- authenticated subject and tenant;
- completed step;
- validated input already received;
- next allowed transition;
- expiry and replay protection.

Then design a deliberate reentry or status interface. Do not assume another
worker can resume an arbitrary coroutine from serialized variables.

### Separate durable business state

Committed records and audit events belong in durable storage with transaction
boundaries. The optional protocol session must not be the only place that
records whether money moved, a ticket closed, or a migration completed.

## 7.3 Scaling

### Scale the business work first

Measure whether the bottleneck is CPU, database I/O, downstream APIs, network
bandwidth, or too many open streams. Adding workers without evidence can create
more database contention or session-routing failures.

For long-running work, consider separating orchestration from execution:

```text
MCP request handler
      |
      +--- validate and authorize
      +--- create operation record
      +--- dispatch bounded work
      |
      +--- report progress or return operation handle
```

MCP `2025-11-25` includes task-related features, but SDK and host support must
be verified independently. A durable application job model remains useful even
when protocol task support is unavailable.

### Bound resources

Set explicit limits for:

- concurrent tool calls per subject and tenant;
- active sessions and SSE connections;
- queued work and queue age;
- request and response size;
- progress-event frequency;
- elicitation wait time;
- downstream connection pools.

An unbounded async queue is not backpressure. It only postpones failure while
memory use grows.

### Proxy behavior

A reverse proxy may buffer SSE data, terminate idle connections, rewrite paths,
or generate redirects. Verify the exact `/mcp` path and test event arrival at
the client, not only event creation in the server log.

For an SSE-capable route, typical proxy concerns include:

- disabling response buffering for the MCP route;
- preserving HTTP request bodies and relevant headers;
- using timeouts appropriate to expected calls;
- passing the original scheme and host safely;
- avoiding cross-origin redirects;
- allowing `POST`, optional `GET`, and optional session `DELETE`.

Do not disable buffering globally when only the MCP route needs it.

## 7.4 Reliability

### Timeouts

Apply separate timeouts to different phases:

- connection establishment;
- request processing;
- downstream API or database calls;
- elicitation waiting;
- idle sessions;
- stream reconnection.

A single large timeout hides which boundary failed. Elicitation waits should
have a clear user-visible outcome when they expire.

### Cancellation

Closing an SSE connection does not cancel an MCP request. The client sends an
explicit cancellation notification that identifies the request being
cancelled.

The server should propagate cancellation to cancellable downstream work and
stop progress notifications. Some side effects cannot be rolled back, so report
their actual status rather than promising cancellation succeeded.

### Resumability

Transport resumability can replay missed SSE messages using event IDs and
`Last-Event-ID`. It does not rerun the business operation and does not by itself
make a tool call safe to repeat.

Maintain event history only for a bounded time and scope it to the correct
stream. Event IDs must not leak data or become authorization credentials.

### Idempotency and unknown outcomes

If a connection fails after a side effect, the client may not know whether the
operation completed. Use an application operation ID or idempotency key and
provide a way to query the operation outcome.

```text
retry decision
    |
    +--- known not executed -> may retry
    +--- known completed ----> return recorded outcome
    +--- outcome unknown ----> query or reconcile first
```

Never retry a write merely because no final response arrived.

### Graceful shutdown

During deployment or shutdown:

1. stop accepting new work;
2. mark the instance unready;
3. allow a bounded drain period;
4. cancel or hand off supported work safely;
5. close sessions and dependencies;
6. record incomplete operation state for recovery.

## 7.5 Configuration

Production settings should be typed, validated once at startup, and shared by
local and containerized execution. Typical settings include:

- public MCP endpoint and allowed origins;
- OAuth resource and issuer metadata;
- required scopes;
- database URL and pool limits;
- request, elicitation, and shutdown timeouts;
- body, session, and concurrency limits;
- log level and telemetry endpoints.

Store local secrets in an uncommitted `.env` file only when needed. Commit a
`.env.example` containing names and safe placeholders. Use
`pydantic-settings` for production configuration and fail startup when a
required value is missing or invalid.

Do not introduce configuration libraries into the earlier concept exercise;
they solve deployment problems, not protocol fundamentals.

## 7.6 Observability

### Logs

Record structured events such as:

- method and tool name;
- request or operation ID;
- authenticated subject or pseudonymous identifier;
- tenant boundary;
- session lifecycle event, when sessions are enabled;
- duration and final outcome;
- cancellation or timeout reason;
- downstream dependency and status.

Do not log access tokens, session IDs, elicitation form contents, secrets, or
full sensitive tool results.

### Metrics

Useful service-level metrics include:

- request rate, latency, and error rate by method;
- active sessions and SSE streams;
- tool duration and outcome;
- progress and elicitation message rate;
- elicitation response latency and timeout count;
- reconnect and replay count;
- queue depth and downstream latency;
- authorization denials and rate-limit decisions.

### Traces

Trace the host-facing request through authorization, tool dispatch, business
services, and dependencies. Keep transport request IDs, trace IDs, and business
operation IDs distinct even when logs show them together.

## 7.7 Deployment Review

Before exposing a remote server, verify:

- the exact protocol revision and SDK behavior;
- host support for required capabilities;
- HTTPS and authorization metadata;
- `Origin` and host validation;
- tool-level authorization and tenant isolation;
- request and concurrency limits;
- proxy buffering, routing, and timeouts;
- session routing or shared state, if sessions are used;
- idempotency and recovery for writes;
- graceful shutdown behavior;
- logs, metrics, traces, and secret redaction.

## Trade-offs

**Stateful sessions:**

> Make server-initiated requests natural in `2025-11-25`, but complicate
> worker routing, expiry, draining, and recovery.

**Frequent progress:**

> Improves perceived responsiveness, but increases traffic and callback load.
> Aggregate updates to the frequency users and operators actually need.

**Long synchronous tool calls:**

> Keep one simple request lifecycle, but increase timeout and unknown-outcome
> risks. Durable operation handles are often clearer for work lasting minutes.

**Session affinity:**

> Is simple for a small deployment, but can create uneven load and loses active
> operations when a worker disappears unless business recovery is separate.

## Summary

- Validate `Origin`, authenticate the caller, and authorize every operation.
- CORS and TLS do not replace authorization.
- Bind user state to authenticated identity, not only a session ID.
- Optional sessions create worker-routing and lifecycle constraints.
- Redis cannot serialize an in-flight Python coroutine.
- Bound connections, queues, progress frequency, waits, and message sizes.
- Disconnection, cancellation, resumability, and retry are distinct events.
- Use operation IDs and idempotency for side effects.
- Observe protocol, transport, and business outcomes separately.

**Professional articulation:**

> “For MCP `2025-11-25`, the main production constraint is the stateful
> back-channel needed by server-initiated requests. We separate that transport
> state from authenticated business state and design recovery explicitly.”

## Official References

- [MCP `2025-11-25`: Streamable HTTP security and sessions](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [MCP `2025-11-25`: Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
- [MCP `2025-11-25`: Security best practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices)
- [MCP `2025-11-25`: Cancellation](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation)
- [MCP `2025-11-25`: Elicitation security](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)

## Next

Continue with [chunk 7: architecture decisions and common mistakes](chunk-7.md).
