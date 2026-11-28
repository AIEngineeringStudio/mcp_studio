# Lesson 10 — Pagination + Completion

These solve two different scaling problems:

```
PAGINATION
"How do I list a very large MCP catalog without returning everything at once?"

COMPLETION
"How do I help a user fill a Prompt argument or Resource Template parameter?"
```

They are easy to confuse because both return partial sets, but the semantics are very different:

```
Pagination
    → divide a large collection into pages

Completion
    → suggest likely argument values
```

---

# Part A — Pagination

## 1. First principle: list operations can become large

Imagine an MCP server exposing:

```
5 tools
```

Returning them all is trivial.

Now imagine a server dynamically exposing:

```
25,000 resources
3,000 tools
900 prompts
```

A naïve:

```
tools/list
```

returning everything causes:

```
large response
high serialization cost
high memory use
slow initial discovery
unnecessary network transfer
```

MCP therefore supports cursor pagination for the major list operations. In `2026-07-28`, `tools/list`, `resources/list`, `resources/templates/list`, and `prompts/list` all use the common paginated request shape. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema)

---

# 2. MCP uses cursors, not page numbers

Do not think:

```
page=1
page=2
page=3
```

The protocol uses:

```
cursor
```

Example:

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "method": "tools/list",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {}
    },
    "cursor": "eyJwYWdlIjogMn0="
  }
}
```

The cursor is explicitly defined as an **opaque token representing a pagination position**. Clients should pass it back unchanged rather than inspecting or modifying it. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema)

Professional wording:

> **“MCP uses opaque cursor-based pagination rather than client-controlled numeric offsets.”**

---

# 3. Why opaque?

Suppose internally your server currently encodes:

```
cursor = base64(offset=100)
```

Later you switch to:

```
cursor =
    database continuation key
    +
    snapshot ID
    +
    tenant ID
```

If clients treated your cursor as:

```
"page 3"
```

you could not safely change the implementation.

Opaque means:

```
CLIENT

receive cursor
      │
      ▼
store cursor
      │
      ▼
send exact cursor back


DO NOT:

decode
modify
increment
interpret
```

That protects the server's pagination implementation from becoming part of the public contract. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema)

---

# 4. Protocol response

Suppose the server has six tools and returns two at a time.

First response:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "complete",
    "tools": [
      {
        "name": "tool_a",
        "inputSchema": {
          "type": "object"
        }
      },
      {
        "name": "tool_b",
        "inputSchema": {
          "type": "object"
        }
      }
    ],
    "nextCursor": "cursor-2",
    "ttlMs": 60000,
    "cacheScope": "public"
  }
}
```

If `nextCursor` exists:

```
there is another page
```

If it is absent:

```
end of collection
```

Modern list results also contain cache hints such as `ttlMs` and `cacheScope`. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema)

---

# 5. Client loop

Raw protocol thinking:

```python
cursor = None

while True:
    response = list_tools(
        cursor=cursor
    )

    process(response.tools)

    cursor = response.next_cursor

    if cursor is None:
        break
```

Conceptually:

```
tools/list
    │
    ▼
page 1
nextCursor=A
    │
    ▼
tools/list(cursor=A)
    │
    ▼
page 2
nextCursor=B
    │
    ▼
tools/list(cursor=B)
    │
    ▼
page 3
no nextCursor
    │
    ▼
done
```

---

# 6. Why cursors beat offsets in distributed systems

Imagine:

```
catalog before page 1

A B C D E F
```

Client fetches:

```
A B
```

Then somebody inserts:

```
X
```

at the front:

```
X A B C D E F
```

A naïve numeric:

```
offset=2
```

can now produce duplicates or omissions depending on ordering.

A sufficiently well-designed cursor can instead encode server-side continuation information or snapshot state.

That behavior is an implementation choice rather than something MCP mandates, but it explains why protocols generally expose opaque cursors instead of exposing their internal indexing strategy.

Professional vocabulary:

- **cursor pagination**
- **offset pagination**
- **continuation token**
- **stable ordering**
- **snapshot consistency**

---

# 7. Raw server implementation

A simplified manual implementation:

```python
TOOLS = [
    {"name": "tool_a"},
    {"name": "tool_b"},
    {"name": "tool_c"},
    {"name": "tool_d"},
    {"name": "tool_e"},
]

PAGE_SIZE = 2
```

Then:

```python
elif method == "tools/list":
    params = message.get("params", {})

    cursor = params.get("cursor")

    if cursor is None:
        start = 0
    else:
        start = decode_cursor(cursor)

    end = start + PAGE_SIZE

    tools = TOOLS[start:end]

    result = {
        "resultType": "complete",
        "tools": tools,
        "ttlMs": 0,
        "cacheScope": "private",
    }

    if end < len(TOOLS):
        result["nextCursor"] = encode_cursor(end)

    success(
        request_id,
        result,
    )
```

Now your server owns:

```
cursor creation
cursor validation
page sizing
ordering
end detection
cache semantics
```

FastMCP removes most of this boilerplate.

---

# 8. FastMCP pagination

FastMCP exposes pagination at server construction time:

```python
from fastmcp import FastMCP


mcp = FastMCP(
    "LargeServer",
    list_page_size=2,
)
```

When `list_page_size` is configured, FastMCP paginates:

```
tools/list
resources/list
resources/templates/list
prompts/list
```

using the same maximum page size. By default FastMCP returns all components in one response for compatibility. [FastMCP](https://gofastmcp.com/servers/pagination)

---

# 9. Working pagination server

```python
from fastmcp import FastMCP


mcp = FastMCP(
    "PaginationDemo",
    list_page_size=2,
)


@mcp.tool
def alpha() -> str:
    return "alpha"


@mcp.tool
def beta() -> str:
    return "beta"


@mcp.tool
def gamma() -> str:
    return "gamma"


@mcp.tool
def delta() -> str:
    return "delta"


@mcp.tool
def epsilon() -> str:
    return "epsilon"


if __name__ == "__main__":
    mcp.run()
```

Five tools, page size two:

```
page 1
alpha
beta

page 2
gamma
delta

page 3
epsilon
```

FastMCP internally creates opaque cursors for those pages. [FastMCP](https://gofastmcp.com/servers/pagination)

---

# 10. FastMCP client: high-level API hides pagination

This:

```python
from fastmcp import Client


async with Client(
    "pagination_server.py"
) as client:

    tools = await client.list_tools()

    print(len(tools))
```

returns the complete list.

FastMCP automatically follows all `nextCursor` values behind the scenes. [FastMCP](https://gofastmcp.com/servers/pagination)

So:

```
client.list_tools()
       │
       ▼
tools/list
       │
       ▼
page 1
nextCursor
       │
       ▼
tools/list(cursor)
       │
       ▼
page 2
       │
       ▼
...
       │
       ▼
merged Python list
```

This is another important abstraction:

> **One Python method call may represent multiple MCP requests.**

---

# 11. Peel the abstraction with `_mcp`

FastMCP lets you access the raw pagination model:

```python
async with Client(
    "pagination_server.py"
) as client:

    page = await client.list_tools_mcp()

    print(
        [tool.name for tool in page.tools]
    )

    while page.next_cursor:
        page = await client.list_tools_mcp(
            cursor=page.next_cursor
        )

        print(
            [tool.name for tool in page.tools]
        )
```

FastMCP documents `_mcp` list methods for manual pagination, while the high-level methods auto-fetch everything. [FastMCP](https://gofastmcp.com/servers/pagination)

Available equivalents include:

```
list_tools_mcp()
list_resources_mcp()
list_resource_templates_mcp()
list_prompts_mcp()
``` :chatgpt-content-reference{index="8"}


---

# 12. When manual pagination is preferable

Auto-pagination is convenient:

```python
tools = await client.list_tools()
```

But imagine:

```
500,000 resources
```

Fetching every page defeats the purpose.

Manual pagination lets you:

```
process one page
release memory
stop early
show progress
apply filtering incrementally
```

FastMCP explicitly recommends manual `_mcp` pagination when incremental processing or early termination matters. [FastMCP](https://gofastmcp.com/servers/pagination)

---

# 13. Pagination + caching

Modern MCP list results can include:

```
ttlMs
cacheScope
```

For example:

```json
{
  "ttlMs": 60000,
  "cacheScope": "public"
}
```

FastMCP clients can optionally cache list results with:

```python
Client(
    server,
    cache=True,
)
```

and honor the server's cache hints on modern connections. [FastMCP](https://gofastmcp.com/clients/client)

Conceptually:

```
list_tools()
    │
    ├── valid cached result?
    │       └── return cache
    │
    └── otherwise
            │
            ▼
          server
```

Pagination and caching therefore solve different problems:

```
Pagination
→ response size

Caching
→ repeated network work
```

---

# Part B — Argument Completion

Completion is completely different.

Suppose you have:

```python
@mcp.prompt
def analyze_language(
    language: str
):
```

A UI could show:

```
Language: [ py____ ]
```

The server may suggest:

```
python
pytorch
pyside
```

This is MCP **argument completion**.

---

# 14. Completion only targets Prompt arguments and Resource Template parameters

At protocol level, a completion request references either:

```
PromptReference
```

or:

```
ResourceTemplateReference
```

It does **not** target Tool arguments. The `CompleteRequestParams` schema accepts only those two reference types. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema)

So:

```
Prompt
review_code(language)
      │
      └── completion supported


Resource Template
github://{owner}/{repo}
      │
      └── completion supported


Tool
search(query)
      │
      └── no MCP completion primitive
```

This distinction is worth memorizing.

---

# 15. Protocol-level `completion/complete`

Client:

```json
{
  "jsonrpc": "2.0",
  "id": "completion-1",
  "method": "completion/complete",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {}
    },
    "ref": {
      "type": "ref/prompt",
      "name": "code_review"
    },
    "argument": {
      "name": "language",
      "value": "py"
    }
  }
}
```

The key idea:

```
argument.name
    → what field are we completing?

argument.value
    → what has the user typed so far?
```

That structure is defined directly in modern MCP. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema)

---

# 16. Response

Server:

```json
{
  "jsonrpc": "2.0",
  "id": "completion-1",
  "result": {
    "resultType": "complete",
    "completion": {
      "values": [
        "python",
        "pytorch",
        "pyside"
      ],
      "total": 10,
      "hasMore": true
    }
  }
}
```

Completion results contain:

```
values
total
hasMore
```

and a single response may contain at most 100 suggested values. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema)

---

# 17. Completion is not pagination

This subtle difference matters.

Pagination uses:

```
nextCursor
```

Completion uses:

```
hasMore
```

Why?

Pagination means:

```
"Fetch the next chunk."
```

Completion usually means:

```
"Narrow your query by typing more."
```

So:

```
LIST PAGINATION

values
nextCursor
    │
    ▼
client fetches next page


COMPLETION

values
hasMore=true
    │
    ▼
user types more characters
    │
    ▼
new completion query
```

There is no `nextCursor` in MCP completion results. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema)

---

# 18. FastMCP completion abstraction

FastMCP gives the server one global completion handler:

```python
@mcp.completion
def complete(
    ref,
    argument,
    context,
):
    ...
```

The framework dispatches all Prompt and Resource Template completion requests through it. Registering a handler also advertises completion support. [FastMCP](https://gofastmcp.com/servers/completions)

---

# 19. Working Prompt completion example

```python
from fastmcp import FastMCP
from mcp.types import PromptReference


mcp = FastMCP("CompletionDemo")


LANGUAGES = [
    "python",
    "pytorch",
    "pyside",
    "javascript",
    "java",
    "julia",
]


@mcp.prompt
def code_review(
    language: str,
) -> str:
    return (
        f"Review this code as "
        f"{language} code."
    )


@mcp.completion
def complete(
    ref,
    argument,
    context,
):
    if (
        isinstance(
            ref,
            PromptReference,
        )
        and ref.name == "code_review"
        and argument.name == "language"
    ):
        prefix = argument.value.lower()

        return [
            language
            for language in LANGUAGES
            if language.startswith(prefix)
        ]

    return None
```

If the client asks:

```
language="py"
```

FastMCP returns:

```
python
pytorch
pyside
```

Returning a simple `list[str]` is automatically wrapped into an MCP completion response. Returning `None` produces an empty completion set. [FastMCP](https://gofastmcp.com/servers/completions)

---

# 20. Peel that abstraction

This:

```python
@mcp.completion
def complete(...):
```

handles protocol traffic equivalent to:

```
completion/complete
       │
       ▼
identify ref
       │
       ├── PromptReference
       └── ResourceTemplateReference
       │
       ▼
identify argument
       │
       ▼
read partial value
       │
       ▼
compute candidates
       │
       ▼
Completion
       │
       ▼
CompleteResult
```

FastMCP removes:

```
protocol routing
reference parsing
result construction
capability declaration
```

---

# 21. Resource Template completion

Recall:

```python
@mcp.resource(
    "github://{owner}/{repo}"
)
def repo_readme(
    owner: str,
    repo: str,
):
    ...
```

Suppose repositories are:

```python
REPOS_BY_OWNER = {
    "prefecthq": [
        "fastmcp",
        "prefect",
        "marvin",
    ],
    "python": [
        "cpython",
        "mypy",
    ],
}
```

Completion:

```python
from mcp.types import (
    ResourceTemplateReference,
)


@mcp.completion
def complete(
    ref,
    argument,
    context,
):
    if not isinstance(
        ref,
        ResourceTemplateReference,
    ):
        return None

    if (
        ref.uri
        != "github://{owner}/{repo}"
    ):
        return None

    if argument.name != "repo":
        return None

    owner = None

    if (
        context
        and context.arguments
    ):
        owner = context.arguments.get(
            "owner"
        )

    candidates = (
        REPOS_BY_OWNER.get(
            owner or "",
            [],
        )
    )

    return [
        repo
        for repo in candidates
        if repo.startswith(
            argument.value
        )
    ]
```

FastMCP exposes previously resolved arguments through `context.arguments`, allowing one suggestion to depend on earlier selections. [FastMCP](https://gofastmcp.com/servers/completions)

---

# 22. Why completion context exists

Suppose the URI is:

```
github://{owner}/{repo}
```

The user chooses:

```
owner = prefecthq
```

Then types:

```
repo = f
```

Without context, the server would search:

```
every repo from every owner
```

With context:

```
owner=prefecthq
        │
        ▼
candidate universe:
fastmcp
prefect
marvin
        │
        ▼
prefix=f
        │
        ▼
fastmcp
```

This is **dependent completion**.

Professional terms:

- **context-sensitive completion**
- **dependent autocomplete**
- **resolved argument context**

---

# 23. Returning more than a simple list

For richer responses:

```python
from mcp.types import Completion
```

Then:

```python
@mcp.completion
def complete(
    ref,
    argument,
    context,
):
    matches = search_candidates(
        argument.value
    )

    return Completion(
        values=matches[:100],
        total=len(matches),
        has_more=(
            len(matches) > 100
        ),
    )
```

FastMCP accepts either a `list[str]`, `None`, or an explicit `Completion` object. The explicit form lets you communicate that the candidate list has been truncated. [FastMCP](https://gofastmcp.com/servers/completions)

---

# 24. Do not return 100,000 suggestions

Completion is a UI assistance mechanism.

Bad:

```
user types:

""

server returns:

83,000 customer names
```

Besides the protocol's 100-value response cap, this is poor UX. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema)

Prefer:

```
empty prefix
→ perhaps no suggestions / top few

"p"
→ shortlist

"py"
→ narrower shortlist

"pyt"
→ very narrow shortlist
```

This is often called:

> **prefix filtering**

or more generally:

> **incremental search**

---

# 25. Completion is not validation

Suppose suggestions are:

```
production
staging
development
```

The user manually enters:

```
banana
```

Completion itself does not necessarily make `banana` invalid.

Think:

```
COMPLETION
"What values might be useful?"


VALIDATION
"What values are actually allowed?"
```

If something is strictly constrained, encode that constraint in the underlying Prompt/Resource design or application logic rather than assuming autocomplete is an enforcement layer.

Professional phrase:

> **“Autocomplete is advisory; validation is authoritative.”**

---

# 26. Completion has an authorization trap

FastMCP uses one global completion handler. It does not automatically resolve the referenced Prompt or Resource Template and apply that component's per-component visibility before calling your handler. If your completion candidates themselves contain restricted information, your handler needs to enforce authorization explicitly. [FastMCP](https://gofastmcp.com/servers/completions)

Example bad design:

```python
@mcp.completion
def complete(...):
    return [
        "secret-project-alpha",
        "secret-project-beta",
    ]
```

for every authenticated user.

Even if the underlying resource is protected, the completion itself leaks names.

Professional phrase:

> **“Completion introduces a metadata-enumeration surface.”**

---

# 27. Pagination vs Completion — side by side

| Dimension | Pagination | Completion |
|---|---|---|
| Purpose | Split large collections | Suggest argument values |
| Request field | `cursor` | partial `argument.value` |
| Continuation signal | `nextCursor` | `hasMore` |
| Client action | fetch next page | type/refine input |
| Target | tools/resources/templates/prompts lists | Prompt args + Resource Template params |
| Ordering | server-defined | usually relevance/prefix-based |
| FastMCP server abstraction | `list_page_size=` | `@mcp.completion` |
| FastMCP client abstraction | auto-pagination | `Client.complete()` |

MCP's modern completion request only accepts Prompt and Resource Template references, while list operations use the shared opaque-cursor mechanism. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema)

---

# 28. Architecture example combining both

Imagine a GitHub-style MCP server.

```
SERVER
│
├── 20,000 resources
│
├── resource template
│     github://{owner}/{repo}
│
└── completion handler
```

When discovering concrete resources:

```
resources/list
       │
       ▼
PAGINATION
```

When filling:

```
github://prefecthq/{repo}
                      │
                      ▼
COMPLETION
```

These address two entirely different scalability problems.

---

# 29. Professional vocabulary checkpoint

| Term | Meaning |
|---|---|
| **Cursor** | Opaque pagination continuation token |
| **Opaque token** | Token whose internal meaning is hidden from the client |
| **Continuation token** | Value used to resume listing from a position |
| **Page size** | Maximum items returned per page |
| **Auto-pagination** | Client automatically follows all cursors |
| **Manual pagination** | Caller explicitly processes each cursor/page |
| **Catalog discovery** | Listing tools/resources/prompts/templates |
| **Completion** | Argument-value suggestion mechanism |
| **Partial value** | Text entered by the user so far |
| **Completion candidate** | Suggested argument value |
| **Completion context** | Previously resolved argument values |
| **Dependent completion** | Suggestions influenced by another argument |
| **Prefix filtering** | Suggesting values beginning with typed input |
| **Autocomplete** | UI built on top of completion suggestions |
| **Metadata enumeration** | Learning names/identifiers through discovery APIs |

A strong explanation:

> **“MCP list operations scale through opaque cursor pagination: the server returns `nextCursor`, and the client passes it back unchanged. FastMCP can enable this globally with `list_page_size`, while its high-level client automatically follows cursors. Argument completion is a separate protocol utility: `completion/complete` targets Prompt arguments or Resource Template parameters, with FastMCP routing those requests through one `@mcp.completion` handler.”** [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/schema)

---

# Hands-on assignment

Build one server containing:

```
5 tools
page size = 2

1 prompt:
code_review(language)

1 resource template:
github://{owner}/{repo}

1 completion handler
```

Then test:

1. `client.list_tools()` and verify you receive all five tools.
2. Use `list_tools_mcp()` and observe three separate pages.
3. Print every `next_cursor`.
4. Do **not** decode or modify a cursor.
5. Add 200 candidate languages and return only 100.
6. Set `total` and `has_more`.
7. Complete `repo` based on the already selected `owner`.
8. Ask for completion on an unknown Prompt and return `None`.
9. Add authorization to the completion handler.
10. Explain why `hasMore=true` does **not** mean “call me with a cursor.”

The conceptual test is:

```
cursor
    ≠
nextCursor
    ≠
partial argument
    ≠
CompletionContext
    ≠
hasMore
```

## Next lesson — Transports: stdio vs Streamable HTTP

This should be the next major lesson because everything we've built so far eventually travels over a transport.

We'll cover:

```
stdio framing
subprocess lifecycle
stdout/stderr discipline

Streamable HTTP
POST /mcp
SSE response streams
request correlation
cancellation semantics
stateless 2026-07-28 requests
headers and protocol versioning

FastMCP:
mcp.run()
mcp.run(transport="http")
Client transport selection
local vs remote deployment
```

That lesson will connect the **protocol model** we've built to the actual bytes and network topology.