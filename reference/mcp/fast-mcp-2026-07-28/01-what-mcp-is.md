# Lesson 1 — MCP and the modern request model

## Outcome and baseline

After this lesson, you can identify the host, client, and server; read one MCP
request; and explain why MCP `2026-07-28` does not use an initialization
handshake or a protocol session.

This lesson targets MCP `2026-07-28`, standalone FastMCP `4.2.0`, and Python
examples managed with `uv`.

## The problem MCP solves

Without a shared protocol, every AI application needs a custom integration for
every external system. MCP standardizes the boundary:

```
User
  |
Host application
  |
MCP client  <---- JSON-RPC over a transport ---->  MCP server
                                                       |
                                                business service
```

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
CLIENT                                      SERVER
  |                                           |
  |---- server/discover (optional) ---------->|
  |<--- versions + server capabilities -------|
  |                                           |
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
    "arguments": {"ticket_id": "T-100"},
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
    "content": [{"type": "text", "text": "T-100 is open"}],
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

The JSON-RPC `id` correlates this response with this request. It is not a user
ID, trace ID, ticket ID, or retry key.

## Capabilities are declared per request

The client advertises optional client features in
`io.modelcontextprotocol/clientCapabilities`. The server advertises its
features through `server/discover`. A peer must not infer support merely from a
package version or client name.

The core server features are tools, resources, and prompts. Elicitation is the
main client feature in the modern core. Optional Apps, Tasks, and Skills live in
the extensions framework and require explicit support from both peers.

## Where FastMCP fits

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

FastMCP handles parsing, schema generation, registration, dispatch,
serialization, and transport integration. You still own business behavior,
authorization, and state.

## Compatibility boundary

```
LEGACY:  initialize -> result -> notifications/initialized -> operations
MODERN:  optional server/discover -> self-contained operations
```

Do not send `initialize` while claiming protocol version `2026-07-28`.
FastMCP 4 can negotiate with both eras, but the wire flows remain distinct.

## Hands-on checkpoint

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python -m unittest -q test_protocol
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

