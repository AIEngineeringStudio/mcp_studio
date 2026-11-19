# Increment 2 — Real stdio Subprocess

## Goal

Replace this:

```
Client and server
inside one Python process
```

with this:

```
┌────────────────────────────┐
│ Client process             │
│ PID: 100                   │
│                            │
│ FastMCP Client             │
└─────────────┬──────────────┘
              │
              │ stdin/stdout pipes
              │ newline-delimited JSON-RPC
              ▼
┌────────────────────────────┐
│ Server subprocess          │
│ PID: 101                   │
│ Parent PID: 100            │
│                            │
│ FastMCP Server             │
└────────────────────────────┘
```

With stdio, the client launches the server as a subprocess and manages its
lifecycle. MCP messages travel through the child process’s standard streams:
requests enter through `stdin`, responses leave through `stdout`, and logs
belong on `stderr`. [FastMCP](https://gofastmcp.com/clients/transports)

The important new concept is the **process boundary**.

---

## 1. Project structure

```
mcp-first-principles/
├── pyproject.toml
├── uv.lock
├── server.py
├── test_client.py
└── test_stdio_client.py
```

Keep the in-memory test. It remains useful as the fastest protocol-level test.

---

## 2. Update `server.py`

```python
from __future__ import annotations

import logging
import os
import sys

from fastmcp import FastMCP

# stdio reserves stdout for MCP protocol messages.
# Python logging uses stderr explicitly.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="First Principles MCP",
    instructions="Use the arithmetic tools for integer calculations.",
)


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two integers and return their sum."""
    return a + b


@mcp.tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers and return their product."""
    return a * b


@mcp.tool
def server_process_info() -> dict[str, str | int]:
    """Return diagnostic information about the MCP server process."""
    return {
        "server_pid": os.getpid(),
        "parent_pid": os.getppid(),
        "environment": os.getenv("APP_ENV", "not-set"),
    }


if __name__ == "__main__":
    logger.info(
        "Starting MCP server process pid=%s parent_pid=%s",
        os.getpid(),
        os.getppid(),
    )

    mcp.run(transport="stdio")
```

## Why add `server_process_info`?

It is a diagnostic tool that proves the server is no longer running inside the
client process.

This is called **instrumenting the boundary**:

> Add enough diagnostic information to prove your architectural assumptions.

We assume there are two processes. The returned process IDs let us verify that
assumption instead of merely believing it.

---

## 3. Create `test_stdio_client.py`

```python
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError

PROJECT_ROOT = Path(__file__).resolve().parent
SERVER_FILE = PROJECT_ROOT / "server.py"


async def main() -> None:
    print(f"Client PID: {os.getpid()}")
    print(f"Python interpreter: {sys.executable}")

    transport = StdioTransport(
        command=sys.executable,
        args=[str(SERVER_FILE)],
        cwd=str(PROJECT_ROOT),
        env={
            "APP_ENV": "development",
        },
        keep_alive=False,
    )

    client = Client(transport)

    async with client:
        tools = await client.list_tools()
        print("Tools:", [tool.name for tool in tools])

        process_result = await client.call_tool(
            "server_process_info",
            {},
        )
        print("Server process:", process_result.data)

        add_result = await client.call_tool(
            "add",
            {
                "a": 20,
                "b": 22,
            },
        )
        print("20 + 22 =", add_result.data)

        multiply_result = await client.call_tool(
            "multiply",
            {
                "a": 6,
                "b": 7,
            },
        )
        print("6 × 7 =", multiply_result.data)

        try:
            await client.call_tool(
                "add",
                {
                    "a": "not-an-integer",
                    "b": 2,
                },
            )
        except ToolError as exc:
            print("Expected tool error:", exc)


if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run python test_stdio_client.py
```

`uv run` executes the command inside the project environment and ensures that
the environment is synchronized with the project lockfile
first. [Astral Docs](https://docs.astral.sh/uv/concepts/projects/run/)

Expected shape of the output:

```
Client PID: 100
Python interpreter: /project/.venv/bin/python
Tools: ['add', 'multiply', 'server_process_info']
Server process: {
    'server_pid': 101,
    'parent_pid': 100,
    'environment': 'development'
}
20 + 22 = 42
6 × 7 = 42
Expected tool error: ...
```

The exact error text may vary between FastMCP versions. The important result is
that `call_tool()` raises `ToolError` when tool execution or argument validation
fails. [FastMCP](https://gofastmcp.com/clients/tools?utm_source=chatgpt.com)

---

# Coding Thought Process

## Decision 1: Explicit transport instead of inference

FastMCP allows this convenience form:

```python
client = Client("server.py")
```

That automatically infers a stdio transport.

We are deliberately using:

```python
transport = StdioTransport(...)
client = Client(transport)
```

because it exposes the important deployment controls:

```
command
args
working directory
environment
process persistence
```

Professional wording:

> “I configured the stdio transport explicitly to make process execution and
> environment propagation deterministic.”

FastMCP’s explicit `StdioTransport` supports command arguments, environment
variables, a working directory, and subprocess persistence
configuration. [FastMCP](https://gofastmcp.com/clients/transports)

---

## Decision 2: Use `sys.executable`

We could launch the child like this:

```python
command = "python"
```

But `python` depends on the operating system’s `PATH`.

Instead:

```python
command = sys.executable
```

uses the exact Python interpreter running the client.

Because the client was started through:

```bash
uv run python test_stdio_client.py
```

`sys.executable` should point to the Python interpreter in the uv-managed
project environment.

This avoids a common failure:

```
Client uses project virtual environment
Server accidentally uses system Python
Server cannot import fastmcp
```

Professional wording:

> “The child process is pinned to the same interpreter as the parent, avoiding
> environment drift.”

---

## Decision 3: Set `cwd` explicitly

```python
cwd = str(PROJECT_ROOT)
```

A subprocess has a working directory. Relative paths inside the server are
resolved from that directory.

Without an explicit `cwd`, server behavior could depend on where the client was
launched.

Bad assumption:

```
The process will always start from the project directory.
```

Better design:

```
The launcher defines the server’s working directory.
```

Professional wording:

> “The working directory is explicit rather than inherited implicitly from the
> caller.”

For production code, application file locations should usually be calculated
from configured absolute paths rather than relying heavily on the working
directory.

---

## Decision 4: Pass only required environment variables

```python
env = {
    "APP_ENV": "development",
}
```

A subprocess environment is part of its configuration boundary.

Current FastMCP stdio transports inherit only a restricted allowlist of basic
environment variables. Additional values such as API keys or database URLs must
be passed explicitly. [FastMCP](https://gofastmcp.com/clients/transports)

Do not do this casually:

```python
env = dict(os.environ)
```

That can expose every available credential to the child process.

Prefer:

```python
required_env = {
    "DATABASE_URL": os.environ["DATABASE_URL"],
    "API_KEY": os.environ["API_KEY"],
}
```

Professional wording:

> “Environment propagation follows least privilege; only required configuration
> is forwarded to the subprocess.”

---

## Decision 5: Disable process persistence for this lesson

```python
keep_alive = False
```

Current FastMCP stdio transports use `keep_alive=True` by default, allowing one
subprocess to be reused across multiple client contexts. We disable it here so
entering and exiting the client context maps cleanly to one isolated server
process lifecycle. [FastMCP](https://gofastmcp.com/clients/transports)

The lifecycle becomes:

```
async with client:
    ├── launch child process
    ├── establish MCP connection
    ├── perform operations
    └── close connection and terminate child
```

Later, process reuse may improve startup performance, but it also changes
isolation and lifecycle semantics.

---

# What Actually Travels Through the Pipes?

Conceptually, the client may write a JSON-RPC request like:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
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

The server writes a correlated response:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "42"
      }
    ]
  }
}
```

FastMCP handles the exact protocol representation. The examples above illustrate
the conceptual shape rather than guaranteeing the exact current wire payload.

The JSON-RPC `id` lets the client correlate a response with its original
request.

```
Request id=3 ───────────────►
                             server executes tool
Response id=3 ◄──────────────
```

Professional term:

> **Request-response correlation**

The current stdio specification uses newline-delimited UTF-8 JSON-RPC messages.
The server must not write non-MCP output to
`stdout`. [Model Context Protocol](https://modelcontextprotocol.io/specification/draft/basic/transports/stdio)

---

# Why `print()` Is Dangerous in `server.py`

This is wrong for a stdio MCP server:

```python
print("Server started")
```

`print()` writes to `stdout` by default.

But `stdout` is the protocol channel:

```
stdout
├── valid JSON-RPC message
├── valid JSON-RPC message
└── "Server started"       ← corrupts the protocol stream
```

Use logging directed to `stderr`:

```python
logger.info("Server started")
```

The stdio specification permits server logging through `stderr`, while reserving
`stdout` exclusively for MCP
messages. [Model Context Protocol](https://modelcontextprotocol.io/specification/draft/basic/transports/stdio)

Professional wording:

> “Application logs must remain out-of-band from the protocol stream.”

---

# Error Layers

Your invalid call demonstrates several possible error categories:

```
Invalid input
    │
    ▼
Schema or model validation
    │
    ▼
Tool execution error representation
    │
    ▼
MCP response
    │
    ▼
FastMCP Client raises ToolError
```

Keep these categories distinct:

| Error type           | Example                             |
|----------------------|-------------------------------------|
| Transport error      | Child process failed to start       |
| Protocol error       | Malformed JSON-RPC message          |
| Discovery error      | Requested capability does not exist |
| Validation error     | `"abc"` cannot become an integer    |
| Application error    | Division by zero                    |
| Infrastructure error | Database connection failed          |

A professional incident description should identify the layer:

Bad:

> “The MCP failed.”

Better:

> “The stdio transport launched successfully, but tool invocation failed during
> input validation.”

---

# Useful Failure Experiments

## 1. Break the server path

Change:

```python
SERVER_FILE = PROJECT_ROOT / "missing_server.py"
```

Expected category:

```
Subprocess startup failure
```

The MCP server never becomes available.

---

## 2. Use the wrong interpreter

Change:

```python
command = "python"
```

On a machine where system Python lacks FastMCP, you may get:

```
ModuleNotFoundError: No module named 'fastmcp'
```

Expected category:

```
Runtime environment mismatch
```

---

## 3. Pollute stdout

Add this before `mcp.run()`:

```python
print("Starting server")
```

Expected category:

```
Protocol framing corruption
```

Remove it afterward.

---

## 4. Remove the environment variable

Delete:

```python
env = {"APP_ENV": "development"}
```

Expected result:

```
"environment": "not-set"
```

This proves the child does not automatically share all parent-process
configuration.

---

# Professional Vocabulary

| Term                        | Meaning                                                                |
|-----------------------------|------------------------------------------------------------------------|
| **Parent process**          | Process that launches another process                                  |
| **Child process**           | Process launched by the parent                                         |
| **Subprocess**              | Another process managed by an application                              |
| **IPC**                     | Inter-process communication                                            |
| **Pipe**                    | Operating-system communication channel between processes               |
| **Process boundary**        | Isolation boundary between separate processes                          |
| **Process ownership**       | Which component starts, monitors, and stops a process                  |
| **Environment propagation** | Passing environment configuration to a child                           |
| **Working directory**       | Base directory used for relative paths                                 |
| **Protocol framing**        | Rules defining where one message ends and another begins               |
| **Correlation ID**          | Identifier pairing a response with a request                           |
| **Out-of-band logging**     | Logs sent outside the main protocol channel                            |
| **Graceful shutdown**       | Allowing work and resources to close cleanly                           |
| **Forced termination**      | Stopping a process through an OS termination mechanism                 |
| **Environment drift**       | Parent and child unexpectedly using different dependencies or settings |

A good summary for this increment:

> “I moved the MCP integration from an in-process test transport to a real stdio
> subprocess. The client now owns the server lifecycle and communicates using
> JSON-RPC over operating-system pipes. I made the interpreter, working directory,
> environment propagation, and process persistence explicit to avoid runtime drift
> and hidden launcher assumptions.”

---

# Completion Check

You have completed this increment when all of these are true:

```
[ ] Client PID differs from server PID
[ ] Server parent PID matches client PID
[ ] Tool discovery returns three tools
[ ] add returns 42
[ ] multiply returns 42
[ ] Invalid input is surfaced as ToolError
[ ] APP_ENV reaches the child process
[ ] No application print statements write to server stdout
```

The next increment will add **resources and prompts**, which completes the three
core server primitives before we introduce HTTP.