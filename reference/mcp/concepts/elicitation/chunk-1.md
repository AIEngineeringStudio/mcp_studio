# MCP Server with Streamable HTTP Transport

## Chunk 1 of 8 — Prerequisites and Definitions

**Version boundary:**

> This eight-part guide targets MCP protocol revision `2025-11-25`. It uses
> the initialization-based lifecycle and may use protocol sessions. Later
> revisions use a different lifecycle, so do not mix their message flows.

**Learning outcome:**

> Explain how an MCP client and server exchange JSON-RPC messages through
> Streamable HTTP, and distinguish HTTP requests, SSE streams, protocol
> sessions, and elicitation.

## §00. Prerequisites

### What you need for this chunk

| Knowledge area              | Level    | Why it helps                                        |
|-----------------------------|----------|-----------------------------------------------------|
| HTTP requests and responses | Beginner | Streamable HTTP carries MCP messages over HTTP      |
| JSON                        | Beginner | MCP uses JSON-RPC messages encoded as JSON          |
| Client and server roles     | Beginner | MCP assigns different responsibilities to each side |

REST, HTTP chunked transfer encoding, asynchronous Python, FastAPI, Docker, and
Uvicorn are not prerequisites for understanding this transport. Later chunks
may introduce Python frameworks and containers as implementation choices.

### Useful background

1. [HTTP overview](https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview)
2. [JSON-RPC 2.0 specification](https://www.jsonrpc.org/specification)
3. [MCP
   `2025-11-25` lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)

### Suggested study time

| Course range |  Estimated time |
|--------------|----------------:|
| §00–§01      |       1–2 hours |
| §02–§04      |       3–4 hours |
| §05–§06      |       6–8 hours |
| §07–§18      |      8–12 hours |
| **Total**    | **18–26 hours** |

## §01. Definitions

### Core definition

**Model Context Protocol (MCP):**

> An open protocol that standardizes communication between an AI application's
> MCP client and an MCP server. It lets the application discover and use server
> capabilities such as tools, resources, and prompts.

**Streamable HTTP:**

> An MCP transport that carries JSON-RPC messages through one HTTP endpoint.
> Clients send messages with HTTP POST. A server answers a request with either
> one JSON response or an optional Server-Sent Events (SSE) stream. A client may
> also open an SSE stream with HTTP GET so the server can send requests or
> notifications that are not tied to a current POST request.

Streamable HTTP does not require one permanently open connection. An SSE
connection can close and, when supported, resume. Each client-to-server
JSON-RPC message is still sent in a new HTTP POST request.

### Basic message flow

```text
MCP client                                      MCP server
    |                                                |
    |--- POST /mcp: one JSON-RPC message ---------->|
    |<-- application/json: one response ------------|
    |                                                |
    |--- POST /mcp: one JSON-RPC request ---------->|
    |<-- text/event-stream: JSON-RPC messages -------|
    |                              then response -----|
```

The second response uses SSE framing to carry multiple complete JSON-RPC
messages. It does not imply arbitrary text fragments, model-token streaming, or
a non-standard `chunk` message type.

### Key terms

**Host:**

> The AI application that manages the user experience, model interaction, and
> one or more MCP clients.

**MCP client:**

> The host-side protocol component that connects to an MCP server. The model
> does not normally send MCP messages directly.

**MCP server:**

> A program that exposes capabilities such as tools, resources, and prompts
> through MCP.

**Transport:**

> The mechanism that carries MCP JSON-RPC messages between client and server.
> MCP `2025-11-25` defines standard transports including stdio and Streamable
> HTTP.

**JSON-RPC 2.0:**

> The message envelope used for MCP requests, responses, and notifications.
> JSON-RPC defines message structure; HTTP and SSE determine how those messages
> travel.

**Server-Sent Events (SSE):**

> A server-to-client streaming format used by Streamable HTTP to carry multiple
> complete JSON-RPC messages. The client sends its own messages in separate HTTP
> POST requests, not back through the SSE stream.

**Protocol session:**

> A sequence of logically related MCP interactions beginning with the
> `initialize` exchange. In Streamable HTTP, the server may assign an
> `MCP-Session-Id`, but session IDs are optional. A protocol session must not be
> treated as AI conversation memory or durable business state.

**Elicitation:**

> A server-to-client `elicitation/create` request asking the client to obtain
> additional user input. In `2025-11-25`, clients declare support for form mode,
> URL mode, or both during initialization.

**Bidirectional communication:**

> Both client and server can originate JSON-RPC messages. This does not mean
> both write through the same HTTP connection: client messages use POST, while
> server messages can travel in an SSE response or an optional GET SSE stream.

**Tool:**

> A named capability exposed by an MCP server that a client can discover and
> invoke, subject to protocol compatibility, advertised capabilities,
> authentication, and authorization.

### Important distinctions

- Streamable HTTP is JSON-RPC over HTTP; it is not a REST API style.
- An SSE event carries a complete JSON-RPC message, not a model-token chunk.
- A Streamable HTTP connection does not have to remain open permanently.
- A protocol session is not the same as chat history or business state.
- Elicitation is a defined MCP request, not an arbitrary prompt embedded in a
  tool result.

### Professional articulation

> “In MCP `2025-11-25`, Streamable HTTP sends each client message as an HTTP
> POST to one MCP endpoint. The server can return one JSON response or use SSE
> to deliver multiple JSON-RPC messages before the final response.”

## Sources

- [MCP `2025-11-25`: Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [MCP `2025-11-25`: Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [MCP `2025-11-25`: Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
- [MCP `2025-11-25`: Architecture](https://modelcontextprotocol.io/specification/2025-11-25/architecture)

## Status

```
CHUNKS GENERATED : [1 / 8]
ACTIVE CHUNK     : [1 / 8]  COMPLETE
NEXT CHUNK       : [2 / 8]  §02 Why It Matters + §03 Core Concepts
```

Continue with [chunk 2](chunk-2.md).
