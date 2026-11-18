Confirmed. I’ll keep this **concise, structured, hands-on, and grounded only in official MCP/FastMCP sources**.

## Baseline we will use

For the main course:

- **MCP protocol:** `2025-11-25`, the current stable specification.
- **FastMCP:** `3.4.5`, the current stable release.
- **Python:** examples will use modern Python with type hints.
- **Transport:** start with `stdio`; move to Streamable HTTP later.

There is an important version boundary: MCP `2026-07-28` introduces a substantially different **stateless-first lifecycle**, but it is currently an RC rather than the stable protocol. FastMCP 4 is also currently beta and supports both protocol eras. We will learn the stable stateful protocol first, then explicitly study the new stateless architecture as a migration/delta module. [github.com](https://github.com/modelcontextprotocol/modelcontextprotocol/releases?utm_source=chatgpt.com)

---

# Course structure

Every concept will follow the same sequence:

| Step | What we do |
|---|---|
| 1. Problem | Why the feature exists |
| 2. Protocol | What MCP actually specifies |
| 3. Wire | Inspect JSON-RPC messages |
| 4. Build | Implement enough manually to understand it |
| 5. FastMCP | Replace plumbing with the abstraction |
| 6. Peel abstraction | Identify exactly what FastMCP generated/managed |
| 7. Design | Discuss production decisions and failure modes |
| 8. Jargon | Learn the precise terminology |
| 9. Exercise | Modify/break/debug the implementation |

The progression will be:

1. **Architecture, JSON-RPC, lifecycle, capabilities, stdio**
2. **Tools** — discovery, schemas, execution, errors, structured results
3. **Resources** — URIs, reads, templates, subscriptions
4. **Prompts** — discovery, arguments, generated messages
5. **Client capabilities** — roots, sampling, elicitation
6. **Protocol utilities** — progress, cancellation, logging, completion, pagination
7. **Streamable HTTP**
8. **Authentication and authorization**
9. **Context, lifecycle state and concurrency**
10. **FastMCP-specific composition** — providers, proxies, transforms, generated servers
11. **Testing, observability, security and production deployment**
12. **MCP 2026-07-28 stateless architecture + FastMCP 4 migration**

The protocol separates server primitives into **tools, resources and prompts**, while client-side capabilities include **sampling, roots and elicitation**. Utilities such as logging, completion, progress and cancellation sit across these features. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25?utm_source=chatgpt.com)

---

# Lesson 1 — What MCP actually is

Forget LLMs temporarily.

Suppose program **A** wants to call capabilities exposed by program **B**.

Without a protocol, A must know B's proprietary API:

```
A ───── custom integration ─────> B
```

Now imagine 20 AI applications and 100 external systems.

Without standardization:

```
20 clients × 100 integrations = integration mess
```

MCP defines a common contract:

```
                  MCP
            ┌──────────────┐
AI Host ─── Client <──────> Server ─── Database
            Client <──────> Server ─── Git
            Client <──────> Server ─── SaaS API
            Client <──────> Server ─── Filesystem
            └──────────────┘
```

The official architecture distinguishes three roles:

```
HOST
│
├── MCP Client A ───── MCP Server A
│
├── MCP Client B ───── MCP Server B
│
└── MCP Client C ───── MCP Server C
```

A **host** is the application containing the AI experience. An **MCP client** is the protocol participant inside that host that connects to one server. An **MCP server** exposes capabilities. MCP itself standardizes their communication rather than defining how your LLM or agent should reason. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25?utm_source=chatgpt.com)

### Professional terminology

| Term | Precise meaning |
|---|---|
| **Host** | Application orchestrating MCP clients |
| **Client** | MCP endpoint connecting to a server |
| **Server** | MCP endpoint exposing capabilities |
| **Primitive** | Core MCP concept such as tool/resource/prompt |
| **Capability** | Declared support for an optional protocol feature |
| **Transport** | Mechanism carrying protocol messages |
| **Protocol message** | JSON-RPC request, response or notification |
| **Wire format** | Actual bytes/messages transmitted between endpoints |

A technically accurate sentence would be:

> “The host creates an MCP client which negotiates capabilities with the server over the stdio transport.”

That is much more precise than saying:

> “The AI connects to the MCP.”

---

# First principle 2 — MCP has two layers

Conceptually:

```
┌─────────────────────────────────────┐
│             Data layer              │
│                                     │
│ JSON-RPC                            │
│ lifecycle                           │
│ tools / resources / prompts         │
│ sampling / elicitation / roots      │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│           Transport layer           │
│                                     │
│ stdio                               │
│ Streamable HTTP                     │
└─────────────────────────────────────┘
```

The **data layer** defines what messages mean. The **transport layer** defines how those messages get from one process to another. MCP currently defines `stdio` and Streamable HTTP as its standard transports. [Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture?utm_source=chatgpt.com)

This distinction matters.

A `tools/call` operation is **not HTTP**.

It is an MCP protocol operation that could travel over:

```
stdio
```

or:

```
HTTP
```

The operation remains conceptually the same.

---

# First principle 3 — MCP is built on JSON-RPC 2.0

At the wire level, stable MCP messages are JSON-RPC.

A request looks conceptually like:

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "some/method",
  "params": {}
}
```

A successful response:

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "result": {}
}
```

An error response:

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "error": {
    "code": -32602,
    "message": "Invalid params"
  }
}
```

And a notification has **no `id`** because no response is expected:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/example"
}
```

MCP requires its protocol messages to follow JSON-RPC 2.0. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic?utm_source=chatgpt.com)

### Important jargon

A **request** expects a response.

A **notification** is one-way.

A **method** identifies the operation, for example:

```
initialize
tools/list
tools/call
resources/list
resources/read
prompts/list
prompts/get
```

That naming convention is worth internalizing.

---

# First principle 4 — Stable MCP has a lifecycle

Before calling tools, the stable MCP protocol performs initialization.

Conceptually:

```
CLIENT                              SERVER
  │                                   │
  │──── initialize ──────────────────>│
  │                                   │
  │<── initialize result ─────────────│
  │                                   │
  │──── notifications/initialized ───>│
  │                                   │
  │        normal operation           │
  │──── tools/list ──────────────────>│
  │<── tools ─────────────────────────│
  │                                   │
```

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

The client initiates the stable lifecycle with `initialize`; after receiving the server response it sends `notifications/initialized`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle?utm_source=chatgpt.com)

This is called **capability negotiation**.

---

# Look at the wire

A simplified client initialization:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {},
    "clientInfo": {
      "name": "learning-client",
      "version": "0.1.0"
    }
  }
}
```

Our server might answer:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "tools": {}
    },
    "serverInfo": {
      "name": "learning-server",
      "version": "0.1.0"
    }
  }
}
```

That `"tools": {}` is meaningful.

It means:

> “I implement the MCP tools capability.”

Then:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

Now normal operations begin. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle?utm_source=chatgpt.com)

---

# Hands-on: build an MCP server without FastMCP

We will expose exactly one tool:

```
add(a, b)
```

The point is **not** to write a production MCP server manually.

The point is to see what FastMCP eventually removes.

Create `raw_server.py`:

```python
import json
import sys

PROTOCOL_VERSION = "2025-11-25"


def send(message: dict) -> None:
    print(json.dumps(message), flush=True)


def success(request_id, result):
    send({
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    })


def error(request_id, code, message):
    send({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    })


for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    request_id = message.get("id")

    if method == "initialize":
        success(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "raw-learning-server",
                    "version": "0.1.0",
                },
            },
        )

    elif method == "notifications/initialized":
        # Notification: no response.
        pass

    elif method == "tools/list":
        success(
            request_id,
            {
                "tools": [
                    {
                        "name": "add",
                        "description": "Add two integers.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "a": {"type": "integer"},
                                "b": {"type": "integer"},
                            },
                            "required": ["a", "b"],
                            "additionalProperties": False,
                        },
                    }
                ]
            },
        )

    elif method == "tools/call":
        params = message.get("params", {})

        if params.get("name") != "add":
            error(
                request_id,
                -32602,
                f"Unknown tool: {params.get('name')}",
            )
            continue

        arguments = params.get("arguments", {})
        a = arguments.get("a")
        b = arguments.get("b")

        if not isinstance(a, int) or not isinstance(b, int):
            success(
                request_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": "a and b must both be integers",
                        }
                    ],
                    "isError": True,
                },
            )
            continue

        success(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": str(a + b),
                    }
                ],
                "isError": False,
            },
        )

    elif request_id is not None:
        error(request_id, -32601, f"Unknown method: {method}")
```

The stdio transport requires the server to read JSON-RPC messages from `stdin` and write messages to `stdout`; messages are newline-delimited. Logs therefore should not be casually printed to stdout because that stream is carrying protocol traffic. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports?utm_source=chatgpt.com)

This implementation intentionally ignores a lot of production requirements. That is useful: every missing piece will later explain why frameworks exist.

---

# What did we just implement?

Our tiny server already contains five distinct protocol responsibilities:

```
transport framing
      │
      ▼
JSON parsing
      │
      ▼
method routing
      │
      ▼
MCP lifecycle
      │
      ▼
tool discovery + execution
```

And we have not implemented:

```
schema validation
pagination
timeouts
cancellation
progress
logging
resources
prompts
HTTP
auth
subscriptions
structured results
concurrency
security
```

That is the abstraction pressure that leads to FastMCP.

---

# Now the FastMCP version

Install the stable version explicitly:

```bash
uv add "fastmcp==3.4.5"
```

FastMCP recommends using `uv`, and its documentation recommends exact version pinning for production because the MCP ecosystem evolves quickly. [FastMCP](https://gofastmcp.com/getting-started/installation?utm_source=chatgpt.com)

Create `fast_server.py`:

```python
from fastmcp import FastMCP

mcp = FastMCP("learning-server")


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


if __name__ == "__main__":
    mcp.run()
```

That is the same conceptual MCP capability.

FastMCP's `FastMCP` server manages protocol communication and exposes Python functions as MCP tools. Its `@mcp.tool` decorator derives tool metadata and schemas from the Python function rather than requiring you to manually construct the MCP representation. `mcp.run()` uses stdio by default. [FastMCP](https://gofastmcp.com/servers/server?utm_source=chatgpt.com)

---

# What FastMCP abstracted away

| Protocol concern | Manual implementation | FastMCP |
|---|---|---|
| JSON-RPC parsing | You wrote it | Framework |
| Request dispatch | `if method == ...` | Framework |
| Initialization | Manual | Framework |
| Capability declaration | Manual JSON | Derived |
| Tool registry | Manual | `@mcp.tool` |
| Input schema | Manual JSON Schema | Python type hints |
| Validation | Manual | Framework |
| Result serialization | Manual content blocks | Framework |
| stdio lifecycle | Manual loop | `mcp.run()` |

This is the key mental model:

```
FastMCP is not a different protocol.

Python code
    │
    ▼
FastMCP abstraction
    │
    ▼
MCP protocol objects
    │
    ▼
JSON-RPC
    │
    ▼
stdio / HTTP
```

When debugging FastMCP professionally, you should always be able to mentally move **down that stack**.

---

# Inspect the generated contract

Do not trust the decorator magically.

Inspect what it generated:

```bash
uv run fastmcp list fast_server.py --input-schema
```

FastMCP's CLI connects as an MCP client and can display the server's complete tool schemas. [FastMCP](https://gofastmcp.com/cli/client)

Then invoke the tool:

```bash
uv run fastmcp call fast_server.py add a=10 b=32
```

The CLI discovers the schema, coerces arguments appropriately and performs the MCP tool call. [FastMCP](https://gofastmcp.com/cli/client)

This habit is important:

> **Write Python → inspect MCP contract → test protocol behavior.**

Do not treat decorators as magic.

---

# One subtle design lesson already

Consider this:

```python
def add(a: int, b: int) -> int:
```

Those type annotations are no longer merely Python documentation.

Through FastMCP they contribute to a **network-facing protocol contract**.

Conceptually:

```
Python annotation
      │
      ▼
JSON Schema
      │
      ▼
MCP Tool.inputSchema
      │
      ▼
client
      │
      ▼
LLM/tool-selection system
```

The MCP specification defines a tool's `inputSchema` as JSON Schema; the stable spec defaults to JSON Schema 2020-12 when `$schema` is omitted. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

Professional terminology:

> “FastMCP derives the tool's protocol schema from the callable's Python signature.”

Or:

> “The Python function signature becomes part of the MCP API surface.”

---

# Tool errors: an important distinction

Notice that our raw server treated two failures differently.

Unknown tool:

```
JSON-RPC protocol error
```

Bad tool input/business failure:

```
successful tools/call RPC
└── tool result
    └── isError = true
```

Why?

Because MCP distinguishes **protocol errors** from **tool execution errors**.

A malformed protocol request means the MCP operation itself failed. An execution error is information the model may be able to understand and correct—for example, an invalid date or rejected business operation. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

That distinction will matter heavily when we build real tools.

---

# Vocabulary checkpoint

By the end of this lesson, these statements should feel natural:

| Phrase | Meaning |
|---|---|
| **“Wire-level MCP”** | Raw JSON-RPC representation |
| **“Capability negotiation”** | Client/server declaring supported optional features |
| **“Protocol lifecycle”** | Initialization → operation → shutdown |
| **“stdio transport”** | MCP messages over process stdin/stdout |
| **“Tool discovery”** | `tools/list` |
| **“Tool invocation”** | `tools/call` |
| **“Input schema”** | JSON Schema describing tool arguments |
| **“Protocol error”** | JSON-RPC-level failure |
| **“Tool execution error”** | Valid MCP response representing tool failure |
| **“Framework abstraction”** | FastMCP hiding protocol plumbing |

One particularly useful professional distinction is:

> **MCP specifies interoperability; FastMCP provides an implementation abstraction.**

---

# Your first exercise

Do these before moving on:

```
1. Run fastmcp list and inspect add's generated JSON Schema.

2. Change:
      a: int
   to:
      a: float
   and inspect the schema difference.

3. Add:
      description/docstring
   and find where it appears in tools/list.

4. Call the tool with invalid input.

5. Compare the FastMCP behavior with the raw server.

6. Add a second tool manually to raw_server.py.

7. Then add the same second tool with @mcp.tool.
```

The important outcome is not merely getting `42`.

It is being able to explain:

```
client
  └─ tools/call
       └─ JSON-RPC request
            └─ stdio transport

FastMCP receives it
  └─ routes tool
       └─ validates schema
            └─ invokes Python function
                 └─ serializes MCP result
```

## Next lesson

The correct next step is **Tools in depth**: `tools/list`, `tools/call`, JSON Schema design, descriptions, structured output, `outputSchema`, content blocks, tool annotations, validation and error semantics. Tools are the best first primitive because they expose nearly every important MCP design idea while remaining easy to test. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)