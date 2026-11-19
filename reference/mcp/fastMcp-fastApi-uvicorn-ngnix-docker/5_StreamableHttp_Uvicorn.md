# Increment 5 — Streamable HTTP and Uvicorn

## Goal

Keep the MCP components and service layer unchanged, but replace stdio with a
network boundary:

```
┌──────────────────────────────┐
│ MCP client process           │
└──────────────┬───────────────┘
               │ HTTP
               ▼
┌──────────────────────────────┐
│ Uvicorn                      │
│ Socket and HTTP handling     │
└──────────────┬───────────────┘
               │ ASGI
               ▼
┌──────────────────────────────┐
│ FastMCP ASGI application     │
│ /mcp                         │
└──────────────┬───────────────┘
               │ Python calls
               ▼
┌──────────────────────────────┐
│ ArithmeticService            │
│ Repository → SQLite          │
└──────────────────────────────┘
```

Unlike stdio, the HTTP server runs independently and can accept connections from
multiple clients. Streamable HTTP uses HTTP POST for client messages and may use
HTTP GET with Server-Sent Events for streaming and server-to-client
communication. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports?utm_source=chatgpt.com)

FastAPI is still intentionally absent. Uvicorn can serve FastMCP’s ASGI
application directly. FastMCP officially supports creating an ASGI app using
`mcp.http_app()` and serving it with
Uvicorn. [FastMCP](https://gofastmcp.com/deployment/http)

---

## 1. Add Uvicorn

```bash
uv add uvicorn
```

Your dependency boundary is now:

```
FastMCP     MCP implementation
Uvicorn     ASGI application server
aiosqlite   Async database adapter
Pydantic    Models and validation
```

Do not describe Uvicorn as a framework.

Professional wording:

> “Uvicorn is the ASGI application server responsible for accepting network
> connections and driving the ASGI application.”

---

# 2. Keep `server.py`

Your existing `server.py` contains:

- The FastMCP instance
- Tool registration
- Resource registration
- Prompt registration
- Service construction
- The optional stdio entry point

Keep this block:

```python
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

Because importing `server.py` does not execute that block, the same MCP server
can support two deployment adapters:

```
server.py
├── executed directly → stdio
└── imported by app.py → HTTP
```

This is useful architectural reuse:

> “The MCP component registry is transport-agnostic; deployment adapters
> determine how it is exposed.”

---

# 3. Create `app.py`

```python
from __future__ import annotations

from server import mcp

app = mcp.http_app(
    path="/mcp",

    # Each HTTP request can be handled independently.
    # This avoids in-memory session affinity when workers are added later.
    stateless_http=True,

    # Validate Host and Origin before MCP request handling.
    host_origin_protection=True,
    allowed_hosts=[
        "127.0.0.1",
        "localhost",
    ],
    allowed_origins=[],
)
```

FastMCP’s `http_app()` creates a standard ASGI application. Its default MCP
route is `/mcp`, although the path can be configured explicitly as
above. [FastMCP](https://gofastmcp.com/deployment/http)

## Why use a separate `app.py`?

It establishes a clean distinction:

```
server.py
└── Defines MCP capabilities

app.py
└── Defines HTTP deployment composition
```

Avoid putting Uvicorn startup logic inside your business or protocol modules.

---

# 4. Stateful vs Stateless HTTP

FastMCP can maintain server-side HTTP sessions by default. That creates a
scaling problem because requests belonging to one client may reach different
worker processes, while the session exists only in one worker’s memory. FastMCP
recommends stateless mode when using multiple workers or horizontal
scaling. [FastMCP](https://gofastmcp.com/deployment/http)

We selected:

```python
stateless_http = True
```

The conceptual difference is:

```
Stateful

Request 1 → Worker A → create session in Worker A memory
Request 2 → Worker B → session unavailable


Stateless

Request 1 → any worker
Request 2 → any worker
```

For our arithmetic service, no protocol-level session state is required.
Calculation history lives in SQLite rather than in the transport session.

Professional wording:

> “The HTTP transport is configured statelessly so requests are not coupled to a
> particular worker process.”

### Important limitation

Stateless HTTP is not a universal choice. Server features that depend on
persistent connection-specific state may require a different design.

Do not set a flag merely because it sounds scalable. First identify where state
lives.

---

# 5. Host and Origin Protection

Streamable HTTP servers must treat browser `Origin` headers carefully because an
unprotected local server can be vulnerable to DNS rebinding. The MCP transport
specification requires invalid origins to be rejected, and recommends binding
local development servers only to
loopback. [Model Context Protocol](https://modelcontextprotocol.io/specification/draft/basic/transports?utm_source=chatgpt.com)

We therefore use:

```python
host_origin_protection = True
```

and permit only:

```python
allowed_hosts = [
    "127.0.0.1",
    "localhost",
]
```

FastMCP describes this as a request guard rather than CORS middleware. It
controls whether the request reaches MCP handling; CORS separately controls what
browser JavaScript may read from a
response. [FastMCP](https://gofastmcp.com/deployment/http)

Do not enable permissive CORS. We do not have a browser client.

---

# 6. Start Uvicorn

From the project root:

```bash
uv run uvicorn app:app \
  --host 127.0.0.1 \
  --port 8000
```

The application is now available at:

```
http://127.0.0.1:8000/mcp
```

FastMCP documents the `module:attribute` Uvicorn pattern and exposes the MCP
endpoint at `/mcp`. [FastMCP](https://gofastmcp.com/deployment/http)

## Meaning of `app:app`

```
app:app
│   │
│   └── Python attribute named app
│
└────── Python module app.py
```

Uvicorn effectively performs:

```python
from app import app
```

and then runs that ASGI application.

---

## Development reload

During active development, you may run:

```bash
uv run uvicorn app:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

`--reload` is a development feature. Do not use it as your production process
strategy.

Reloading also means imports may occur repeatedly, which is one reason
import-time side effects are dangerous.

---

# 7. ASGI From First Principles

ASGI means **Asynchronous Server Gateway Interface**.

It is a Python interface between an application server and an asynchronous
Python application.

```
Network client
    │
    │ TCP + HTTP
    ▼
Uvicorn
    │
    │ ASGI events
    ▼
FastMCP application
```

Uvicorn owns:

- Listening sockets
- HTTP parsing
- Connection management
- Request timeouts
- Starting and stopping the ASGI application
- Passing requests to Python

FastMCP owns:

- The `/mcp` endpoint
- MCP protocol negotiation
- JSON-RPC decoding
- Tool, resource, and prompt dispatch
- MCP response encoding

Your application service owns:

- Business rules
- Arithmetic
- Persistence orchestration

This responsibility split is important:

```
Uvicorn does not understand MCP tools.
FastMCP does not implement arithmetic rules.
ArithmeticService does not understand HTTP.
```

---

# 8. What an ASGI Interaction Looks Like

Conceptually, Uvicorn invokes the application like this:

```python
await app(scope, receive, send)
```

The three parameters mean:

| Parameter | Purpose                                              |
|-----------|------------------------------------------------------|
| `scope`   | Connection metadata such as method, path and headers |
| `receive` | Async function for receiving request events          |
| `send`    | Async function for sending response events           |

A simplified request flow:

```
1. Uvicorn accepts TCP connection
2. Uvicorn parses HTTP request
3. Uvicorn creates ASGI scope
4. FastMCP reads request body through receive()
5. FastMCP processes the MCP message
6. FastMCP sends response events through send()
7. Uvicorn writes the HTTP response
```

Professional wording:

> “Uvicorn translates network-level HTTP traffic into ASGI events consumed by
> the FastMCP application.”

---

# 9. Create `test_http_client.py`

```python
from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError

MCP_URL = "http://127.0.0.1:8000/mcp"


def text_content(item: Any) -> str:
    text = getattr(item, "text", None)
    return text if text is not None else str(item)


async def main() -> None:
    transport = StreamableHttpTransport(
        url=MCP_URL,
    )

    async with Client(transport) as client:
        tools = await client.list_tools()

        print("Tools:")
        for tool in tools:
            print(f"- {tool.name}")

        add_result = await client.call_tool(
            "add",
            {
                "a": 20,
                "b": 22,
            },
        )

        print("\nAdd result:")
        print(add_result.data)

        multiply_result = await client.call_tool(
            "multiply",
            {
                "a": 6,
                "b": 7,
            },
        )

        print("\nMultiply result:")
        print(multiply_result.data)

        history = await client.read_resource(
            "history://calculations/recent/10"
        )

        print("\nCalculation history:")
        for item in history:
            print(text_content(item))

        prompt = await client.get_prompt(
            "explain_arithmetic",
            {
                "operation": "multiply",
                "a": 6,
                "b": 7,
                "audience": "beginner",
            },
        )

        print("\nRendered prompt:")
        for message in prompt.messages:
            print(f"Role: {message.role}")
            print(text_content(message.content))

        try:
            await client.call_tool(
                "add",
                {
                    "a": 2_000_000,
                    "b": 1,
                },
            )
        except ToolError as exc:
            print("\nExpected business error:")
            print(exc)


if __name__ == "__main__":
    asyncio.run(main())
```

FastMCP clients can connect through an explicit `StreamableHttpTransport`, or
infer HTTP transport when passed an `http://` or `https://`
URL. [FastMCP](https://gofastmcp.com/clients/transports?utm_source=chatgpt.com)

---

# 10. Run the Integration

## Terminal 1 — server

```bash
uv run uvicorn app:app \
  --host 127.0.0.1 \
  --port 8000
```

## Terminal 2 — client

```bash
uv run python test_http_client.py
```

Expected output shape:

```
Tools:
- add
- multiply

Add result:
{
    'id': 1,
    'operation': 'add',
    'a': 20,
    'b': 22,
    'result': 42,
    ...
}

Multiply result:
{
    'id': 2,
    'operation': 'multiply',
    'a': 6,
    'b': 7,
    'result': 42,
    ...
}

Calculation history:
[
    ...
]

Rendered prompt:
Role: user
Explain how to multiply 6 and 7...

Expected business error:
Operand 'a' has value 2000000...
```

---

# 11. The Major Lifecycle Difference

## stdio

```
Client starts
    │
    └── launches server subprocess

Client disconnects
    │
    └── server subprocess terminates
```

The client owns the server lifecycle.

## HTTP

```
Uvicorn starts
    │
    └── server remains available

Client A connects and disconnects
Client B connects and disconnects
Client C connects later

Uvicorn continues running
```

The deployment environment owns the server lifecycle.

Professional wording:

> “Moving to Streamable HTTP changes lifecycle ownership: the server becomes a
> long-running independent service rather than a client-owned subprocess.”

You can verify this directly:

1. Start Uvicorn.
2. Run the HTTP client.
3. Let the client exit.
4. Run it again.
5. Observe that Uvicorn never restarted.

---

# 12. Wire-Level Flow

A tool call now travels approximately like this:

```
FastMCP client
    │
    │ JSON-RPC request inside HTTP POST
    ▼
http://127.0.0.1:8000/mcp
    │
    ▼
Uvicorn
    │
    │ ASGI request events
    ▼
FastMCP
    │
    │ tools/call → add
    ▼
ArithmeticService
    │
    ▼
SQLite repository
```

The client must advertise support for both JSON and event-stream responses.
Streamable HTTP may return a normal JSON response or open an SSE stream
depending on the
interaction. [Model Context Protocol](https://modelcontextprotocol.io/specification/draft/basic/transports?utm_source=chatgpt.com)

On connections using the modern `2026-07-28` protocol, FastMCP clients also
attach routing headers such as:

```
Mcp-Method: tools/call
Mcp-Name: add
```

These let future gateways and reverse proxies identify the operation without
parsing the JSON-RPC body. FastMCP handles these protocol headers; do not
manually create them in the
client. [FastMCP](https://gofastmcp.com/deployment/http)

---

# 13. HTTP Is Not the MCP Protocol

Avoid this incorrect statement:

> “MCP is an HTTP API.”

More accurately:

```
MCP
└── Application protocol based on JSON-RPC

Streamable HTTP
└── One transport capable of carrying MCP messages
```

The same operation:

```
tools/call → add
```

can travel through:

```
stdio
or
Streamable HTTP
```

Professional wording:

> “MCP semantics remain transport-independent; Streamable HTTP provides the
> network delivery mechanism.”

---

# 14. Why Not Use `mcp.run(transport="http")`?

This would also work:

```python
if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8000,
    )
```

FastMCP’s direct HTTP runner is appropriate for simple standalone deployments.
The ASGI application approach gives explicit access to Uvicorn configuration,
workers, middleware and future application
composition. [FastMCP](https://gofastmcp.com/deployment/http)

We chose:

```python
app = mcp.http_app()
```

because the target architecture specifically separates:

```
FastMCP application
from
Uvicorn process runtime
```

Professional wording:

> “I expose FastMCP as an ASGI application and delegate process-level HTTP
> concerns to Uvicorn.”

---

# 15. Binding Addresses

## Loopback

```bash
--host 127.0.0.1
```

Only the local machine can connect.

Use this now.

## All interfaces

```bash
--host 0.0.0.0
```

The process listens on every available network interface.

`0.0.0.0` is a bind address, not normally the URL clients type.

Do not expose our current server through `0.0.0.0` because it has:

- No authentication
- No TLS
- No rate limiting
- No reverse proxy
- No hardened lifecycle management

The current server is for local development only. Authentication is strongly
recommended for remote FastMCP
servers. [FastMCP](https://gofastmcp.com/deployment/http)

---

# 16. Concurrency Model

One Uvicorn worker usually contains:

```
One process
└── One event loop
    ├── request task A
    ├── request task B
    └── request task C
```

When request A awaits database I/O, the event loop can run request B.

This is concurrency, not CPU parallelism.

```
Async concurrency:
one process interleaves waiting tasks

Worker parallelism:
multiple operating-system processes execute separately
```

Do not add several workers yet:

```bash
--workers 4
```

Our current SQLite and initialization design has not yet been reviewed for
multi-process behavior. Also, development reload and multiple workers serve
different purposes and should not be treated as interchangeable process
strategies.

---

# 17. Failure Experiments

## Experiment 1 — Server unavailable

Stop Uvicorn and run:

```bash
uv run python test_http_client.py
```

Expected layer:

```
Transport connection failure
```

The application service never executes.

Professional diagnosis:

> “The client failed to establish an HTTP transport connection to the MCP
> endpoint.”

---

## Experiment 2 — Wrong endpoint

Change:

```python
MCP_URL = "http://127.0.0.1:8000/wrong"
```

Expected layer:

```
HTTP routing failure
```

The network connection succeeds, but no MCP route exists at that path.

---

## Experiment 3 — Wrong port

Change:

```python
MCP_URL = "http://127.0.0.1:9000/mcp"
```

Expected layer:

```
TCP connection failure
```

No process is listening on that address and port.

---

## Experiment 4 — Invalid Host

Send a request using an unapproved `Host` header.

Expected result:

```
HTTP 403 Forbidden
```

The request guard should reject the request before MCP dispatch.

---

## Experiment 5 — Application error

Call:

```python
await client.call_tool(
    "add",
    {
        "a": 2_000_000,
        "b": 1,
    },
)
```

Expected layer:

```
HTTP works
MCP dispatch works
Service executes
Business validation fails
ToolError is returned
```

This distinction is crucial:

```
Connection error ≠ protocol error ≠ business error
```

---

# 18. Professional Vocabulary

| Term                      | Meaning                                                                |
|---------------------------|------------------------------------------------------------------------|
| **Application server**    | Process that runs an application and handles network protocol concerns |
| **ASGI**                  | Async interface between Python servers and applications                |
| **ASGI application**      | Callable receiving `scope`, `receive` and `send`                       |
| **Bind address**          | Network interface on which a server listens                            |
| **Loopback interface**    | Local-only network interface                                           |
| **Port**                  | Numeric network endpoint within a host                                 |
| **Endpoint**              | Network-accessible protocol location                                   |
| **Long-running service**  | Server process that exists independently of clients                    |
| **Lifecycle ownership**   | Component responsible for starting and stopping another component      |
| **Transport negotiation** | Client and server agreeing on communication behavior                   |
| **Stateless request**     | Request processable without worker-local history                       |
| **Session affinity**      | Routing related requests to the same server instance                   |
| **Horizontal scaling**    | Adding server processes or machines                                    |
| **Worker process**        | Independent process serving application requests                       |
| **Event loop**            | Scheduler that runs asynchronous tasks                                 |
| **SSE**                   | Server-Sent Events, an HTTP streaming mechanism                        |
| **Network boundary**      | Architectural boundary crossed through network communication           |
| **Request guard**         | Validation performed before application dispatch                       |
| **Protocol adapter**      | Component translating protocol operations into application calls       |

## Professional summary

> “I exposed the existing FastMCP component registry as a stateless ASGI
> application and served it through Uvicorn using Streamable HTTP. The service is
> now independently deployed and can support multiple remote client connections.
> Uvicorn owns sockets and HTTP processing, FastMCP owns MCP dispatch, and the
> application service remains transport-agnostic.”

---

# Completion Check

```
[ ] Uvicorn is a direct project dependency
[ ] app.py exposes an ASGI application
[ ] Uvicorn binds only to 127.0.0.1
[ ] MCP endpoint is available at /mcp
[ ] HTTP client discovers the existing tools
[ ] Tool calls persist calculations
[ ] Resources work over HTTP
[ ] Prompts work over HTTP
[ ] Business errors still become ToolError
[ ] Client can disconnect without stopping the server
[ ] HTTP transport is configured statelessly
[ ] Host and Origin protection is enabled
[ ] No public network exposure exists yet
```

## Next increment

The next increment introduces FastAPI as the application composition and
lifecycle owner:

```
FastAPI lifespan startup
├── validate configuration
├── initialize repository
└── mark application ready

FastAPI runtime
├── /health/live
├── /health/ready
└── mounted /mcp

FastAPI lifespan shutdown
└── release application resources
```

That removes lazy initialization from the first user request and gives
deployment systems meaningful liveness and readiness checks.