# MCP TUTORIAL — CHUNK 2 OF 8

## CHUNKS GENERATED: [2 / 8]

## ACTIVE CHUNK: [2 / 8]

## SECTIONS IN THIS CHUNK: [§03, §04]

---

## §03. CORE CONCEPTS (FOUNDATION)

### Topic List

1. MCP Architecture (Client / Server / Transport)
2. Protocol Messages (JSON-RPC 2.0)
3. Capabilities (Tools, Resources, Prompts)
4. Lifecycle (Initialize → Request → Shutdown)
5. Context Object
6. Tool Definition Schema

---

### Block 1 — MCP Architecture

**MCP** uses a three-layer model.

```
┌─────────────────────────────────────────────┐
│                MCP CLIENT                   │
│  (AI agent / LLM host — e.g. Claude, GPT)  │
└──────────────────┬──────────────────────────┘
                   │  Transport Layer
                   │  (stdio | HTTP/SSE | WebSocket)
┌──────────────────▼──────────────────────────┐
│                MCP SERVER                   │
│  (your code — exposes tools/resources)      │
└─────────────────────────────────────────────┘
```

| Layer         | Role                                      |
|---------------|-------------------------------------------|
| **Client**    | Sends requests (LLM host)                 |
| **Transport** | Carries messages (stdio, HTTP, WebSocket) |
| **Server**    | Handles requests, returns results         |

🔑 Jargon:

- **Client** — the AI agent that calls MCP tools
- **Server** — your code that exposes capabilities
- **Transport** — the wire protocol between them

---

### Block 2 — Protocol Messages (JSON-RPC 2.0)

MCP uses **JSON-RPC 2.0** for all messages.

Every message is a JSON object with this shape:

```json
{
  "jsonrpc": "2.0",
  // always "2.0"
  "id": 1,
  // unique request ID
  "method": "tools/call",
  // what to do
  "params": {
    // arguments
    "name": "get_weather",
    "arguments": {
      "city": "London"
    }
  }
}
```

Response shape:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "15°C, cloudy"
      }
    ]
  }
}
```

🔑 Jargon:

- **JSON-RPC 2.0** — a standard for remote calls over JSON
- **method** — the action to invoke
- **params** — arguments passed to the method
- **result** — the response payload

---

### Block 3 — Capabilities

MCP servers expose three capability types:

```
MCP Server
├── Tools      → functions the LLM can call
├── Resources  → read-only data the LLM can read
└── Prompts    → reusable prompt templates
```

| Capability   | Analogy          | Example                     |
|--------------|------------------|-----------------------------|
| **Tool**     | API endpoint     | `get_weather(city)`         |
| **Resource** | File / DB record | `file://readme.md`          |
| **Prompt**   | Template         | `summarize_issue(issue_id)` |

🔑 Jargon:

- **Tool** — callable function exposed to the LLM
- **Resource** — URI-addressed read-only data
- **Prompt** — parameterized prompt template

---

### Block 4 — Lifecycle

```
Client                          Server
  │                               │
  │── initialize ────────────────>│  Handshake + capability
  │<─ initialize result ──────────│  exchange
  │                               │
  │── tools/list ────────────────>│  Discover available tools
  │<─ tools/list result ──────────│
  │                               │
  │── tools/call ────────────────>│  Invoke a tool
  │<─ tools/call result ──────────│
  │                               │
  │── shutdown ──────────────────>│  Graceful close
  │<─ (close) ────────────────────│
```

Steps:

1. Client sends `initialize` with its protocol version.
2. Server responds with supported capabilities.
3. Client discovers tools via `tools/list`.
4. Client calls tools via `tools/call`.
5. Client sends `shutdown` to close the session.

🔑 Jargon:

- **initialize** — first message; negotiates capabilities
- **tools/list** — request to enumerate available tools
- **tools/call** — request to execute a specific tool
- **shutdown** — signals graceful session end

---

### Block 5 — Context Object

The **Context** object is passed into every tool handler.
It provides access to logging and MCP session metadata.

```python
# Every tool handler receives a Context object
async def my_tool(args: dict, ctx: Context) -> str:
    # ctx.info()  → structured log at INFO level
    # ctx.error() → structured log at ERROR level
    # ctx.session → raw MCP session (advanced use)
    await ctx.info("Tool called", extra={"args": args})
    return "result"
```

---

### Block 6 — Tool Definition Schema

Each tool must declare:

- **name** — unique identifier
- **description** — plain-English purpose
- **inputSchema** — JSON Schema for arguments

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-server")


@mcp.tool()  # registers this as an MCP tool
async def add(a: int, b: int) -> int:
    """Add two integers."""  # becomes the description
    return a + b
# FastMCP auto-generates inputSchema from type hints
```

Auto-generated schema for the above:

```json
{
  "name": "add",
  "description": "Add two integers.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "a": {
        "type": "integer"
      },
      "b": {
        "type": "integer"
      }
    },
    "required": [
      "a",
      "b"
    ]
  }
}
```

---

### How Blocks Connect

```
┌────────────────────────────────────────────┐
│              MCP CLIENT (LLM)              │
│  1. Sends initialize                       │
│  2. Sends tools/list                       │
│  3. Reads Tool Definition Schemas          │
│  4. Sends tools/call with JSON-RPC msg     │
└────────────────┬───────────────────────────┘
                 │  Transport (stdio/HTTP)
┌────────────────▼───────────────────────────┐
│              MCP SERVER                    │
│  5. Parses JSON-RPC 2.0 message            │
│  6. Passes Context to tool handler         │
│  7. Executes Tool / Resource / Prompt      │
│  8. Returns JSON-RPC result                │
└────────────────────────────────────────────┘
```

---

## §04. HOW IT WORKS (MECHANISM)

### Internal Working — Step by Step

#### Step 1 — Server Starts, Registers Capabilities

```
Developer writes tool functions
        │
        ▼
FastMCP reads type hints + docstrings
        │
        ▼
Builds internal capability registry:
  { "add": <handler>, "schema": {...} }
        │
        ▼
Server binds to transport (stdio or HTTP port)
        │
        ▼
Server enters event loop — waits for messages
```

#### Step 2 — Client Connects and Initializes

```
Client opens transport connection
        │
        ▼
Client sends initialize request:
  {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {}
    }
  }
        │
        ▼
Server responds with its capabilities:
  {
    "result": {
      "protocolVersion": "2024-11-05",
      "capabilities": {
        "tools": { "listChanged": true }
      }
    }
  }
```

#### Step 3 — Client Lists Tools

```
Client sends tools/list
        │
        ▼
Server returns all registered tool schemas:
  {
    "result": {
      "tools": [
        {
          "name": "add",
          "description": "Add two integers.",
          "inputSchema": { ... }
        }
      ]
    }
  }
        │
        ▼
LLM now knows what tools exist and what
arguments each tool accepts
```

#### Step 4 — LLM Decides to Call a Tool

```
User prompt: "What is 3 + 7?"
        │
        ▼
LLM reasons: I should use the "add" tool
        │
        ▼
LLM constructs tool call:
  {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "add",
      "arguments": { "a": 3, "b": 7 }
    }
  }
```

#### Step 5 — Server Executes Tool

```
Server receives tools/call
        │
        ▼
Server validates arguments against inputSchema
        │
        ▼
Server creates Context object for this request
        │
        ▼
Server calls: await add(a=3, b=7, ctx=ctx)
        │
        ▼
Tool returns: 10
        │
        ▼
Server wraps result in JSON-RPC response:
  {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
      "content": [
        { "type": "text", "text": "10" }
      ]
    }
  }
```

#### Step 6 — Client Receives Result

```
Client receives result
        │
        ▼
LLM reads content: "10"
        │
        ▼
LLM generates final response to user:
  "3 + 7 = 10"
```

---

### Full Sequence Diagram

```
User        LLM/Client          Transport         MCP Server
 │               │                   │                  │
 │─ "3 + 7?" ──> │                   │                  │
 │               │─ initialize ─────>│─ initialize ────>│
 │               │<──────────────────│<─ result ────────│
 │               │─ tools/list ─────>│─ tools/list ────>│
 │               │<──────────────────│<─ tool schemas ──│
 │               │                   │                  │
 │               │ (LLM decides)     │                  │
 │               │                   │                  │
 │               │─ tools/call ─────>│─ tools/call ────>│
 │               │  add(3,7)         │  add(3,7)        │
 │               │<──────────────────│<─ result: 10 ────│
 │               │                   │                  │
 │<─ "3+7 = 10"─ │                   │                  │
```

---

### Key Internal Components

| Component               | Role                                      |
|-------------------------|-------------------------------------------|
| **FastMCP**             | Framework that auto-builds the server     |
| **Capability Registry** | Maps tool names → handler functions       |
| **JSON-RPC Router**     | Routes incoming method calls to handlers  |
| **Schema Validator**    | Validates arguments before handler runs   |
| **Context**             | Injects logging/session into each handler |
| **Transport Adapter**   | Abstracts stdio vs HTTP vs WebSocket      |

🔑 Jargon:

- **FastMCP** — high-level Python MCP server framework
- **Capability Registry** — internal map of name → handler
- **JSON-RPC Router** — dispatches calls to correct handler
- **Schema Validator** — enforces inputSchema at runtime
- **Transport Adapter** — decouples wire protocol from logic

---

## 🔑 JARGON SUMMARY (Chunk 2)

| Term                    | Definition                                    |
|-------------------------|-----------------------------------------------|
| **Client**              | AI agent / LLM host that calls MCP tools      |
| **Server**              | Your code that exposes MCP capabilities       |
| **Transport**           | Wire protocol (stdio, HTTP/SSE, WebSocket)    |
| **JSON-RPC 2.0**        | Standard JSON message format for remote calls |
| **Tool**                | Callable function exposed to the LLM          |
| **Resource**            | URI-addressed read-only data                  |
| **Prompt**              | Reusable parameterized prompt template        |
| **initialize**          | First handshake message in MCP lifecycle      |
| **tools/list**          | Message to enumerate available tools          |
| **tools/call**          | Message to invoke a specific tool             |
| **Context**             | Per-request object with logging + session     |
| **FastMCP**             | High-level Python MCP server library          |
| **Capability Registry** | Internal map of tool name → handler           |
| **Schema Validator**    | Validates args against inputSchema at runtime |
| **Transport Adapter**   | Decouples wire protocol from business logic   |