# Lesson 11 — MCP Transports: stdio vs Streamable HTTP

A **transport** answers one question:

> **How do MCP JSON-RPC messages physically move between client and server?**

It does **not** redefine Tools, Resources, Prompts, schemas, or JSON-RPC semantics.

```
                 MCP data/protocol layer

 tools/list
 tools/call
 resources/read
 prompts/get
 JSON-RPC
 _meta
 progress
 cancellation

                    │
                    ▼

               TRANSPORT BINDING

          ┌─────────┴──────────┐
          │                    │
        stdio           Streamable HTTP
          │                    │
    stdin/stdout          HTTP POST/SSE
```

MCP `2026-07-28` defines two standard bindings: **stdio**, using newline-delimited JSON-RPC over a client-launched subprocess's streams, and **Streamable HTTP**, where each message is a POST to one MCP endpoint and responses are either JSON or a request-scoped SSE stream. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)

---

# 1. First principle: protocol ≠ transport

Suppose the client wants:

```
tools/call
```

The logical MCP request is approximately:

```json
{
  "jsonrpc": "2.0",
  "id": 17,
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": {
      "a": 10,
      "b": 20
    }
  }
}
```

That logical operation can travel through:

```
stdin/stdout
```

or:

```
HTTP
```

The Tool contract does not become an HTTP API merely because HTTP carries it.

Professional phrasing:

> **“MCP is transport-agnostic; the transport binding defines framing, connection lifecycle, metadata mapping, and cancellation.”** [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)

---

# Part A — stdio

## 2. stdio architecture

With stdio:

```
MCP HOST / CLIENT
      │
      │ launches subprocess
      ▼
┌───────────────────────┐
│      MCP SERVER       │
│                       │
│ stdin   ◄── client    │
│ stdout  ──► client    │
│ stderr  ──► logs      │
└───────────────────────┘
```

The client owns the subprocess lifecycle. The server reads MCP messages from `stdin`, writes MCP messages to `stdout`, and may use `stderr` for diagnostics. Messages are UTF-8 JSON-RPC, one message per line. `stdout` must contain nothing except valid MCP traffic. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)

This is why:

```python
print("server started")
```

can break a stdio MCP server.

`print()` normally writes:

```
stdout
```

which is the protocol channel.

Instead, diagnostic output belongs on:

```python
print(
    "server started",
    file=sys.stderr,
)
```

---

# 3. stdio framing

**Framing** means:

> How does the receiver know where one message ends and the next begins?

stdio MCP uses:

```
one JSON-RPC object
newline
one JSON-RPC object
newline
...
```

Example conceptual byte stream:

```
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n
{"jsonrpc":"2.0","id":2,"method":"tools/call",...}\n
```

The newline is the **message delimiter**. The current binding requires messages themselves not to contain literal embedded newline delimiters. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)

Professional terminology:

- **message framing**
- **delimiter**
- **byte stream**
- **serialization**
- **wire format**

---

# 4. All stdio traffic shares one channel

Suppose two requests are running:

```
request #10
request #11
```

stdout could conceptually carry:

```
progress for #10
response for #11
progress for #10
response for #10
```

There are no separate streams per request.

The client correlates normal responses using:

```
JSON-RPC id
```

and correlates request-scoped notifications using their protocol metadata. Modern stdio servers must not initiate JSON-RPC requests; client-required interactions are represented through `InputRequiredResult`/MRTR instead. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)

So stdio is:

```
one physical stream
       │
       ├── many logical requests
       ├── many responses
       └── notifications
```

That's **multiplexing** again.

---

# 5. Modern stdio metadata stays inside JSON

Remember modern MCP:

```
protocol version
client capabilities
client identity
```

With stdio there is no HTTP header layer.

Everything lives inside:

```
params._meta
```

The current stdio specification explicitly says request metadata remains inline in the JSON-RPC message body. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)

Conceptually:

```json
{
  "method": "tools/call",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion":
        "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities":
        {}
    }
  }
}
```

---

# 6. stdio cancellation

Because every request shares the same stdout stream, you cannot cancel request 17 by:

```
closing "request 17's stream"
```

There isn't one.

So modern stdio uses:

```
notifications/cancelled
```

with the JSON-RPC request ID. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)

```
single connection
├── #16
├── #17 ← cancel specifically
└── #18
```

This is exactly the design we learned in the previous lesson.

---

# 7. stdio shutdown

A stdio server generally exists because the client started it.

The graceful lifecycle is:

```
CLIENT
  │
  ├── starts server subprocess
  │
  ├── communicates
  │
  ├── closes server stdin
  │
  ▼
SERVER sees EOF
  │
  ▼
server exits
```

If it fails to exit, the client can escalate to process termination. The current spec treats closing stdin/EOF as the primary portable graceful-shutdown mechanism. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)

Professional term:

> **Process lifecycle ownership**

The client owns it.

---

# 8. FastMCP stdio server

Create:

```python
# server.py

from fastmcp import FastMCP


mcp = FastMCP("TransportDemo")


@mcp.tool
def add(
    a: int,
    b: int,
) -> int:
    """Add two integers."""
    return a + b


if __name__ == "__main__":
    mcp.run()
```

FastMCP uses stdio by default when `mcp.run()` receives no transport argument. [FastMCP](https://gofastmcp.com/deployment/running-server)

Conceptually FastMCP handles:

```
stdin
 │
 ▼
message framing
 │
 ▼
JSON-RPC parsing
 │
 ▼
MCP dispatch
 │
 ▼
your add()
 │
 ▼
serialization
 │
 ▼
stdout
```

---

# 9. Working FastMCP stdio client

Create:

```python
# client_stdio.py

import asyncio

from fastmcp import Client


async def main():
    client = Client("server.py")

    async with client:
        result = await client.call_tool(
            "add",
            {
                "a": 10,
                "b": 32,
            },
        )

        print(result.data)


asyncio.run(main())
```

FastMCP infers that a local Python script should be run through a stdio transport and manages the subprocess connection. Its explicit `StdioTransport` API also lets you configure the command, arguments, environment, and subprocess reuse behavior. [FastMCP](https://gofastmcp.com/clients/transports)

Expected:

```
42
```

---

# 10. Peel the FastMCP client abstraction

This:

```python
Client("server.py")
```

looks tiny.

Conceptually it does:

```
Client("server.py")
       │
       ▼
choose StdioTransport
       │
       ▼
spawn Python process
       │
       ├── open stdin
       ├── open stdout
       └── capture stderr
       │
       ▼
send MCP messages
       │
       ▼
parse responses
       │
       ▼
terminate/reuse process
```

Again, a Python constructor hides a lot of distributed/process infrastructure.

---

# Part B — Streamable HTTP

## 11. Why HTTP exists

stdio has a key topology assumption:

```
client and server
can share a machine/process environment
```

For a centralized server:

```
Laptop A ──┐
Laptop B ──┼────► MCP service
Agent C  ──┘
```

we need a network transport.

Streamable HTTP makes the MCP server an independently running web service capable of serving multiple clients. FastMCP recommends HTTP for network/production deployments. [FastMCP](https://gofastmcp.com/deployment/running-server)

---

# 12. Modern Streamable HTTP is simpler than older MCP HTTP

MCP `2026-07-28` significantly simplified Streamable HTTP:

```
ONE MCP endpoint

https://example.com/mcp
```

Every client JSON-RPC message is:

```
HTTP POST /mcp
```

For requests, the server responds with either:

```
application/json
```

or:

```
text/event-stream
```

The old standalone GET SSE stream and protocol-level sessions were removed in `2026-07-28`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

---

# 13. Modern HTTP request flow

Simple request:

```
CLIENT

POST /mcp
Content-Type: application/json
Accept: application/json, text/event-stream

JSON-RPC request
       │
       ▼
SERVER
       │
       ▼
application/json

JSON-RPC response
```

For an operation that emits progress:

```
CLIENT
   │
   │ POST /mcp
   ▼
SERVER
   │
   ├── opens SSE response
   │
   ├── progress notification
   │
   ├── progress notification
   │
   └── final JSON-RPC response
          │
          ▼
       stream ends
```

Modern Streamable HTTP permits either a single JSON response or a request-scoped SSE stream; clients must support both. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

---

# 14. Important: Streamable HTTP uses SSE, but is not the old SSE transport

This terminology causes confusion.

### Deprecated old transport

```
HTTP+SSE transport

GET /sse
persistent server stream

POST /message
client messages
```

### Modern Streamable HTTP

```
POST /mcp

response can be:
application/json
or
text/event-stream
```

So:

> **SSE is a response-streaming format used by Streamable HTTP; it is not synonymous with the deprecated HTTP+SSE transport.**

The old HTTP+SSE transport has been deprecated since the Streamable HTTP replacement was introduced. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

---

# 15. Why SSE?

Suppose a Tool takes 20 seconds and generates:

```
progress 10%
progress 50%
progress 90%
final result
```

A single JSON HTTP response cannot emit those intermediate notifications before completion.

An SSE response can:

```
HTTP response starts
   │
   ├── event: progress
   ├── event: progress
   ├── event: progress
   └── final JSON-RPC response
```

SSE provides **server-to-client streaming over one HTTP response**.

---

# 16. Every modern HTTP request is independent

This is central to MCP `2026-07-28`.

Think:

```
POST #1
complete request/response

POST #2
complete request/response

POST #3
complete request/response
```

not:

```
establish MCP session
keep server-side connection state forever
```

The modern transport removed protocol-level HTTP sessions and standalone GET streams. Client interactions such as sampling and elicitation now use MRTR rather than server-initiated requests. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

This is why horizontal scaling becomes easier:

```
                 load balancer
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
      worker A     worker B     worker C

round 1             ✓
round 2                          ✓
round 3          ✓
```

FastMCP 4 is specifically designed to support both modern sessionless MCP and older handshake-era clients from one deployment. [FastMCP](https://gofastmcp.com/getting-started/whats-new?utm_source=chatgpt.com)

---

# 17. Modern HTTP mirrors protocol metadata into headers

With stdio:

```
metadata only in JSON body
```

With HTTP:

```
metadata in JSON body
+
selected values mirrored as HTTP headers
```

For example a modern Tool call requires headers including:

```
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: add
```

The body remains the source of truth, and servers must reject mismatches between required mirrored headers and body values. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

Why mirror them?

Because infrastructure can route based on:

```
HTTP headers
```

without parsing JSON.

Example:

```
load balancer

Mcp-Method=tools/call
Mcp-Name=search_orders
          │
          ▼
orders backend
```

Professional phrase:

> **“Modern Streamable HTTP exposes routing metadata at the transport envelope while retaining the JSON body as the protocol source of truth.”**

---

# 18. Raw HTTP Tool call

Conceptually, modern HTTP looks like:

```http
POST /mcp HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: add
```

Body:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": {
      "a": 10,
      "b": 32
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion":
        "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities":
        {}
    }
  }
}
```

The official transport requires `MCP-Protocol-Version` on modern POSTs, `Mcp-Method` on all requests, and `Mcp-Name` for named operations such as `tools/call`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

Normally you should **not hand-build these headers**; your MCP client library should.

---

# 19. HTTP cancellation is elegant

Recall stdio:

```
one shared stream
→ notifications/cancelled(requestId)
```

HTTP has:

```
one response stream
per request
```

So:

```
close request's SSE response
```

means:

```
cancel exactly that request
```

Modern MCP requires the server to treat that stream closure as cancellation. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

This is a transport-level cancellation signal:

```
STDIO
protocol notification

HTTP
transport disconnect
```

Same semantics, different mechanism.

---

# 20. Long-lived notifications in modern HTTP

What about events such as:

```
tools/list_changed
resources/updated
```

Those aren't tied to one ordinary Tool call.

Modern MCP uses:

```
subscriptions/listen
```

The client opens that request and its HTTP response remains an SSE stream carrying the subscribed change notifications. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

So modern HTTP has two SSE patterns:

```
REQUEST-SCOPED

tools/call
   │
   ├── progress
   └── final response
        → close


SUBSCRIPTION

subscriptions/listen
   │
   ├── update
   ├── update
   ├── update
   └── stays open
```

---

# 21. FastMCP HTTP server

The same Tool code:

```python
from fastmcp import FastMCP


mcp = FastMCP("TransportDemo")


@mcp.tool
def add(
    a: int,
    b: int,
) -> int:
    return a + b


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8000,
    )
```

FastMCP exposes the MCP endpoint at:

```
http://127.0.0.1:8000/mcp
```

with that direct HTTP configuration. [FastMCP](https://gofastmcp.com/deployment/running-server)

Run it:

```bash
python server.py
```

or independently of the `__main__` configuration:

```bash
fastmcp run server.py:mcp \
  --transport http \
  --host 127.0.0.1 \
  --port 8000
```

The FastMCP CLI supports selecting HTTP directly. [FastMCP](https://gofastmcp.com/cli/running?utm_source=chatgpt.com)

---

# 22. Working FastMCP HTTP client

```python
# client_http.py

import asyncio

from fastmcp import Client


async def main():
    client = Client(
        "http://127.0.0.1:8000/mcp"
    )

    async with client:
        result = await client.call_tool(
            "add",
            {
                "a": 10,
                "b": 32,
            },
        )

        print(result.data)


asyncio.run(main())
```

FastMCP recognizes an HTTP URL and uses its Streamable HTTP client transport; explicit `StreamableHttpTransport` configuration is available when you need custom headers, authentication, TLS settings, and similar transport controls. [FastMCP](https://gofastmcp.com/clients/transports)

Expected:

```
42
```

---

# 23. Notice what did not change

stdio:

```python
await client.call_tool(
    "add",
    {"a": 10, "b": 32},
)
```

HTTP:

```python
await client.call_tool(
    "add",
    {"a": 10, "b": 32},
)
```

Exactly the same application-level call.

Only:

```
transport
```

changed.

That is successful abstraction:

```
APPLICATION
    │
    ▼
FastMCP Client
    │
    ▼
Transport
 ┌──┴──────────┐
stdio          HTTP
```

---

# 24. HTTP has a much larger security surface

stdio:

```
local subprocess
```

HTTP:

```
network-facing service
```

Now you must think about:

```
authentication
TLS
Origin validation
reverse proxies
rate limits
network exposure
authorization
load balancers
timeouts
CORS/Host policy
```

The modern MCP spec requires Streamable HTTP servers to validate `Origin` when present to mitigate DNS rebinding, recommends binding local services to `127.0.0.1` rather than `0.0.0.0`, and recommends proper authentication. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

This is why casually changing:

```python
host="127.0.0.1"
```

to:

```python
host="0.0.0.0"
```

is not merely a convenience change.

It alters the network exposure boundary.

---

# 25. Reverse proxies can break streaming

Imagine:

```
MCP server
    │
    ▼
nginx
    │
    ▼
client
```

Server sends:

```
20%
40%
60%
```

But the proxy buffers data until it has enough bytes.

Client sees:

```
20%, 40%, 60%, 100%
```

all at once.

That defeats streaming.

The modern specification recommends servers set:

```
X-Accel-Buffering: no
```

when opening SSE streams to discourage proxy buffering. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

Professional phrase:

> **“SSE requires end-to-end streaming semantics; intermediary buffering can destroy latency characteristics without breaking HTTP correctness.”**

---

# 26. Local vs remote is mostly a topology distinction

Typical:

```
STDIO

desktop app
    │
    └── local MCP process
```

versus:

```
HTTP

desktop/web/cloud client
          │
          ▼
      internet/VPC
          │
          ▼
     MCP service
```

The MCP architecture documentation describes stdio servers as commonly local and Streamable HTTP servers as commonly remote. [Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture?utm_source=chatgpt.com)

But remember:

> stdio ≠ inherently trusted  
> HTTP ≠ inherently public

Those are deployment choices.

---

# 27. Choose the transport deliberately

| Requirement | Prefer |
|---|---|
| Local desktop integration | stdio |
| CLI/local developer tool | stdio |
| Easy subprocess isolation | stdio |
| Centralized shared service | HTTP |
| Multiple remote clients | HTTP |
| Authentication through web infrastructure | HTTP |
| Load balancing | HTTP |
| Cloud deployment | HTTP |
| Simple testing in one Python process | FastMCP in-memory transport |

FastMCP documents HTTP as the recommended network/production transport and provides an in-memory transport for tests where neither subprocess nor network behavior is relevant. [FastMCP](https://gofastmcp.com/clients/transports)

---

# 28. A useful three-level test strategy

Do not test everything over HTTP.

Use:

```
LEVEL 1
in-memory
     │
     └── business + MCP behavior


LEVEL 2
stdio
     │
     └── subprocess/framing behavior


LEVEL 3
HTTP
     │
     └── network/deployment behavior
```

FastMCP supports an in-process transport by passing the server object directly to `Client`, specifically avoiding subprocess and network overhead for testing. [FastMCP](https://gofastmcp.com/clients/transports)

Example:

```python
client = Client(mcp)

async with client:
    result = await client.call_tool(
        "add",
        {"a": 1, "b": 2},
    )
```

This is usually your fastest integration test.

---

# 29. Modern vs legacy HTTP — memorize this

The transport evolved significantly.

### `2024-11-05`

```
HTTP + SSE transport

GET SSE endpoint
+
POST message endpoint
```

Deprecated.

### `2025-03-26` through `2025-11-25`

```
Streamable HTTP

single MCP endpoint
POST
optional GET SSE
sessions
server-initiated requests
Last-Event-ID resumability
```

### `2026-07-28`

```
Streamable HTTP

single MCP endpoint
POST only
no MCP protocol sessions
no standalone GET stream
no server-initiated requests
no Last-Event-ID resumability
MRTR
subscriptions/listen
```

Those older mechanisms were explicitly removed from the current Streamable HTTP revision. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)

This version history explains a lot of seemingly contradictory MCP documentation you may encounter.

---

# 30. FastMCP version implication

FastMCP 4 beta is the branch designed around MCP's modern sessionless `2026-07-28` protocol while still negotiating older handshake-era clients from the same server. Its client defaults to automatic protocol-era negotiation. [FastMCP](https://gofastmcp.com/getting-started/whats-new?utm_source=chatgpt.com)

Therefore, for current protocol experiments:

```
FastMCP 4 beta
+
mode="auto"
```

is the appropriate path.

For historical `ctx.sample()`, `ctx.list_roots()`, or live back-channel behavior:

```
FastMCP 3.x
+
legacy MCP era
```

is the model we studied earlier. [FastMCP](https://gofastmcp.com/getting-started/whats-new?utm_source=chatgpt.com)

---

# 31. Complete abstraction map

| Protocol/transport concern | FastMCP abstraction |
|---|---|
| stdio framing | `mcp.run()` |
| subprocess creation | `Client("server.py")` |
| explicit stdio | `StdioTransport(...)` |
| HTTP endpoint | `mcp.run(transport="http")` |
| HTTP client | `Client("https://.../mcp")` |
| explicit HTTP | `StreamableHttpTransport(...)` |
| protocol negotiation | FastMCP client/server |
| HTTP metadata headers | transport |
| SSE parsing | transport |
| cancellation | transport/framework |
| subprocess lifecycle | stdio transport |
| HTTP TLS/auth headers | HTTP transport config |

FastMCP's design deliberately separates `Client`, which handles MCP operations, from the transport responsible for connection mechanics. [FastMCP](https://gofastmcp.com/clients/transports)

---

# 32. Professional vocabulary

| Term | Meaning |
|---|---|
| **Transport** | Mechanism carrying MCP messages |
| **Transport binding** | MCP rules for one communication mechanism |
| **Framing** | Determining message boundaries |
| **Wire format** | Actual representation transmitted |
| **Subprocess transport** | Client-launched process communication |
| **Endpoint** | Network URL receiving protocol traffic |
| **SSE** | Server-Sent Events response stream |
| **Request-scoped stream** | Stream belonging to one request |
| **Envelope metadata** | Transport-level metadata surrounding protocol body |
| **Reverse proxy** | HTTP intermediary in front of server |
| **Origin validation** | Checking web request origin |
| **DNS rebinding** | Attack that abuses browser DNS behavior to reach local services |
| **Horizontal scaling** | Serving requests across multiple replicas |
| **Sticky session** | Routing one session repeatedly to the same worker |
| **Protocol negotiation** | Selecting compatible MCP version/era |
| **Transport cancellation** | Cancelling through transport behavior, such as closing an SSE stream |

A strong explanation:

> **“MCP separates protocol semantics from transport bindings. stdio carries newline-delimited JSON-RPC over a client-managed subprocess, with all requests multiplexed on one stream. Modern Streamable HTTP sends each JSON-RPC message as an independent POST to one MCP endpoint and returns either JSON or a request-scoped SSE stream. In `2026-07-28`, HTTP sessions and standalone GET streams are gone; metadata is per-request, server-to-client interactions use MRTR, and HTTP cancellation is represented by closing the request's response stream.”** [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)

---

# Hands-on assignment

Use exactly the same `add` server and test it three ways:

```
1. In-memory
   Client(mcp)

2. stdio
   Client("server.py")

3. Streamable HTTP
   Client("http://127.0.0.1:8000/mcp")
```

Then:

1. Add `ctx.report_progress()` and observe stdio vs HTTP delivery.
2. Print to `stdout` in stdio and observe why it breaks framing.
3. Move that diagnostic to `stderr`.
4. Add a client timeout and compare cancellation semantics.
5. Inspect one HTTP request and locate `MCP-Protocol-Version`, `Mcp-Method`, and `Mcp-Name`.
6. Run two HTTP clients concurrently.
7. Restart the HTTP server and reason about why modern protocol state cannot depend on a sticky MCP session.
8. Put a buffering reverse proxy in front of the HTTP server and observe how it can affect SSE progress delivery.

The conceptual test is being able to explain:

```
MCP protocol
      ≠
JSON-RPC
      ≠
transport
      ≠
stdio
      ≠
HTTP
      ≠
SSE
```

They are related layers, not interchangeable terms.

## Next lesson — Authentication + Authorization

The next major topic should be **security**, specifically:

```
Authentication
    → Who is calling?

Authorization
    → What may they do?

OAuth / bearer tokens
protected-resource metadata
scopes
401 vs 403
token audience
confused-deputy risks
per-tool authorization
FastMCP auth providers
HTTP request identity
```

That lesson matters especially now because moving from stdio to HTTP turns your MCP server from a local process into a network security boundary.