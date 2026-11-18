# MCP Server with Streamable HTTP Transport

## Chunk 2 of 8 — Sections §02 and §03

**Version boundary:**

> This chapter describes MCP protocol revision `2025-11-25`. That revision
> uses the initialization-based lifecycle and may use protocol sessions. Do not
> combine this flow with the different lifecycle introduced after this revision.

- **Chunks generated:** 2 of 8
- **Active chunk:** 2 of 8
- **Sections:** §02 and §03

## §02. Why Streamable HTTP Matters

### The problem it solves

An MCP server may need more than a one-shot HTTP response. For example, a
long-running tool might report progress, or the server might request additional
user input before it returns the final tool result.

An ordinary JSON HTTP response can still be handled asynchronously, so it does
not inherently block the user interface. Its limitation here is that it carries
only one response object and provides no standard channel for intermediate MCP
messages.

Streamable HTTP addresses that transport problem. In MCP `2025-11-25`:

- A client sends each JSON-RPC message in a new HTTP `POST` to one MCP endpoint.
- A server answers a request with one JSON object or an SSE response stream.
- The SSE stream can carry JSON-RPC requests and notifications before the final
  JSON-RPC response.
- A client sends notifications or responses to server-initiated requests in new
  HTTP `POST` requests to the same MCP endpoint.
- A client may open a separate SSE stream with `GET` when the server supports
  it.

**Important limitation:**

> SSE transports MCP messages. It does not automatically turn a tool result
> into arbitrary row-by-row or token-by-token output. A normal `tools/call`
> still completes with one final JSON-RPC response.

### Representative uses

**Long-running operation:**

> A database-maintenance tool sends `notifications/progress` while it works and
> later returns one final `CallToolResult`.

**Additional user input:**

> A tool needs a missing batch size. The server sends an
> `elicitation/create` request, the client obtains the user's response, and the
> server then completes the original operation.

**Server-to-client communication:**

> A server sends related notifications or requests on an SSE response stream
> while the original client request remains active.

For a large business result, use a bounded final response, pagination, or an
MCP resource. Do not invent a custom sequence of partial tool results unless
both sides explicitly implement that nonstandard application contract.

## §03. Core Concepts

### Topic list

1. HTTP as a transport
2. Server-Sent Events
3. MCP roles and messages
4. The initialization lifecycle and optional session
5. MCP tools
6. Progress versus final results
7. Elicitation
8. Bidirectional protocol messaging

### 1. HTTP as a transport

**Transport:**

> The mechanism that carries protocol messages between the MCP client and MCP
> server. It does not define the tool's business behavior.

Streamable HTTP uses one MCP endpoint, such as `/mcp`. Every JSON-RPC message
from the client uses a new `POST` request.

```
Client                      MCP endpoint                     Server
  |--- POST /mcp ---------------------------------------------->|
  |    JSON-RPC request                                        |
  |<-- application/json or text/event-stream ------------------|
```

For a request, the client advertises that it accepts both
`application/json` and `text/event-stream`. The server chooses either a single
JSON response or an SSE response stream.

After initialization, HTTP requests include the negotiated version:

```
MCP-Protocol-Version: 2025-11-25
```

### 2. Server-Sent Events

**Server-Sent Events (SSE):**

> A text framing format that lets a server send multiple events over an HTTP
> response stream.

In Streamable HTTP, the `data` field of a meaningful MCP SSE event contains a
JSON-RPC message. For example, a progress notification could be framed as:

```
data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"job-7","progress":50,"total":100}}

```

SSE is server-to-client on that HTTP connection. The client does not write back
on the same connection. Instead, it sends another HTTP `POST` to the MCP
endpoint.

Streamable HTTP does not require one permanently open connection. In
`2025-11-25`, a server can close an SSE connection without ending the logical
stream. When resumability is implemented, the client reconnects with
`Last-Event-ID` so the server can redeliver missed events.

The marker `[DONE]` and application messages such as `stream/chunk` are not
standard MCP messages.

### 3. MCP roles and messages

**Model Context Protocol (MCP):**

> An open protocol for connecting an AI application to servers that expose
> capabilities such as tools, resources, and prompts.

MCP uses a host-client-server architecture:

```
+---------------- Host application ----------------+
|                                                   |
|  Model or agent <--> MCP client <====> MCP server |
|                     protocol       tools/resources|
|                                                   |
+---------------------------------------------------+
```

- The **host** coordinates the model, permissions, user experience, and MCP
  clients.
- An **MCP client** is a protocol component created by the host. It maintains a
  connection with one server.
- An **MCP server** exposes tools, resources, prompts, or other negotiated
  capabilities.
- The model is not itself the MCP client, and the server is not itself a tool.

MCP messages use JSON-RPC 2.0 requests, responses, and notifications. A tool
call is a client-to-server request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "process_batch",
    "arguments": {
      "batch_size": 10
    }
  }
}
```

### 4. Initialization and the optional session

Protocol revision `2025-11-25` begins with initialization and capability
negotiation.

```
Client                                             Server
  |--- initialize request -------------------------->|
  |<-- InitializeResult response --------------------|
  |--- notifications/initialized ------------------->|
  |                                                  |
  |--- normal MCP operations ----------------------->|
```

The server response identifies the negotiated protocol version and server
capabilities. The client then sends `notifications/initialized`; there is no
server message named an "initialized response."

**MCP session:**

> The logically related interactions between a client and server beginning
> with initialization.

For Streamable HTTP, server-managed session IDs are optional. A server that
wants a stateful HTTP session may return an `MCP-Session-Id` header with the
initialization response. If it does, the client must include that header in
later requests.

```
MCP-Session-Id: <server-issued-session-id>
```

The specification does not require session data to live in Python memory,
Redis, or any other particular store. Those are application architecture
choices. Durable business state should not be confused with transport session
state.

### 5. MCP tools

**MCP tool:**

> A server capability with a name, description, input schema, and optional
> output-related metadata. A model may select a tool, but the host controls the
> actual protocol interaction and user-consent experience.

An illustrative tool definition is:

```json
{
  "name": "process_batch",
  "description": "Process a bounded batch of records",
  "inputSchema": {
    "type": "object",
    "properties": {
      "batch_size": {
        "type": "integer",
        "minimum": 1
      }
    },
    "required": ["batch_size"]
  }
}
```

Clients discover tools with `tools/list` and invoke one with `tools/call`.
The protocol does not require tools to be registered only at server startup.
A server can change its tool list and, when it advertises support, send
`notifications/tools/list_changed`.

### 6. Progress versus final results

Progress and results are different protocol concepts.

```
tools/call request
    |
    +--- notifications/progress: 10 of 100
    +--- notifications/progress: 60 of 100
    +--- elicitation/create, if additional input is needed
    |
    +--- one final tools/call response
```

To request progress, the caller includes a `progressToken` in the request's
`_meta`. The receiver may then send `notifications/progress` messages that
refer to that token.

Progress does not replace the final response. Even a `100%` progress update
does not prove that the operation succeeded; the final JSON-RPC response
establishes completion or failure.

Also keep these streams separate:

- **MCP progress:** structured notifications about work status.
- **MCP final result:** the completed `tools/call` response.
- **SSE:** transport framing for JSON-RPC messages.
- **Model-token streaming:** text generated incrementally by a model.
- **Application UI events:** custom events interpreted by a particular UI.

### 7. Elicitation

**Elicitation:**

> A standardized way for an MCP server to request additional information from
> a user through a capable client.

The client must advertise the `elicitation` capability before the server uses
it. The standardized request method is `elicitation/create`.

```
Client                                             Server
  |--- tools/call ------------------------------------>|
  |<-- elicitation/create request over SSE ------------|
  |                                                    |
  |    host presents the request to the user           |
  |                                                    |
  |--- JSON-RPC response in a new POST --------------->|
  |<-- final tools/call response ----------------------|
```

The diagram shows one valid interaction during an active tool call. The wire
protocol defines requests and responses; it does not require a particular
Python implementation such as a suspended generator or `asyncio.Queue`.

MCP `2025-11-25` supports two elicitation modes:

- **Form mode** collects structured, non-sensitive user input described by a
  restricted JSON Schema.
- **URL mode** directs the user to an external URL for sensitive or out-of-band
  interactions. URL mode was introduced in `2025-11-25`.

A response records one of three actions: `accept`, `decline`, or `cancel`.
Form mode must not be used to request passwords, API keys, access tokens, or
payment credentials. Those interactions require URL mode.

Elicitation is not `sampling/createMessage`. Sampling asks the client to obtain
an LLM generation; elicitation asks the client to obtain user input.

### 8. Bidirectional protocol messaging

MCP is bidirectional at the protocol level: either peer can issue supported
JSON-RPC requests. Streamable HTTP achieves this with multiple HTTP messages,
not with a full-duplex SSE connection.

```
Client                         /mcp                         Server
  |--- POST: tools/call ------------------------------------>|
  |<== SSE: elicitation/create ==============================|
  |--- POST: JSON-RPC elicitation response ----------------->|
  |<== SSE: final tools/call response =======================|
```

Every client-to-server JSON-RPC request, notification, or response uses a new
`POST` to the same MCP endpoint. If the server issued an optional session ID,
the client includes it in the `MCP-Session-Id` header.

Server-to-client requests are allowed only when the relevant capability was
negotiated. Application code may use an async queue internally, but an
`asyncio.Queue` is not part of MCP or Streamable HTTP.

### How the concepts connect

```
+----------------------- MCP session ------------------------+
|                                                            |
| Host                                                       |
|   |                                                        |
|   +-- MCP client -- POST /mcp --> MCP server -- tool       |
|          ^                              |                  |
|          +-- JSON-RPC over SSE ---------+                  |
|              progress, elicitation, final response         |
|                                                            |
+------------------------------------------------------------+
```

The flow is:

1. Initialization negotiates the protocol version and capabilities.
2. The server may issue an optional Streamable HTTP session ID.
3. The client invokes a discovered tool with `tools/call`.
4. The server may send progress notifications or supported requests over SSE.
5. The client answers server requests with a new `POST` to the same endpoint.
6. The server sends one final JSON-RPC response for the tool call.

## Summary — §02 and §03

- Streamable HTTP carries MCP JSON-RPC messages over `POST`, optional `GET`,
  JSON responses, and optional SSE streams.
- SSE is one-way on an individual connection; client messages use separate
  `POST` requests.
- A normal tool call has one final result. Progress notifications are not
  partial tool results.
- The host, model, MCP client, MCP server, and tool are distinct components.
- The `2025-11-25` lifecycle is `initialize` response followed by the client's
  `notifications/initialized` notification.
- Streamable HTTP session IDs are optional and travel in the
  `MCP-Session-Id` header.
- Elicitation uses `elicitation/create`, not `sampling/createMessage`.
- URL mode elicitation is part of the `2025-11-25` revision.
- `asyncio.Queue`, suspended generators, and custom chunk messages are
  implementation choices, not MCP protocol requirements.

**Professional articulation:**

> "In MCP `2025-11-25`, Streamable HTTP uses one endpoint and can return either
> JSON or an SSE stream. SSE carries JSON-RPC progress, requests, notifications,
> and the final response; it does not redefine a tool result as arbitrary data
> chunks."

## Official references

- [MCP `2025-11-25`: Architecture](https://modelcontextprotocol.io/specification/2025-11-25/architecture)
- [MCP `2025-11-25`: Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [MCP `2025-11-25`: Streamable HTTP](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [MCP `2025-11-25`: Progress](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/progress)
- [MCP `2025-11-25`: Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [MCP `2025-11-25`: Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)

## Next

```
Chunk 3 of 8 -> §04. How Streamable HTTP works
```
