# Why MCP exists

**Outcome:** Explain the integration problem MCP solves and when a direct function is sufficient.

**Prerequisites:** None.

## Begin with a real requirement

A support assistant needs the status of ticket T-100. The language model does
not own the ticket database. It needs an application to fetch the record and
return evidence it can use in an answer.

Start with the ordinary application function `lookup_ticket("T-100")`.
If one Python program is the only caller, a direct function call may satisfy
the entire requirement. MCP becomes useful when several AI applications need
to discover and call the same service through a common interface.

**Protocol:**

> A shared agreement about message structure, meaning, and valid interaction.
> A protocol allows independently built programs to communicate.

Without a common agreement, each host needs a different adapter for every
service. MCP standardizes the host-facing boundary. The server still needs
an adapter to its actual database or upstream API.

```text
Support host ----+
                 +---- MCP interface ---- Ticket server ---- Records
Developer host --+
```

The arrows mean requests and results, not direct database access by a model.
The ticket server remains responsible for validating inputs and controlling
access.

## Follow one lookup

1. The user asks for a ticket's status.
2. The host makes the available tool contract accessible to its model.
3. The model proposes a lookup with an ID.
4. The host checks its policy and uses an MCP client to send the call.
5. The server obtains the record and returns a result.
6. The host can give that result to the model to compose an answer.

The model's proposal and the server's execution are different events. A model
can propose an unavailable tool, malformed arguments, or an unauthorized action.
The receiving software must handle those cases.

## What MCP does and does not supply

MCP supplies a common way to expose tools, readable resources, and reusable
prompts. It does not itself create a reasoning loop, pick a model, guarantee a
correct answer, or grant permission to a user.

An existing REST API can remain the system of record. An MCP server can call
that API. Rewriting the business service is not a prerequisite for adopting
MCP. Likewise, a server can perform useful work without calling an LLM at all.

The common “universal connector” analogy describes interface compatibility.
It does not mean every host supports every feature or that all connected
services become trustworthy.

## Worked design choice

For a one-file arithmetic script, direct functions keep the design simple.
For a ticket service shared by three compatible hosts, a reusable MCP boundary
can reduce host-specific integration code. The benefit depends on reuse and
interoperability; an extra network service still adds deployment and failure
costs.

If ticket T-100 does not exist, the system should expose that failure as a
controlled result or error. It should not ask the model to invent a plausible
ticket.

**Professional articulation:**

> “MCP standardizes the interface between AI applications and external
> capabilities. Our service still owns the business rules and data access.”

## Sources and next step

- [Archive: conversations/chunks/01-mcp-chunk1.md](../../conversations/chunks/01-mcp-chunk1.md)
- [Archive: docs/mcp.md](../../docs/%5BDONE%5Dmcp.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28) — checked 2026-11-15.

Next: [Host, client, model, and server](02-host-client-server.md).

