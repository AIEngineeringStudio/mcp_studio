# Lesson 3 — MCP Resources

The central question:

> **Why expose something as a Resource when a Tool could return exactly the same
data?**

The answer is not implementation. Both can run Python functions or query
databases.

The difference is **protocol semantics and who controls access**:

```
TOOL
"Perform this operation."
model-controlled
tools/call

RESOURCE
"Here is addressable context/data."
application-driven
resources/read
```

MCP explicitly describes tools as **model-controlled**, while resources are *
*application-driven**: the host may expose them in a picker, search them,
automatically include them as context, or use another UI
policy. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/tools?utm_source=chatgpt.com)

---

# 1. First principle: resources are addressable data

Imagine an MCP server exposing:

```
company://handbook
customer://123/profile
repo://my-app/README.md
schema://production/orders
```

The important property is not that these are strings.

It is that each piece of information has an **identity**:

```
resource
   │
   └── URI
        │
        ├── identifies what data this is
        └── lets the client request it later
```

In stable MCP, every resource is uniquely identified by a URI. A resource
definition can additionally contain a name, title, description, MIME type, size
and display
metadata. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

Conceptually:

```
Tool identity       → name
                     "search_orders"

Resource identity   → URI
                     "customer://123/orders"
```

That difference becomes important later with caching, subscriptions, linking and
context management.

---

# 2. A resource is not necessarily a file

A common misconception:

```
resource = file
```

Wrong.

Resources can represent things such as:

```
files
database rows
database schemas
configuration
API responses
generated reports
application state
documentation
repository content
```

The protocol only cares that the information is exposed as an **addressable
resource**. MCP explicitly gives files, database schemas and
application-specific information as
examples. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

So this is perfectly valid conceptually:

```
postgres://schema/orders
```

even if no physical file exists.

---

# 3. Tool vs Resource: the design test

Suppose we have customer information.

We could write:

```python
@mcp.tool
def get_customer(customer_id: str):
    ...
```

or:

```python
@mcp.resource("customer://{customer_id}")
def customer(customer_id: str):
    ...
```

Both may execute the same database query.

The choice should come from semantics.

### Prefer a Resource when

```
"This data exists and can be addressed/read."
```

Examples:

```
customer://123/profile
repo://foo/README.md
config://production
schema://orders
document://policy/refunds
```

### Prefer a Tool when

```
"Please perform an operation."
```

Examples:

```
search_customers(...)
calculate_shipping(...)
create_order(...)
cancel_subscription(...)
send_email(...)
```

A useful mental shortcut is:

```
RESOURCE ≈ noun

customer profile
configuration
document
schema

TOOL ≈ verb

search
calculate
create
delete
send
```

That heuristic is not a protocol rule, but it usually produces better API
design.

---

# 4. Resources have a discovery/read split

Like tools, resources separate **discovery** from **use**.

```
RESOURCE DISCOVERY

client
  │
  ├── resources/list
  │
  ▼
server
  │
  └── available resource metadata


RESOURCE RETRIEVAL

client
  │
  ├── resources/read(uri)
  │
  ▼
server
  │
  └── resource contents
```

`resources/list` is pageable. `resources/read` retrieves the content associated
with a specific
URI. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

---

# 5. Protocol-level `resources/list`

Suppose our inventory server exposes its product catalog.

The client sends:

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "method": "resources/list",
  "params": {}
}
```

The server could reply:

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": {
    "resources": [
      {
        "uri": "inventory://catalog",
        "name": "product_catalog",
        "title": "Product Catalog",
        "description": "Current product catalog and stock levels",
        "mimeType": "application/json"
      }
    ]
  }
}
```

Notice what is absent:

```
NO content yet
```

We have returned metadata describing an available resource.

That is **discovery**.

---

# 6. Protocol-level `resources/read`

Now the client wants the content:

```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "method": "resources/read",
  "params": {
    "uri": "inventory://catalog"
  }
}
```

Response:

```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "result": {
    "contents": [
      {
        "uri": "inventory://catalog",
        "mimeType": "application/json",
        "text": "{\"ABC-1001\":27,\"XYZ-2002\":0}"
      }
    ]
  }
}
```

Stable MCP resource contents are either **text** or **binary/blob content**.
Binary data is base64 encoded. A read may return multiple content
entries. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

---

# 7. Important difference from Tools: no `structuredContent`

Recall a tool:

```
CallToolResult
├── content
├── structuredContent
└── isError
```

Resources work differently:

```
ReadResourceResult
└── contents[]
     ├── text
     └── blob
```

There is no equivalent stable-MCP `structuredContent` field for resources.

If your resource represents JSON, you typically return:

```
mimeType = application/json
text     = serialized JSON
```

This matters when designing clients.

---

# 8. MIME type is part of the contract

Consider:

```json
{
  "text": "{\"version\":3}"
}
```

Without context, that could be:

```
plain text
JSON
JavaScript fragment
something else
```

With:

```json
{
  "mimeType": "application/json",
  "text": "{\"version\":3}"
}
```

the representation is explicit.

Professional term:

> **content negotiation metadata**

Strictly speaking MCP is not performing HTTP content negotiation here, but MIME
types communicate the representation format.

Typical examples:

```
text/plain
text/markdown
application/json
image/png
application/pdf
```

MCP resource definitions and resource contents can carry MIME
types. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

---

# 9. Raw server implementation

Extend our manual MCP server:

```python
import json

INVENTORY = {
    "ABC-1001": 27,
    "XYZ-2002": 0,
}
```

During initialization:

```python
"capabilities": {
    "tools": {},
    "resources": {}
}
```

Then discovery:

```python
elif method == "resources/list":
success(
    request_id,
    {
        "resources": [
            {
                "uri": "inventory://catalog",
                "name": "product_catalog",
                "description": (
                    "Current product catalog and stock levels."
                ),
                "mimeType": "application/json",
            }
        ]
    },
)
```

And reading:

```python
elif method == "resources/read":
uri = message["params"]["uri"]

if uri != "inventory://catalog":
    error(
        request_id,
        -32002,
        "Resource not found",
    )
    continue

success(
    request_id,
    {
        "contents": [
            {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(INVENTORY),
            }
        ]
    },
)
```

For stable MCP, resource-not-found is conventionally reported as JSON-RPC error
`-32002`; servers should also validate URIs and enforce permissions before
serving sensitive
resources. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

---

# 10. Notice the routing problem

Our manual code contains:

```python
if uri == "inventory://catalog":
```

Add ten resources:

```python
if uri == ...
elif uri == ...
elif uri == ...
elif uri == ...
```

Now imagine dynamic resources:

```
inventory://ABC-1001
inventory://XYZ-2002
inventory://QRS-4000
...
```

You could register every product individually.

That does not scale.

This creates the need for **Resource Templates**.

---

# 11. Resource Templates

A resource template describes a family of resources.

Instead of registering:

```
inventory://ABC-1001
inventory://XYZ-2002
inventory://QRS-4000
```

we describe:

```
inventory://{sku}
```

This means:

```
               TEMPLATE
                   │
          inventory://{sku}
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
ABC-1001       XYZ-2002     QRS-4000
```

Stable MCP exposes templates separately through:

```
resources/templates/list
```

and defines them using URI
templates. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

---

# 12. Protocol-level template discovery

Request:

```json
{
  "jsonrpc": "2.0",
  "id": 20,
  "method": "resources/templates/list"
}
```

Response:

```json
{
  "jsonrpc": "2.0",
  "id": 20,
  "result": {
    "resourceTemplates": [
      {
        "uriTemplate": "inventory://{sku}",
        "name": "inventory_item",
        "description": "Inventory status for one SKU",
        "mimeType": "application/json"
      }
    ]
  }
}
```

Notice:

```
resources/list
    → concrete resources

resources/templates/list
    → parameterized resource families
```

This distinction is worth memorizing.

---

# 13. Reading a templated resource

There is **no separate protocol method** such as:

```
resources/templates/read
```

The client expands the URI:

```
inventory://ABC-1001
```

and sends normal:

```json
{
  "jsonrpc": "2.0",
  "id": 21,
  "method": "resources/read",
  "params": {
    "uri": "inventory://ABC-1001"
  }
}
```

Server routing determines that the concrete URI matches:

```
inventory://{sku}
```

and extracts:

```
sku = ABC-1001
```

Conceptually:

```
resources/read
      │
      ▼
inventory://ABC-1001
      │
      ▼
match URI template
inventory://{sku}
      │
      ▼
extract parameter
sku="ABC-1001"
      │
      ▼
generate contents
```

---

# 14. Raw template routing

Without FastMCP you might write something ugly:

```python
elif method == "resources/read":
uri = message["params"]["uri"]

prefix = "inventory://"

if uri.startswith(prefix):
    sku = uri[len(prefix):]

    if sku not in INVENTORY:
        error(
            request_id,
            -32002,
            "Resource not found",
        )
        continue

    units = INVENTORY[sku]

    data = {
        "sku": sku,
        "available_units": units,
        "in_stock": units > 0,
    }

    success(
        request_id,
        {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(data),
                }
            ]
        },
    )
```

Now you own:

```
URI parsing
template matching
percent decoding
parameter extraction
security checks
routing
serialization
errors
metadata
```

Again, abstraction pressure appears.

---

# 15. FastMCP static Resource

FastMCP collapses the static resource to:

```python
import json

from fastmcp import FastMCP

mcp = FastMCP("InventoryServer")

INVENTORY = {
    "ABC-1001": 27,
    "XYZ-2002": 0,
}


@mcp.resource(
    "inventory://catalog",
    mime_type="application/json",
)
def product_catalog() -> str:
    """Current product catalog and stock levels."""
    return json.dumps(INVENTORY)
```

The function is **lazy**: FastMCP executes it when the client actually reads
that URI rather than when the resource is merely discovered. FastMCP derives the
default resource name from the function and its description from the
docstring. [FastMCP](https://gofastmcp.com/servers/resources)

---

# 16. Peel that abstraction

This:

```python
@mcp.resource(
    "inventory://catalog",
    mime_type="application/json",
)
def product_catalog() -> str:
    ...
```

roughly creates:

```
FastMCP registry
       │
       ├── URI
       │   inventory://catalog
       │
       ├── name
       │   product_catalog
       │
       ├── description
       │   docstring
       │
       └── MIME type
           application/json
```

Then FastMCP effectively handles:

```
resources/list
      │
      ▼
resource metadata

resources/read
      │
      ▼
find registered URI
      │
      ▼
call product_catalog()
      │
      ▼
serialize return value
      │
      ▼
TextResourceContents
```

FastMCP is replacing **resource registry + protocol handlers + serialization
plumbing**. [FastMCP](https://gofastmcp.com/servers/resources)

---

# 17. FastMCP Resource Template

Now the dynamic resource:

```python
import json

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError

mcp = FastMCP("InventoryServer")

INVENTORY = {
    "ABC-1001": 27,
    "XYZ-2002": 0,
}


@mcp.resource(
    "inventory://{sku}",
    mime_type="application/json",
)
def inventory_item(sku: str) -> str:
    """Inventory status for one SKU."""

    if sku not in INVENTORY:
        raise ResourceError(
            f"Unknown SKU: {sku}"
        )

    units = INVENTORY[sku]

    return json.dumps({
        "sku": sku,
        "available_units": units,
        "in_stock": units > 0,
    })
```

The presence of:

```
{sku}
```

causes FastMCP to treat this as a **resource template** and map the URI
parameter onto the function argument named `sku`. FastMCP uses RFC 6570
URI-template semantics and also supports more advanced wildcard/query
forms. [FastMCP](https://gofastmcp.com/servers/resources)

The abstraction is:

```
inventory://ABC-1001
        │
        ▼
inventory://{sku}
        │
        ▼
sku="ABC-1001"
        │
        ▼
inventory_item(sku)
```

No manual parsing.

---

# 18. Important: function arguments mean something different here

With tools:

```python
@mcp.tool
def check_inventory(sku: str):
```

the arguments come from:

```json
{
  "arguments": {
    "sku": "ABC-1001"
  }
}
```

With resource templates:

```python
@mcp.resource("inventory://{sku}")
def inventory_item(sku: str):
```

the argument comes from:

```
URI matching
```

So:

```
TOOL
Python parameters
    ↕
MCP arguments / inputSchema


RESOURCE TEMPLATE
Python parameters
    ↕
URI template variables
```

This is a major conceptual difference.

---

# 19. Resources do not have `inputSchema`

A tool needs:

```
inputSchema
```

because the caller sends an arbitrary argument object.

A resource template encodes its addressing parameters into:

```
URI template
```

Therefore:

```
tools
    → JSON Schema parameter contract

resource templates
    → URI-template parameter contract
```

This also explains why URI design matters more for resources than it does for
tools.

---

# 20. URI design is API design

Bad:

```
thing://123
```

What is `123`?

Better:

```
customer://123/profile
```

Or:

```
orders://customer/123
```

A URI should communicate stable resource identity.

Think:

```
scheme://hierarchical/resource/identity
```

For application-specific resources, custom URI schemes are allowed as long as
they follow RFC 3986. The MCP spec also warns against using `https://` merely
because your server internally downloads something over HTTP: `https://` should
generally identify something the client itself can fetch directly from the
web. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

That distinction is subtle but professional.

---

# 21. Resource URI ≠ backend location

Suppose internally you fetch:

```
https://internal-api.example.com/users/42
```

You do **not** necessarily expose:

```
https://internal-api.example.com/users/42
```

as the MCP URI.

You could expose:

```
customer://42/profile
```

Then:

```
MCP identity
customer://42/profile
        │
        ▼
server implementation
        │
        ▼
internal HTTP call
        │
        ▼
database/API
```

The resource URI describes the **MCP-facing identity**, not necessarily the
storage topology.

Professional phrase:

> “The resource URI provides logical identity; it does not have to leak the
> physical storage location.”

---

# 22. JSON returns in FastMCP

FastMCP allows resource functions to return Python values such as:

```python
dict
list
tuple
int
bool
None
```

and serializes JSON-native values to JSON text. But the declared MIME type
remains important; FastMCP documentation explicitly recommends setting:

```python
mime_type = "application/json"
```

when clients depend on the representation being
JSON. [FastMCP](https://gofastmcp.com/servers/resources)

Therefore this is convenient:

```python
@mcp.resource(
    "inventory://{sku}",
    mime_type="application/json",
)
def inventory_item(sku: str) -> dict:
    return {
        "sku": sku,
        "available_units": INVENTORY[sku],
    }
```

Mentally remember that the wire-level stable resource still becomes resource *
*contents**, not tool-style `structuredContent`.

---

# 23. Text vs binary resources

FastMCP maps simple return types roughly like:

```
str
 │
 ▼
TextResourceContents


bytes
 │
 ▼
BlobResourceContents
 │
 ▼
base64 on wire
```

FastMCP documents `str` as text content and `bytes` as binary/blob content, with
explicit MIME types recommended for non-text
data. [FastMCP](https://gofastmcp.com/servers/resources)

Example:

```python
@mcp.resource(
    "image://company-logo",
    mime_type="image/png",
)
def company_logo() -> bytes:
    return load_logo_bytes()
```

Wire conceptually:

```json
{
  "contents": [
    {
      "uri": "image://company-logo",
      "mimeType": "image/png",
      "blob": "iVBORw0KGgo..."
    }
  ]
}
```

---

# 24. `ResourceResult`: peel another abstraction

Normally:

```python
return "hello"
```

or:

```python
return some_bytes
```

is enough.

When you need control over:

```
multiple content items
different MIME types
per-content metadata
result metadata
```

FastMCP provides `ResourceResult` and
`ResourceContent`. [FastMCP](https://gofastmcp.com/servers/resources)

Example:

```python
from fastmcp.resources import (
    ResourceContent,
    ResourceResult,
)


@mcp.resource("report://weekly")
def weekly_report() -> ResourceResult:
    return ResourceResult(
        contents=[
            ResourceContent(
                content='{"revenue": 120000}',
                mime_type="application/json",
            ),
            ResourceContent(
                content="# Weekly Report\nRevenue: $120,000",
                mime_type="text/markdown",
            ),
        ]
    )
```

Now one read can provide multiple representations.

This mirrors the protocol's:

```
ReadResourceResult
└── contents[]
```

---

# 25. Resource errors differ from tool execution errors

Remember Tools:

```
business failure
      │
      ▼
CallToolResult
isError=true
```

Resources do not use that model.

A failed resource read uses a protocol error.

For example:

```json
{
  "jsonrpc": "2.0",
  "id": 50,
  "error": {
    "code": -32002,
    "message": "Resource not found"
  }
}
```

The stable MCP resource specification recommends `-32002` for resource-not-found
and standard internal error handling for server
failures. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

FastMCP exposes `ResourceError` when you want explicit client-safe error details
and can mask details from ordinary exceptions with
`mask_error_details=True`. [FastMCP](https://gofastmcp.com/servers/resources)

This is another important distinction:

```
TOOL DOMAIN FAILURE
CallToolResult(isError=true)

RESOURCE READ FAILURE
JSON-RPC/MCP error
```

---

# 26. Why resources are powerful: linking

A tool can return a **resource link**.

Imagine:

```
generate_report()
```

The report is too large to dump directly into the tool result.

Instead:

```
tool
generate_report()
     │
     ▼
resource link
report://2026/08/10/abc123
     │
     ▼
client reads when needed
resources/read
```

The stable MCP tool specification explicitly allows tool results to return links
to resources, which may then be fetched or subscribed to by the
client. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/tools?utm_source=chatgpt.com)

This produces a good architecture:

```
ACTION
Tool

creates

DATA
Resource
```

Example:

```
Tool:
generate_financial_report(...)

Result:
report://financial/7f94

Resource:
report://financial/7f94
```

That is much cleaner than returning a 20 MB report directly from the tool.

---

# 27. Resources can change

Suppose:

```
inventory://ABC-1001
```

currently says:

```
27 units
```

Five minutes later:

```
19 units
```

The **identity** remains the same.

The **representation** changed.

```
URI identity
inventory://ABC-1001
        │
        ├── t1 → 27 units
        ├── t2 → 19 units
        └── t3 → 12 units
```

This is why resource subscriptions exist.

---

# 28. Stable MCP resource subscriptions

During initialization a stable MCP server can declare:

```json
{
  "capabilities": {
    "resources": {
      "subscribe": true,
      "listChanged": true
    }
  }
}
```

These are separate capabilities:

```
subscribe
    → individual resource changed

listChanged
    → catalog of available resources changed
``` :chatgpt-content-reference{index="18"}


---

# 29. `resources/subscribe`

Client:

```json
{
  "jsonrpc": "2.0",
  "id": 60,
  "method": "resources/subscribe",
  "params": {
    "uri": "inventory://ABC-1001"
  }
}
```

Later the server sends:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/resources/updated",
  "params": {
    "uri": "inventory://ABC-1001"
  }
}
```

Important:

```
notification does NOT need to contain
the new resource contents
```

It tells the client:

> That resource changed; read it again.

That is an **invalidation notification**.

Professional vocabulary:

> “The server invalidates the client's cached representation and the client can
> re-read the canonical resource.”

The stable protocol defines exactly this subscription/update
flow. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

---

# 30. `list_changed` is different

Imagine we previously expose:

```
resource A
resource B
```

and now expose:

```
resource A
resource B
resource C
```

The contents of A/B did not necessarily change.

The **resource catalog** changed.

Server:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/resources/list_changed"
}
```

Then the client can call:

```
resources/list
```

again.

```
notifications/resources/updated
→ one resource representation changed

notifications/resources/list_changed
→ available-resource set changed
```

FastMCP automatically emits list-changed notifications for runtime
resource/template additions, enabling and disabling when those changes happen
within an active MCP request
context. [FastMCP](https://gofastmcp.com/servers/resources)

---

# 31. Do not mix protocol eras

We are still learning **stable MCP `2025-11-25`**.

So for now:

```
resources/subscribe
notifications/resources/updated
```

is the model to learn.

Current FastMCP documentation also covers the newer MCP `2026-07-28` model,
where the subscription architecture changes. We will deliberately cover that
later rather than mixing two lifecycle models now. The official MCP changelog
identifies subscription changes between these
revisions. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/changelog?utm_source=chatgpt.com)

---

# 32. Resources also support annotations

For stable MCP `2025-11-25`, resource/content annotations include:

```
audience
priority
lastModified
```

For example:

```json
{
  "uri": "docs://architecture",
  "name": "Architecture",
  "annotations": {
    "audience": [
      "assistant"
    ],
    "priority": 0.9,
    "lastModified": "2026-08-01T12:00:00Z"
  }
}
```

These are hints allowing clients to prioritize, filter or display resources
appropriately. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

One version-related caution: current FastMCP documentation spans both MCP
protocol eras and exposes additional annotation concepts such as
read-only/idempotency hints. Do not assume every FastMCP annotation maps to the
stable `2025-11-25` resource annotation shape. When discussing protocol
behavior, always anchor yourself to the negotiated MCP
version. [FastMCP](https://gofastmcp.com/servers/resources)

That is exactly why we're learning **protocol first**.

---

# 33. Security: resource templates create an attack surface

Suppose:

```python
@mcp.resource("file:///{path}")
def read_file(path: str):
    return open(path).read()
```

Now someone requests:

```
file:///../../etc/passwd
```

A resource URI is still **untrusted input**.

MCP requires servers to validate resource URIs and recommends enforcing access
controls before resource operations. FastMCP additionally documents
path-security handling for template-derived
parameters. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

Professional phrase:

> “A URI template expands the server's externally controlled input surface.”

Never confuse:

```
read-only
```

with:

```
safe
```

Reading sensitive information can be more damaging than changing it.

---

# 34. FastMCP client: observe the abstraction

You can test directly:

```python
import asyncio

from fastmcp import Client


async def main():
    client = Client("inventory_server.py")

    async with client:
        resources = await client.list_resources()

        for resource in resources:
            print(resource.uri)

        contents = await client.read_resource(
            "inventory://catalog"
        )

        print(contents[0].text)


asyncio.run(main())
```

FastMCP clients expose `list_resources()` and `read_resource(uri)` over the
underlying MCP resource
operations. [FastMCP](https://gofastmcp.com/llms-full.txt?utm_source=chatgpt.com)

For templates, inspect:

```
resources/templates/list
```

separately, then read a concrete expanded URI such as:

```
inventory://ABC-1001
```

---

# 35. Complete abstraction map

| MCP protocol               | FastMCP                                     |
|----------------------------|---------------------------------------------|
| Resource                   | `@mcp.resource(...)`                        |
| Resource URI               | decorator URI                               |
| `resources/list`           | server registry / `client.list_resources()` |
| `resources/read`           | decorated function execution                |
| `TextResourceContents`     | `str`                                       |
| `BlobResourceContents`     | `bytes`                                     |
| resource template          | `{parameter}` in decorator URI              |
| URI-template parsing       | automatic routing                           |
| template parameter         | function argument                           |
| `resources/templates/list` | generated template registry                 |
| read error                 | exception / `ResourceError`                 |
| multiple contents          | `ResourceResult`                            |
| resource metadata          | decorator options                           |
| list change notification   | FastMCP runtime notification handling       |

The low-level SDK comparison in FastMCP's official migration guide makes the
abstraction especially clear: low-level implementations need separate
list-resources, list-resource-templates and read-resource handlers plus manual
URI routing; FastMCP collapses them into declarative resource
decorators. [FastMCP](https://gofastmcp.com/getting-started/upgrading/from-low-level-sdk-v2?utm_source=chatgpt.com)

---

# 36. Professional vocabulary

| Term                    | Precise meaning                                          |
|-------------------------|----------------------------------------------------------|
| **Resource**            | URI-addressable server data                              |
| **Resource URI**        | unique logical identity of a resource                    |
| **Resource discovery**  | obtaining concrete resources through `resources/list`    |
| **Resource read**       | retrieving contents through `resources/read`             |
| **Resource template**   | URI pattern describing dynamically addressable resources |
| **URI expansion**       | substituting parameters into a URI template              |
| **Logical identity**    | MCP-facing identity independent of backend storage       |
| **Representation**      | actual content returned for a resource                   |
| **MIME type**           | representation/content format metadata                   |
| **Lazy loading**        | generating/fetching content only when read               |
| **Resource catalog**    | set of resources exposed by a server                     |
| **Subscription**        | client interest in updates to a resource                 |
| **Invalidation**        | notification that previously read data may be stale      |
| **Binary resource**     | blob content encoded for the wire                        |
| **Resource routing**    | matching concrete URIs to implementations                |
| **Addressable context** | context that has stable URI identity                     |

A strong explanation would sound like:

> “Resources are application-driven, URI-addressable context. Concrete resources
> are discovered through `resources/list`, templates through
`resources/templates/list`, and both are retrieved through `resources/read`.
> FastMCP maps URI templates onto Python function parameters and handles routing,
> serialization and protocol result construction.”

---

# 37. Design exercise

Extend your inventory server with all three:

```
STATIC

inventory://catalog


TEMPLATE

inventory://{sku}


TOOL

check_inventory(
    sku,
    warehouse,
    minimum_units
)
```

Then explain why all three deserve to exist.

### `inventory://catalog`

Represents:

```
a named body of data
```

### `inventory://ABC-1001`

Represents:

```
a specific addressable entity
```

### `check_inventory(...)`

Represents:

```
an operation with arbitrary query semantics
```

This distinction is more important than the code.

---

# 38. Breaking exercise

Deliberately make these mistakes:

1. Request a resource URI that doesn't exist.
2. Return JSON without `application/json`.
3. Create `{sku}` but name the Python argument `product`.
4. Try a URI containing malicious path traversal.
5. Compare `resources/list` with `resources/templates/list`.
6. Read the same resource twice and verify the function executes lazily.
7. Return `bytes` and inspect the blob representation.
8. Return `ResourceResult` containing JSON **and** Markdown.
9. Build one capability once as a tool and once as a resource, then inspect the
   wire contracts.

The goal is to internalize:

```
same backend logic
      ≠
same MCP semantics
```

---

# The mental model to retain

```
                         MCP SERVER
                             │
               ┌─────────────┴─────────────┐
               │                           │
             TOOLS                     RESOURCES
               │                           │
          operations                     data
               │                           │
             name                         URI
               │                           │
          inputSchema            concrete / template
               │                           │
          tools/call                 resources/read
               │                           │
          execution                   retrieval
               │                           │
     content + structuredContent      text / blob
```

## Next lesson — Prompts

Next we should complete MCP's three primary server primitives:

```
Tools      → actions
Resources  → context/data
Prompts    → reusable interaction patterns
```

We’ll cover `prompts/list`, `prompts/get`, prompt arguments, message roles,
embedded resources, FastMCP `@prompt`, and—most importantly—**why prompts are
protocol objects rather than just strings stored in Python**.