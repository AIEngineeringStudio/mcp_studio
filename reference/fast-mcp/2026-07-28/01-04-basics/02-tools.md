# Lesson 2 — Tools and executable contracts

## Outcome

After this lesson, you can design a tool contract, distinguish discovery from
execution, and classify protocol errors separately from tool execution errors.

## Say it professionally:

> An MCP tool has a discovery contract and an execution contract. JSON Schema
> constrains structure, while the implementation still enforces business rules,
> authorization, side-effect policy, and failure semantics.

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

```json
{
  "name": "lookup_ticket",
  "description": "Return one support ticket by its stable ticket ID.",
  "inputSchema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "ticket_id": {
        "type": "string",
        "pattern": "^T-[0-9]+$"
      }
    },
    "required": [
      "ticket_id"
    ],
    "additionalProperties": false
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "ticket_id": {
        "type": "string"
      },
      "status": {
        "enum": [
          "open",
          "closed"
        ]
      }
    },
    "required": [
      "ticket_id",
      "status"
    ]
  }
}
```

Schema validation answers “is this structurally valid?”
Business validation answers “is this operation allowed and meaningful?”
Keep both.

## The contract

A useful tool definition states a narrow name and description, an `inputSchema`,
an optional `outputSchema`, and useful annotations. Annotations are hints, not
security policy.

MCP `2026-07-28` supports JSON Schema Draft 2020-12 for `inputSchema` and
`outputSchema`. The input schema root remains an object, but it can use
references(`$ref`, `$defs`), composition(`oneOf`, `anyOf`, `allOf`), and
conditional validation(`if` / `then` / `else`).

We'll extend your `lookup_ticket` tool while keeping `ticket_id` required.

### **1. What each keyword does**

| Keyword                | Meaning                        | Example use                             |
|------------------------|--------------------------------|-----------------------------------------|
| `$defs`                | Define reusable schemas        | Define a ticket ID format               |
| `$ref`                 | Reference a schema             | Reuse the ticket ID definition          |
| `oneOf`                | Exactly one schema must match  | Ticket found **or** not found           |
| `anyOf`                | At least one schema must match | Include comments, history, or both      |
| `allOf`                | Every schema must match        | Combine base rules with detail rules    |
| `if` / `then` / `else` | Apply conditional rules        | Require extra options for a full lookup |

The key distinction is that `oneOf` rejects an instance matching two branches,
while `anyOf` accepts it.

### **2. Complete MCP tool definition**

This example keeps the original ticket lookup behavior but adds a full-detail
mode.

```json
{
  "name": "lookup_ticket",
  "description": "Return one support ticket by its stable ticket ID.",
  "inputSchema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "$defs": {
      "ticketId": {
        "type": "string",
        "pattern": "^T-[0-9]+$"
      },
      "ticketRequest": {
        "type": "object",
        "properties": {
          "ticket_id": {
            "$ref": "#/$defs/ticketId"
          }
        },
        "required": [
          "ticket_id"
        ]
      }
    },
    "properties": {
      "detail_level": {
        "enum": [
          "summary",
          "full"
        ]
      },
      "include_comments": {
        "const": true
      },
      "include_history": {
        "const": true
      }
    },
    "allOf": [
      {
        "$ref": "#/$defs/ticketRequest"
      },
      {
        "if": {
          "properties": {
            "detail_level": {
              "const": "full"
            }
          },
          "required": [
            "detail_level"
          ]
        },
        "then": {
          "anyOf": [
            {
              "required": [
                "include_comments"
              ]
            },
            {
              "required": [
                "include_history"
              ]
            }
          ]
        },
        "else": {
          "not": {
            "anyOf": [
              {
                "required": [
                  "include_comments"
                ]
              },
              {
                "required": [
                  "include_history"
                ]
              }
            ]
          }
        }
      }
    ],
    "unevaluatedProperties": false
  },
  "outputSchema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "ticket_id": {
        "type": "string",
        "pattern": "^T-[0-9]+$"
      }
    },
    "required": [
      "ticket_id"
    ],
    "oneOf": [
      {
        "properties": {
          "found": {
            "const": true
          },
          "status": {
            "enum": [
              "open",
              "closed"
            ]
          },
          "comments": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "history": {
            "type": "array",
            "items": {
              "type": "string"
            }
          }
        },
        "required": [
          "found",
          "status"
        ]
      },
      {
        "properties": {
          "found": {
            "const": false
          },
          "error": {
            "const": "NOT_FOUND"
          }
        },
        "required": [
          "found",
          "error"
        ]
      }
    ],
    "unevaluatedProperties": false
  }
}
```

### **3. Example requests**

**Valid: summary lookup**

```json
{
  "ticket_id": "T-42"
}
```

The ticket ID is valid. No full-detail options are needed.

**Valid: full lookup**

```json
{
  "ticket_id": "T-42",
  "detail_level": "full",
  "include_comments": true,
  "include_history": true
}
```

Both flags are accepted because `anyOf` means at least one, not exactly one.

**Invalid: full lookup without a section**

```json
{
  "ticket_id": "T-42",
  "detail_level": "full"
} 
```

Fails the conditional `then` rule because neither `include_comments` nor
`include_history` is present.

## **4. Example output**

If the ticket is found:

```json

{
  "ticket_id": "T-42",
  "found": true,
  "status": "open",
  "comments": [
    "Customer requested an update."
  ],
  "history": [
    "Ticket created",
    "Assigned to support"
  ]
}

```

If the ticket is not found:

```json

{
  "ticket_id": "T-42",
  "found": false,
  "error": "NOT_FOUND"
}

```

The `oneOf` rule enforces the two distinct result shapes. A successful result
must include `status`; a not-found result must include `error`.

### **5. Important design detail**

Notice that the example uses:

```
"unevaluatedProperties": false
```

rather than your original:

```
"additionalProperties": false
```

When `allOf` and `$ref` compose object schemas, `additionalProperties` may
reject properties declared in another subschema. `unevaluatedProperties` can
recognize properties successfully evaluated through the composition.

Also, JSON Schema validates structure. It does not implement the lookup,
automatically choose summary behavior, or control authorization. The MCP server
must enforce those behaviors.

**References:**
[MCP 2026-07-28 — Tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools?utm_source=chatgpt.com)
and [JSON Schema — Composition keywords](https://json-schema.org/understanding-json-schema/reference/combining?utm_source=chatgpt.com).

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
    "arguments": {
      "ticket_id": "T-100"
    }
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "resultType": "complete",
    "content": [
      {
        "type": "text",
        "text": "T-100 is open"
      }
    ],
    "structuredContent": {
      "ticket_id": "T-100",
      "status": "open"
    },
    "isError": false
  }
}
```

`content` is the content-block representation.
`structuredContent` is the machine-friendly object associated with
`outputSchema`.

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

## HTTP routing metadata

Modern Streamable HTTP sends `Mcp-Method` on every request and `Mcp-Name` for
`tools/call`, `resources/read`, and `prompts/get`. A tool schema may use
`x-mcp-header` to mirror selected primitive arguments into `Mcp-Param-*`
headers. This is routing metadata, not a substitute for request-body validation
or authorization.

## Hands-on checkpoint

### FastMCP implementation

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

### Follow the local ticket example

The runnable [server](labs/server.py) uses a simpler contract than the extended
`lookup_ticket` schema above. It stores two synthetic records in `TICKETS`.
`lookup_ticket(ticket_id)` is a plain domain function; `@mcp.tool` exposes the
wrapper `get_ticket(ticket_id: str) -> dict` to MCP. The same domain function
also serves the resource template, so both paths read the same records.

The [client check](labs/verify_primitives.py) calls `client.list_tools()`, finds
`get_ticket`, and checks that its generated `input_schema` requires
`ticket_id`. It then calls
`client.call_tool("get_ticket", {"ticket_id": "T-100"})`. FastMCP validates
the argument, calls the wrapper, and returns the record:

```json
{
  "id": "T-100",
  "title": "Cannot sign in",
  "status": "open"
}
```

The check reads the parsed object from `result.data` and prints the text
content from `result.content[0].text`. The generated output schema is a broad
object because the function declares `dict` without a specific value shape;
it does not enforce the `id`, `title`, and `status` fields shown here. A typed
result model would make that contract stricter. An unknown ID raises
`ValueError` in `lookup_ticket`; this local check covers only the successful
call, not the failure path or authorization.

The script also prints the actual generated schemas and the ticket JSON. Its
`--transport stdio` option starts the adjacent `server.py` as a subprocess;
`--transport http` expects that server already running at
`http://127.0.0.1:8000/mcp`. The `--focus tools` choice runs only this check.

Read [
`../concepts/05-tool-contracts.md`](../../../mcp/concepts/05-tool-contracts.md) for
the deeper contract-design lesson.

## Official references

- [Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [Schema reference](https://modelcontextprotocol.io/specification/2026-07-28/schema)
- [FastMCP tools](https://gofastmcp.com/servers/tools)

