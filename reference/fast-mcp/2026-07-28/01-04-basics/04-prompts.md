# Lesson 4 — Prompts as reusable message templates

## Outcome

After this lesson, you can distinguish a prompt from a tool or resource and
trace `prompts/list` and `prompts/get` in the modern protocol.

## **Say it professionally:**

> An MCP prompt is a discoverable, parameterized message template. Fetching it
> returns messages; it does not invoke a model or authorize an operation.

## A prompt is a definition, then a rendered result

```
Prompt definition                 Rendered prompt
-----------------                 ---------------
name                              description
description                       messages
argument declarations      --->   text or other content blocks
```

Prompts are user-controlled or application-selected templates. Retrieving a
prompt does not execute a model. The host decides whether and how the returned
messages are used.

## Choose the right primitive

**Tool:**

> Performs an operation or computes a result.

**Resource:**

> Reads addressable context identified by a URI.

**Prompt:**

> Produces reusable messages that guide a model or user workflow.

Do not hide business side effects inside a prompt. Do not use prompts as an
authorization boundary; model instructions are not enforcement.

## Protocol flow

The repeated modern request `_meta` is omitted here for readability.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "prompts/get",
  "params": {
    "name": "triage_ticket",
    "arguments": {
      "ticket_id": "T-100"
    }
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "complete",
    "description": "Guide a support-ticket triage review",
    "messages": [
      {
        "role": "user",
        "content": {
          "type": "text",
          "text": "Review ticket T-100 and identify the next action."
        }
      }
    ]
  }
}
```

Prompt messages use `user` or `assistant` roles. MCP does not define a
`system` role for `PromptMessage`. A host may combine the result with its own
model-specific system instructions.

Prompt argument declarations are simpler than a tool's JSON Schema contract.
FastMCP may offer richer Python typing, but do not assume every generated
constraint is represented identically on the wire.

## Multi-round prompt retrieval

`prompts/get` is one of only three core requests that may return an
`InputRequiredResult`; the others are `resources/read` and `tools/call`. If
additional user input is needed, use the MRTR flow from lesson 7. Do not suspend
a handler while sending a server-initiated request on a modern connection.

## List changes and caching

`prompts/list` returns `resultType: "complete"` and must provide `ttlMs` and
`cacheScope`. If the prompt catalog changes, modern clients can opt into
`promptsListChanged` through `subscriptions/listen`.

## Prompt-injection boundary

A prompt is untrusted content from the host's perspective, especially when it
includes external data. Hosts should visibly identify its source and preserve
user control. Servers must still enforce all authorization and data policy in
code.

## Hands-on checkpoint

### FastMCP implementation

```python
from fastmcp import FastMCP

mcp = FastMCP("Ticket prompts")


@mcp.prompt
def triage_ticket(ticket_id: str) -> str:
    """Guide a support-ticket triage review."""
    return f"Review ticket {ticket_id} and identify the next action."
```

### Follow the local ticket example

The runnable [server](labs/server.py) registers
`summarize_ticket(ticket_id: str) -> str` with `@mcp.prompt`. This is a
different prompt from the illustrative `triage_ticket` above. The function
formats an instruction using the ID; it does not call `lookup_ticket`, read a
resource, or invoke a model.

The [client check](labs/verify_primitives.py) calls `client.list_prompts()`,
finds
`summarize_ticket`, and prints its declared required `ticket_id` argument.
It then calls:

```python
result = await client.get_prompt(
    "summarize_ticket", {"ticket_id": "T-100"}
)
```

FastMCP turns the returned string into one `user` message. The client prints
its text:

```text
Summarize ticket T-100 using the provided ticket data. State its status and distinguish facts from missing information.
```

The words “provided ticket data” do not cause a ticket read. The host must
provide ticket data separately, for example by reading `ticket://T-100`, and
decide whether to send both the data and this message to a model. A prompt
parameter is not an authorization check for the ticket.

From the repository root, run the example files beside this guide. The pinned
environment comes from `../labs/pyproject.toml` and its lockfile:

Expected output:

```
prompts: discovered summarize_ticket and rendered its message
prompts: no model was invoked
```

The script also prints the prompt description, argument declaration, role,
and text. `--transport stdio` starts the adjacent `server.py` as a subprocess;
`--transport http` expects it already running at
`http://127.0.0.1:8000/mcp`.

### How to run

```bash
cd reference/mcp/fast-mcp-2026-07-28
UV_CACHE_DIR=../labs/.uv-cache uv run --project ../labs --locked python verify_primitives.py --transport in-memory --focus prompts
```

Read [`../concepts/10-prompts.md`](../../../mcp/concepts/10-prompts.md) for a deeper
trace.

## Official references

- [Prompts](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts)
- [MRTR](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [FastMCP prompts](https://gofastmcp.com/servers/prompts)

