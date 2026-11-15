# MCP Learning Guide


## 1. MCP OVERVIEW

### 1.1 What is MCP?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MCP = Model Context Protocol                                               │
│                                                                             │
│  DEFINITION:                                                                │
│  A standardized protocol letting an AI client discover                      │
│  and call tools/data/prompts exposed by a server.                           │
│                                                                             │
│  Think of it as:                                                            │
│  • A "USB port" for AI — plug in any tool                                   │
│  • A contract between AI and tools                                          │
│  • Language-agnostic protocol (works with any programming language)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 The problem MCP solves

Without a shared protocol, every AI-to-tool integration
reinvents discovery, argument typing, invocation, error handling, and session
management.

MCP standardizes those conversations. It does not run a model and
does not decide when a model should use a tool — that's the client/agent's job.

```
WITHOUT MCP:                          WITH MCP:
─────────────────────────────────     ─────────────────────────────────
• Custom integration per tool         • Standard interface for all tools
• Tight coupling                      • Loose coupling
• Hard to swap tools                  • Easy to add/remove tools
• Vendor lock-in                      • Interoperability
• No standard discovery               • Built-in tool discovery 
```

### 1.3 MCP Specification Source

Official specification: https://modelcontextprotocol.io

## 2. Concept Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MCP CONCEPT HIERARCHY                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PROTOCOL LAYER                                                             │
│  ├── JSON-RPC 2.0 ─────────── message format                                │
│  └── Transport ────────────── How messages travel                           │
│       ├── Streamable HTTP                                                   │
│       └── stdio                                                             │
│                                                                             │
│  COMPONENT LAYER                                                            │
│  ├── MCP Server ───────────── exposes capabilities                          │
│  └── MCP Client ───────────── consumes capabilities                         │
│                                                                             │
│  CAPABILITY LAYER                                                           │
│  ├── Tools ────────────────── executable functions                          │
│  ├── Resources ────────────── readable data by URI                          │
│  ├── Prompts ──────────────── reusable prompt templates                     │
│  ├── Sampling ─────────────── server can request an LLM completion          │
│  └── Elicitation ──────────── server can ask the user for input             │
│                                                                             │
│  LIFECYCLE LAYER                                                            │
│  ├── Initialization ───────── Capability negotiation                        │
│  ├── Discovery ────────────── List available items                          │
│  ├── Invocation ───────────── Call tools / read resources                   │
│  └── Shutdown ─────────────── Clean disconnect                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 High-Level Architecture

```


                     ┌──────────────────────────┐
                     │        MCP CLIENT        │
                     │   ( Agent / App / IDE )  │
                     └────────────┬─────────────┘
                                  │ JSON-RPC Messages
                                  ▼
                     ┌──────────────────────────┐
                     │        TRANSPORT         │
                     ├──────────────────────────┤
                     │     stdio                │
                     │     Streamable HTTP      │
                     └────────────┬─────────────┘
                                  │ JSON-RPC Messages
                                  ▼
                     ┌──────────────────────────┐
                     │        MCP SERVER        │
                     │ (tools + data + prompts) │
                     └────────────┬─────────────┘
                                  │                             
          ┌───────────────────────┼─────────────────────────┐
          │                       │                         │
          ▼                       ▼                         ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐ 
│         TOOLS        │ │      RESOURCES       │ │       PROMPTS        │ 
│       (actions)      │ │        (data)        │ │     (templates)      │ 
├──────────────────────┤ ├──────────────────────┤ ├──────────────────────┤ 
│   tools/list         │ │  resources/list      │ │   prompts/list       │ 
│   tools/call         │ │  resources/read      │ │   prompts/get        │ 
│   streaming          │ │  subscriptions       │ │   arguments          │
│   progress           │ │  templates           │ │   sampling           │ 
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘   
```

### 3.2 Tool Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   MCP CLIENT                              MCP SERVER                        │
│                                                                             │
│   ┌───────────────┐                       ┌───────────────┐                 │
│   │               │   "tools/list"        │               │                 │
│   │   Asks:       │ ───────────────────▶  │   Responds:   │                 │
│   │   What can    │                       │   Here are    │                 │
│   │   you do?     │ ◀───────────────────  │   my tools    │                 │
│   │               │   [tool1, tool2...]   │               │                 │
│   └───────────────┘                       └───────────────┘                 │
│                                                                             │
│   ┌───────────────┐                       ┌───────────────┐                 │
│   │               │    "tools/list"       │               │                 │
│   │   Requests:   │ ───────────────────▶  │   Executes:   │                 │
│   │   Run this    │                       │   Runs tool,  │                 │
│   │   tool        │ ◀───────────────────  │   returns     │                 │
│   │               │   {result: ...}       │   result      │                 │
│   └───────────────┘                       └───────────────┘                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Tool Definition Structure

```
{
 "name": "get_weather",
 "description": "Get weather for a city",
 "inputSchema": {
   "type": "object",
   "properties": {
      "city": {
         "type": "string"
      }
   }
 }
}
```

### 3.4 Tool Operations

```
 ┌─────────────────────┬───────────────────────────────┐  
 │ CATEGORY            │ MEANINIG                      │  
 ├─────────────────────┼───────────────────────────────┤  
 │ tool/list           │ discover available tools      │  
 │ tool/call           │ execute tool                  │  
 │ streaming           │ partial outputs               │  
 │ progress updates    │ execution status              │  
 │ cancel              │ stop tool                     │  
 └─────────────────────┴───────────────────────────────┘  
```

### 4. Term Definitions

```
┌──────────────────┬─────────────────────────────────────────────────────────┐
│ TERM             │ DEFINITION                                              │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ MCP Server       │ EXPOSES tools/resources/prompts.                        │
│                  │ MEMORIZE: "Server = Provider = Exposes"                 │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ MCP Client       │ CALLS what a server exposes.                            │
│                  │ MEMORIZE: "Client = Consumer = Calls"                   │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Tool             │ Invocable function.                                     │
│                  │ Has: name, description, input schema, output.           │
│                  │ Example: search_transactions, send_email                │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Resource         │ Read-only data by URI.                                  │
│                  │ Has: URI, name, mime type, contents.                    │
│                  │ Example: file://config.json, db://users                 │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Prompt           │ Reusable template with arguments                        │
│                  │ Has: name, description, arguments, messages.            │
│                  │ Example: "summarize_document" prompt template           │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Transport        │ Channel messages travel over.                           │
│                  │ Options: Streamable HTTP, stdio                         │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ JSON-RPC 2.0     │ The message format used by MCP.                         │
│                  │ Every message has: jsonrpc, method/result, id           │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Capability       │ A feature a peer(client/server) supports;               │
│                  │ Negotiated during initialization.                       │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Session          │ A stateful connection between client and server.        │
└──────────────────┴─────────────────────────────────────────────────────────┘
```

## 5. Transports

```
┌─────────────────┬──────────────────────────────────────────────────────────┐
│ TRANSPORT       │ DETAILS                                                  │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ Streamable HTTP │ Single HTTP endpoint.                                    │
│                 │                                                          │
│                 │ POST for client → server messages;                       │
│                 │ optional GET opens an SSE-formatted event stream         │
│                 │ for server→client messages.                              │
│                 │                                                          │
│                 │ Best for: remote/deployed servers, scaling.              │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ stdio           │ Standard input/output pipes                              │
│                 │                                                          │
│                 │ HOW IT WORKS:                                            │
│                 │ • Client spawns server as subprocess                     │
│                 │ • Communication via stdin/stdout                         │
│                 │                                                          │
│                 │ Best for: local tools, IDE plugins, CLIs.                │
│                 │ Do NOT print logs to stdout — it's the wire.             │
└─────────────────┴──────────────────────────────────────────────────────────┘

LEGACY / DEPRECATED:
"HTTP+SSE" — a separate, older transport (distinct GET-SSE and POST
endpoints). Superseded by Streamable HTTP. Still seen in some clients
for backward compatibility, but new servers should not implement it.
```

> Note  
> Discovery pattern for a client that doesn't know which transport a server
> uses:
> try Streamable HTTP first; if it 404s/405s, fall back to legacy HTTP+SSE.

## 6. CONNECTION LIFECYCLE

```
ClientSession       Client HTTP transport       FastMCP server
     │                        │                         │
     │ initialize             │                         │
     │───────────────────────>│ POST initialize         │
     │                        │────────────────────────>│
     │                        │ session + capabilities  │
     │ initialize result      │<────────────────────────│
     │<───────────────────────│                         │
     │ initialized notice     │ POST notification       │
     │───────────────────────>│────────────────────────>│
     │                        │ 202 acknowledgement     │
     │                        │<────────────────────────│
     │                        │ GET event stream        │
     │                        │────────────────────────>│
     │             ***** READY STATE *****              │
     │ tools/list             │ POST tools/list         │
     │───────────────────────>│────────────────────────>│ Discover available tools
     │ list result            │<────────────────────────│
     │<───────────────────────│                         │
     │                        │                         │
     │ tools/call             │ POST tools/call         │
     │───────────────────────>│────────────────────────>│ Invoke a tool
     │ call result            │<────────────────────────│
     │<───────────────────────│                         │
     │                        │                         │
     │ close                  │ DELETE + session ID     │
     │───────────────────────>│────────────────────────>│ Terminate session 
     │                        │ 200; event stream ends  │
     │                        │<────────────────────────│```
```

```
┌─────────────────────┬───────────────────────────────────────────────────────┐
│ METHOD              │ PURPOSE                                               │
├─────────────────────┼───────────────────────────────────────────────────────┤
│ initialize          │ Start session, negotiate capabilities                 │
│ tools/list          │ Get available tools                                   │
│ tools/call          │ Execute a tool                                        │
│ resources/list      │ Get available resources                               │
│ resources/read      │ Read a resource's content                             │
│ prompts/list        │ Get available prompts                                 │
│ prompts/get         │ Get a prompt template                                 │
│ notifications/*     │ Various fire-and-forget notifications                 │
│ ping                │ Keep connection alive                                 │
└─────────────────────┴───────────────────────────────────────────────────────┘
```

### Step 1: Uvicorn starts the application

- Uvicorn imports the FastAPI application and enters its lifespan.
- The lifespan enters the MCP session manager and then yields control,  
  meaning the application is ready to receive traffic.

### Step 2: the client creates transport infrastructure

`streamable_http_client` creates an HTTP client, internal tasks, and the AnyIO
streams used by `ClientSession`. At this point there is transport
infrastructure, but MCP negotiation has not happened yet.

### Step 3: `initialize`

`session.initialize()` creates request ID `0` and sends:

```json
{
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {},
    "clientInfo": {
      "name": "mcp",
      "version": "0.1.0"
    }
  },
  "jsonrpc": "2.0",
  "id": 0
}
```

The server selects a compatible protocol version, creates a session ID, and
returns its capabilities and identity. The observed server capabilities
include tools, prompts, and resources. A capability says what a peer supports;
it does not necessarily mean the corresponding list contains items.

The server's advertised version is the MCP SDK version because no separate
application version was supplied to FastMCP.

### Step 4: `notifications/initialized`

After accepting the initialization result, the client sends
`notifications/initialized`. This changes the session from negotiation to
normal operation. It is a notification, so there is no JSON-RPC result. HTTP
`202 Accepted` confirms transport-level acceptance.

### Step 5: the event stream

The client transport may open `GET /mcp/` with `Accept: text/event-stream`.
This gives the server a channel for messages it initiates rather than direct
responses to a client request. It can carry notifications, progress, logging,
or requests for client-supported features.

This GET can remain open while later POST requests occur on other connections.
That is normal asynchronous behavior, not a duplicate session.

### Step 6: `tools/list`

`session.list_tools()` sends request ID `1`. FastMCP inspects registered
functions and returns tool metadata and JSON Schemas.

For `add`, the schema states that `a` and `b` are required numbers. A client can
use that schema to validate or construct arguments before invoking the tool.
The source of truth remains the Python type annotations.

### Step 7: `tools/call`

`session.call_tool("add", {"a": 20, "b": 22})` sends request ID `2`. FastMCP:

1. Resolves the registered tool by name.
2. Validates arguments against the generated input model.
3. Calls the Python function.
4. Validates and serializes its return value.
5. Produces MCP content blocks and structured content.

The result contains both:

- `content`, portable MCP content blocks that clients can render or pass to a
  model.
- `structuredContent`, the machine-readable object described by the output
  schema.

`isError: false` means the tool execution succeeded.

### Step 8: graceful session termination

Leaving the transport context sends:

```text
DELETE /mcp/
Mcp-Session-Id: <the negotiated session>
Mcp-Protocol-Version: 2025-11-25
```

The server removes the session and ends its associated event stream.

There is no JSON-RPC `shutdown` method in this MCP lifecycle. The `DELETE`
request is the graceful session-termination mechanism for stateful Streamable
HTTP. Separately, stopping Uvicorn ends the entire server process through the
FastAPI lifespan.

### 2. Tool System (Primary MCP Feature)

Tools are the **main reason MCP exists**.

| Category   | Feature                           | Description                           |
|------------|-----------------------------------|---------------------------------------|
| ✓ Core     | Tool Registration                 | Server exposes tool                   |
| ✓ Core     | Tool Discovery `(tools/list)`     | Client queries available tools        |
| ✓ Core     | Tool  Execution `(tools/call)`    | Client invokes tool                   |
| ✓ Core     | Input Schema (validate arguments) | JSON schema describing tool arguments |
| ~ Advanced | Tool Streaming                    | Stream partial tool output            |
| ~ Advanced | Execution progress                | Tool execution Updates/Notifications  |
| ~ Advanced | Cancel tool execution             | Stop long running tool                |

**Tool Architecture:**

```
 Client
   │ tools/list
   ▼
 Server ────► returns tool definitions


 Client
   │ tools/call
   ▼
 Server ────► executes tool
    │ 
    ▼
 Response
```

### 3. Resource System (Second Major Feature)

Resources expose **data instead of actions**.

| Category   | Feature              | Description                                |
|------------|----------------------|--------------------------------------------|
| ✓ Core     | Resources            | Data accessible by URI                     |
| ~ Advanced | Templates            | Parameterized resource URIs                |
| ~ Advanced | Subscriptions        | Subscribe to resource update notifications |
| ~ Advanced | BlobResourceContents | Binary resource content support            |
| ~ Advanced | Pagination           | Partial listing of resources               |
| ~ Advanced | Roots                | Resource namespace roots                   |

**Flow:**

```
Client
   |
   | resources/list
   v
Server returns resources

Client
   |
   | resources/read
   v
Server returns content
```

Resources use URIs.

**Examples:**

```
file://docs/api.md
db://users/123
logs://server/errors
```

### 4. Prompt System

Prompts are **templates for AI input**.

**Purpose:**

- standardize prompts
- parameterized prompts
- reuse prompt logic

| Category   | Feature          | Description                          |
|------------|------------------|--------------------------------------|
| ✓ Core     | Prompts          | Prompt templates hosted on server    |
| ✓ Core     | Prompt Arguments | Dynamic prompt parameters            |
| ~ Advanced | Sampling         | Server can requests model generation |

**Flow:**

```
Client
   |
   | prompts/list
   v
Server returns prompts

Client
   |
   | prompts/get
   v
Server returns prompt template
```

**Prompt Template Example**

```
Prompt: summarize_document

Template:
"Summarize the following document:

{{document}}

Focus on:
- key insights
- decisions
- risks"
```

Arguments:

```
{
 "document": "text here"
}
```

### 5. Transport Layer

How MCP messages travel. Transport carries JSON-RPC messages.

| Category  | Feature                   | Description                  |
|-----------|---------------------------|------------------------------|
| Transport | stdio Transport           | Local process transport      |
| Transport | SSE Transport             | Server-sent events over HTTP |
| Transport | Streamable HTTP Transport | HTTP streaming of responses  |

| Transport      | Use Case            |
|----------------|---------------------|
| stdio          | Local process tools |
| SSE            | Web streaming       |
| HTTP streaming | Remote MCP servers  |

```
 Client
  │
  │ JSON-RPC
  ▼
 Transport
  │
  ▼
 Server
```

### 6. Notifications and Messaging

- MCP messages use JSON-RPC 2.0
- MCP supports two message types.

| Category   | Feature                    | Description               | 
|------------|----------------------------|---------------------------| 
| ✓ Core     | Message type: Request      | Requires response         | 
| ✓ Core     | Message type: Notification | Fire-and-forget           | 
| ~ Advanced | Logging to Client          | Server logs forwarded     |  
| IC         | Debug/Message logging      | Debugging message traffic | 

Request: → response expected

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": {
      "a": 20,
      "b": 22
    }
  }
}
```

The matching result uses the same `id`:

The identifier lets a client match responses to requests even when several
requests are in flight concurrently.

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "structuredContent": {
      "a": 20.0,
      "b": 22.0,
      "sum": 42.0
    },
    "isError": false
  }
}
```

Notification: → No response is expected for a notification.
That is why the server returns an HTTP acknowledgement but no JSON-RPC result.
Used for:

- progress/update
- log/message
- resource/changed

A notification deliberately has no `id`:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

An unsuccessful JSON-RPC request contains `error` instead of `result`.

**Protocol errors are separate from HTTP status codes:**
HTTP reports whether the transport exchange worked,
while JSON-RPC reports whether the requested operation worked.

### 7. Runtime & Operational Features

These are **operational features**, not core protocol.

| Category | Feature        | Description                         |
|----------|----------------|-------------------------------------|
| IC       | Authentication | Access control                      |
| IC       | Rate Limiting  | Server throttling to prevent abuse  |
| IC       | Health Checks  | Server status monitoring            |
| IC       | Error Handling | Structured JSON-RPC error responses |

### 8. AI / Agent Integration

| Category   | Feature                 | Description               | 
|------------|-------------------------|---------------------------| 
| ~ Advanced | AI Agent Integration    | Agent orchestrated tools  | 
| ~ Advanced | Human-in-the-Loop(HITL) | User approval workflow    | 
| ~ Advanced | Elicitation             | Server asks user for info | 

**Elicitation:**

```
Tool requires confirmation

Server
  │
  │ elicitation request
  ▼
Client
  │
  │ ask user
  ▼
User response
```

### 9. Data & Content Features

| Category   | Feature                | Description              |
|------------|------------------------|--------------------------|
| ✓ Core     | Multiple Content Types | Rich response formats    |
| ~ Advanced | Embedding Support      | Return vector embeddings |

| Content Type | Example     |
|--------------|-------------|
| text         | markdown    |
| image        | PNG         |
| blob         | binary file |
| embeddings   | vectors     |

### 10. Implementation Patterns

Important for Python/Node MCP servers.

| Category | Feature             | Description                   |
|----------|---------------------|-------------------------------|
| IC       | Async/Await Pattern | Non-blocking server execution |

**Legend**

* ✓ Core = Core MCP concept
* ~ Advanced = Advanced capability
* IC = Implementation concern (not protocol feature)

## 7. Message Format (JSON-RPC 2.0)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ JSON-RPC 2.0 REQUEST                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   {                                                                         │
│     "jsonrpc": "2.0",        // Always "2.0"                                │
│     "method": "tools/call",  // The method being called                     │
│     "params": {...},         // Method parameters                           │
│     "id": 1                  // Request ID (for matching response)          │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ JSON-RPC 2.0 SUCCESS RESPONSE                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   {                                                                         │
│     "jsonrpc": "2.0",        // Always "2.0"                                │
│     "id": 1,                 // Matches request ID                          │
│     "result": {                                                             │
│         "structuredContent": { "x": 1, "y": 2, "sum": 3 },                  │
│         "isError": false                                                    │
│     }                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Notification (fire-and-forget, no id, no response expected):
┌─────────────────────────────────────────────────────────────────────────────┐
│ JSON-RPC 2.0 SUCCESS RESPONSE                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   {                                                                         │
│     "jsonrpc": "2.0",        // Always "2.0"                                │
│     "id": 1,                 // Matches request ID                          │
│     "result": {                                                             │
│         "structuredContent": { "x": 1, "y": 2, "sum": 3 },                  │
│         "isError": false                                                    │
│     }                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ JSON-RPC 2.0 ERROR RESPONSE                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   {                                                                         │
│     "jsonrpc": "2.0",                                                       │
│     "id": 1,                                                                │
│     "error": {                                                              │
│       "code": -32600,        // Error code                                  │
│       "message": "Invalid Request",                                         │
│       "data": {...}          // Optional additional info                    │
│     }                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Key distinction: HTTP status tells you the transport exchange worked. 
JSON-RPC `result/error` tells you the requested operation worked. 
A `200 OK` does not by itself prove a tool call succeeded — check `isError`
```

### 7.2 Complete Message Flow Example

```
USER ACTION: Click "Search Transactions" with risk_level="high"

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: UI → Gateway (HTTP)                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   POST http://gateway:8002/tools/call                                       │
│   Content-Type: application/json                                            │
│                                                                             │
│   {                                                                         │
│     "tool_name": "search_transactions",                                     │
│     "arguments": {                                                          │
│       "risk_level": "high",                                                 │
│       "limit": 10                                                           │
│     }                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Gateway opens SSE connection to MCP Server                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   GET http://mcp-server:8001/sse                                            │
│   Accept: text/event-stream                                                 │
│                                                                             │
│   (Connection established, ready for events)                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Gateway sends initialize (JSON-RPC)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   → CLIENT TO SERVER:                                                       │
│   {                                                                         │
│     "jsonrpc": "2.0",                                                       │
│     "method": "initialize",                                                 │
│     "params": {                                                             │
│       "protocolVersion": "2024-11-05",                                      │
│       "capabilities": {},                                                   │
│       "clientInfo": {"name": "gateway", "version": "1.0.0"}                 │
│     },                                                                      │
│     "id": 0                                                                 │
│   }                                                                         │
│                                                                             │
│   ← SERVER TO CLIENT:                                                       │
│   {                                                                         │
│     "jsonrpc": "2.0",                                                       │
│     "id": 0,                                                                │
│     "result": {                                                             │
│       "protocolVersion": "2024-11-05",                                      │
│       "capabilities": {"tools": {}},                                        │
│       "serverInfo": {"name": "transaction-server", "version": "1.0.0"}      │
│     }                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Gateway sends tools/call (JSON-RPC)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   → CLIENT TO SERVER:                                                       │
│   {                                                                         │
│     "jsonrpc": "2.0",                                                       │
│     "method": "tools/call",                                                 │
│     "params": {                                                             │
│       "name": "search_transactions",                                        │
│       "arguments": {                                                        │
│         "risk_level": "high",                                               │
│         "limit": 10                                                         │
│       }                                                                     │
│     },                                                                      │
│     "id": 1                                                                 │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: MCP Server executes tool                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   1. server.py receives tools/call                                          │
│   2. Looks up "search_transactions" in registry                             │
│   3. Calls tools.search_transactions(risk_level="high", limit=10)           │
│   4. tools.py calls db.search_transactions(...)                             │
│   5. db.py executes SQL query against PostgreSQL                            │
│   6. Results flow back up: db → tools → server                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 6: MCP Server sends response (JSON-RPC)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ← SERVER TO CLIENT:                                                       │
│   {                                                                         │
│     "jsonrpc": "2.0",                                                       │
│     "id": 1,                                                                │
│     "result": {                                                             │
│       "content": [                                                          │
│         {                                                                   │
│           "type": "text",                                                   │
│           "text": "{\"transactions\":[{\"transaction_id\":\"TX-001\",...}]}"│
│         }                                                                   │
│       ]                                                                     │
│     }                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 7: Gateway returns response to UI (HTTP)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   HTTP 200 OK                                                               │
│   Content-Type: application/json                                            │
│                                                                             │
│   {                                                                         │
│     "tool_name": "search_transactions",                                     │
│     "arguments": {"risk_level": "high", "limit": 10},                       │
│     "result": {                                                             │
│       "transactions": [...],                                                │
│       "total_count": 10                                                     │
│     },                                                                      │
│     "duration_ms": 45,                                                      │
│     "success": true,                                                        │
│     "message_log": [                                                        │
│       {"phase": "REQUEST", ...},                                            │
│       {"phase": "MCP_REQUEST", ...},                                        │
│       {"phase": "MCP_RESPONSE", ...},                                       │
│       {"phase": "COMPLETE", ...}                                            │
│     ]                                                                       │
│   }                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 8: UI displays results                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Left panel: Transaction results (JSON)                                    │
│   Right panel: MCP message flow (formatted log)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 9. Generic Code Patterns

```python
# --- SERVER SIDE ---
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-server")


@mcp.tool()
def example_tool(x: float, y: float) -> dict[str, float]:
    """One clear purpose. Typed inputs. Small, deterministic output."""
    return {"x": x, "y": y, "sum": x + y}


mcp.run(transport="stdio")
# or: mcp.run(transport="http", host="0.0.0.0", port=8000)
```

```python
# --- CLIENT SIDE (Streamable HTTP) ---
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async with streamable_http_client(url) as (read, write, get_session_id):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("example_tool", {"x": 1, "y": 2})
```

**Good tool design:**

- one clear purpose
- typed inputs
- small output
- deterministic where possible
- explicit errors
- no hidden side effects

**Bad tool design:**

- many unrelated arguments
- printing instead of returning
- leaking raw internal objects
- mixing logs with the stdio wire channel.

## 10. ASGI / Network Stack (Python HTTP servers only)

This layer is implementation detail, not MCP itself — relevant only when a
Python MCP server runs over Streamable HTTP via an ASGI web server (e.g.,
Uvicorn) instead of stdio.

```
Application intent: call a tool
        │
MCP: lifecycle, capabilities, tools/resources/prompts
        │
JSON-RPC 2.0: method, params, id, result/error
        │
Streamable HTTP: POST, optional GET event stream, session ID
        │
ASGI / async runtime: async messages, event loop (asyncio/uvloop)
        │
TCP/IP: bytes between host:port
```

- **ASGI** is the interface between the async web server and the application;
  it's not a network protocol.
- **stdio-based** MCP servers skip this entire stack — no HTTP, no ASGI, just
  process pipes.

## 11. Error Boundaries

```
┌──────────────┬────────────────────────────────┬────────────────────────────┐
│ LAYER        │ EXAMPLE                        │ OBSERVABLE FORM            │
├──────────────┼────────────────────────────────┼────────────────────────────┤
│ Tool         │ Tool raises or returns an error│ Call result, isError:true  │
│ MCP/JSON-RPC │ Unknown method, bad request    │ JSON-RPC error object      │
│ HTTP         │ Wrong route, bad media type    │ HTTP 4xx/5xx               │
│ Session      │ Missing/expired session ID     │ HTTP or JSON-RPC error     │
│ Network      │ Server unreachable             │ Client transport exception │
│ Process      │ Startup/config failure         │ Runtime/lifespan error     │
└──────────────┴────────────────────────────────┴────────────────────────────┘
```

## 12. Debugging Checklist

```
┌─────────────────────────────┬───────────────────────────────────────────────┐
│ PROBLEM                     │ CHECK                                         │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ Tools not discovered        │ Is MCP server running? Check /health          │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ 404 on endpoint             │ Transport mismatch (stdio vs HTTP)            │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ Tool returns empty          │ Check underlying data source                  │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ Connection refused          │ Check port / process / networking             │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ JSON parse error            │ Tool not returning valid JSON string          │
├─────────────────────────────┼───────────────────────────────────────────────┤
│ Timeout                     │ Long-running tool, increase timeout           │
└─────────────────────────────┴───────────────────────────────────────────────┘
```

## SUMMARY: KEY TAKEAWAYS

```
┌─────────────────────────────────────────────────────────────────────────────┐

 1. MCP = standard protocol for AI clients to call tools/data/prompts.
  
  2. Server EXPOSES capabilities, Client CALLS them.
  
  3. All messages use JSON-RPC 2.0.
  
  4. Two standard transports: 
      - stdio (local) and 
      - Streamable HTTP (remote).
  
        Standalone SSE ("HTTP+SSE") is deprecated legacy, not a third option.
     
  5. Discovery: */list· 
     Execution: */call.
  
  6. initialize() must complete before any other method.
  
  7. A capability being advertised ≠ its list being non-empty.
  
  8. HTTP 200 ≠ tool success — check isError in the JSON-RPC result.

└─────────────────────────────────────────────────────────────────────────────┘
```

