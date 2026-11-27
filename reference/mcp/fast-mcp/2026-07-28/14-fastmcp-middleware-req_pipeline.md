# Lesson 14 — FastMCP middleware and the request pipeline

## Outcome

After this lesson, you can place cross-cutting behavior in middleware, explain
ordering, and keep middleware separate from MCP protocol semantics.

## Middleware is a framework feature

The client still sends standard MCP methods such as `tools/call` or
`resources/read`. Middleware is FastMCP's internal interception pipeline.

```
MCP request
  -> outer middleware before
    -> inner middleware before
      -> component handler
    <- inner middleware after
  <- outer middleware after
MCP result
```

Use middleware for behavior that crosses many components:

- request correlation and timing;
- audit evidence;
- rate limiting;
- broad authentication or authorization checks;
- safe error mapping;
- carefully scoped caching;
- response-size limits.

Keep domain rules in services or dependencies. A tool-specific ownership check
usually belongs near the business operation, not only in generic middleware.

## The continuation contract

A middleware hook receives a context and a `call_next` function. Calling
`call_next` continues the pipeline; omitting it short-circuits the request.

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext


class ToolAuditMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        return result
```

This minimal example changes nothing. Real middleware should record safe,
structured fields and preserve cancellation.

## Ordering changes behavior

```
error mapping
  -> tracing/timing
    -> authentication
      -> rate limit
        -> authorization
          -> cache
            -> handler
```

This is a design example, not a universal order. Ask concrete questions:

- Should denied requests count against the rate limit?
- Should cache hits appear in timing metrics?
- Is the cache keyed by identity, tenant, scopes, protocol version, method,
  component, and arguments?
- Does error middleware preserve cancellation rather than convert it to
  success?

## Caching danger

Never cache mutating tool calls indiscriminately. For read results, include all
security-relevant request dimensions in the key and honor the result's cache
scope. A public cache entry must never contain caller-specific data.

Discovery filtering is not authorization. Even if middleware removes a tool
from `tools/list`, direct `tools/call` must be denied through the same policy.

## Retry danger

Middleware must not retry a side-effecting call merely because the transport
failed. The operation may have committed before the response was lost. Retry
only when the business contract is idempotent or uses a safe idempotency key and
outcome lookup.

## Middleware and protocol eras

A FastMCP 4 server can serve modern and legacy clients. Middleware may inspect
request context when behavior truly differs by era, but application rules
should not depend on user-agent guessing. Negotiate protocol behavior and test
both paths explicitly.

## Hands-on checkpoint

**Execution boundary:**

> In-memory MCP. This isolates FastMCP's middleware ordering around real tool
> dispatch.

Run the focused middleware exercise from the repository root. It records the
before/handler/after order and compares the tool schema before and after the
call:

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python verify_middleware.py
```

Expected output:

```
middleware order: before -> tool handler -> after
tool schema and client call stayed unchanged
```

The complete runnable exercise is
[`verify_middleware.py`](labs/verify_middleware.py). It keeps diagnostics in
an in-memory list, so it cannot corrupt stdio framing.

**Say it professionally:**

> FastMCP middleware wraps protocol dispatch for cross-cutting behavior.
> Ordering affects security, caching, retries, and observability, but middleware
> does not create new MCP methods or replace component-level authorization.

## Official references

- [FastMCP middleware](https://gofastmcp.com/servers/middleware)
- [MCP tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)

