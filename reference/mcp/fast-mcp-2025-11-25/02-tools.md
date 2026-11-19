We’ll keep it **protocol-first → raw wire behavior → FastMCP abstraction →
design reasoning → professional vocabulary**.

# Lesson 2 — MCP Tools in Depth

By the end, you should be able to explain this pipeline without treating
`@mcp.tool` as magic:

```
Python function
      │
      ▼
FastMCP Tool
      │
      ├── name
      ├── description
      ├── inputSchema
      ├── outputSchema
      └── annotations
      │
      ▼
tools/list
      │
      ▼
Client / model discovers contract
      │
      ▼
tools/call
      │
      ▼
input validation
      │
      ▼
function execution
      │
      ▼
CallToolResult
      ├── content
      ├── structuredContent
      └── isError
```

MCP tools are **model-controlled server capabilities**. Servers advertise them
through `tools/list`; clients invoke them through `tools/call`. A server
supporting tools must declare the `tools` capability, and tool-list changes can
optionally be advertised through
`notifications/tools/list_changed`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

---

# 1. First principle: a tool has two separate concerns

Do not mentally model a tool simply as:

```
function
```

There are really two planes.

```
                 MCP TOOL

       DISCOVERY                    EXECUTION
           │                            │
           ▼                            ▼
      tools/list                    tools/call
           │                            │
           ▼                            ▼
   Tool definition                Arguments
           │                            │
    ┌──────┼───────┐                    ▼
    │      │       │              Tool implementation
  name   schema metadata                 │
                                        ▼
                                  CallToolResult
```

### Discovery plane

The client asks:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

The server returns **descriptions of capabilities**, not the functions
themselves. `tools/list` is also
pageable. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

### Execution plane

Later:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "check_inventory",
    "arguments": {
      "sku": "ABC-1001"
    }
  }
}
```

The important separation is:

> `tools/list` describes the contract.  
> `tools/call` executes against that contract.

Professional phrasing:

> “MCP separates tool discovery from tool invocation.”

---

# 2. What exactly is a Tool?

Let's build one slightly more realistic than `add()`.

Our requirement:

```
check_inventory(sku)
```

Given:

```
ABC-1001
```

return:

```json
{
  "sku": "ABC-1001",
  "in_stock": true,
  "available_units": 27
}
```

At protocol level, the tool definition could look like:

```json
{
  "name": "check_inventory",
  "title": "Check Inventory",
  "description": "Check available inventory for a product SKU.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "sku": {
        "type": "string",
        "pattern": "^[A-Z]{3}-[0-9]{4}$",
        "description": "Product SKU such as ABC-1001"
      }
    },
    "required": [
      "sku"
    ],
    "additionalProperties": false
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "sku": {
        "type": "string"
      },
      "in_stock": {
        "type": "boolean"
      },
      "available_units": {
        "type": "integer"
      }
    },
    "required": [
      "sku",
      "in_stock",
      "available_units"
    ]
  },
  "annotations": {
    "readOnlyHint": true,
    "idempotentHint": true,
    "openWorldHint": false
  }
}
```

The stable MCP tool definition supports fields including `name`, optional
`title`, `description`, `icons`, `inputSchema`, optional `outputSchema`,
`annotations`, and execution metadata. Input and output schemas are JSON Schema;
absent an explicit `$schema`, MCP uses JSON Schema 2020-12 by
default. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

---

# 3. `inputSchema` is your real API contract

This is one of the most important MCP design ideas.

Consider:

```json
{
  "type": "object",
  "properties": {
    "sku": {
      "type": "string"
    }
  },
  "required": [
    "sku"
  ]
}
```

That tells the client:

```
sku exists
+
sku must be a string
```

But compare:

```json
{
  "type": "object",
  "properties": {
    "sku": {
      "type": "string",
      "pattern": "^[A-Z]{3}-[0-9]{4}$",
      "description": "Product SKU such as ABC-1001"
    }
  },
  "required": [
    "sku"
  ],
  "additionalProperties": false
}
```

Now we have expressed:

```
TYPE
string

CONSTRAINT
specific format

SEMANTICS
this represents a product SKU

EXAMPLE
ABC-1001

STRICTNESS
don't invent extra arguments
```

That is substantially better for both machine validation and model tool use.

## Design rule

Your schema should encode everything that is **structurally knowable before
execution**.

Bad:

```python
sku: str
```

followed by 20 lines of manual validation.

Better:

```
schema:
  string
  required
  correct pattern
  useful description
```

Then reserve business logic for facts that cannot be expressed structurally:

```
Does ABC-1001 actually exist?
```

JSON Schema cannot answer that.

---

# 4. Schema validation vs business validation

Keep these separate.

Suppose the model sends:

```json
{
  "sku": "hello"
}
```

That's a **schema/input validation problem**.

But:

```json
{
  "sku": "XYZ-9999"
}
```

may satisfy the schema perfectly while referring to a nonexistent product.

That's a **domain/business validation problem**.

```
                 validation
                     │
          ┌──────────┴──────────┐
          │                     │
     structural             semantic
     validation             validation
          │                     │
   JSON Schema          business logic
          │                     │
 "Is this shaped         "Does this SKU
 correctly?"              actually exist?"
```

Professional vocabulary:

- **structural validation**
- **schema validation**
- **semantic validation**
- **domain validation**
- **business-rule validation**

---

# 5. Why descriptions matter

Suppose you expose:

```json
{
  "name": "search"
}
```

What does it search?

Files?

Customers?

Git?

Internet?

Invoices?

A model must infer when a tool is appropriate largely from its contract.

Better:

```
Search the internal product catalog by SKU or product name.
Does not search external marketplaces.
```

That description establishes both:

```
positive scope
+
negative boundary
```

This is good tool design.

FastMCP can derive the tool description and parameter descriptions from
docstrings, and explicit `Annotated`/`Field` descriptions can be used to control
parameter metadata. [FastMCP](https://gofastmcp.com/servers/tools)

---

# 6. Protocol-level execution

Now the client calls:

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "tools/call",
  "params": {
    "name": "check_inventory",
    "arguments": {
      "sku": "ABC-1001"
    }
  }
}
```

The server performs roughly:

```
lookup tool
     │
     ▼
validate arguments
     │
     ▼
execute implementation
     │
     ▼
serialize result
     │
     ▼
CallToolResult
```

---

# 7. `content` versus `structuredContent`

This distinction is fundamental.

A successful response might be:

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"sku\":\"ABC-1001\",\"in_stock\":true,\"available_units\":27}"
      }
    ],
    "structuredContent": {
      "sku": "ABC-1001",
      "in_stock": true,
      "available_units": 27
    },
    "isError": false
  }
}
```

MCP defines `structuredContent` as server-produced JSON data. When structured
content is returned, the specification recommends also returning its serialized
representation in a text content block for backwards
compatibility. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

Think about the audiences differently:

```
content
│
└── presentation/context-oriented representation

structuredContent
│
└── machine-processable representation
```

For example:

```
content:
"27 units currently available."

structuredContent:
{
  "sku": "ABC-1001",
  "available_units": 27
}
```

Those need not conceptually serve the same purpose.

---

# 8. Content blocks are richer than strings

`content` is an array because tool results can contain multiple content blocks.

Stable MCP supports tool-result content such as:

```
Text
Image
Audio
ResourceLink
EmbeddedResource
``` :chatgpt-content-reference{index="5"}


So a tool could conceptually return:

```
tools/call
    │
    ▼
"Analysis complete"
+
chart.png
+
resource://report/123
```

This explains why MCP does not define a tool result as simply:

```json
{
  "result": "hello"
}
```

The protocol needs richer multimodal semantics.

---

# 9. What `outputSchema` adds

Without an output schema:

```
server
   │
   └── returns some JSON
```

With one:

```
server
   │
   ├── declares expected result contract
   │
   ▼
outputSchema
   │
   ▼
structuredContent
```

The MCP specification requires the server's structured result to conform when an
`outputSchema` is declared, and clients should validate structured results
against
it. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

This means tools can have contracts in both directions:

```
             TOOL CONTRACT

client --------------------------> server
              inputSchema

client <-------------------------- server
              outputSchema
```

Professional phrasing:

> “The tool has schema-defined request and response contracts.”

---

# 10. Raw implementation

Extending the server from Lesson 1, conceptually:

```python
INVENTORY = {
    "ABC-1001": 27,
    "XYZ-2002": 0,
}

TOOL = {
    "name": "check_inventory",
    "description": "Check available inventory for a product SKU.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "sku": {
                "type": "string",
                "pattern": "^[A-Z]{3}-[0-9]{4}$",
                "description": "Product SKU such as ABC-1001",
            }
        },
        "required": ["sku"],
        "additionalProperties": False,
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "sku": {"type": "string"},
            "in_stock": {"type": "boolean"},
            "available_units": {"type": "integer"},
        },
        "required": [
            "sku",
            "in_stock",
            "available_units",
        ],
    },
    "annotations": {
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}
```

Then discovery:

```python
elif method == "tools/list":
success(
    request_id,
    {
        "tools": [TOOL]
    },
)
```

Invocation:

```python
elif method == "tools/call":
params = message["params"]

if params["name"] != "check_inventory":
    error(
        request_id,
        -32602,
        "Unknown tool",
    )
    continue

sku = params["arguments"]["sku"]

if sku not in INVENTORY:
    success(
        request_id,
        {
            "content": [
                {
                    "type": "text",
                    "text": f"Unknown SKU: {sku}",
                }
            ],
            "isError": True,
        },
    )
    continue

units = INVENTORY[sku]

result = {
    "sku": sku,
    "in_stock": units > 0,
    "available_units": units,
}

success(
    request_id,
    {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result),
            }
        ],
        "structuredContent": result,
        "isError": False,
    },
)
```

Notice how much responsibility remains ours:

```
schema declaration
schema synchronization
validation
serialization
error conversion
annotations
result formatting
```

If we change the Python implementation, nothing automatically updates our JSON
Schema.

That creates **schema drift**.

---

# 11. Now FastMCP

FastMCP collapses most of that contract into Python's type system.

```python
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

mcp = FastMCP("InventoryServer")

INVENTORY = {
    "ABC-1001": 27,
    "XYZ-2002": 0,
}


class InventoryResult(BaseModel):
    sku: str
    in_stock: bool
    available_units: int


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def check_inventory(
        sku: Annotated[
            str,
            Field(
                pattern=r"^[A-Z]{3}-[0-9]{4}$",
                description="Product SKU such as ABC-1001",
            ),
        ],
) -> InventoryResult:
    """Check available inventory for a product SKU."""

    if sku not in INVENTORY:
        raise ToolError(f"Unknown SKU: {sku}")

    units = INVENTORY[sku]

    return InventoryResult(
        sku=sku,
        in_stock=units > 0,
        available_units=units,
    )


if __name__ == "__main__":
    mcp.run()
```

FastMCP generates input schemas from function parameters/type annotations,
performs parameter validation, extracts descriptions, and can generate output
schemas from return-type annotations. Pydantic `Field` constraints such as
patterns and numeric bounds can become part of the generated parameter
schema. [FastMCP](https://gofastmcp.com/servers/tools)

---

# 12. Peel the abstraction apart

This:

```python
sku: Annotated[
    str,
    Field(
        pattern=r"^[A-Z]{3}-[0-9]{4}$",
        description="Product SKU such as ABC-1001",
    ),
]
```

roughly contributes:

```
Python type
    │
    ▼
str
    │
    ▼
JSON Schema
    │
    ├── type: string
    ├── pattern
    └── description
```

And this:

```python
-> InventoryResult
```

causes FastMCP to derive an output schema from the typed model. FastMCP
specifically supports typed models such as Pydantic models and dataclasses for
generating detailed output
schemas. [FastMCP](https://gofastmcp.com/servers/tools)

So:

```
Python signature
        │
        ▼
FastMCP introspection
        │
        ▼
MCP Tool
        │
        ├── inputSchema
        └── outputSchema
```

This is why good FastMCP design often looks like good typed Python API design.

---

# 13. Inspect instead of trusting it

Run:

```bash
uv run fastmcp list inventory_server.py --input-schema
```

Look specifically for:

```
check_inventory

sku:
  type: string
  pattern: ...
  description: ...
```

Then call it:

```bash
uv run fastmcp call inventory_server.py check_inventory sku=ABC-1001
```

Then deliberately break validation:

```bash
uv run fastmcp call inventory_server.py check_inventory sku=hello
```

Then try:

```bash
uv run fastmcp call inventory_server.py check_inventory sku=ZZZ-9999
```

These test two different failure classes:

```
hello
  │
  └── structural validation failure

ZZZ-9999
  │
  └── valid schema
      but domain/business failure
```

---

# 14. FastMCP structured-output behavior

There is an abstraction detail you should know because it can otherwise look
mysterious.

For:

```python
@mcp.tool
def add(a: int, b: int) -> int:
    return a + b
```

MCP requires structured content to be an object.

An integer isn't an object.

So FastMCP wraps primitive structured results roughly as:

```json
{
  "result": 8
}
```

and marks the generated schema accordingly. The FastMCP client can then unwrap
that representation back to the primitive through its higher-level `.data`
API. [FastMCP](https://gofastmcp.com/servers/tools)

This is an excellent example of:

> **FastMCP abstraction behavior that does not exist as a protocol concept.**

MCP did not invent:

```json
{
  "result": 8
}
```

FastMCP did that to bridge:

```
Python primitive
        ↕
MCP object-shaped structured content
```

That distinction is exactly the kind of detail that makes someone sound like
they actually understand the stack.

---

# 15. Raw MCP result vs FastMCP client result

At protocol level you have:

```
CallToolResult
├── content
├── structuredContent
└── isError
```

FastMCP's higher-level client exposes:

```python
result.data
result.content
result.structured_content
result.is_error
```

`structured_content` corresponds to MCP's structured JSON. `content` exposes MCP
content blocks. `.data` is a **FastMCP convenience abstraction** that can
deserialize/hydrate data into richer Python objects. For full protocol-level
access, FastMCP provides
`call_tool_mcp()`. [FastMCP](https://gofastmcp.com/clients/tools)

So professionally:

> “`structuredContent` is MCP; `.data` is a FastMCP client abstraction.”

Important distinction.

---

# 16. Errors: transport success does not imply tool success

This confuses many people.

Consider:

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Unknown SKU: ZZZ-9999"
      }
    ],
    "isError": true
  }
}
```

JSON-RPC succeeded.

We received a valid result.

But:

```
tool execution
     =
failure
```

Compare that with:

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "error": {
    "code": -32602,
    "message": "Unknown tool"
  }
}
```

Now the protocol operation itself failed.

MCP explicitly distinguishes **protocol errors** from **tool execution errors**.
The latter use `isError: true` and are intended to provide actionable
information that a model may use to correct or retry its
operation. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

Think:

```
                failure
                   │
          ┌────────┴────────┐
          │                 │
      protocol            domain
       failure            failure
          │                 │
    JSON-RPC error      isError=true
```

---

# 17. FastMCP's `ToolError`

For controlled failures:

```python
from fastmcp.exceptions import ToolError

if sku not in INVENTORY:
    raise ToolError(f"Unknown SKU: {sku}")
```

FastMCP also handles ordinary Python exceptions, while `ToolError` gives you
explicit control over information returned to clients. FastMCP can additionally
mask details from ordinary exceptions using
`mask_error_details=True`. [FastMCP](https://gofastmcp.com/servers/tools)

That matters for:

```python
raise RuntimeError(
    "postgres://admin:secret@internal-db/customer..."
)
```

You generally don't want arbitrary internals becoming model-visible error text.

Think in two categories:

```
SAFE / ACTIONABLE
"SKU ZZZ-9999 does not exist"

INTERNAL
"psycopg connection failed against db-prod-03..."
```

Expose the first intentionally.

Do not casually expose the second.

---

# 18. Tool annotations

Annotations answer:

> **What kind of operation is this?**

Our tool says:

```python
ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    openWorldHint=False,
)
```

FastMCP exposes standard MCP annotation hints including:

- `readOnlyHint`
- `destructiveHint`
- `idempotentHint`
- `openWorldHint`

These are advisory metadata; they are not security enforcement. The MCP
specification explicitly tells clients to consider tool annotations untrusted
unless they come from trusted
servers. [FastMCP](https://gofastmcp.com/servers/tools)

### `readOnlyHint`

```
Does this operation modify state?
```

Example:

```
get_customer       → read-only
search_orders      → read-only
create_order       → not read-only
delete_customer    → not read-only
```

### `idempotentHint`

Conceptually:

```
same call once
≈
same call repeatedly
```

Example:

```
set_user_timezone("UTC")
```

can often be idempotent.

But:

```
charge_credit_card($100)
```

should not be assumed idempotent.

### `destructiveHint`

Signals that a mutating operation may have destructive consequences.

```
delete_database
truncate_table
revoke_access
```

### `openWorldHint`

Distinguishes operations interacting with an external/open-world domain from
more closed operations.

For our hard-coded/internal inventory example:

```
openWorldHint=False
```

is reasonable.

---

# 19. Critical security principle

This is wrong:

```python
@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True
    )
)
def delete_everything():
    ...
```

and then assuming:

> “The client won't allow destructive behavior.”

Annotations are **claims**, not controls.

Your security boundary belongs elsewhere:

```
authentication
authorization
input validation
business rules
credentials
database permissions
network controls
```

MCP's tool security guidance requires server-side input validation, proper
access controls, rate limiting, and output sanitation; clients are also advised
to handle sensitive operations carefully and validate
results. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

Professional phrase:

> “Tool annotations are advisory metadata, not an authorization boundary.”

Remember that sentence.

---

# 20. Tool design is API design for an unusual caller

Your caller is not necessarily a human developer writing:

```python
check_inventory("ABC-1001")
```

Often the caller is a model deciding:

```
Should I invoke this tool?

Which arguments should I construct?

What does this field mean?

Is this operation dangerous?

What should I do with the result?
```

Therefore a good MCP tool contract optimizes for:

```
discoverability
+
unambiguous semantics
+
constrained arguments
+
predictable results
+
recoverable errors
```

This is why naming and descriptions matter more than they might in an internal
Python function.

---

# 21. Bad tool design vs good tool design

Avoid:

```python
@mcp.tool
def execute(
        action: str,
        data: dict,
) -> dict:
    ...
```

It creates a vague mega-tool:

```
execute
  action = ???
  data = ???
```

The model must invent your hidden protocol.

Prefer narrower semantic contracts:

```
get_customer
create_customer
update_customer_address
cancel_order
search_products
check_inventory
```

The schema now carries intent.

This principle is often described as designing a **semantic API surface** rather
than exposing a generic command interpreter.

---

# 22. One more useful FastMCP abstraction: `ToolResult`

Normally:

```python
return InventoryResult(...)
```

is best.

But sometimes you want precise control over both:

```
human/model-facing content
+
machine-facing structured data
```

FastMCP exposes `ToolResult` for
this. [FastMCP](https://gofastmcp.com/servers/tools)

Example:

```python
from fastmcp.tools import ToolResult
from mcp.types import TextContent


@mcp.tool
def check_inventory_summary(sku: str) -> ToolResult:
    units = INVENTORY[sku]

    return ToolResult(
        content=[
            TextContent(
                type="text",
                text=f"{units} units of {sku} are available.",
            )
        ],
        structured_content={
            "sku": sku,
            "available_units": units,
            "in_stock": units > 0,
        },
    )
```

Now:

```
content
│
└── concise natural-language representation

structured_content
│
└── stable application data
```

Use this when presentation and data representation should intentionally diverge.

---

# 23. The complete abstraction map

You should now be able to map:

| Protocol MCP              | FastMCP                                                      |
|---------------------------|--------------------------------------------------------------|
| Tool definition           | decorated Python function                                    |
| `name`                    | function name / `name=`                                      |
| `description`             | docstring / `description=`                                   |
| `inputSchema`             | parameters + type annotations + `Field`                      |
| `outputSchema`            | return annotation                                            |
| annotations               | `ToolAnnotations`                                            |
| `tools/list`              | generated tool registry                                      |
| `tools/call`              | function dispatch                                            |
| argument validation       | FastMCP/Pydantic validation                                  |
| `structuredContent`       | Python structured return value                               |
| content blocks            | ordinary returns/helper types/`ToolResult`                   |
| `isError`                 | tool execution failure                                       |
| list-changed notification | automatically handled when FastMCP's active tool set changes |

FastMCP automatically emits `notifications/tools/list_changed` for supported
runtime tool-set changes when they occur in an active MCP request
context. [FastMCP](https://gofastmcp.com/servers/tools)

---

# 24. Professional vocabulary checkpoint

Be comfortable saying these:

| Term                          | Meaning                                                  |
|-------------------------------|----------------------------------------------------------|
| **Tool discovery**            | obtaining definitions via `tools/list`                   |
| **Tool invocation**           | executing via `tools/call`                               |
| **Tool contract**             | name + semantics + schemas + metadata                    |
| **API surface**               | set of capabilities exposed by the server                |
| **Schema-derived validation** | validating arguments from declared JSON Schema           |
| **Structural validation**     | checking argument shape/types/constraints                |
| **Domain validation**         | checking business meaning                                |
| **Structured content**        | MCP machine-readable result                              |
| **Content block**             | typed MCP result content                                 |
| **Output schema**             | contract for structured result data                      |
| **Schema drift**              | implementation and declared schema diverging             |
| **Idempotency**               | repeated equivalent calls don't add further effects      |
| **Side effect**               | change caused outside the returned value                 |
| **Advisory metadata**         | hints that communicate semantics but don't enforce them  |
| **Protocol error**            | JSON-RPC/MCP request failure                             |
| **Execution error**           | valid tool result carrying `isError=true`                |
| **Serialization**             | converting implementation values to wire representation  |
| **Hydration/deserialization** | reconstructing richer application objects from wire data |

A strong explanation in an interview would sound like:

> “FastMCP introspects the Python callable to derive the MCP tool's input and
> output schemas. The client discovers that contract through `tools/list` and
> later invokes it through `tools/call`. Structured results travel in
`structuredContent`, while traditional MCP content blocks preserve a
> presentation-oriented representation and backwards compatibility.”

---

# Hands-on assignment

Modify the inventory server in this order:

1. Add `warehouse` with `Literal["PHX", "LAX", "DFW"]`.
2. Add `minimum_units` constrained to `ge=0`.
3. Inspect the generated `inputSchema`.
4. Return a Pydantic `InventoryResult`.
5. Inspect the generated `outputSchema`.
6. Trigger a **schema failure**.
7. Trigger a **business-rule failure** using a syntactically valid nonexistent
   SKU.
8. Add the three correct annotations.
9. Replace the normal return with `ToolResult` and make `content` human-readable
   while keeping `structured_content` machine-readable.
10. Use a FastMCP client with `call_tool_mcp()` and inspect the **raw
    MCP `CallToolResult`**, then compare it with higher-level `call_tool()` and
    `.data`. FastMCP specifically provides `call_tool_mcp()` for this
    protocol-level inspection. [FastMCP](https://gofastmcp.com/clients/tools)

### The test

You understand MCP tools when you can explain why these are **four different
things**:

```
Python return value
        ≠
structuredContent
        ≠
content
        ≠
outputSchema
```

They frequently correspond to each other, but they exist at different layers and
serve different purposes.

## Next lesson: Resources

Next we should build **Resources from first principles**:

```
resource vs tool
URI semantics
resources/list
resources/read
static resources
resource templates
URI parameters
MIME types
subscriptions
list_changed
embedded resources
FastMCP @resource
FastMCP ResourceTemplate
```

The main conceptual challenge will be understanding **why MCP needs resources
when a tool could simply return the same data**. That distinction is central to
good MCP architecture.