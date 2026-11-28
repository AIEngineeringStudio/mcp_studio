# Concept Hierarchy

```
    ┌──────────────────────────────────────────────────────────────────────┐
    │                        Model Context Protocol                        │
    ├──────────────────────────────────────────────────────────────────────┤
    │                                                                      │
    │  PROTOCOL LAYER                                                      │
    │  ├── JSON-RPC 2.0 ─────────── message format                         │
    │  └── Transport ────────────── How messages travel                    │
    │       ├── Streamable HTTP                                            │
    │       └── stdio                                                      │
    │                                                                      │
    │  COMPONENT LAYER                                                     │
    │  ├── MCP Host   ───────────── exposes capabilities                   │
    │  ├── MCP Server ───────────── exposes capabilities                   │
    │  └── MCP Client ───────────── manages protocol communication         │
    │                                                                      │
    │  CAPABILITY LAYER                                                    │
    │  ├── Tools ────────────────── executable operation                   │
    │  ├── Resources ────────────── readable context identified by a URI   │
    │  ├── Prompts ──────────────── reusable interaction templates         │
    │  └── Elicitation ──────────── server can ask the user for input      │
    │                                                                      │
    │  LIFECYCLE LAYER                                                     │
    │  ├── Discovery (optional) ─── List available items                   │
    │  ├── Invocation ───────────── tools/call + request metadata          │
    │  └── Shutdown ─────────────── Clean disconnect                       │
    │                                                                      │
    └──────────────────────────────────────────────────────────────────────┘
```

# Lesson 1 — MCP and the modern request model

## Baseline and Outcome

This lesson targets MCP `2026-07-28`, standalone FastMCP `4.2.0`, and Python
examples managed with `uv`.

After this lesson, you can identify the host, client, and server; read one MCP
request; and explain why MCP `2026-07-28` does not use an initialization
handshake or a protocol session.

## What MCP Actually Is

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

## The problem MCP solves

Suppose an application A wants to call capabilities exposed by application B.
Without a shared protocol, A must know B's proprietary API:

```
A ───── custom integration ─────> B
```

Without a shared protocol,
every AI application needs a custom integration for every external system.

Every integration has to reinvent discovery, argument typing, invocation,
error handling, and session management.

MCP standardizes communication between an MCP client and an MCP server.

```
Host Application
      |
      | Application-specific logic
      |
MCP Client
      |
      | MCP protocol
      | JSON-RPC over transport
      |
MCP Server
      |
      | Application-specific logic
      |
Business Service
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

MCP standardizes communication.

MCP does not:
> - define how your LLM or agent should reason
> - run a model
> - decide when a model should use a tool

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
│   progress/cancel    │ │  templates           │ │                      │ 
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘   
```

## The main participants

```
Host
└── Client
    └── Server
        ├── Tools
        ├── Resources
        └── Prompts
```

“The host creates an MCP client which negotiates capabilities with the server
over a stdio/http transport.”

#### Host

> A MCP host is the **application containing the AI experience**.
> It orchestrates MCP clients.
>
> It coordinates the model, user experience, permissions, and one or more MCP
> clients.

**Examples:** AI desktop application, IDE, agent runtime, or chat application.

#### Client

> An MCP client is **the protocol participant inside the host**.
>
>A client communicates with one MCP server and attaches protocol metadata to
> every request.

Professional wording:

> “The host owns the user interaction, while its MCP client manages protocol
> communication with the server.”

#### Server

> An MCP server is a program that **exposes capabilities and context**.
>
> It receives only the context sent through its MCP client. It does not
> automatically see the host's whole conversation or other servers.

It does **not necessarily contain an LLM**. It may simply expose database
queries, API calls, calculations, files, or business operations.

## MCP has two layers

```
┌────────────────────────────────────────────┐
│ Data layer                                 │
│                                            │
│ JSON-RPC methods, schemas, results, errors │
│ capabilities: tools, resources, prompts,   │
│ notifications, elicitation                 │
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

## Data Layer (Message Format)

At the wire level,
MCP protocol messages use JSON-RPC 2.0.

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
┌─────────────────────┬────────────────────────────────────────┐
│ METHOD              │ PURPOSE                                │
├─────────────────────┼────────────────────────────────────────┤
│ discovery(optional) │ Start session, negotiate capabilities  │
│ tools/list          │ Get available tools                    │
│ tools/call          │ Execute a tool                         │
│ resources/list      │ Get available resources                │
│ resources/read      │ Read a resource's content              │
│ prompts/list        │ Get available prompts                  │
│ prompts/get         │ Get a prompt template                  │
│ notifications/*     │ Various fire-and-forget notifications  │
│ ping                │ Keep connection alive                  │
└─────────────────────┴────────────────────────────────────────┘
```

**Note:**
> > That naming convention is worth internalizing.

## Transport Layer

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

### MCP architecture with two connection types

**STDIO, Streamable HTTP transports**

```
┌────────────────────────────────────────┐
│ HOST APPLICATION (Python Process A)    │
│                                        │
│  ┌────────────┐       ┌────────────┐   │
│  │ MCP Client │       │ MCP Client │   │
│  │     A      │       │     B      │   │
│  └──────┬─────┘       └──────┬─────┘   │
│         │                    │         │
└─────────┼────────────────────┼─────────┘
          │                    │
          │ STDIO              │ Streamable HTTP
          │                    │
          ▼                    ▼
 ┌─────────────────┐    ┌────────────────┐
 │ MCP Server A    │    │ MCP Server B   │
 │                 │    │                │
 │ Local Process B │    │ Remote Process │
 └─────────────────┘    └────────────────┘
```

### What changes between the two?

The key architectural difference is that while STDIO crosses a process boundary,
HTTP crosses an HTTP service boundary.

| Connection      | Where server runs         | Communication               |
|-----------------|---------------------------|-----------------------------|
| STDIO           | Separate local process    | Standard input/output pipes |
| Streamable HTTP | HTTP server, often remote | HTTP requests and responses |

#### Important distinction:

A `tools/call` is **NOT an HTTP operation**.
It is an **MCP protocol operation** that could travel over `stdio` or `HTTP`

Changing from stdio to HTTP should not change the meaning of `tools/call`.
It changes process and network behavior - **how messages travel**,
not the **tool contract** (what the tool does).

## Modern MCP is stateless at the protocol layer

MCP `2026-07-28` removed `initialize`, `notifications/initialized`, and the
`Mcp-Session-Id` header. Each request supplies what a server needs to interpret
that request.

```
CLIENT                                       SERVER
  |                                            |
  |---- server/discover (optional) ----------->|
  |<--- versions + server capabilities --------|
  |                                            |
  |---- tools/call + request metadata -------->|
  |<--- complete result + server metadata -----|
```

`server/discover` is a normal request. Clients may use it to select a supported
version or probe whether a server understands the modern era. It is not a
session-opening handshake.

**Important boundary:**

> Protocol statelessness does not forbid application state. A shopping tool can
> return a server-minted `basket_id`, and later calls can pass that handle as an
> ordinary argument. Durable state belongs in an application store, not an MCP
> connection session.

## Read one complete request

### MCP Client sends sever/discover (JSON-RPC) to MCP Server

→ CLIENT TO SERVER:

```json

```

← SERVER TO CLIENT:

```json

```

### MCP Client sends tools/call (JSON-RPC) to MCP Server

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "lookup_ticket",
    "arguments": {
      "ticket_id": "T-100"
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientInfo": {
        "name": "study-client",
        "version": "1.0.0"
      },
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

### MCP Server sends response (JSON-RPC)

← SERVER TO CLIENT:

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "resultType": "complete",
    "content": [
      {
        "type": "text",
        "text": "T-100 is open"
      }
    ],
    "isError": false,
    "_meta": {
      "io.modelcontextprotocol/serverInfo": {
        "name": "ticket-server",
        "version": "1.0.0"
      }
    }
  }
}
```

The JSON-RPC `id` correlates this response with this request.
It is not a user ID, trace ID, ticket ID, or retry key.

## Capabilities are declared per request

The client advertises optional client features in
`io.modelcontextprotocol/clientCapabilities`. The server advertises its
features through `server/discover`. A peer must not infer support merely from a
package version or client name.

The core server features are tools, resources, and prompts. Elicitation is the
main client feature in the modern core. Optional Apps, Tasks, and Skills live in
the extensions framework and require explicit support from both peers.

**Do not confuse server discovery with tool execution:**

| MCP method        | Purpose                                                  | Does it execute a tool? |
|-------------------|----------------------------------------------------------|-------------------------|
| `server/discover` | Read supported protocol versions and server capabilities | No                      |
| `tools/list`      | List individual tools                                    | No                      |
| `tools/call`      | Execute a specific tool                                  | Yes                     |

In the FastMCP example, the client automatically performs `server/discover`
when entering `async with Client(...)`. Reading
`client.session.discover_result` uses that saved response. The separate
`inspect_request_metadata` tool is **not** a discovery mechanism: it only
shows the client metadata attached to its own `tools/call` request.

## Where FastMCP fits

FastMCP is a Python framework that simplifies implementing both MCP clients and
MCP servers.

```
Host Application
      |
      | Calls FastMCP Client API
      v
FastMCP Client
      |
      | MCP 2026-07-28
      v
FastMCP Server
      |
      | Calls Python functions
      v
Business Service
```

**Key distinction:**

- **MCP** = **protocol contract** between client and server.
- **FastMCP** = **implementation framework** that hides much of the protocol
  complexity on both sides.
- **Host** = **application** that decides when and why to use an MCP client.

FastMCP handles parsing, schema generation, registration, dispatch,
serialization, and transport integration.

You still own business behavior, authorization, and state.

### MCP architecture with three connection types

This diagram includes **STDIO, Streamable HTTP, and in-memory communication**,
using MCP `2026-07-28` and FastMCP `4.2.0` context.

```
┌───────────────────────────────────────────────────────┐
│ HOST APPLICATION (Python Process A)                   │
│                                                       │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐   │
│  │ MCP Client │    │ MCP Client │    │ MCP Client │   │
│  │     A      │    │     B      │    │     C      │   │
│  └──────┬─────┘    └──────┬─────┘    └──────┬─────┘   │
│         │                 │                 │         │
│         │                 │             In-memory     │
│         │                 │             (Fast MCP)    │
│         │                 │                 │         │
│         │                 │                 ▼         │
│         │                 │          ┌────────────┐   │
│         │                 │          │ MCP Server │   │
│         │                 │          │     C      │   │
│         │                 │          └────────────┘   │
└─────────┼─────────────────┼───────────────────────────┘
          │                 │
          │ STDIO (MCP)     │ Streamable HTTP (MCP)
          │                 │
          ▼                 ▼
  ┌────────────────┐   ┌────────────────┐
  │ MCP Server A   │   │ MCP Server B   │
  │                │   │                │
  │ Local Process B│   │ Remote Process │
  └────────────────┘   └────────────────┘
```

### What changes between the three?

The key architectural difference is that
**in-memory keeps the client and server in one process**.

| Connection      | Where server runs             | Communication                        |
|-----------------|-------------------------------|--------------------------------------|
| In-memory       | Same Python process as client | In-process, no network or subprocess |
| STDIO           | Separate local process        | Standard input/output pipes          |
| Streamable HTTP | HTTP server, often remote     | HTTP requests and responses          |

**Important distinction:**
`STDIO` and `Streamable HTTP` are MCP specification transports.

`In-memory` communication is a **FastMCP implementation feature**, commonly
useful for testing and embedding servers. It is not a separately
standardized MCP transport.

FastMCP supports this pattern by allowing a `Client` to receive a `FastMCP`
server object directly, such as `Client(mcp)`.

Source: [Official FastMCP documentation](https://gofastmcp.com/?utm_source=chatgpt.com).

```python
from fastmcp import FastMCP

mcp = FastMCP("Ticket server")


@mcp.tool
def lookup_ticket(ticket_id: str) -> dict[str, str]:
    """Return the current status of one synthetic ticket."""
    return {"ticket_id": ticket_id, "status": "open"}


if __name__ == "__main__":
    mcp.run()
```

## Compatibility boundary

```
LEGACY:  initialize -> result -> notifications/initialized -> operations
MODERN:  optional server/discover -> self-contained operations
```

Do not send `initialize` while claiming protocol version `2026-07-28`.
FastMCP 4 can negotiate with both eras, but the wire flows remain distinct.

## SUMMARY

> MCP `2026-07-28` is a stateless JSON-RPC protocol. Each request carries its
> protocol version and client capabilities, so any compatible server instance
> can process it without an initialization session.


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
   
  6. A capability being advertised ≠ its list being non-empty.
  
  7. HTTP 200 ≠ tool success — check isError in the JSON-RPC result.

└─────────────────────────────────────────────────────────────────────────────┘
```

## Hands-on checkpoint

**Execution boundary:**

> A real FastMCP client and server exchange protocol messages through
> STDIO, and HTTP transports.
>
> Fast MCP's In-memory mode is also demonstrated.

The server defines one tool, resource, and prompt so `server/discover` has
features to advertise. Supplying `elicitation_handler` opts the client into the
optional elicitation capability.

The client provides **two independent demonstrations**:

- **Example A — Server discovery:** FastMCP automatically performs
  `server/discover` when connecting. The client reads `discover_result` and
  optionally uses `tools/list` to list registered tools. No `tools/call` is
  made.
- **Example B — Per-request client metadata:** The client uses `tools/call` to
  invoke the custom `inspect_request_metadata` tool. The tool reports the
  protocol version and client capabilities carried on that request. It does
  not perform server discovery.

Select the demonstration using `--example discovery`, `--example metadata`, or
`--example both` (default). FastMCP still negotiates the protocol when the
client connects, even if only the metadata example is selected.

For in-depth
details: [README](../labs/lesson_1/README.md)

### Run Commands

### In-Memory

```bash
cd ../../../reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python transport_inspection/client.py --transport in-memory --example discovery
# Run only the per-request metadata example:
uv run python transport_inspection/client.py --transport in-memory --example metadata
```

### STDIO

```bash
cd ../../../reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python transport_inspection/client.py --transport stdio --example discovery
```

### HTTP

**Server:**

```bash
cd ../../../reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python transport_inspection/server.py --transport http
```

**Client:**

```bash
cd ../../../reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python transport_inspection/client.py --transport http --example discovery
```

## Expected shape of the output

**Example A (`--example discovery`):**

```text
Transport: in-memory

EXAMPLE A: Server discovery (no tools/call)
server/discover response (already obtained during connection)
  supported versions: ['2026-07-28']
  server capabilities: ['extensions', 'logging', 'prompts', 'resources', 'tools']

tools/list response
  Name: inspect_request_metadata
  Description: Return protocol metadata that the server received on this request.
  Input schema: ...
```

**Example B (`--example metadata`):**

```text
Transport: in-memory

EXAMPLE B: Client metadata on an ordinary tools/call request
tools/call -> inspect_request_metadata
  io.modelcontextprotocol/protocolVersion: 2026-07-28
  io.modelcontextprotocol/clientCapabilities:
{
    "elicitation": {
        "form": {},
        "url": {}
    }
}

Verified: the client advertised optional elicitation support.
```

The capability list and schemas can vary by server configuration and FastMCP
version. The key difference is that Example A never calls a tool.

The same commands work on Intel and Apple Silicon Macs.

# Troubleshooting

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

1. Port/address already in use
    ```
   ERROR:    
   [Errno 48] error while attempting to bind on address ('127.0.0.1', 8000): 
   [errno 48] address already in use
   ```

    ```shell
      lsof -tiTCP:8000 -sTCP:LISTEN | xargs -r kill
    ```

   On macOS, where xargs -r may not be supported, use:

    ```shell
      pids=$(lsof -tiTCP:8000 -sTCP:LISTEN); [ -z "$pids" ] || kill $pids
    ```

## Official references

- [MCP 2026-07-28 overview](https://modelcontextprotocol.io/specification/2026-07-28)
- [Architecture](https://modelcontextprotocol.io/specification/2026-07-28/architecture)
- [Key changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [FastMCP documentation](https://gofastmcp.com/)

