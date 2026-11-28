# Lesson 10 — Pagination, caching, and completion

## Outcome

After this lesson, you can consume a paginated list, honor modern cache hints,
and distinguish argument completion from validation.

## Pagination uses opaque cursors

List methods can return more data than one response should carry. MCP uses
opaque cursors rather than page numbers.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "complete",
    "tools": [],
    "nextCursor": "opaque-next-page-token",
    "ttlMs": 300000,
    "cacheScope": "public"
  }
}
```

The client sends the returned value unchanged:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {"cursor": "opaque-next-page-token"}
}
```

Do not parse a cursor, construct one on the client, or assume it is a numeric
offset. Servers should protect cursor integrity and bind it to the relevant
query, authorization, and expiry.

## Modern cache hints

Cacheable complete results from `server/discover`, list methods, and
`resources/read` must include:

- `ttlMs`: how long an eligible result can be cached;
- `cacheScope`: whether the result is safe for public or private reuse.

```
request identity + authorization + method + parameters
                         |
                         v
                   cache key and scope
```

Never mark identity-specific or permission-filtered content public. A cache
must not leak a tool or resource catalog from one principal to another.

`input_required` results and MRTR retries containing `inputResponses` or
`requestState` are not cacheable.

Change notifications can invalidate cached catalogs before their TTL expires.
Modern clients opt into list changes through `subscriptions/listen`.

## Argument completion

`completion/complete` suggests values for:

- prompt arguments;
- resource-template parameters.

It does not complete arbitrary tool arguments.

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "completion/complete",
  "params": {
    "ref": {"type": "ref/prompt", "name": "triage_ticket"},
    "argument": {"name": "ticket_id", "value": "T-"}
  }
}
```

A completion result can contain suggested values, a total, and a flag showing
whether more values exist. Keep suggestions bounded and authorization-aware.

## Completion is not validation

```
completion -> helps a user choose
validation -> decides whether supplied input is acceptable
```

A client can ignore suggestions and send another value. The server must still
validate the final prompt argument or resource URI.

Completion can use previously supplied argument values as context. Treat that
context as untrusted and do not reveal suggestions the caller is not allowed to
discover.

## FastMCP completion handler

FastMCP declares the completions capability when a handler is registered. The
handler still filters suggestions according to application authorization.

```python
from fastmcp import FastMCP
from mcp_types import PromptReference

mcp = FastMCP("Ticket completion")


@mcp.prompt
def triage_ticket(ticket_id: str) -> str:
    return f"Triage {ticket_id}."


@mcp.completion
def complete_ticket_id(ref, argument, _context):
    allowed = ["T-100", "T-101", "T-200"]
    if isinstance(ref, PromptReference) and ref.name == "triage_ticket":
        if argument.name == "ticket_id":
            return [item for item in allowed if item.startswith(argument.value)]
    return None
```

## Hands-on checkpoint

**Execution boundary:**

> Mixed. Cursor pagination is a plain-Python application model; completion is
> a real in-memory MCP `completion/complete` request.

Run the focused exercise from the repository root. It follows an
integrity-protected opaque cursor until `next_cursor` is absent, then sends a
real `completion/complete` request through FastMCP:

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python verify_pagination_completion.py
```

Expected output:

```
pagination: followed opaque cursors and collected all five tickets
completion: T-2 -> ['T-200', 'T-201']
validation remains required for the final supplied argument
```

The complete runnable exercise is
[`verify_pagination_completion.py`](labs/verify_pagination_completion.py).
The paginator is a small application model; the completion call uses the real
MCP client and server APIs.

For deeper cache and invalidation rules, read:

- [`../concepts/26-pagination-cache.md`](../../../01-mcp-concepts/guides/26-pagination-cache.md)

**Say it professionally:**

> MCP pagination uses server-issued opaque cursors. Modern results can also
> carry explicit TTL and cache-scope hints, while completion supplies bounded,
> authorization-aware suggestions without replacing validation.

## Official references

- [Pagination](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/pagination)
- [Caching](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/caching)
- [Completion](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/completion)

