# Tools and their contracts

**Outcome:** Design one narrow MCP tool and explain its name, description,
input schema, result, side effects, and failures.

**Prerequisites:**
[02: Host, model, client, and server](02-host-client-server.md) and
[03: JSON-RPC requests, responses, and notifications](03-json-rpc.md).

## A tool is more than a Python function

A Python function has executable code. An MCP tool also needs a contract that
another program can discover and understand.

**Contract:**

> An explicit agreement about valid input, expected output, behavior, and
> failure. The contract helps a caller use the operation without reading its
> source code.

For the ticket example, the operation is:

```text
get_ticket(ticket_id="T-100")
             |
             v
{"id": "T-100", "title": "Cannot sign in", "status": "open"}
```

A useful tool contract answers six questions:

1. What is the tool called?
2. When should a caller use it?
3. Which inputs are valid?
4. What result shape does it return?
5. Does it change anything?
6. How can it fail?

## Start with the ordinary business function

```python
TICKETS = {
    "T-100": {"id": "T-100", "title": "Cannot sign in", "status": "open"},
}


def lookup_ticket(ticket_id: str) -> dict:
    """Return one ticket or fail when the ID is unknown."""
    if ticket_id not in TICKETS:
        raise ValueError("Unknown ticket")
    return dict(TICKETS[ticket_id])
```

This function defines the business behavior. Returning `dict(...)` makes a
copy, so a caller cannot accidentally modify the stored fixture by changing the
returned dictionary.

## Publish a narrow tool

```python
from fastmcp import FastMCP

mcp = FastMCP("Ticket learning service")


@mcp.tool
def get_ticket(ticket_id: str) -> dict:
    """Read a support ticket by ID. Does not change the ticket."""
    return lookup_ticket(ticket_id)
```

FastMCP can use the function name, type hints, and docstring when it builds the
discoverable tool definition.

**Name:**

> `get_ticket` identifies the operation. Prefer a specific verb and noun over a
> vague name such as `ticket_action`.

**Description:**

> The docstring says what the tool reads and that it has no side effect. A side
> effect is a change outside the returned value, such as updating a record or
> sending an email.

**Type hint:**

> `ticket_id: str` says the argument is a string. The framework uses type
> information to help create and validate the input schema.

**Return value:**

> The dictionary gives callers stable, machine-readable fields.

## Schema validates structure, not truth

**Schema:**

> A machine-readable description of the allowed data shape. For example, a
> schema can require a property named `ticket_id` whose value is a string.

A simplified input schema looks like this:

```json
{
  "type": "object",
  "properties": {
    "ticket_id": {
      "type": "string"
    }
  },
  "required": ["ticket_id"]
}
```

The schema can reject a missing `ticket_id` or a number where a string is
required. It cannot prove that `T-100` exists or belongs to the current user.
Application code must enforce existence, authorization, and business rules.

```text
schema validation -> Is the request shaped correctly?
business validation -> Is the requested action valid and allowed?
```

## Prefer narrow tools

If callers only need to read a ticket, expose `get_ticket` rather than
`run_sql`. A narrow operation is easier to:

- describe accurately;
- validate;
- authorize;
- test;
- observe;
- change without breaking unrelated callers.

Narrow does not mean “one tool for every line of code.” It means the tool
represents a meaningful operation with a clear boundary.

## Return useful, bounded results

Return only fields the caller needs. Do not return a complete internal database
row containing secrets or unrelated personal data.

If a tool returns a list, define its maximum size and pagination behavior. If
clients depend on fields such as `id` and `status`, treat those names and types
as part of the contract.

Human-readable text can help a person, while structured content helps software.
Do not make clients parse sentences when stable fields are available.

## Define controlled failures

The business function raises `ValueError("Unknown ticket")` for `T-999`. The
framework translates Python behavior into its tool-result or protocol error
model according to the pinned API.

Do not assume every exception automatically becomes a safe user-facing error.
Production code should map expected domain failures deliberately and avoid
leaking stack traces, secrets, or internal database details.

Write operations need an additional rule: what happens when the change succeeds
but the response is lost? That problem needs an operation identity and retry
policy, introduced in concept 25.

## Inspect the discovered contract

After completing the [lab setup](../labs/README.md), the client can list tools:

```python
async with Client(mcp) as client:
    tools = await client.list_tools()
    for tool in tools:
        print(tool.name)
        print(tool.inputSchema)
```

The exact FastMCP client is imported and created in the complete
[lab client](../labs/client.py). Inspecting discovery distinguishes two
questions:

```text
Does my Python function work?
Does the server expose the contract I intended?
```

Both must be true.

## Contract checklist

Before publishing a tool, confirm:

- the name describes one meaningful operation;
- the description states purpose and important side effects;
- the input schema is narrow and typed;
- server code enforces business rules and authorization;
- the result is bounded and contains stable fields;
- expected failures are controlled and useful;
- retries cannot repeat unsafe side effects accidentally.

**Say it professionally:**

> “The tool schema validates request structure. The application service
> separately enforces business rules, authorization, and access to the requested
> record.”

## Sources and next step

- [Archived definitions](../../temp/definitions.md)
- [Archived in-process FastMCP example](../fastMcp-fastApi-uvicorn-ngnix-docker/1_FirstMCPTool_InProcess.md)
- [Archived tool notes](../fast-mcp/02-tools.md)
- [Official MCP tools reference](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)

Next: [FastMCP registration and dispatch](06-fastmcp-registry.md).
