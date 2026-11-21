# Lesson 2 — Tools and executable contracts

## Outcome

After this lesson, you can design a tool contract, distinguish discovery from
execution, and classify protocol errors separately from tool execution errors.

## A tool has two planes

```
Discovery                         Execution
---------                         ---------
tools/list                        tools/call
name + description                arguments
input/output schema               complete or input_required result
annotations                       isError for execution failure
```

A tool is model-controlled: a model can select it based on its description and
schema. The host should still provide visibility and user control for sensitive
or consequential calls.

## The contract

A useful tool definition states a narrow name and description, an `inputSchema`,
an optional `outputSchema`, and useful annotations. Annotations are hints, not
security policy.

MCP `2026-07-28` supports full JSON Schema 2020-12 for tool input and output
schemas. The input schema root remains an object, but it may use `$ref`,
`$defs`, `oneOf`, `anyOf`, `allOf`, and conditionals.

```json
{
  "name": "lookup_ticket",
  "description": "Return one support ticket by its stable ticket ID.",
  "inputSchema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "ticket_id": {"type": "string", "pattern": "^T-[0-9]+$"}
    },
    "required": ["ticket_id"],
    "additionalProperties": false
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "ticket_id": {"type": "string"},
      "status": {"enum": ["open", "closed"]}
    },
    "required": ["ticket_id", "status"]
  }
}
```

Schema validation answers “is this structurally valid?” Business validation
answers “is this operation allowed and meaningful?” Keep both.

## Listing and caching

Modern list results include `resultType: "complete"` and must carry cache hints:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "complete",
    "tools": [],
    "ttlMs": 300000,
    "cacheScope": "public"
  }
}
```

Tool lists must not vary because of hidden connection state. They may vary by
the authorization attached to the request. Use deterministic ordering to make
client and model prompt caches stable.

## Calling a tool

The repeated modern `_meta` block is omitted here for readability; it remains
required in the request.

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "lookup_ticket",
    "arguments": {"ticket_id": "T-100"}
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "resultType": "complete",
    "content": [{"type": "text", "text": "T-100 is open"}],
    "structuredContent": {"ticket_id": "T-100", "status": "open"},
    "isError": false
  }
}
```

`content` is the content-block representation. `structuredContent` is the
machine-friendly object associated with `outputSchema`.

## Error layers

**Protocol error:**

> The request cannot be parsed or dispatched, such as an unknown method or
> invalid MCP parameters. Return a JSON-RPC error.

**Tool execution error:**

> The tool ran but could not complete its domain operation. Return a normal
> tool result with `resultType: "complete"` and `isError: true`, so the model
> can inspect the failure.

Never use `isError: false` to signal failure. Never reveal internal stack
traces or secrets in model-visible content.

## FastMCP implementation

```python
from typing import Literal

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP("Ticket server")


class Ticket(BaseModel):
    ticket_id: str = Field(pattern=r"^T-[0-9]+$")
    status: Literal["open", "closed"]


@mcp.tool
def lookup_ticket(ticket_id: str) -> Ticket:
    """Return one synthetic ticket by its stable ticket ID."""
    return Ticket(ticket_id=ticket_id, status="open")
```

FastMCP derives schemas from type hints and Pydantic, but you still own the
tool's semantics, authorization, idempotency, and side effects.

## HTTP routing metadata

Modern Streamable HTTP sends `Mcp-Method` on every request and `Mcp-Name` for
`tools/call`, `resources/read`, and `prompts/get`. A tool schema may use
`x-mcp-header` to mirror selected primitive arguments into `Mcp-Param-*`
headers. This is routing metadata, not a substitute for request-body validation
or authorization.

## Hands-on checkpoint

**Execution boundary:**

> In-memory MCP. This isolates tool discovery, schema validation, dispatch, and
> error behavior from process and network concerns.

Run the tool-specific exercise from the repository root. It inspects the
generated input schema and calls the discovered tool:

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python verify_primitives.py tools
```

Expected output:

```
tools: discovered get_ticket and called it successfully
```

Then run the negative contract checks. They prove that a missing required
argument and an unknown business record fail through different validation
paths:

```bash
uv run python -m unittest -q test_protocol
```

The complete runnable exercise is
[`verify_primitives.py`](../labs/verify_primitives.py).

Read [`../concepts/05-tool-contracts.md`](../concepts/05-tool-contracts.md) for
the deeper contract-design lesson.

**Say it professionally:**

> An MCP tool has a discovery contract and an execution contract. JSON Schema
> constrains structure, while the implementation still enforces business rules,
> authorization, side-effect policy, and failure semantics.

## Official references

- [Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [Schema reference](https://modelcontextprotocol.io/specification/2026-07-28/schema)
- [FastMCP tools](https://gofastmcp.com/servers/tools)

