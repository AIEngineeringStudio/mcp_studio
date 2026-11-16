# Tools and their contracts

**Outcome:** Design a narrow tool with a clear input, result, side effect, and failure contract.

**Prerequisites:** [02: Host, client, model, and server](02-host-client-server.md), [03: JSON-RPC requests, responses, and notifications](03-json-rpc.md).

## Begin with the operation

Our requirement is to read one ticket by its identifier. A good contract names
the operation, describes its purpose, defines valid arguments, and explains
what callers can expect.

```text
get_ticket(ticket_id="T-100")
           |
           v
{"id":"T-100", "title":"Cannot sign in", "status":"open"}
```

The tool name helps selection. The description explains intent and side
effects. The input schema describes acceptable structure. The handler performs
the operation. These pieces work together; none replaces the others.

## Schema versus business rules

A schema can require `ticket_id` to be a string. That does not prove the
ticket exists or belongs to the caller. Application code enforces existence,
authorization, and domain constraints.

Use a narrow operation such as `get_ticket` instead of an unrestricted
`run_sql` when callers only need a ticket lookup. The narrower contract is
easier to explain, validate, authorize, and test.

In the [lab server](../learning/labs/server.py), the decorated handler delegates to
`lookup_ticket`. The function returns a copy of the fixture record, so a
caller cannot mutate the stored dictionary merely by changing its result.

## Results must be usable

A tool result may include human-readable content and structured data. Keep
machine-readable fields stable when clients depend on them. If an operation
returns a list, make size and pagination behavior explicit. Avoid returning
an entire database record containing fields the user does not need.

A description such as “Read a synthetic support ticket by ID; does not change
the ticket” tells the caller more than “Ticket function.” Tool annotations
can provide hints, but the service must still enforce behavior.

## Failure example

For `ticket_id="missing"`, our domain function raises a controlled exception.
The framework translates failures according to its API. A library may provide
a dedicated tool-error type for user-facing messages; do not assume every
Python exception or arbitrary dictionary becomes a correctly flagged tool
error.

For a write operation, define what happens if the write succeeds but the
response is lost. That requires an operation identity and retry design,
introduced later.

## Inspect the real contract

Run the supplied in-memory client after following the lab setup. It lists
tools before calling `get_ticket`. Inspect the discovered schema when a
client reports invalid arguments. This distinguishes “the function is correct”
from “the exposed contract matches the caller.”

**Professional articulation:**

> “The tool schema validates request structure. The application service
> separately enforces business rules and access to the requested record.”

## Sources and next step

- [Archive: definitions.md](../../definitions.md)
- [Archive: conversations/chatgpt/1_FirstMCPTool_InProcess.md](../../conversations/chatgpt/1_FirstMCPTool_InProcess.md)
- [Archive: conversations/chunks/05-mcp-chunk5.md](../../conversations/chunks/05-mcp-chunk5.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) — checked 2026-11-15.

Next: [FastMCP registration and dispatch](06-fastmcp-registry.md).

