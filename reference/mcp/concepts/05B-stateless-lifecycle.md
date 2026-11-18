# Stateless-first lifecycle in MCP 2026-07-28

**Outcome:** Trace a modern self-contained MCP request and explain how protocol
statelessness changes discovery, HTTP routing, additional-input flows, and
application state ownership.

**Prerequisites:** [03: JSON-RPC requests, responses, and notifications](03-json-rpc.md),
[04: Protocol versions and capability discovery](04-versions-discovery.md), and
[05A: Stateful connection lifecycle](05A-stateful-lifecycle.md).

## Version boundary

This guide describes **MCP 2026-07-28**, the stateless-first protocol revision.
It removed the mandatory `initialize` / `notifications/initialized` handshake
and removed protocol-level HTTP sessions.

Each request carries the protocol facts needed to interpret it. A server can
process a request without retrieving capability state created by an earlier
connection-level handshake.

*Stateless-first* describes the MCP protocol core. It does not forbid a server
from using a database, cache, explicit business handle, or protected
continuation state.

## The modern request lifecycle

The modern flow has no connection-wide ready state:

```
Client                                      Server
  |                                           |
  |---- server/discover (optional) ---------->|
  |<--- versions and capabilities ------------|
  |                                           |
  |---- self-contained tools/list ----------->|
  |<--- complete result ----------------------|
  |                                           |
  |---- self-contained tools/call ----------->|
  |<--- complete result ----------------------|
```

`server/discover` is implemented by modern servers, but calling it is optional.
A client may use it to select a supported version, learn server capabilities,
or probe whether it must fall back to the legacy handshake. A client that has
already selected version `2026-07-28` may send another self-contained request
directly.

There is no `notifications/initialized`, `MCP-Session-Id`, protocol-session
`DELETE`, or HTTP GET event stream in the 2026-07-28 core flow.

## What every request carries

Every request carries modern metadata under `params._meta`:

- `io.modelcontextprotocol/protocolVersion` is required and identifies the
  protocol revision.
- `io.modelcontextprotocol/clientCapabilities` is required and declares
  relevant client feature support.
- `io.modelcontextprotocol/clientInfo` identifies the client and should be
  included on each request.

Each result has a required `resultType`. Ordinary final results use
`"complete"`; a result that requires another client round trip uses
`"input_required"`. Servers should identify themselves in each result's
`_meta.io.modelcontextprotocol/serverInfo`.

For Streamable HTTP, selected body fields are also mirrored into headers so a
gateway can route and inspect requests without parsing JSON:

| HTTP header | Mirrors | When required |
|---|---|---|
| `MCP-Protocol-Version` | Protocol version in `params._meta` | Every request POST |
| `Mcp-Method` | JSON-RPC `method` | Every request POST |
| `Mcp-Name` | `params.name` or `params.uri` | Named tool, prompt, and resource requests |

The mirrored header values must agree with the JSON-RPC body. The SDK should
construct them; hand-written examples make them visible for learning.

## Trace one self-contained tool call

Assume an MCP host receives this application-specific request:

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

This is host application traffic, not MCP. The host's MCP client sends one
self-contained request to the MCP endpoint:

```http
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: search_transactions

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_transactions",
    "arguments": {
      "risk_level": "high",
      "limit": 10
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientInfo": {
        "name": "gateway",
        "version": "1.0.0"
      },
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

The server validates the headers and metadata, authorizes the caller,
dispatches the tool, and returns either one JSON object or a request-scoped
Server-Sent Events (SSE) stream. A single JSON response can be:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "complete",
    "content": [
      {
        "type": "text",
        "text": "{\"transactions\":[{\"transaction_id\":\"TX-001\"}]}"
      }
    ],
    "_meta": {
      "io.modelcontextprotocol/serverInfo": {
        "name": "transaction-server",
        "version": "2.0.0"
      }
    }
  }
}
```

The response uses the same JSON-RPC ID as its request. A later, independent
request uses a new ID and repeats its protocol version and client capability
metadata.

## Streamable HTTP is request-scoped

Every client message is a new HTTP POST to one MCP endpoint. A JSON-RPC request
receives either:

- `application/json` with one response object, or
- `text/event-stream` with request-related notifications followed by the final
  response.

An SSE stream belongs to its originating request. The server may send progress
or message notifications on that stream, but it must not send an independent
JSON-RPC request on it. Closing the response stream cancels that request.

The modern transport does not support `Last-Event-ID` resumability. If a stream
breaks before the final response, the client cannot infer the outcome from the
disconnect. A retry is a new request with a new JSON-RPC ID, and the operation
still needs an idempotency strategy if it can produce side effects.

Long-lived change notifications use a separate `subscriptions/listen` request.
They do not restore a general connection-wide protocol session.

## Additional input uses a new request

MCP 2026-07-28 replaces in-flight server-to-client requests with the Multi
Round-Trip Request (MRTR) pattern. If a transaction action needs a reason, the
server returns an interim result:

```
Client                                      Server
  |---- tools/call, id 10 ------------------->|
  |<--- input_required + requestState ------- |
  |                                           |
  |     obtain the requested user input       |
  |                                           |
  |---- tools/call + inputResponses, id 11 -->|
  |<--- complete result ----------------------|
```

The retry is independent and must use a different JSON-RPC ID. The client
echoes an opaque `requestState` exactly as received and adds the requested
`inputResponses`. The server treats returned state as attacker-controlled,
protects its integrity when it affects behavior, rechecks authorization, and
prevents unsafe replay where single use matters.

MRTR is continuation across self-contained requests, not a suspended handler
or a hidden sticky session.

## Stateless protocol, stateful application

Protocol statelessness removes connection-level storage as an implicit
dependency. Applications still have several valid state mechanisms:

**Explicit business handle:**

> A tool creates a basket, browser, transaction search, or workflow and returns
> a server-minted identifier. Later calls pass that identifier as an ordinary
> argument.

**Durable service state:**

> A database stores business records, authorization data, idempotency outcomes,
> and audit history independently of any MCP connection.

**Protected continuation state:**

> MRTR may carry opaque `requestState` through the client. The server validates
> its integrity, identity binding, operation binding, and expiry on reentry.

**Request-local state:**

> Temporary objects can exist while one request is executing. They disappear
> after the final result and cannot be assumed to exist for the next request.

The important rule is visibility: state that must survive a request boundary
must be represented explicitly or stored in a service designed for that
lifetime.

## Scaling consequence

Because the protocol does not require a previous session to interpret a
request, successive requests can reach different server instances:

```
                         +--> MCP server A
Client --> load balancer |
                         +--> MCP server B
```

Plain round-robin routing becomes possible at the protocol layer. This does not
make every application horizontally scalable automatically. In-memory business
state, local files, process-local locks, and non-shared subscription feeds can
still require shared infrastructure or deliberate routing.

## Common failure cases

**Unsupported protocol version:**

> The server returns HTTP 400 with `UnsupportedProtocolVersionError` and its
> supported versions. The client selects a mutually supported version or uses a
> compatible legacy flow; it does not send `initialize` inside a modern flow.

**Header and body disagree:**

> The server returns HTTP 400 with `HeaderMismatch`. Fix the client or gateway
> that changed one representation without changing the other.

**Capability was not declared:**

> The server must not request an input feature the client did not declare. It
> should return a compatible result or a clear error instead of assuming the
> host can provide that input.

**Retry repeats a side effect:**

> A new request ID prevents JSON-RPC correlation conflicts; it does not make the
> business operation idempotent. Use an operation key, conditional update, or
> persisted outcome where repetition would be harmful.

**Authorization inferred from metadata:**

> Client identity and capabilities describe implementation behavior. They do
> not authenticate a user or grant access. Authenticate and authorize every
> request at the application boundary.

## Compare the lifecycle eras

| Concern | Through 2025-11-25 | 2026-07-28 |
|---|---|---|
| Start | `initialize`, result, `initialized` | Self-contained request; optional `server/discover` |
| Version and client capabilities | Established during initialization | Repeated in every request's `_meta` |
| HTTP protocol session | Optional `MCP-Session-Id` | Removed |
| Server-to-client input | In-flight server request | `input_required`, then a new client request |
| HTTP server events | POST/GET streams; optional resumption | Request-scoped POST stream; `subscriptions/listen` for changes |
| Shutdown | Close transport; optional session `DELETE` | Finish or cancel individual requests; no protocol session to delete |

**Professional articulation:**

> “MCP 2026-07-28 makes each request self-contained by carrying its protocol
> version and client capabilities in request metadata. It removes protocol
> sessions, but applications still model durable and multi-step state
> explicitly through handles, storage, and protected continuation state.”

## Sources and next step

- [Official 2026-07-28 protocol overview](https://modelcontextprotocol.io/specification/2026-07-28/basic/index) — checked 2026-11-17.
- [Official versioning and compatibility](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning) — checked 2026-11-17.
- [Official 2026-07-28 Streamable HTTP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) — checked 2026-11-17.
- [Official Multi Round-Trip Requests](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr) — checked 2026-11-17.
- [Official 2026-07-28 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog) — checked 2026-11-17.
- [Version baseline](../VERSIONS.md).

Next: [Tools and their contracts](05-tool-contracts.md). For deeper network
behavior, continue to [Streamable HTTP](11-streamable-http.md).
