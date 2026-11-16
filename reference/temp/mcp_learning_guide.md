# MCP Basics

## Baseline

- MCP protocol:
    - 2025-11-25: stateful architecture
    - 2026-07-28: stateless-first architecture
- Transport:
    - stdio
    - Streamable HTTP
- FastMCP:
    - 3.4.5, the current stable release
    - > = 4
- Python
    - Modern Python with type hints.

We will learn the stable stateful protocol first, then explicitly study the new
stateless architecture as a migration.

## Course structure

1. Architecture, JSON-RPC, lifecycle, capabilities, stdio
2. **Tools** — discovery, schemas, execution, errors, structured results
3. **Resources** — URIs, reads, templates, subscriptions
4. **Prompts** — discovery, arguments, generated messages
5. **Client capabilities** — roots, elicitation, sampling  (deprecated in  
   `MCP 2026-07-28`)
6. **Protocol utilities** — progress, cancellation, logging, pagination and
   completion,
7. **Streamable HTTP**
8. **Authentication and authorization**
9. **Context, lifecycle state and concurrency**
10. **FastMCP-specific composition** — providers, proxies, transforms, generated
    servers
11. **Testing, observability, security and production deployment**
12. **MCP 2026-07-28 stateless architecture + FastMCP 4 migration**

The protocol separates server primitives into tools, resources and prompts,
while client-side capabilities include sampling, roots and elicitation.

Utilities such as logging, completion, progress and cancellation sit across
these features.

> Sampling is deprecated in `MCP 2026-07-28`.
> It still exists for compatibility, but the specification says new
> implementations should not add it.
> Suggested replacement is a direct LLM-provider integration.
>
> We should still learn it because it exposes several important MCP concepts:
> client capabilities, model abstraction, multi-round interactions, tool loops,
> trust boundaries, and the difference between the 2025-11-25 and 2026-07-28
> protocol architectures.

## Concept Hierarchy

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
│  └── MCP Client ───────────── manages protocol communication                │
│                                                                             │
│  CAPABILITY LAYER                                                           │
│  ├── Tools ────────────────── executable operation                          │
│  ├── Resources ────────────── readable context identified by a URI          │
│  ├── Prompts ──────────────── reusable interaction templates                │
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

## High-Level Architecture

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

## Term Definitions

```
┌──────────────────┬─────────────────────────────────────────────────────────┐
│ TERM             │ DEFINITION                                              │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ MCP Host         │ Application with AI experience.                         │
│                  │ MEMORIZE: "Host = Orchestrates clients"                 │
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
│ Capability       │ Declared support for an optional protocol feature       │
│                  │ Negotiated during initialization.                       │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Transport        │ Mechanism carrying protocol messages                    │
│                  │ Options: Streamable HTTP, stdio                         │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Protocol message │ JSON-RPC request, response or notification              │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Wire format      │ Actual bytes/messages transmitted between endpoints     │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ JSON-RPC 2.0     │ The message format used by MCP.                         │
│                  │ Every message has: jsonrpc, method/result, id           │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ Session          │ A stateful connection between client and server.        │
└──────────────────┴─────────────────────────────────────────────────────────┘
```

## First principles 1: What MCP Actually Is

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MCP = Model Context Protocol                                               │
│                                                                             │
│  DEFINITION:                                                                │
│  MCP is a standard contract between an AI application and                   │
│  external capabilities.                                                     │
│                                                                             │
│  This standardized protocol lets an AI application discover and call        │
│  tools/resources/prompts exposed by a server.                               │
│                                                                             │
│  Think of it as:                                                            │
│  • A "USB port" for AI — plug in any tool                                   │
│  • A contract between AI and tools                                          │
│  • Language-agnostic protocol (works with any programming language)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The problem MCP solves

Suppose program A wants to call capabilities exposed by program B.
Without a shared protocol, A must know B's proprietary API:

```
A ───── custom integration ─────> B
```

Every AI-to-tool integration reinvents discovery, argument typing, invocation,
error handling, and session management.

Now imagine 20 AI applications and 100 external systems.
Without standardization:

```
20 clients × 100 integrations = integration mess
```

### MCP to the rescue

MCP defines a common contract and standardizes those conversations.

```
                  MCP
            ┌──────────────┐
AI Host ─── Client <──────> Server ─── Database
            Client <──────> Server ─── Git
            Client <──────> Server ─── SaaS API
            Client <──────> Server ─── Filesystem
            └──────────────┘
```

### Comparison

```
WITHOUT MCP:                          WITH MCP:
─────────────────────────────────     ─────────────────────────────────
• Custom integration per tool         • Standard interface for all tools
• Tight coupling                      • Loose coupling
• Hard to swap tools                  • Easy to add/remove tools
• Vendor lock-in                      • Interoperability
• No standard discovery               • Built-in tool discovery 
```

> MCP does not:
> > - define how your LLM or agent should reason
> > - run a model
> > - decide when a model should use a tool

### The main participants

```
Host
└── Client
    └── Server
        ├── Tools
        ├── Resources
        └── Prompts
```

#### Host

A MCP host is the **application containing the AI experience**.
It orchestrates MCP clients.

**Examples:** AI desktop application, IDE, agent runtime, or chat application.

#### Client

An MCP client is the **protocol participant inside the host** that communicates
with one MCP server.

Professional wording:

> “The host owns the user interaction, while its MCP client manages protocol
> communication with the server.”

#### Server

An MCP server is a program that **exposes capabilities and context**.

It does **not necessarily contain an LLM**. It may simply expose database
queries, API calls, calculations, files, or business operations.

A technically accurate sentence would be:
> “The host creates an MCP client which negotiates capabilities with the
> server over the stdio transport.”

---

## First principles 2: MCP has two layers

```
┌────────────────────────────────────────────┐
│ Data layer                                 │
│                                            │
│ JSON-RPC messages                          │
│ lifecycle                                  │
│ tools, resources, prompts, notifications   │
│ sampling / elicitation / roots             │
└────────────────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────┐
│ Transport layer                            │
│                                            │
│ stdio                                      │
│ Streamable HTTP                            │
└────────────────────────────────────────────┘
```

The **data layer** defines what messages mean.

The **transport layer** defines **how messages travel**.

### Transport Layer

Transport carries JSON-RPC messages.

MCP's two standard transports:

- `stdio` for local process communication and
- `Streamable HTTP` for network communication.

| Transport       | Use Case                    |
|-----------------|-----------------------------|
| stdio           | Local process tools         |
| Streamable HTTP | HTTP streaming of responses |

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
"HTTP+SSE" — a separate, older transport (distinct GET-SSE and POST endpoints).
Still seen in some clients for backward compatibility, but new servers 
should not implement it.

HTTP+SSE is superseded by Streamable HTTP. 
```

#### Important distinction:

A `tools/call` is **NOT an HTTP operation**.
It is an **MCP protocol operation** that could travel over `stdio` or `HTTP`

The same logical tool can be used through either transport.
The transport changes **how messages travel**, not what the tool does.

## First principles 3 — Message Format

At the wire level,
MCP protocol messages use JSON-RPC 2.0.

| Category   | Feature                    | Description               | 
|------------|----------------------------|---------------------------| 
| ✓ Core     | Message type: Request      | Requires response         | 
| ✓ Core     | Message type: Notification | Fire-and-forget           | 
| ~ Advanced | Logging to Client          | Server logs forwarded     |  
| IC         | Debug/Message logging      | Debugging message traffic | 

MCP supports two message types.

1. **request:** expects a response.

    ```
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │ JSON-RPC 2.0 REQUEST                                                        │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │   {                                                                         │
    │     "jsonrpc": "2.0",        // Always "2.0"                                │
    │     "id": 1                  // Request ID (for matching response)          │
    │     "method": "tools/call",  // The method being called                     │
    │     "params": {...},         // Method parameters                           │
    │   }                                                                         │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘
    ```

   The matching result uses the same `id`:

   The `id` lets a client match responses to requests even when several
   requests are in flight concurrently.

    ```
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
    ```

   ### Error Boundaries

   An unsuccessful JSON-RPC request contains `error` instead of `result`.

    ```
    ┌──────────────┬────────────────────────────────┬────────────────────────────┐
    │ LAYER        │ EXAMPLE                        │ OBSERVABLE FORM            │
    ├──────────────┼────────────────────────────────┼────────────────────────────┤
    │ Tool         │ Tool raises or returns an error│ Call result, isError:true  │
    │ MCP/JSON-RPC │ Unknown method, bad request    │ JSON-RPC error object      │
    │ HTTP         │ Wrong route, bad media type    │ HTTP 4xx/5xx               │
    │ Network      │ Server unreachable             │ Client transport exception │
    │ Process      │ Startup/config failure         │ Runtime/lifespan error     │
    └──────────────┴────────────────────────────────┴────────────────────────────┘
    ```

    ```
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
    ```

   **Key distinction:** Protocol errors are separate from HTTP errors

    - HTTP `200 OK` reports whether the transport exchange worked.
      It does not by itself prove a tool call succeeded — check `isError`
    - JSON-RPC `result/error` reports whether the requested operation worked.

2. **notification:** is one-way. No response is expected.

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

A **method** identifies the operation, for example:

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

**Note:**
> > That naming convention is worth internalizing.

## First principles 4 — MCP CONNECTION LIFECYCLE

### 2025-11-25: stateful protocol

Before calling tools, the MCP protocol performs initialization.

The client initiates the lifecycle with `initialize`;
after receiving the server response it sends `notifications/initialized`.
This is called **capability negotiation**.

The initialization exchange negotiates:

```
protocol version
+
client capabilities
+
server capabilities
+
implementation identity
```

**Conceptually:**

```
CLIENT                              SERVER
  │                                   │
  │──── initialize ──────────────────>│
  │                                   │
  │<── initialize result ─────────────│
  │                                   │
  │──── notifications/initialized ───>│
  │                                   │
  │    ***** READY STATE *****        │
  │                                   │
  │        normal operation           │
  │──── tools/list ──────────────────>│  Discover available tools
  │<── tools ─────────────────────────│
  │                                   │ 
  │──── tools/call ──────────────────>│  Invoke a tool
  │<── call result────────────────────│
  │                                   │
  │──── close ───────────────────────>│Terminate session
  │                                   │   
```

**Graceful session termination**

There is no JSON-RPC `shutdown` method in this MCP lifecycle.

The `DELETE` request is the graceful session-termination mechanism for
stateful Streamable HTTP.

#### Complete Message Flow Example

```

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: MCP Host → MCP Client (HTTP)                                        │
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
│ STEP 2: MCP Client sends initialize (JSON-RPC) to MCP Server                │
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
│ STEP 4: MCP Client sends tools/call (JSON-RPC) to MCP Server                │
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
│ STEP 7: MCP Client returns response to MCP Host (HTTP)                      │
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
│ STEP 8: MCP Host displays results                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Left panel: Transaction results (JSON)                                    │
│   Right panel: MCP message flow (formatted log)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2026-07-28: stateless-first protocol

TODO: update this section

## First principles 5 — MCP Primitives

Core MCP concept such as tool/resource/prompt

### Tools System

Tool is an executable operation.
Use a tool when something must be **performed**.

Tools are the **main reason MCP exists**.

**Tool Operations**

| Category   | Feature                           | Description                           |
|------------|-----------------------------------|---------------------------------------|
| ✓ Core     | Registration                      | Server exposes tool                   |
| ✓ Core     | Discovery `(tools/list)`          | Client queries available tools        |
| ✓ Core     | Execution `(tools/call)`          | Client invokes tool                   |
| ✓ Core     | Input Schema (validate arguments) | JSON schema describing tool arguments |
| ~ Advanced | Streaming                         | Stream partial tool output            |
| ~ Advanced | Execution progress                | Tool execution Updates/Notifications  |
| ~ Advanced | Cancel execution                  | Stop long running tool                |

**Tool Architecture**

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

### 3. Resource System (Second Major Feature)

Resources expose **data instead of actions**.
Use a resource when something must be **retrieved or inspected**.

| Category   | Feature              | Description                                |
|------------|----------------------|--------------------------------------------|
| ✓ Core     | Resources            | Readable context accessible by an URI      |
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
config://application
customer://123/profile
schema://orders
```

### 4. Prompt System

Prompt is a **reusable interaction template**.

Use a prompt when the server wants to provide a recommended workflow or
structured instruction to the host.

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

## Advanced Concepts

### Runtime & Operational Features

These are **operational features**, not core protocol.

| Category | Feature        | Description                         |
|----------|----------------|-------------------------------------|
| IC       | Authentication | Access control                      |
| IC       | Rate Limiting  | Server throttling to prevent abuse  |
| IC       | Health Checks  | Server status monitoring            |
| IC       | Error Handling | Structured JSON-RPC error responses |

### AI / Agent Integration

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

### Data & Content Features

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

## Debugging Checklist

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

## SUMMARY

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

