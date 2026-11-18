# MCP Server with Streamable HTTP Transport

## Chunk 3 of 8 — §04. How Streamable HTTP Works

**Version boundary:**

> This chapter describes MCP protocol revision `2025-11-25`. It uses the
> initialization handshake and the legacy session-capable Streamable HTTP
> binding defined for that revision.

**Learning outcome:**

> Trace initialization, a tool call with progress, an elicitation request, and
> the final response without confusing SSE events with partial tool results.

## §04. The Complete Message Flow

### One endpoint, several HTTP exchanges

The server exposes one MCP endpoint, such as `https://example.com/mcp`. The
endpoint accepts `POST` for every client-to-server JSON-RPC message. It can also
accept `GET` for an optional server-to-client SSE stream.

```text
MCP client                  /mcp                    MCP server
    |--- POST: JSON-RPC message ----------------------->|
    |<-- JSON object or SSE response ------------------|
    |                                                   |
    |--- GET: optional SSE listening stream ---------->|
    |<== server requests and notifications ============|
```

The client includes this `Accept` header on `POST` requests:

```http
Accept: application/json, text/event-stream
```

The server chooses either `application/json` for one response object or
`text/event-stream` for a stream of JSON-RPC messages.

### Step 1 — Initialize

Initialization must be the first protocol interaction.

```http
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "elicitation": {
        "form": {},
        "url": {}
      }
    },
    "clientInfo": {
      "name": "learning-client",
      "version": "1.0.0"
    }
  }
}
```

The server returns an `InitializeResult`. It may also issue a session ID in an
HTTP response header:

```http
HTTP/1.1 200 OK
Content-Type: application/json
MCP-Session-Id: 7f5f2e6b-4dd6-4bc3-a2ca-6a8118c53de0

{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "tools": {
        "listChanged": true
      }
    },
    "serverInfo": {
      "name": "batch-server",
      "version": "1.0.0"
    }
  }
}
```

The session header is optional. If the server supplies it, the client must
include it on later HTTP requests.

### Step 2 — Send the initialized notification

The client—not the server—sends `notifications/initialized` after accepting the
initialization response.

```http
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2025-11-25
MCP-Session-Id: 7f5f2e6b-4dd6-4bc3-a2ca-6a8118c53de0

{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

Because this message is a notification, a server that accepts it returns HTTP
`202 Accepted` with no response body.

### Step 3 — Discover and call a tool

The client normally discovers tools with `tools/list`, then sends a
`tools/call` request. A progress token opts the call into progress updates.

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "process_batch",
    "arguments": {
      "batch_size": 20
    },
    "_meta": {
      "progressToken": "batch-2"
    }
  }
}
```

The client sends the request with the negotiated protocol version and, when
issued, the session ID:

```http
MCP-Protocol-Version: 2025-11-25
MCP-Session-Id: 7f5f2e6b-4dd6-4bc3-a2ca-6a8118c53de0
```

### Step 4 — Receive progress over SSE

Suppose the server responds to the tool request with
`Content-Type: text/event-stream`. Each meaningful SSE `data` field contains a
complete JSON-RPC message.

```text
data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"batch-2","progress":20,"total":100,"message":"Processed 20 records"}}

data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"batch-2","progress":40,"total":100,"message":"Processed 40 records"}}

```

These messages report status. They are not partial `CallToolResult` objects.
The tool has not completed merely because a notification arrived.

### Step 5 — Handle an elicitation request

If the tool requires more user input, the server may send an
`elicitation/create` JSON-RPC request before the final tool response:

```text
data: {"jsonrpc":"2.0","id":"ask-1","method":"elicitation/create","params":{"mode":"form","message":"Choose the next batch size","requestedSchema":{"type":"object","properties":{"batch_size":{"type":"integer","minimum":1,"maximum":100}},"required":["batch_size"]}}}

```

The host presents an appropriate user interface. If the user accepts and enters
`25`, the client sends the JSON-RPC response in a new `POST` to `/mcp`:

```json
{
  "jsonrpc": "2.0",
  "id": "ask-1",
  "result": {
    "action": "accept",
    "content": {
      "batch_size": 25
    }
  }
}
```

The response uses the same JSON-RPC ID as the server's request. It is not sent
to a custom `/reply` or `/elicit` URL.

### Step 6 — Receive the final tool response

After processing finishes, the server places the final JSON-RPC response on the
SSE stream:

```text
data: {"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"Processed 100 records"}],"structuredContent":{"processed":100},"isError":false}}

```

The final response matches the original tool request ID, `2`. After sending it,
the server should terminate that SSE stream.

There is no MCP `[DONE]` sentinel. The JSON-RPC response establishes protocol
completion.

## Logical Sequence Diagram

```text
Client                                                Server
  |--- POST initialize -------------------------------->|
  |<-- InitializeResult + optional session header ------|
  |--- POST notifications/initialized ---------------->|
  |<-- 202 Accepted ------------------------------------|
  |                                                     |
  |--- POST tools/list -------------------------------->|
  |<-- tool definitions --------------------------------|
  |                                                     |
  |--- POST tools/call + progressToken ---------------->|
  |<== SSE notifications/progress ======================|
  |<== SSE elicitation/create request ==================|
  |--- POST elicitation response ---------------------->|
  |<== SSE notifications/progress ======================|
  |<== SSE final tools/call response ===================|
```

The SSE response is one-way at the HTTP level. The overall protocol exchange is
bidirectional because the client can send new `POST` requests while it receives
the server's SSE messages.

## Optional GET Stream

A client may send `GET /mcp` with `Accept: text/event-stream` to open a stream
for server messages not tied to a current `POST` request. The server may instead
return `405 Method Not Allowed` if it does not provide this stream.

The server must not place ordinary JSON-RPC responses on this GET stream. The
exception is replay while resuming a previously interrupted request stream.

## Resumability

When a server implements resumability, it assigns SSE event IDs. If the
connection breaks, the client reconnects with `GET /mcp` and the last event ID:

```http
GET /mcp HTTP/1.1
Accept: text/event-stream
Last-Event-ID: stream-a:42
MCP-Protocol-Version: 2025-11-25
MCP-Session-Id: 7f5f2e6b-4dd6-4bc3-a2ca-6a8118c53de0
```

The server may replay only the events associated with the interrupted stream.
A transport disconnect does not mean the tool call was cancelled. Cancellation
requires an explicit MCP cancellation notification.

## Routing Rules

| Message | Direction | Correlation |
|---|---|---|
| `initialize` | Client to server | JSON-RPC request ID |
| `notifications/initialized` | Client to server | No ID; notification |
| `tools/call` | Client to server | JSON-RPC request ID |
| `notifications/progress` | Either direction | `progressToken` |
| `elicitation/create` | Server to client | JSON-RPC request ID |
| Elicitation result | Client to server | Same elicitation request ID |
| Final tool result | Server to client | Same tool-call request ID |

## Failure Trace

If the client sends an expired or unknown `MCP-Session-Id`, the server returns
HTTP `404 Not Found`. The client must begin a new session with a fresh
`initialize` request that omits the old session ID.

The client must not blindly repeat a tool with side effects after a transport
failure. It first needs an idempotency or operation-status strategy at the
application layer.

## Summary

- One MCP endpoint receives every client JSON-RPC message with `POST`.
- A request receives one JSON object or an SSE stream.
- SSE events carry complete JSON-RPC messages, not arbitrary output chunks.
- Progress uses `notifications/progress` and a caller-provided token.
- Elicitation uses `elicitation/create` and a normal JSON-RPC response.
- The final response, not `[DONE]`, completes the tool call.
- Optional session IDs travel in headers, not URL paths.
- Resumability and cancellation are separate mechanisms.

**Professional articulation:**

> “Streamable HTTP is bidirectional at the MCP message level, not on one HTTP
> connection. The server can send progress or elicitation over SSE while the
> client sends corresponding JSON-RPC messages in separate POST requests.”

## Official References

- [MCP `2025-11-25`: Streamable HTTP](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [MCP `2025-11-25`: Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [MCP `2025-11-25`: Progress](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/progress)
- [MCP `2025-11-25`: Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)

## Next

Continue with [chunk 4: a basic Python example](chunk-4.md).
