# Semantic tracing

Semantic tracing establishes observability for both application boundaries:

1. Client application boundary: `Client Application ↔ MCP client`

   Semantic tracing here captures the `application operation`, its `arguments`,
   `result`, and `error`.

2. Server application boundary: `MCP server ↔ Server Application`

   Semantic tracing here captures the `tool invocation` and its `result` or
   `exception`.

```
CLIENT SIDE                                  SERVER SIDE

+----------------------------+               +----------------------------+
| Client Application         |               | Server Application         |
| verify_primitives.py       |               | get_ticket()               |
|                            |               |                            |
| SEMANTIC: CALL / RESULT    |               |                            |
+----------------------------+               +----------------------------+
       |            ^                                ^            |  
       | Semantic   |                                | Semantic   | 
       v Boundary 1 |                                | Boundary 2 v
+----------------------------+               +----------------------------+
| FastMCP Client             |               | FastMCP Server             |
|                            |               |                            |
|                            |               | SEMANTIC: IN / DONE        |
|                            |               | (middleware boundary)      |
|                            |               |                            |
| JSON-RPC Layer             |               | JSON-RPC Layer             |
|                            |               |                            |
| [1] CLIENT OUT TRACE       |               | [2] SERVER IN TRACE        |
| [4] CLIENT IN TRACE        |               | [3] SERVER OUT TRACE       |
|                            |               |                            |
+----------------------------+               +----------------------------+
       |            ^                                ^            |
       | Protocol   |                                | Protocol   |
       | Boundary 1 |                                | Boundary 2 |
       v            |                                |            v
+----------------------------+               +----------------------------+
| Client Transport           |               | Server Transport           |
|                            |-- REQUEST --->|                            |
| STDIO / HTTP               |<-- RESPONSE --| STDIO / HTTP               |
+----------------------------+               +----------------------------+
```

**Semantic Boundary 2:**
`SEMANTIC: IN / DONE` trace is inside FastMCP server middleware, not at the
boundary between the server application and FastMCP.

Our completion criterion is that, for tools, resources, and prompts, you can see
the client call, server entry, server completion, and client result.

**What semantic tracing does not guarantee**

It does not capture the actual JSON-RPC envelope.
That requires tracing closer to the `MCP session/transport boundary`.

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "get_ticket",
    "arguments": {
      "ticket_id": "T-100"
    }
  }
}
```

**One limitation to remember:**

Client-side semantic tracing through this helper captures only calls you
explicitly wrap. **Server middleware has broader coverage.**

That difference is precisely why we need the next protocol tracing layer.

## Project Structure

```
mcp-studio-labs/
└── lesson_2/
    ├── semantic_trace_server.py
    ├── semantic_trace_client.py
    ├── server.py
    └── verify_primitives.py
```

## **1. Add server-side semantic tracing**

This traces `inbound requests` and `notifications` at the server middleware
layer

FastMCP 4 provides `on_message` middleware, which receives inbound requests and
notifications, including discovery and protocol errors.

Its `call_next()` lets you observe the resulting operation, but that result is
not necessarily the final serialized JSON-RPC response.

### Create `semantic_trace_server.py`:

```python
import sys
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext, CallNext


class SemanticTrace(Middleware):
    """ Covers `inbound requests` and `notifications`
    at the server middleware layer """

    async def on_message(
            self,
            context: MiddlewareContext,
            call_next: CallNext[Any, Any]
    ):
        # [2] SERVER IN TRACE
        # Observe messages and log necessary details
        print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n",
              file=sys.stderr,
              flush=True)
        print(
            f"\n[SERVER IN] {context.method}: {context.message!r}",
            # What is `context.source` ??
            file=sys.stderr,
            flush=True,
        )

        # In Python, !r means use repr() inside an f-string.
        # It displays the developer representation of a value instead of its
        # normal string representation.
        # message = "Hello\nWorld"
        #
        # print(f"{message}")     # Uses str()
        # print(f"{message!r}")   # Uses repr()
        #
        # With !r:    Prints 'Hello\nWorld'.
        # Without !r: Prints world in next line

        try:
            # forward the original message unchanged
            result = await call_next(context)
        except Exception as exc:
            print(
                f"\n[SERVER ERROR] {context.method}: {exc!r}",
                file=sys.stderr,
                flush=True,
            )
            print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n",
                  file=sys.stderr,
                  flush=True)
            raise

        # [3] SERVER OUT TRACE
        print(
            f"\n[SERVER DONE] {context.method}: {result!r}",
            file=sys.stderr,
            flush=True
        )
        print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n",
              file=sys.stderr,
              flush=True)

        return result
```

FastMCP 4 documents the `on_message` hook, `MiddlewareContext`, and `call_next`
contract.

We deliberately use `stderr` because printing trace information to
an STDIO MCP server's `stdout` would corrupt its protocol stream.

### Changes in `server.py`

Add this import:

```
from semantic_trace_server import SemanticTrace
```

Immediately after `mcp = FastMCP("Ticket learning service")`, add:

```
mcp.add_middleware(SemanticTrace())

```

## **2. Add client-side semantic tracing**

This traces the calls made by your application without modifying FastMCP's
client internals.

**One important detail:** Your `trace_client()` helper logs the method and
parameters you supply as descriptive labels.

It does not capture the actual JSON-RPC message. That's appropriate for our
current semantic tracing step.

Use the same wrapper for the four operations in `verify_resources()` and
`verify_prompts()`.

### Create `semantic_trace_client.py` and add this code

```
import sys

from typing import Any
from collections.abc import Awaitable

async def trace_client(
    method: str,
    params: dict[str, Any],
    operation: Awaitable[Any],
) -> Any:
    print(
        f"[CLIENT CALL] {method}: {params!r}",
        file=sys.stderr,
        flush=True,
    )

    try:
        result = await operation
    except Exception as exc:
        print(
            f"[CLIENT ERROR] {method}: {exc!r}",
            file=sys.stderr,
            flush=True,
        )
        raise

    print(
        f"[CLIENT RESULT] {method}: {result!r}",
        file=sys.stderr,
        flush=True,
    )
    return result
```

### Changes in `verify_primitives.py`

Add this import:

```
from semantic_trace_client import trace_client
```

#### Changes to two operations inside `verify_tools()`

**Replace:**

```
tools = await client.list_tools()
```

**With:**

```
tools = await trace_client(
    "tools/list", {}, client.list_tools()
)
```

---

**Replace:**

```
result = await client.call_tool("get_ticket", {"ticket_id": "T-100"})
```

**With:**

```
result = await trace_client(
    "tools/call",
    {"name": "get_ticket", "arguments": {"ticket_id": "T-100"}},
    client.call_tool("get_ticket", {"ticket_id": "T-100"}),
)
```

#### Changes to two operations inside `verify_resources()`

**Replace:**

```
templates = await client.list_resource_templates()
```

**With:**

```
templates = await trace_client(
        "resources/templates/list", 
        {}, 
        client.list_resource_templates()
)
```

---

**Replace:**

```
contents = await client.read_resource("ticket://T-100")
```

**With:**

```
contents = await trace_client(
    "resources/read",
    {"uri": "ticket://T-100"},
    client.read_resource("ticket://T-100"),
)
```

#### Changes to two operations inside `verify_prompts()`

**Replace:**

```
await client.list_prompts()
```

**With:**

```
prompts = await trace_client(
        "prompts/list",
        {},
        client.list_prompts(),
)
```

---

**Replace:**

```
result = await client.get_prompt(
        "summarize_ticket",
        {"ticket_id": "T-100"},
)
```

**With:**

```
result = await trace_client(
    "prompts/get",
    {
        "name": "summarize_ticket",
        "arguments": {"ticket_id": "T-100"},
    },
    client.get_prompt(
        "summarize_ticket",
        {"ticket_id": "T-100"},
    ),
)
```

### Why tools and resources have different request structures?

**Tool call:**

```json
{
  "method": "tools/call",
  "params": {
    "name": "get_ticket",
    "arguments": {
      "ticket_id": "T-100"
    }
  }
}
```

**Resource read:**

```json
{
  "method": "resources/read",
  "params": {
    "uri": "ticket://T-100"
  }
}
```

Your server registers` @mcp.resource("ticket://{ticket_id}")`,
so FastMCP resolves the resource using the URI.

You don't pass the Python function name.

## **3. Run the first verification**

Start with in-memory:

```
python verify_primitives.py --transport in-memory --focus tools
```

Your semantic trace should follow this sequence (illustrative output,
abbreviated):

```
[CLIENT CALL] tools/list: {}
[SERVER IN] tools/list: ...
[SERVER DONE] tools/list: ...
[CLIENT RESULT] tools/list: ...

[CLIENT CALL] tools/call: {'name': 'get_ticket', ...}
[SERVER IN] tools/call: ...
[SERVER DONE] tools/call: ...
[CLIENT RESULT] tools/call: ...

tools: discovered get_ticket and called it successfully
```

The `SERVER DONE` value is the middleware operation result, **not necessarily
the final JSON-RPC response**.

Likewise, the client wrapper observes application calls, not automatically
generated lifecycle messages.

⚠️ The code uses documented FastMCP hooks, but I could not execute an end-to-end
test because FastMCP is not installed in this environment.

