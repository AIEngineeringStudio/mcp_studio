# FastMCP registration and dispatch

**Outcome:** Trace how a Python function becomes a discoverable MCP tool.

**Prerequisites:** [05: Tools and their contracts](05-tool-contracts.md).

## Why a registry exists

When a request names `get_ticket`, the server needs to locate its handler.
A component registry stores that association together with the metadata needed
for discovery and validation.

**Registration:**

> Adding a component and its contract to the server's known components.

**Dispatch:**

> Selecting and invoking the component that matches an incoming request.

```
Python function + annotations + description
                    |
                 decorator
                    |
                 registry
               /          \
        tools/list        tools/call
        description       validate --> handler --> result
```

Registration and execution happen at different times. Importing a module can
register its functions without executing their business operations.

## Read the lab declaration

The [server](../labs/server.py) creates `FastMCP("Ticket learning service")`
and applies `@mcp.tool` to `get_ticket`. The function's name, annotations,
and docstring contribute to the exposed tool contract. The body delegates to
ordinary application code.

The framework handles protocol parsing, component lookup, conversion between
data representations, and transport integration. It does not know which
customer is allowed to access a particular ticket unless the application
supplies and enforces that policy.

## Discovery and invocation share a definition

If registration never runs, the tool may be absent from discovery even though
its source file exists. Importing a different server instance can produce the
same symptom. The registry belongs to the object the application actually
serves.

A practical debugging order is to check the loaded module, the served server
instance, then the catalog returned by `list_tools()`. Only after that should
you investigate the handler's business logic.

## Keep implementation families distinct

This course's lab uses standalone `from fastmcp import FastMCP`. The archive
also contains the SDK v1 import `from mcp.server.fastmcp import FastMCP`.
The official SDK v2 uses `MCPServer`. These related implementations are not
interchangeable imports for a shared set of examples.

The [SDK migration guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md)
documents API changes. When adapting an old lesson, migrate a complete minimal
example and test it before combining snippets from different generations.

## The main guard

The server's `if __name__ == "__main__"` block starts its transport only when
the file is run directly. Importing it from the in-memory client registers
components without opening a listening socket or launching a second process.
This separation makes the same application reusable in several tests.

**Professional articulation:**

> “FastMCP turns component definitions into discoverable contracts and
> dispatches incoming operations to their handlers.”

## Sources and next step

- [Archive: definitions.md](../../definitions.md)
- [Archive: conversations/chatgpt/1_FirstMCPTool_InProcess.md](../../conversations/chatgpt/1_FirstMCPTool_InProcess.md)
- [Official reference](https://gofastmcp.com/docs/getting-started/welcome) — checked 2026-11-15.

Next: [The first client and in-memory testing](07-in-memory-client.md).

