# Why MCP exists

**Outcome:** Explain the integration problem MCP solves and decide when a
direct function call is simpler.

**Prerequisites:** [Start here: the MCP mental model](00-intro.md).

## Start with the user's need

A user asks a support assistant:

> “Is ticket T-100 still open?”

The language model does not own the ticket records. Some application code must
look up the ticket and return trustworthy data.

In one Python program, the simplest solution is a direct function call:

```python
TICKETS = {
    "T-100": {"id": "T-100", "title": "Cannot sign in", "status": "open"},
}


def lookup_ticket(ticket_id: str) -> dict:
    if ticket_id not in TICKETS:
        raise ValueError("Unknown ticket")
    return dict(TICKETS[ticket_id])


ticket = lookup_ticket("T-100")
print(ticket["status"])
```

Expected output:

```
open
```

No protocol is needed here. The caller already knows the function's name, its
argument, its return value, and how to execute it.

## The integration problem appears when programs separate

Now suppose several AI applications need the same lookup. The ticket service
may be maintained by another team or run in another process.

> How does an AI application/agent communicate with external tools in real time?

Without a shared protocol, every application needs custom answers to questions
such as:

- How does it discover the available operation?
- What argument does the operation accept?
- How does it send a call?
- How does it recognize a result or error?
- How does the request travel to the other program?

```
Support app   ---- custom adapter A ---- Ticket service
IDE assistant ---- custom adapter B ---- Ticket service
Chat app      ---- custom adapter C ---- Ticket service
```

An **adapter** is code that translates between two interfaces. Adapters are not
bad, but a different adapter for every pair of programs creates repeated work
and inconsistent behavior.

## MCP provides a common boundary

MCP stands for **Model Context Protocol**. It is an agreement that lets an MCP
client and MCP server describe and exchange tools, resources, prompts, and
related results in a standard way.

```
Support app   -- MCP client --+
IDE assistant -- MCP client --+-- MCP boundary -- Ticket server -- Records
Chat app      -- MCP client --+
```

The server still needs code that talks to its database or upstream API. MCP
standardizes the host-facing communication; it does not replace business logic
or data storage.

**Plain English:**

> MCP gives compatible applications a shared way to ask, “What can you do?”
> and then request one of those operations with structured input.




## Follow one ticket lookup

```
User -> Host -> Model proposes a tool call
              Host approves and uses its MCP client
                       |
                       v
                 MCP server -> ticket service -> record
                       |
                       v
                 structured result -> Host -> answer
```

The steps are:

1. The user asks for ticket `T-100`.
2. The host makes the `get_ticket` tool description available to the model.
3. The model proposes `get_ticket(ticket_id="T-100")`.
4. The host applies its policy and asks its MCP client to send the call.
5. The MCP server validates the input and calls the ticket code.
6. The server returns data; the host decides how to use it in the answer.

The model's proposal is not execution. The host and server remain responsible
for permission checks, validation, and controlled failure behavior.

## The business function and MCP wrapper stay separate

FastMCP can publish the ordinary Python function through an MCP tool:

```python
from fastmcp import FastMCP

mcp = FastMCP("Ticket learning service")


def lookup_ticket(ticket_id: str) -> dict:
    if ticket_id != "T-100":
        raise ValueError("Unknown ticket")
    return {"id": ticket_id, "status": "open"}


@mcp.tool
def get_ticket(ticket_id: str) -> dict:
    """Read a support ticket by ID. Does not change the ticket."""
    return lookup_ticket(ticket_id)
```

`lookup_ticket` contains the application behavior. `get_ticket` is the MCP
entry point. Keeping the two separate lets you test the business function
without running an MCP client.

This snippet is a concept preview. The tested, pinned project and exact run
commands begin in [concept 07](07-in-memory-client.md).

## What MCP does not do

MCP does not automatically:

- run a language model;
- decide when a model should call a tool;
- make a tool safe or correct;
- authenticate a user or grant permission;
- replace the ticket database or existing REST API.

An MCP server can call an existing REST API. A useful MCP server can also work
without calling a language model.

The common “universal connector” analogy is useful only for interface
compatibility. It does not mean every host supports every feature, or that a
connected server should automatically be trusted.

## When not to add MCP

Use a direct function when one program is the only caller and no standard
integration boundary is needed. MCP adds setup, compatibility decisions, and
new failure points, especially across a process or network.

Consider MCP when independently built AI applications need a reusable,
discoverable interface to the same capabilities.

**Decision rule:**

> Start with the direct function. Add MCP when reuse across compatible hosts or
> process boundaries provides enough value to justify the extra boundary.

## One important failure

If ticket `T-999` does not exist, the server should return a controlled failure.
It should not ask the model to invent a likely status. MCP structures the
interaction; the application still defines what “ticket not found” means.

**Say it professionally:**

> “MCP standardizes the interface between AI applications and external
> capabilities. Our service still owns business rules, authorization, and data
> access.”

## Sources and next step

- [Archived MCP introduction](../fast-mcp/01-what-mcp-is.md)
- [Archived MCP learning guide](../../temp/mcp_learning_guide.md)
- [Official MCP specification](https://modelcontextprotocol.io/specification/2026-07-28)

Next: [Host, client, model, and server](02-host-client-server.md).
