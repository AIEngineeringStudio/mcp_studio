# Increment 3 — Resources and Prompts

## Goal

Complete the three primary server-side MCP primitives:

```text
FastMCP server
├── Tools       Perform operations
├── Resources   Provide readable context
└── Prompts     Provide reusable interaction templates
```

Their intended control models differ:

| Primitive | Primary controller     | Purpose                     |
|-----------|------------------------|-----------------------------|
| Tool      | Model-controlled       | Execute an operation        |
| Resource  | Application-controlled | Supply context              |
| Prompt    | User-controlled        | Start a predefined workflow |

The MCP specification describes tools as model-controlled, resources as
application-driven, and prompts as user-controlled. These are intended
interaction models, not strict security
boundaries. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)

## Correction from the previous increment

Current FastMCP documentation uses `PythonStdioTransport` for explicitly
launching a Python server script. Replace the previous generic `StdioTransport`
example with it. The architecture remains the same: the client launches a
subprocess and communicates over
stdio. [FastMCP](https://gofastmcp.com/clients/client)

---

# 1. The Conceptual Difference

## Tool

A tool answers:

> “What operation should the server perform?”

```python
@mcp.tool
def multiply(a: int, b: int) -> int:
    return a * b
```

Calling it causes execution.

---

## Resource

A resource answers:

> “What information can the server provide?”

```python
@mcp.resource("docs://arithmetic/operations")
def arithmetic_operations() -> str:
    ...
```

Reading it retrieves content.

Resources are read-only context identified by URIs. They can expose files,
configuration, schemas, database content, generated documentation, or other
application data. FastMCP executes the resource function lazily when its URI is
requested. [FastMCP](https://gofastmcp.com/servers/resources)

---

## Prompt

A prompt answers:

> “What reusable instruction or conversation template can the user select?”

```python
@mcp.prompt
def explain_arithmetic(...) -> str:
    ...
```

Retrieving a prompt does **not** itself run an LLM. The server returns one or
more prepared messages; the host decides how to present or send those messages
to a model. [FastMCP](https://gofastmcp.com/servers/prompts)

---

# 2. Update `server.py`

Replace the file with:

```python
from __future__ import annotations

import json
import logging
import os
import sys

from fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="First Principles MCP",
    instructions=(
        "Use arithmetic tools for calculations. "
        "Use arithmetic resources for reference information. "
        "Offer arithmetic prompts when the user requests a guided explanation."
    ),
)


# ---------------------------------------------------------------------------
# Tools: executable operations
# ---------------------------------------------------------------------------


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two integers and return their sum."""
    return a + b


@mcp.tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers and return their product."""
    return a * b


@mcp.tool
def server_process_info() -> dict[str, str | int]:
    """Return diagnostic information about the MCP server process."""
    return {
        "server_pid": os.getpid(),
        "parent_pid": os.getppid(),
        "environment": os.getenv("APP_ENV", "not-set"),
    }


# ---------------------------------------------------------------------------
# Static resource: one fixed URI
# ---------------------------------------------------------------------------


@mcp.resource(
    uri="docs://arithmetic/operations",
    name="ArithmeticOperations",
    title="Supported Arithmetic Operations",
    description="Describes the arithmetic operations exposed by this server.",
    mime_type="application/json",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)
def arithmetic_operations() -> str:
    """Return documentation for the supported arithmetic operations."""
    return json.dumps(
        {
            "operations": {
                "add": {
                    "description": "Add two integers.",
                    "symbol": "+",
                    "example": "20 + 22 = 42",
                },
                "multiply": {
                    "description": "Multiply two integers.",
                    "symbol": "×",
                    "example": "6 × 7 = 42",
                },
            }
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Resource template: one URI pattern, many possible resources
# ---------------------------------------------------------------------------


@mcp.resource(
    uri="math://integer/{value}/profile",
    name="IntegerProfile",
    title="Integer Profile",
    description="Returns mathematical properties of a requested integer.",
    mime_type="application/json",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)
def integer_profile(value: int) -> str:
    """Return basic mathematical properties for an integer."""
    sign = "zero"

    if value > 0:
        sign = "positive"
    elif value < 0:
        sign = "negative"

    return json.dumps(
        {
            "value": value,
            "sign": sign,
            "parity": "even" if value % 2 == 0 else "odd",
            "absolute_value": abs(value),
            "square": value ** 2,
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Prompt: reusable user-selectable instruction
# ---------------------------------------------------------------------------


@mcp.prompt(
    name="explain_arithmetic",
    title="Explain an Arithmetic Calculation",
    description=(
            "Creates a structured request for explaining an addition or "
            "multiplication calculation."
    ),
)
def explain_arithmetic(
        operation: str,
        a: int,
        b: int,
        audience: str = "beginner",
) -> str:
    """Create an explanation request for an arithmetic calculation.

    Args:
        operation: The operation to explain. Supported values are add and multiply.
        a: The first integer.
        b: The second integer.
        audience: The intended audience for the explanation.
    """
    normalized_operation = operation.strip().lower()

    if normalized_operation not in {"add", "multiply"}:
        raise ValueError(
            "Unsupported operation. Expected 'add' or 'multiply'."
        )

    return (
        f"Explain how to {normalized_operation} {a} and {b} to a "
        f"{audience} audience.\n\n"
        "Requirements:\n"
        "1. Show the calculation step by step.\n"
        "2. Explain why each step is valid.\n"
        "3. State the final answer clearly.\n"
        "4. Include one similar practice problem.\n"
        "5. Do not assume prior knowledge."
    )


if __name__ == "__main__":
    logger.info(
        "Starting MCP server process pid=%s parent_pid=%s",
        os.getpid(),
        os.getppid(),
    )

    mcp.run(transport="stdio")
```

FastMCP uses the `@mcp.resource` decorator for both static resources and URI
templates. A URI containing placeholders such as `{value}` becomes a resource
template, and matching URI values are passed to the Python function. It uses
`@mcp.prompt` to register parameterized prompt-generating
functions. [FastMCP](https://gofastmcp.com/servers/resources)

---

# 3. Static Resource vs Resource Template

## Static resource

```text
docs://arithmetic/operations
```

There is one exact address:

```text
URI ──► one resource handler ──► one representation
```

The client must request that exact URI.

---

## Resource template

```text
math://integer/{value}/profile
```

This defines a URI pattern:

```text
math://integer/42/profile
math://integer/-7/profile
math://integer/100/profile
```

All three map to the same Python function:

```text
math://integer/42/profile
                  │
                  ▼
        integer_profile(value=42)
```

Professional wording:

> “The server exposes a parameterized resource namespace using an RFC 6570 URI
> template.”

FastMCP implements resource templates using URI placeholders and supports RFC
6570 template behavior. [FastMCP](https://gofastmcp.com/servers/resources)

---

# 4. URI Does Not Mean URL

A URI is an **identifier**. A URL is a URI that also describes where and how
something can be accessed.

This resource:

```text
docs://arithmetic/operations
```

does not need to exist on the public internet.

The client sends that identifier to the MCP server:

```text
Client
  │
  │ resources/read:
  │ docs://arithmetic/operations
  ▼
MCP server
  │
  ▼
arithmetic_operations()
```

The `docs` and `math` schemes are application-defined URI schemes. MCP permits
resources to use standard or custom URI
schemes. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/server/resources)

Professional wording:

> “The URI is a logical resource identifier, not necessarily a directly
> dereferenceable web URL.”

---

# 5. Why Return JSON as a String?

Our resource declares:

```python
mime_type = "application/json"
```

and returns:

```python
json.dumps(...)
```

This creates a clear representation contract:

```text
Resource identity:
docs://arithmetic/operations

Representation:
application/json text
```

That distinction matters:

- The URI identifies the resource.
- The MIME type describes its representation.
- The function creates the current representation.

Professional wording:

> “The resource URI identifies the logical entity, while the MIME type describes
> the returned representation.”

Resources can return text or binary content. FastMCP converts the function
result into the corresponding MCP resource
content. [FastMCP](https://gofastmcp.com/servers/resources)

---

# 6. Resource Annotations

We added:

```python
annotations = {
    "readOnlyHint": True,
    "idempotentHint": True,
}
```

## `readOnlyHint`

Reading the resource should not alter external state.

```text
Read integer profile
        │
        └── No database mutation
            No email sent
            No file changed
```

## `idempotentHint`

Repeated reads have no additional side effects:

```text
Read once    → same environmental effect
Read 10 times → same environmental effect
```

These annotations are advisory metadata. They help clients understand behavior
but do not enforce it. The implementation must actually remain read-only and
idempotent. [FastMCP](https://gofastmcp.com/servers/resources)

Professional wording:

> “The annotations communicate behavioral semantics to the client but are not an
> enforcement mechanism.”

---

# 7. Update the stdio client

Create or replace `test_stdio_client.py`:

```python
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

PROJECT_ROOT = Path(__file__).resolve().parent
SERVER_FILE = PROJECT_ROOT / "server.py"


def text_content(item: Any) -> str:
    """Extract human-readable text from an MCP content object."""
    text = getattr(item, "text", None)

    if text is not None:
        return text

    return str(item)


async def main() -> None:
    print(f"Client PID: {os.getpid()}")

    transport = PythonStdioTransport(
        str(SERVER_FILE),
        env={
            "APP_ENV": "development",
        },
    )

    async with Client(transport) as client:
        # ------------------------------------------------------------------
        # Discover all three MCP primitive types
        # ------------------------------------------------------------------

        tools = await client.list_tools()
        resources = await client.list_resources()
        resource_templates = await client.list_resource_templates()
        prompts = await client.list_prompts()

        print("\nTools:")
        for tool in tools:
            print(f"- {tool.name}")

        print("\nStatic resources:")
        for resource in resources:
            print(f"- {resource.name}: {resource.uri}")

        print("\nResource templates:")
        for template in resource_templates:
            print(f"- {template.name}")

        print("\nPrompts:")
        for prompt in prompts:
            print(f"- {prompt.name}")

        # ------------------------------------------------------------------
        # Read a static resource
        # ------------------------------------------------------------------

        operation_docs = await client.read_resource(
            "docs://arithmetic/operations"
        )

        print("\nArithmetic documentation:")
        for item in operation_docs:
            print(text_content(item))

        # ------------------------------------------------------------------
        # Read a dynamically generated resource
        # ------------------------------------------------------------------

        integer_data = await client.read_resource(
            "math://integer/42/profile"
        )

        print("\nInteger profile:")
        for item in integer_data:
            print(text_content(item))

        # ------------------------------------------------------------------
        # Retrieve a rendered prompt
        # ------------------------------------------------------------------

        prompt_result = await client.get_prompt(
            "explain_arithmetic",
            {
                "operation": "multiply",
                "a": 6,
                "b": 7,
                "audience": "beginner",
            },
        )

        print("\nRendered prompt:")

        for message in prompt_result.messages:
            print(f"Role: {message.role}")
            print(text_content(message.content))


if __name__ == "__main__":
    asyncio.run(main())
```

Run:

```bash
uv run python test_stdio_client.py
```

FastMCP clients expose separate operations for listing tools, resources,
resource templates, and prompts; reading a resource uses its URI, while
rendering a prompt uses its registered name and argument
object. [FastMCP](https://gofastmcp.com/v2/clients/resources)

---

# 8. Expected Output

The exact formatting may differ, but the result should resemble:

```text
Client PID: 12000

Tools:
- add
- multiply
- server_process_info

Static resources:
- ArithmeticOperations: docs://arithmetic/operations

Resource templates:
- IntegerProfile

Prompts:
- explain_arithmetic

Arithmetic documentation:
{
  "operations": {
    "add": {
      "description": "Add two integers.",
      "symbol": "+",
      "example": "20 + 22 = 42"
    },
    "multiply": {
      "description": "Multiply two integers.",
      "symbol": "×",
      "example": "6 × 7 = 42"
    }
  }
}

Integer profile:
{
  "value": 42,
  "sign": "positive",
  "parity": "even",
  "absolute_value": 42,
  "square": 1764
}

Rendered prompt:
Role: user
Explain how to multiply 6 and 7 to a beginner audience.

Requirements:
1. Show the calculation step by step.
2. Explain why each step is valid.
3. State the final answer clearly.
4. Include one similar practice problem.
5. Do not assume prior knowledge.
```

Notice what did **not** happen:

```text
Prompt retrieved
      │
      ▼
Messages returned

No LLM was called.
No explanation was generated.
```

The result is merely a prepared message that a host could subsequently send to a
model.

---

# 9. Protocol Operations

Your client code maps conceptually to these protocol operations:

| Python client call          | MCP operation               |
|-----------------------------|-----------------------------|
| `list_tools()`              | `tools/list`                |
| `call_tool()`               | `tools/call`                |
| `list_resources()`          | `resources/list`            |
| `list_resource_templates()` | Resource-template discovery |
| `read_resource()`           | `resources/read`            |
| `list_prompts()`            | `prompts/list`              |
| `get_prompt()`              | `prompts/get`               |

This separation matters because discovery and execution are different phases:

```text
Discovery
├── What tools exist?
├── What resources exist?
└── What prompts exist?

Usage
├── Call a tool
├── Read a resource
└── Render a prompt
```

Professional wording:

> “MCP separates capability discovery from capability consumption.”

---

# 10. The Coding Thought Process

## Step 1: Classify the capability

Before writing a decorator, ask:

```text
Does it change or perform something?
    └── Tool

Does it provide readable context?
    └── Resource

Does it provide a reusable user-selectable instruction?
    └── Prompt
```

Do not choose based on convenience.

---

## Step 2: Decide whether the resource is static or parameterized

One known document:

```text
docs://arithmetic/operations
```

Use a static resource.

A family of related documents:

```text
math://integer/{value}/profile
```

Use a resource template.

---

## Step 3: Design the identifier before the handler

We chose:

```text
math://integer/{value}/profile
```

instead of something vague:

```text
data://get
```

A good resource URI should communicate:

- Domain
- Entity
- Identifier
- Representation or view

General pattern:

```text
scheme://entity/{identifier}/view
```

Examples:

```text
customer://profile/{customer_id}
database://schema/{table_name}
repository://{owner}/{repo}/readme
deployment://service/{service_name}/status
```

---

## Step 4: Keep retrieval side-effect free

This would be bad:

```python
@mcp.resource("customer://{id}/profile")
def get_customer(id: str) -> str:
    mark_customer_as_contacted(id)
    return load_customer(id)
```

A read unexpectedly performs a write.

Better:

```python
@mcp.resource("customer://{id}/profile")
def get_customer(id: str) -> str:
    return load_customer(id)
```

A resource read should behave like a query, not a command.

---

## Step 5: Separate prompt retrieval from model execution

Our prompt function does this:

```text
Arguments
    │
    ▼
Template rendering
    │
    ▼
Prompt messages
```

It does not do this:

```text
Arguments
    │
    ▼
Call OpenAI/Anthropic/other model
    │
    ▼
Generated answer
```

That distinction prevents hidden model calls, surprise cost, and unclear
lifecycle ownership.

Professional wording:

> “The MCP server owns prompt composition; the host owns model execution.”

---

# 11. Resource vs Tool: Practical Decision Test

Suppose the server accesses customer data.

## Get customer profile

Usually a resource:

```text
customer://profile/123
```

because it represents readable context.

## Search customers

Often a tool:

```python
search_customers(query: str)
```

because search is an operation with arguments and potentially expensive
execution.

## Update customer email

Definitely a tool:

```python
update_customer_email(customer_id: str, email: str)
```

because it changes state.

## Customer-support response template

A prompt:

```python
draft_customer_response(customer_name: str, issue: str)
```

because it creates reusable model instructions.

---

# 12. Query–Command Separation

A useful architecture principle is **Command Query Separation**:

```text
Query
├── Reads information
└── Does not change state

Command
├── Performs an operation
└── May change state
```

Mapped loosely to MCP:

```text
Query-like capability   → Resource
Command-like capability → Tool
Workflow template       → Prompt
```

This mapping is not absolute. A complex parameterized query may still be more
practical as a tool. For example:

```python
search_orders(
    customer_id: str,
start_date: str,
end_date: str,
statuses: list[str],
)
```

Forcing that into a URI would produce an awkward interface.

The uncomfortable truth: **not every read should be a resource**.

Use a resource when the data has a meaningful identity. Use a tool when the
client is performing a computation, search, or operation.

---

# 13. Failure Experiments

## Invalid resource URI

Add to the client:

```python
await client.read_resource(
    "docs://arithmetic/does-not-exist"
)
```

Expected category:

```text
Resource resolution error
```

The transport still works. The requested resource does not exist.

---

## Invalid template value

```python
await client.read_resource(
    "math://integer/not-a-number/profile"
)
```

Expected category:

```text
Resource parameter validation error
```

The URI matches the template shape, but `not-a-number` cannot satisfy:

```python
value: int
```

---

## Invalid prompt argument

```python
await client.get_prompt(
    "explain_arithmetic",
    {
        "operation": "divide",
        "a": 10,
        "b": 2,
    },
)
```

Expected category:

```text
Prompt rendering application error
```

The MCP prompt exists, and its arguments are structurally valid, but the
application rejects the unsupported operation.

---

## Missing required prompt argument

```python
await client.get_prompt(
    "explain_arithmetic",
    {
        "operation": "add",
        "a": 10,
    },
)
```

Expected category:

```text
Prompt argument validation error
```

`b` is required by the function signature.

---

# 14. Professional Vocabulary

| Term                           | Meaning                                              |
|--------------------------------|------------------------------------------------------|
| **Resource URI**               | Unique identifier for readable MCP content           |
| **Resource representation**    | Content returned when a resource is read             |
| **MIME type**                  | Machine-readable description of the content format   |
| **Resource template**          | URI pattern that generates parameterized resources   |
| **URI scheme**                 | Prefix identifying the URI namespace, such as `docs` |
| **Dereference**                | Resolve an identifier into its content               |
| **Lazy evaluation**            | Generate content only when requested                 |
| **Application-driven context** | Host decides how resources enter model context       |
| **Prompt template**            | Reusable parameterized message definition            |
| **Prompt rendering**           | Converting prompt arguments into messages            |
| **Capability discovery**       | Listing server-exposed functionality                 |
| **Command Query Separation**   | Separating state changes from read operations        |
| **Idempotent**                 | Repeating an operation causes no additional effect   |
| **Side effect**                | Observable state change beyond returning a value     |
| **Logical identifier**         | Identity independent of physical storage location    |
| **Representation contract**    | Agreement about content type and structure           |

A professional summary:

> “I expanded the MCP surface beyond executable tools by adding a static
> resource, a parameterized resource template, and a reusable prompt. Resource
> URIs model stable application data identities, while prompt rendering remains
> separate from downstream LLM execution. The client independently discovers and
> consumes each MCP primitive over the existing stdio transport.”

---

# Completion Check

```text
[ ] Current client uses PythonStdioTransport
[ ] Three tools are discoverable
[ ] One static resource is discoverable
[ ] One resource template is discoverable
[ ] One prompt is discoverable
[ ] Static JSON resource can be read
[ ] Resource template resolves value=42
[ ] Prompt arguments render a user message
[ ] Invalid integer URI produces an error
[ ] Unsupported prompt operation produces an error
[ ] Server logs remain on stderr
```

The next increment introduces a small service layer and asynchronous I/O so the
MCP decorators stop containing application logic. That separation is necessary
before adding HTTP, FastAPI lifecycle management, and shared infrastructure
resources.