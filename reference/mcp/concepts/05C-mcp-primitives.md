# Compare MCP tools, resources, and prompts

This is a supplemental comparison. For a first pass, read
[tool contracts](05-tool-contracts.md), [resources](09-resources.md), and
[prompts](10-prompts.md) in that order.

**Outcome:** Choose the correct MCP server primitive for a small requirement.

**Prerequisites:** [01: Why MCP exists](01-why-mcp.md).

## What “primitive” means

A **primitive** is a basic kind of component defined by the protocol. MCP
servers commonly publish three primitives:

```
Need to perform an operation?       -> tool
Need to read identified content?    -> resource
Need a reusable message template?   -> prompt
```

The categories describe caller intent. They are not security boundaries. A
server must still validate identity, permission, arguments, and data access.

## Tool: perform an operation

Use a tool when the caller needs the server to execute an operation.

```python
@mcp.tool
def get_ticket(ticket_id: str) -> dict:
    """Read one ticket by ID. Does not change it."""
    return lookup_ticket(ticket_id)
```

The main protocol operations are:

- `tools/list`: discover visible tools and their contracts;
- `tools/call`: invoke one named tool with arguments.

```
client -- tools/list ----------------> server
client <-- tool definitions ---------- server

client -- tools/call: get_ticket ----> server
client <-- tool result --------------- server
```

A read-only lookup can still be a tool when the caller's intent is “perform
this parameterized operation.” Tool descriptions and annotations can describe
side effects, but server code must enforce the real behavior.

## Resource: read content by URI

Use a resource when the caller needs content identified by an address.

**URI:**

> Uniform Resource Identifier. A string that identifies a resource, such as
> `ticket://T-100`. A URI is an identifier; it does not automatically mean the
> content is public or available through a web browser.

```python
import json


@mcp.resource("ticket://{ticket_id}")
def ticket_resource(ticket_id: str) -> str:
    """Read one ticket as JSON text."""
    return json.dumps(lookup_ticket(ticket_id))
```

The main protocol operations are:

- `resources/list`: discover fixed resources;
- `resources/templates/list`: discover parameterized URI patterns;
- `resources/read`: read content at one URI.

The `{ticket_id}` part is a resource-template parameter. The concrete URI
`ticket://T-100` identifies one result.

## Prompt: retrieve a reusable message template

Use a prompt when the server provides a reusable starting set of messages for
a host workflow.

```python
@mcp.prompt
def summarize_ticket(ticket_id: str) -> str:
    """Prepare instructions for summarizing a ticket."""
    return (
        f"Summarize ticket {ticket_id}. State its status and distinguish "
        "known facts from missing information."
    )
```

The main protocol operations are:

- `prompts/list`: discover prompt templates;
- `prompts/get`: retrieve a prompt with supplied arguments.

Retrieving the prompt returns messages. It does not by itself run a language
model. The host decides whether and how to use those messages.

## See all three in one server

```python
import json
from fastmcp import FastMCP

mcp = FastMCP("Ticket learning service")
TICKETS = {
    "T-100": {"id": "T-100", "status": "open"},
}


def lookup_ticket(ticket_id: str) -> dict:
    if ticket_id not in TICKETS:
        raise ValueError("Unknown ticket")
    return dict(TICKETS[ticket_id])


@mcp.tool
def get_ticket(ticket_id: str) -> dict:
    return lookup_ticket(ticket_id)


@mcp.resource("ticket://{ticket_id}")
def ticket_resource(ticket_id: str) -> str:
    return json.dumps(lookup_ticket(ticket_id))


@mcp.prompt
def summarize_ticket(ticket_id: str) -> str:
    return f"Summarize ticket {ticket_id} and state its status."
```

This is the same structure used in the [complete lab server](../fast-mcp-2026-07-28/labs/server.py).
Concept 07 provides the pinned environment and exact commands to run it.

## Choose by the user's intent

**“Look up T-100 as an operation and return structured fields.”**

> Choose a tool: `get_ticket(ticket_id="T-100")`.

**“Read the content identified by `ticket://T-100`.”**

> Choose a resource.

**“Give the host our recommended ticket-summary instructions.”**

> Choose a prompt.

The same underlying ticket service can support more than one primitive when
the user journeys are genuinely different. Do not publish duplicates merely to
use every MCP feature.

## Common beginner mistakes

**Mistake: calling `tools/list` to execute a tool.**

> `tools/list` discovers definitions. `tools/call` executes one selected tool.

**Mistake: assuming a resource is automatically safe because it is read-only.**

> Reading private data still requires authorization.

**Mistake: assuming `prompts/get` runs a model.**

> It retrieves messages. Model execution belongs to the host or another
> explicitly designed boundary.

**Say it professionally:**

> “Tools expose operations, resources expose addressable content, and prompts
> expose reusable message templates. We choose the primitive from the caller's
> intent and enforce security independently.”

Next: [FastMCP registration and dispatch](06-fastmcp-registry.md).
