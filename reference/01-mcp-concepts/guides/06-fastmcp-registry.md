# FastMCP registration and dispatch

**Outcome:** Trace how FastMCP turns a Python function into a discoverable tool
and later dispatches a call to that function.

**Prerequisites:** [05: Tools and their contracts](05-tool-contracts.md).

## Begin with the problem the framework solves

The MCP server receives a request naming `get_ticket`. It needs to answer two
questions:

1. What contract should discovery return for `get_ticket`?
2. Which Python function should run when that tool is called?

A **registry** stores component names, contracts, and handlers so the server can
answer both questions.

```
Python function + type hints + docstring
                    |
                    | registration
                    v
                registry
               /        \
      tools/list          tools/call
      returns contract    validate -> select handler -> run -> return result
```

**Registration:**

> Adding a component and its contract to the server's registry.

**Discovery:**

> Reading registered contracts so a caller can learn what is available.

**Dispatch:**

> Matching an incoming component name to its registered handler and invoking
> that handler after validation.

Registration and execution happen at different times.

## Watch registration happen

```python
from fastmcp import FastMCP

mcp = FastMCP("Ticket learning service")


@mcp.tool
def get_ticket(ticket_id: str) -> dict:
    """Read one ticket by ID. Does not change it."""
    return {"id": ticket_id, "status": "open"}
```

Read this from top to bottom:

1. `FastMCP(...)` creates one server object and its component registries.
2. Python defines the `get_ticket` function.
3. `@mcp.tool` registers that function on this particular `mcp` object.
4. Registration records information used for discovery and later dispatch.
5. The function body has not performed a ticket lookup yet.

The decorator changes how the function is exposed; it does not cause every
import to run the tool's business operation.

## Trace discovery and invocation separately

During discovery:

```
client -> tools/list -> registry -> get_ticket contract -> client
```

During invocation:

```
client -> tools/call(name="get_ticket", arguments={...})
       -> validate arguments
       -> registry selects handler
       -> Python function runs
       -> result returns to client
```

If discovery does not include the tool, debugging the function body is too
early. The dispatcher cannot call a component it does not know.

## Inspect the real registry through a client

The supported public behavior to inspect is discovery:

```python
from fastmcp import Client


async def show_tools() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        for tool in tools:
            print(tool.name)
```

The complete runnable client in [concept 07](07-in-memory-client.md) also calls
the tool and verifies the returned status.

Avoid depending on undocumented internal registry attributes. Public client
behavior is a more stable test of what the server actually exposes.

## The server instance matters

This bug creates two different server objects:

```python
from fastmcp import FastMCP

registered_server = FastMCP("Registered here")
served_server = FastMCP("Served here")


@registered_server.tool
def get_ticket(ticket_id: str) -> dict:
    return {"id": ticket_id}
```

If the runtime serves `served_server`, `get_ticket` is absent. Its source code
exists, but it was registered on another object.

When a tool is missing, check in this order:

1. Was the module containing the decorator imported?
2. Did registration finish without an exception?
3. Was the tool registered on the server object actually being served?
4. Does `list_tools()` return it?
5. Only then inspect call arguments and handler behavior.

## Separate import from starting a transport

The lab ends with:

```python
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

When Python runs `server.py` directly, `__name__` is `"__main__"`, so the
transport starts. When a test imports `server`, registration still happens,
but this guarded block does not start a child process or network listener.

That separation lets the same server object support:

- a fast in-memory test;
- a local `stdio` child process;
- a Streamable HTTP service.

The contracts remain the same while the execution boundary changes.

## Framework and application responsibilities

FastMCP handles protocol parsing, component discovery, input conversion,
dispatch, result conversion, and transport integration.

FastMCP cannot infer which customer may read `T-100`. Your application must
supply verified identity, authorization rules, and business validation.

```
FastMCP:      Is this a valid call to a registered component?
Application:  Is this caller allowed to perform this business operation?
```

## Do not mix implementation families

This course uses standalone FastMCP:

```python
from fastmcp import FastMCP
```

Older examples may use SDK v1:

```python
from mcp.server.fastmcp import FastMCP
```

The official Python SDK v2 uses another high-level API surface. These examples
are related but not interchangeable line by line. Choose one pinned
implementation, follow its documentation, and test a complete minimal example
before copying features from another generation.

**Say it professionally:**

> “FastMCP registers component contracts for discovery and dispatches incoming
> operations to their handlers. Our application remains responsible for
> business rules and authorization.”

## Sources and next step

- [Archived definitions](../../../_archive/temp/definitions.md)
- [Archived in-process FastMCP example](../fastMcp-fastApi-uvicorn-ngnix-docker/1_FirstMCPTool_InProcess.md)
- [Official FastMCP getting-started guide](https://gofastmcp.com/docs/getting-started/welcome)
- [Official Python SDK migration guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md)

Next: [The first client and in-memory testing](07-in-memory-client.md).
