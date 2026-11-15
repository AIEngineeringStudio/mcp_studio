## How it works:

1. `mcp = FastMCP("Learning MCP Server")`
   **What this does:**
    - creates a server object
    - names the server
    - starts it with the default runtime behavior

2. `@mcp.tool` registers the function as a tool.
    - Function name becomes the tool name by default.
    - Type hints become schema.
    - Docstring becomes description.
    - parameter without default = required
    - parameter with default = optional

3. For stdio servers, **do not print** normal logs **to stdout**.
    - `stdout` is part of the protocol channel.
    - Use `stderr` or`logging`.

4. Response
    - Returning a `dict` makes FastMCP create structured content automatically.
    - Response fields
        - result.content
            - Sent to the LLM. The model reads this field directly.
            - Part of the conversation.
            - Supports multiple content types(text, image, json, resource,
              binary).
        - result.structured_content
            - Strict structure.
            - Easier for the model to extract fields.
            - Often used with tool schemas.
        - result.data
            - Mainly for backend usage.
            - Not always sent to the model.
            - Can contain large objects.

| Field                     | Used By          | Format         | Purpose                |
|---------------------------|------------------|----------------|------------------------|
| result.content            | LLM              | Content blocks | Conversational output  |
| result.structured_content | LLM              | JSON object    | Structured tool output |
| result.data               | Client / backend | Any object     | Raw program data       |

## Tool Design Rules

Good tool design:

- one clear purpose
- typed inputs
- small output
- deterministic behavior when possible
- explicit errors
- no hidden side effects

Bad tool design:

- too many unrelated arguments
- printing instead of returning
- returning raw internal objects
- mixing logging with stdout

## Common transports supported by FastMCP servers:

1. STDIO (local process communication)
2. HTTP (REST style)
3. Streamable HTTP (MCP protocol over HTTP)

## 1. Running mcp server over stdio transport

mcp.run(transport="stdio")

---

## 2. Running mcp server over Streamable HTTP

`mcp.run(transport="http", host="0.0.0.0", port=8000)`

MCP endpoint is usually not mounted at `/`.

What to try:

- http://localhost:8000/mcp
- sometimes http://localhost:8000/mcp/

```
Client
  |
  | GET /mcp
  | Accept: text/event-stream
  v
Server opens SSE stream

or

Client
  |
  | POST /mcp
  | Content-Type: application/json
  | Accept: application/json, text/event-stream
  | JSON-RPC body
  v
Server returns JSON or SSE
```

**Test with curl:**
-N helps curl show streamed events as they arrive.

### Case 1: Open SSE stream

For MCP over HTTP, a `GET` to the MCP endpoint is used to open an SSE stream,
and the client must send a header:

Accept: text/event-stream

```bash
curl -N -i \
-H "Accept: text/event-stream" \
http://localhost:8000/mcp
```

### Case 2: Send MCP request

```bash
curl -N -i \
  -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    }
  }'
```

---

## 3. Running mcp server over SSE

`mcp.run(transport="sse", host="0.0.0.0", port=8000)`

Flow

1. Client connects to SSE endpoint
2. Server opens event stream
3. JSON-RPC messages travel in stream
4. Client calls tools

```
Remote SSE architecture

           Client Server (B)
           AI Agent / Worker
                 │
                 │ HTTP Request
                 ▼
        ┌─────────────────────┐
        │   SSE Transport     │
        │   event stream      │
        └─────────────────────┘
                 │
                 ▼
          MCP Server (A)
        tools / resources / prompts

```

MCP endpoint is usually not mounted at `/`.

What to try:

- http://localhost:8000/sse

**Test with curl:**
-N helps curl show streamed events as they arrive.

### Open SSE stream

For MCP over HTTP, a `GET` to the MCP endpoint is used to open an SSE stream,
and the client must send a header:

Accept: text/event-stream

```bash
curl -N -i \
-H "Accept: text/event-stream" \
http://localhost:8000/sse
```

---

## # discover tools

| Transport | Behavior         | Best Use      |
|-----------|------------------|---------------|
| stdio     | local process    | IDE plugins   |
| SSE       | streaming HTTP   | remote agents |
| HTTP      | request/response | APIs          |

**SSE advantage**

- server can stream events
- low latency
- simple HTTP protocol

## What "0.0.0.0" Means

Term to remember:
"0.0.0.0" = bind to all network interfaces.

Result:
The server accepts connections from:

- localhost
- local network
- external IP (if firewall allows)

## Basic Access (Same Machine)

Use localhost.

Example URLs:

http://localhost:8000/mcp
http://127.0.0.1:8000/mcp
http://localhost:8000/mcp/

## Access From Another Machine

Use the machine's IP address (on which mcp server is running).
http://192.168.1.25:8000/mcp

## Access Using Python Client

Example:

import requests

url = "http://localhost:8000/mcp"

response = requests.get(url)

print(response.text)

## Common MCP HTTP Endpoints

Typical endpoints:

- /health
- /info
- /call
- /schema

---
**Minimal checklist:**

When FastMCP is mounted into an ASGI/Starlette/FastAPI app, the FastMCP lifespan
must be wired correctly. The FastMCP deployment docs say that otherwise the
session manager may not be initialized, which can lead to session failures.

| Check                 | Expected value              |
| --------------------- | --------------------------- |
| Client URL            | `http://127.0.0.1:8000/mcp` |
| Manual `initialize()` | Remove it                   |
| Server transport      | HTTP / Streamable HTTP      |
| Mounted ASGI lifespan | Properly connected          |


## Key Concepts to Remember

Term Meaning
MCP Server AI tool server exposing functions
transport communication protocol
HTTP web protocol for requests
port network entry point

---

## Next

If you want, I can also show:

1) How to connect an MCP server to Claude / OpenAI
2) How to test MCP endpoints with curl 