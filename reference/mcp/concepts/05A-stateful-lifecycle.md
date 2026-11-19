# Stateful connection lifecycle through MCP 2025-11-25

**Outcome:** Trace the legacy MCP initialization, operation, and shutdown
phases without confusing connection state, an optional HTTP session, and
durable application state.

**Prerequisites:**
[03: JSON-RPC requests, responses, and notifications](03B-json-rpc.md)
and [04: Protocol versions and capability discovery](04-versions-discovery.md).

## Version boundary

This guide describes the stateful connection lifecycle used by protocol
revisions through **2025-11-25**. The lifecycle begins with an `initialize`
request and ends when the underlying transport is closed.

MCP 2026-07-28 removed this handshake and protocol-level HTTP sessions. See
[05B: Stateless-first lifecycle](05B-stateless-lifecycle.md) for the modern
flow. Do not combine messages from the two eras into one trace.

The word *stateful* has a precise meaning here: the endpoints establish
connection-level facts that later messages rely on. It does not mean every
server must store business data in memory or issue an HTTP session ID.

## The three lifecycle phases

**Initialization:**

> The client proposes a protocol version and declares its capabilities and
> identity. The server selects a protocol version and returns its capabilities,
> identity, and optional instructions. The client then sends
> `notifications/initialized` to confirm readiness.

**Operation:**

> Client and server exchange normal MCP messages. Each endpoint must respect
> the selected version and use only capabilities established during
> initialization.

**Shutdown:**

> MCP defines no JSON-RPC `shutdown` method. The endpoints close the underlying
> transport. A legacy Streamable HTTP server that issued a session ID may also
> allow the client to terminate that session with HTTP `DELETE`.

```
Client                                      Server
  |                                           |
  |---- initialize -------------------------->|
  |<--- initialize result --------------------|
  |---- notifications/initialized ----------->|
  |                                           |
  |       READY FOR NORMAL OPERATION          |
  |                                           |
  |---- tools/list -------------------------->|
  |<--- tools list ---------------------------|
  |---- tools/call -------------------------->|
  |<--- tool result --------------------------|
  |                                           |
  |---- close transport --------------------->|
```

The ready state begins only after the server receives
`notifications/initialized`. A client should not send ordinary requests before
the `initialize` result. A server should not begin ordinary server-to-client
requests before the initialized notification.

## What initialization establishes

Initialization carries four groups of information:

```
protocol version
+ client capabilities and identity
+ server capabilities and identity
+ optional server instructions
```

The client proposes the latest revision it supports. If the server supports
that revision, it returns the same value. Otherwise, it returns another
revision it supports. If the client cannot use the returned revision, it should
disconnect instead of continuing with incompatible assumptions.

Capabilities are promises, not permissions. For example, a client may declare
that it can handle elicitation, while authorization still determines whether
the caller may update a particular transaction.

## Complete initialization example

The client starts the MCP exchange with this JSON-RPC request:

```json
{
  "jsonrpc": "2.0",
  "id": 0,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {},
    "clientInfo": {
      "name": "gateway",
      "version": "1.0.0"
    }
  }
}
```

The server selects the version and describes what it offers:

```json
{
  "jsonrpc": "2.0",
  "id": 0,
  "result": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "tools": {}
    },
    "serverInfo": {
      "name": "transaction-server",
      "version": "1.0.0"
    }
  }
}
```

The client acknowledges the result with a notification. A notification has no
`id`, so the server does not send a JSON-RPC response:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

## Trace one tool call

Assume an MCP host exposes its own application endpoint:

```http
POST /tools/call HTTP/1.1
Content-Type: application/json

{
  "tool_name": "search_transactions",
  "arguments": {
    "risk_level": "high",
    "limit": 10
  }
}
```

This first request is **host application traffic**, not an MCP wire message.
The host's MCP client translates it into a JSON-RPC request after the legacy
connection has completed initialization:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_transactions",
    "arguments": {
      "risk_level": "high",
      "limit": 10
    }
  }
}
```

The server dispatches the method to its registered tool, validates the
arguments, calls the business service, and returns the result using the same
JSON-RPC request ID:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"transactions\":[{\"transaction_id\":\"TX-001\"}]}"
      }
    ]
  }
}
```

The MCP client can then translate that result into the host application's own
response shape. That translation is an application concern; MCP does not define
the host's `/tools/call` endpoint or its response fields.

## Optional Streamable HTTP session

In the 2025-11-25 Streamable HTTP transport, a server may attach an
`MCP-Session-Id` header to the HTTP response that carries the initialization
result. If it does, the client must send that header on subsequent requests.

```
initialize POST
    -> initialize response + MCP-Session-Id: s-123

later POST
    -> MCP-Session-Id: s-123
```

This session mechanism is optional. Initialization is required in the legacy
era, but receiving `MCP-Session-Id` is not. A server that does not issue the
header can still implement the 2025-11-25 lifecycle.

The session ID is sensitive routing state. It should be unpredictable,
protected in transit, and never treated as proof that the caller is authorized.

After initialization, legacy HTTP clients also send
`MCP-Protocol-Version: 2025-11-25` on subsequent requests. This version header
states how to interpret the request; the optional session header identifies the
server-managed session. They solve different problems.

## Shutdown and termination

**stdio:**

> The client closes the server process's input stream and waits for it to exit.
> If necessary, it may terminate the child process after a reasonable timeout.

**Streamable HTTP connection:**

> Closing the associated HTTP connection or response stream ends that transport
> connection. Closing one connection does not by itself mean that durable
> business data should be deleted.

**Optional Streamable HTTP session:**

> If the server issued `MCP-Session-Id`, a client that no longer needs the
> session should send HTTP `DELETE` to the MCP endpoint with that header. The
> server may answer `405 Method Not Allowed` if client-initiated session
> deletion is unsupported.

Therefore, `DELETE` is not a universal MCP close message. It applies only to an
optional legacy Streamable HTTP session.

## Common failure cases

**Unsupported version:**

> The server returns a version the client cannot use. The client disconnects
> instead of entering the operation phase.

**Capability used without negotiation:**

> One endpoint sends a feature that the other endpoint did not declare. Treat
> this as a protocol compatibility error, not as an application result.

**Lost or expired HTTP session:**

> A request carrying an unknown legacy session ID can receive HTTP 404. The
> client starts a new lifecycle with `initialize`; it must not assume that an
> interrupted side effect is safe to repeat.

**Transport closed during work:**

> A broken connection does not prove whether the operation ran. Retry safety
> depends on the tool's idempotency and recorded business outcome, not on the
> lifecycle handshake.

## Keep the state layers separate

| State layer                 | Example                                | Typical owner                |
|-----------------------------|----------------------------------------|------------------------------|
| Connection state            | Selected version and capabilities      | MCP client and server        |
| Optional HTTP session state | `MCP-Session-Id` routing context       | Legacy HTTP server           |
| Continuation state          | Context for a multi-step operation     | Application workflow         |
| Durable business state      | Transactions, approvals, audit records | Database or business service |

The initialization handshake creates connection state. It does not replace a
database, transaction boundary, authorization check, or idempotency design.

**Professional articulation:**

> “Through MCP 2025-11-25, each connection began with version and capability
> negotiation. An optional Streamable HTTP session could add routing state, but
> durable business state and authorization remained application concerns.”

## Sources and next step

- [Legacy Streamable HTTP definitions](../elicitation/chunk-1.md)
- [Legacy complete HTTP message trace](../elicitation/chunk-3.md)
- [Legacy pinned progress exercise](../elicitation/chunk-4.md)
- [Legacy progress and elicitation exercise](../elicitation/chunk-5.md)
- [Official 2025-11-25 lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [Official 2025-11-25 transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [Version baseline](../VERSIONS.md).

Next: [05B: Stateless-first lifecycle](05B-stateless-lifecycle.md).
