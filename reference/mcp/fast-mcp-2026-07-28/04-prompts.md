# Lesson 4 — Prompts as reusable message templates

## Outcome

After this lesson, you can distinguish a prompt from a tool or resource and
trace `prompts/list` and `prompts/get` in the modern protocol.

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
    "arguments": {"ticket_id": "T-100"}
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

## FastMCP implementation

```python
from fastmcp import FastMCP

mcp = FastMCP("Ticket prompts")


@mcp.prompt
def triage_ticket(ticket_id: str) -> str:
    """Guide a support-ticket triage review."""
    return f"Review ticket {ticket_id} and identify the next action."
```

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

**Execution boundary:**

> In-memory MCP. The client performs prompt discovery and retrieval without
> launching a model or opening a network port.

Run the prompt-specific exercise from the repository root. It discovers the
prompt, renders it with an argument, and confirms that retrieval did not invoke
a model:

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python verify_primitives.py prompts
```

Expected output:

```
prompts: discovered summarize_ticket and rendered its message
prompts: no model was invoked
```

The complete runnable exercise is
[`verify_primitives.py`](../labs/verify_primitives.py).

Read [`../concepts/10-prompts.md`](../concepts/10-prompts.md) for a deeper trace.

**Say it professionally:**

> An MCP prompt is a discoverable, parameterized message template. Fetching it
> returns messages; it does not invoke a model or authorize an operation.

## Official references

- [Prompts](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts)
- [MRTR](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [FastMCP prompts](https://gofastmcp.com/servers/prompts)

