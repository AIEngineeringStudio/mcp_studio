> > I want to learn mcp hands-on from first principles.
> > Python/uv
> > FastMcp
> > FastApi for life cycle management
> > Uvicorn as Http server
> > Nginx as reverse proxy
> > Docker

I want you to teach me the coding thought process, technical implementation and
the jargon to sound professional.
Start from first principles and build incrementally.

# MCP From First Principles: Course Plan

We will build **one MCP service incrementally**, ending with this
production-style topology:

```
┌───────────────────────────────┐
│ AI application / MCP host     │
│                               │
│   MCP client                  │
└───────────────┬───────────────┘
                │ Streamable HTTP
                ▼
┌───────────────────────────────┐
│ Nginx                         │
│ TLS termination               │
│ Reverse proxy                 │
│ Forwarded headers             │
└───────────────┬───────────────┘
                │ HTTP
                ▼
┌───────────────────────────────┐
│ Uvicorn                       │
│ ASGI server / process runtime │
└───────────────┬───────────────┘
                │ ASGI
                ▼
┌───────────────────────────────┐
│ FastAPI                       │
│ Lifespan, health, middleware  │
│                               │
│   Mounted FastMCP app         │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Application services          │
│ Databases, APIs, files        │
└───────────────────────────────┘

Everything packaged with Docker.
Dependencies managed with uv.
```

## One important correction

**FastAPI is not required to build an MCP server.**

FastMCP can run directly over stdio or HTTP. We introduce FastAPI later when we
need:

- Application startup and shutdown
- Database connection pools
- Health and readiness endpoints
- Middleware
- Several HTTP interfaces in one service
- A clear application composition root

Starting with FastAPI, Uvicorn, Nginx, and Docker would hide the protocol behind
infrastructure. We will first prove the MCP behavior without a network.

---

# Learning Roadmap

| Increment | What we build                   | Concepts                                             |
|-----------|---------------------------------|------------------------------------------------------|
| 1         | In-memory MCP server and client | Tools, schemas, discovery, invocation                |
| 2         | Local stdio server              | Processes, stdin/stdout, transport boundary          |
| 3         | Resources and prompts           | MCP primitives and URI design                        |
| 4         | Real service layer              | Async I/O, validation, errors, dependency boundaries |
| 5         | Streamable HTTP server          | HTTP transport and ASGI                              |
| 6         | FastAPI integration             | Lifespan, application state, health checks           |
| 7         | Uvicorn runtime                 | Workers, graceful shutdown, concurrency              |
| 8         | Nginx reverse proxy             | Upstreams, headers, buffering, TLS                   |
| 9         | Docker and Compose              | Images, containers, networks, health checks          |
| 10        | Production hardening            | Authentication, observability, timeouts, testing     |

There is one version-sensitive issue to know early: the current MCP
architecture, dated **July 28, 2026**, describes a modern stateless discovery
model, while older MCP implementations use an initialization handshake. Current
FastMCP clients can negotiate between these protocol eras automatically. We will
therefore work through FastMCP rather than prematurely hard-coding JSON-RPC
messages. [Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture)

---

# Part 1: What MCP Actually Is

MCP is a standard contract between an AI application and external capabilities.
It separates two layers:

```
┌────────────────────────────────────────────┐
│ Data layer                                 │
│                                            │
│ JSON-RPC messages                          │
│ Tools, resources, prompts, notifications   │
├────────────────────────────────────────────┤
│ Transport layer                            │
│                                            │
│ stdio or Streamable HTTP                   │
└────────────────────────────────────────────┘
```

The same logical tool can be used through either transport. The transport
changes **how messages travel**, not what the tool does. MCP currently defines
stdio for local process communication and Streamable HTTP for network
communication. [Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture)

## The main participants

```
Host
└── Client
    └── Server
        ├── Tools
        ├── Resources
        └── Prompts
```

### Host

The user-facing AI application.

Examples include an AI desktop application, IDE, agent runtime, or chat
application.

### Client

The protocol component inside the host that communicates with a particular MCP
server.

Professional wording:

> “The host owns the user interaction, while its MCP client manages protocol
> communication with the server.”

### Server

The program exposing capabilities and context.

It does **not necessarily contain an LLM**. It may simply expose database
queries, API calls, calculations, files, or business operations.

---

# MCP Primitives

## Tool

An executable operation.

```python
def create_invoice(customer_id: str, amount: float) -> dict:
    ...
```

Use a tool when something must be **performed**.

Typical verbs:

- Search
- Calculate
- Create
- Update
- Send
- Delete

## Resource

Readable context identified by a URI.

```
config://application
customer://123/profile
schema://orders
```

Use a resource when something must be **retrieved or inspected**.

## Prompt

A reusable interaction template.

Use a prompt when the server wants to provide a recommended workflow or
structured instruction to the host.

FastMCP turns ordinary Python functions into MCP tools and derives the tool
description and input schema from the function’s docstring and type
annotations. [FastMCP](https://gofastmcp.com/tutorials/create-mcp-server)

---

# Increment 1: Your First MCP Tool

## Objective

Build and test this flow:

```
Python test client
        │
        │ in-memory MCP transport
        ▼
FastMCP server
        │
        ▼
add(a, b)
```

Using an in-memory client removes:

- Subprocess management
- HTTP
- Ports
- Uvicorn
- Nginx
- Docker

This lets us answer one question first:

> Does the MCP contract work?

---

## Step 1: Create the project

```bash
uv init mcp-first-principles
cd mcp-first-principles
uv add fastmcp
```

`uv` manages the project environment, dependencies, lockfile, and Python
tooling. `uv add` records the dependency in `pyproject.toml` and updates the
environment and lockfile. [Astral Docs](https://docs.astral.sh/uv/)

Your project should look like this:

```
mcp-first-principles/
├── pyproject.toml
├── uv.lock
├── server.py
└── test_client.py
```

The lockfile is important professional terminology:

> “`uv.lock` provides reproducible dependency resolution.”

---

## Step 2: Create `server.py`

```python
from fastmcp import FastMCP

mcp = FastMCP(
    name="First Principles MCP",
    instructions="Use the add tool when integer addition is required.",
)


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two integers and return their sum."""
    return a + b


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

## Why every line exists

### `FastMCP(...)`

```python
mcp = FastMCP(...)
```

This is the server’s **registry and protocol adapter**.

It owns the collection of exposed tools, resources, and prompts.

Professional wording:

> “The FastMCP instance acts as the application’s MCP component registry.”

### `@mcp.tool`

```python
@mcp.tool
```

The decorator registers the Python function as an MCP tool.

Without the decorator, `add` remains an ordinary private Python function.

### Type annotations

```python
def add(a: int, b: int) -> int:
```

These form part of the tool’s machine-readable contract.

Conceptually, FastMCP exposes something similar to:

```json
{
  "name": "add",
  "description": "Add two integers and return their sum.",
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

The model does not import or directly execute your Python function. The client
identifies the tool by name and sends structured arguments through MCP.

### Docstring

```python
"""Add two integers and return their sum."""
```

This is not merely developer documentation. It becomes part of the description
available to the MCP client and potentially the model.

Weak descriptions produce weak tool selection.

Bad:

```python
"""Adds stuff."""
```

Better:

```python
"""Add two integers and return their sum."""
```

For real tools, document:

- What it does
- When it should be used
- Important constraints
- Side effects
- Meaning of the result

### Main guard

```python
if __name__ == "__main__":
```

This prevents the server process from starting when another Python module
imports `server.py`. FastMCP recommends placing `run()` inside this
guard. [FastMCP](https://gofastmcp.com/deployment/running-server)

### Explicit stdio transport

```python
mcp.run(transport="stdio")
```

FastMCP uses stdio by default, but we make it explicit because explicit
infrastructure decisions are easier to review.

With stdio, an MCP client normally launches the server as a subprocess and
communicates through its input and output
streams. [FastMCP](https://gofastmcp.com/deployment/running-server)

---

## Step 3: Create `test_client.py`

```python
import asyncio

from fastmcp import Client

from server import mcp


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()

        print("Available tools:", [tool.name for tool in tools])

        result = await client.call_tool(
            "add",
            {
                "a": 20,
                "b": 22,
            },
        )

        print("Result:", result.data)


if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run python test_client.py
```

Expected output:

```
Available tools: ['add']
Result: 42
```

FastMCP’s in-memory client connects directly to the server object in the same
process, which makes it useful for deterministic testing without subprocess or
network complexity. Client operations use an asynchronous context manager so
connection setup and teardown are handled
correctly. [FastMCP](https://gofastmcp.com/clients/client)

---

# The Coding Thought Process

The implementation order was deliberate.

## 1. Begin with domain behavior

```python
def add(a: int, b: int) -> int:
    return a + b
```

This is the actual capability.

## 2. Define the contract

```python
a: int
b: int
-> int
```

The types describe valid inputs and output.

## 3. Describe intent

```python
"""Add two integers and return their sum."""
```

This helps consumers understand when the operation should be selected.

## 4. Expose it through MCP

```python
@mcp.tool
```

This converts private application functionality into a protocol capability.

## 5. Test without infrastructure

```python
Client(mcp)
```

This isolates protocol behavior from deployment behavior.

Professional wording:

> “We test the MCP surface in-process before introducing subprocess and network
> boundaries.”

That is a useful engineering habit well beyond MCP.

---

# What Happens During the Test

Conceptually:

```
1. Client connects
2. Client discovers server capabilities
3. Client requests the tool catalogue
4. Server returns the add tool and its schema
5. Client invokes add with structured arguments
6. FastMCP validates the arguments
7. Python executes add(20, 22)
8. FastMCP serializes the result
9. Client receives 42
10. Context manager closes the connection
```

The important boundary is:

```
MCP request
    │
    ▼
Input validation
    │
    ▼
Python handler
    │
    ▼
Result serialization
```

---

# Professional Jargon for This Lesson

| Term                     | Meaning                                                        |
|--------------------------|----------------------------------------------------------------|
| **Tool surface**         | The collection of tools exposed by a server                    |
| **Contract**             | The defined inputs, outputs, and behavior                      |
| **Schema-driven**        | Behavior described using machine-readable schemas              |
| **Handler**              | The function that processes an operation                       |
| **Capability discovery** | Learning what operations a server supports                     |
| **Protocol boundary**    | The point where application data becomes protocol messages     |
| **Transport boundary**   | The point where messages cross a process or network            |
| **In-process**           | Client and server execute in the same operating-system process |
| **Transport-agnostic**   | Business logic does not depend on stdio or HTTP                |
| **Serialization**        | Converting program objects into transferable data              |
| **Deterministic test**   | A controlled test with repeatable inputs and outputs           |

A professional summary of what you built:

> “I implemented a schema-driven MCP tool using FastMCP. Python type annotations
> define the input contract, while the docstring provides semantic metadata. I
> validated discovery and invocation using an in-process client before
> introducing
> a transport boundary.”

---

# Rules to Keep From Day One

## Keep handlers thin

Avoid placing all business logic inside decorated tool functions.

Preferred direction:

```python
@mcp.tool
def add(a: int, b: int) -> int:
    return calculator.add(a, b)
```

Later, this separation lets us test business logic independently from MCP.

## Do not treat docstrings as decoration

The descriptions are part of the AI-facing interface.

## Do not mix deployment concerns into tool logic

A tool should not know whether it is running under:

- stdio
- HTTP
- Uvicorn
- Nginx
- Docker

## Be careful with stdout under stdio

The stdio transport uses standard output for protocol messages. Arbitrary output
can interfere with that communication. MCP’s current guidance directs
implementations to use `stderr` or structured telemetry for logging rather than
treating stdout as an ordinary
console. [Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture)

---

# Exercises

Before moving forward:

1. Add this tool:

```python
@mcp.tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers and return the product."""
    return a * b
```

2. Verify that discovery returns both tools.

3. Call `multiply` with `6` and `7`.

4. Call `add` with an invalid argument:

```python
{
    "a": "not-an-integer",
    "b": 2,
}
```

Record the complete error. That error will introduce our next topics:

- Schema validation
- Protocol errors
- Application errors
- Failure contracts

The next increment will replace the in-memory connection with a real stdio
subprocess and inspect where the process and transport boundaries appear.