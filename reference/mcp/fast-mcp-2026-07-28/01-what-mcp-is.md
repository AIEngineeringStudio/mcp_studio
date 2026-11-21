# Lesson 1 — MCP and the modern request model

## Baseline and Outcome

This lesson targets MCP `2026-07-28`, standalone FastMCP `4.2.0`, and Python
examples managed with `uv`.

After this lesson, you can identify the host, client, and server; read one MCP
request; and explain why MCP `2026-07-28` does not use an initialization
handshake or a protocol session.

## The problem MCP solves

Without a shared protocol,
every AI application needs a custom integration for every external system.

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

### **MCP architecture with two connection types**

**STDIO, Streamable HTTP transports**, using MCP `2026-07-28`.

```
┌──────────────────────────────────────┐
│ HOST APPLICATION (Python Process A)  │
│                                      │
│  ┌────────────┐    ┌────────────┐    │
│  │ MCP Client │    │ MCP Client │    │
│  │     A      │    │     B      │    │
│  └──────┬─────┘    └──────┬─────┘    │
│         │                 │          │
└─────────┼─────────────────┼──────────┘
          │                 │
          │ STDIO           │ Streamable HTTP
          │                 │
          ▼                 ▼
  ┌────────────────┐   ┌────────────────┐
  │ MCP Server A   │   │ MCP Server B   │
  │                │   │                │
  │ Local Process B│   │ Remote Process │
  └────────────────┘   └────────────────┘
```

### **What changes between the two?**

The key architectural difference is that while STDIO crosses a process boundary,
HTTP crosses an HTTP service boundary.

| Connection      | Where server runs         | Communication               |
|-----------------|---------------------------|-----------------------------|
| STDIO           | Separate local process    | Standard input/output pipes |
| Streamable HTTP | HTTP server, often remote | HTTP requests and responses |

**Host:**

> The application that coordinates the model, user experience, permissions,
> and one or more MCP clients.

**Client:**

> The protocol participant inside the host. One client communicates with one
> server and attaches protocol metadata to every request.

**Server:**

> A focused service that exposes tools, resources, and prompts. It receives
> only the context sent through its MCP client; it does not automatically see
> the host's whole conversation or other servers.

MCP standardizes communication. It does not define how an agent reasons, how a
database is organized, or how business authorization is decided.

## Data layer and transport layer

```
MCP data layer
  JSON-RPC methods, schemas, results, errors, capabilities

MCP transport layer
  stdio or Streamable HTTP carrying those messages
```

Changing from stdio to HTTP should not change the meaning of `tools/call`.
It changes process and network behavior, not the tool contract.

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

### **MCP architecture with three connection types**

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

### **What changes between the three?**

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

## Hands-on checkpoint

**Execution boundary:**

> A real FastMCP client and server exchange protocol messages through
> STDIO, and HTTP transports.
>
> Fast MCP's In-memory mode is also demonstrated.

The server defines one tool, resource, and prompt so `server/discover` has
features to advertise. Supplying `elicitation_handler` opts the client into the
optional elicitation capability.

The inspection tool then reports the protocol version and client capabilities
that arrived with its own `tools/call` request.

For in-depth
details: [README](../../../reference/mcp/labs/transport_inspection/README.md)

### Run Commands

### In-Memory

```bash
cd ../../../reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python transport_inspection/client.py --transport in-memory
```

### STDIO

```bash
cd ../../../reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python transport_inspection/client.py --transport stdio
```

### HTTP

**Server: **

```bash
cd ../../../reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python transport_inspection/server.py --transport http
```

**Client:**

```bash
cd ../../../reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python transport_inspection/client.py --transport http
```

### Troubleshooting

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

## Expected shape of the output:

```
server/discover response
  supported versions: ['2026-07-28']
  server capabilities: ['extensions', 'logging', 'prompts', 'resources', 'tools']

tools/call metadata observed by the server
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

The same commands work on Intel and Apple Silicon Macs.

**Say it professionally:**

> MCP `2026-07-28` is a stateless JSON-RPC protocol. Each request carries its
> protocol version and client capabilities, so any compatible server instance
> can process it without an initialization session.

## Official references

- [MCP 2026-07-28 overview](https://modelcontextprotocol.io/specification/2026-07-28)
- [Architecture](https://modelcontextprotocol.io/specification/2026-07-28/architecture)
- [Key changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [FastMCP documentation](https://gofastmcp.com/)

