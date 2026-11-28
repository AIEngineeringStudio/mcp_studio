# Lesson 13 — Context, dependencies, lifespan, and state

## Outcome

After this lesson, you can assign each kind of state to the correct lifetime and
avoid rebuilding protocol sessions inside a modern server.

## Protocol inputs are not implementation dependencies

Tool arguments are part of the public MCP contract. A database pool, settings
object, authenticated principal, and logger are implementation dependencies and
must not appear in the tool schema.

```
MCP arguments                    Injected dependencies
-------------                    ---------------------
ticket_id                        repository
new_status                       settings
                                 authenticated principal
                                 request/trace context
```

Dependency injection separates capability logic from dependency construction.

```python
from fastmcp import FastMCP
from fastmcp.dependencies import Depends

mcp = FastMCP("Tickets")


def get_repository() -> dict[str, str]:
    return {"T-100": "open"}


@mcp.tool
def ticket_status(
    ticket_id: str,
    repository: dict[str, str] = Depends(get_repository),
) -> str:
    return repository[ticket_id]
```

The client sees `ticket_id`; FastMCP resolves `repository` internally.

## Four useful lifetimes

**Application lifetime:**

> Expensive shared infrastructure created at startup and closed at shutdown,
> such as database pools or HTTP clients. FastMCP lifespan owns this work.

**Request lifetime:**

> Identity, request metadata, trace context, dependency cache, and temporary
> values for one MCP request.

**Continuation lifetime:**

> State needed across MRTR retries. Use protected `requestState` or a
> server-minted operation handle; do not depend on a suspended handler.

**Durable business lifetime:**

> Tickets, approvals, baskets, and jobs stored in a database or durable queue.

```
application process
  +-- lifespan resources
  +-- request A context
  +-- request B context

durable store
  +-- business records and explicit operation state
```

## Stateless protocol does not mean stateless application

MCP `2026-07-28` removes protocol sessions. It does not prohibit state. Use an
explicit, authorized state model:

- a server-minted handle passed as a tool argument;
- an authenticated user session backed by configured storage;
- durable business records;
- integrity-protected MRTR continuation state.

Do not key security-sensitive state only by a client-supplied handle. Bind it to
the authenticated principal, tenant, operation, and expiry.

## Concurrency and workers

Lifespan state is shared only inside one process. With multiple workers, each
worker has its own memory and its own lifespan resources.

```
load balancer
  +-- worker A memory
  +-- worker B memory
  +-- worker C memory
         |
         +-- shared external database/cache when required
```

Protect mutable in-process state with appropriate concurrency controls, but do
not mistake a lock for cross-process consistency. Use database constraints,
transactions, idempotency keys, and durable coordination where the business
rule requires them.

## Context is request-scoped

FastMCP `Context` exposes information and operations associated with the current
request. Treat it as a boundary object, not a global service locator. Prefer
explicit dependencies for reusable business services because they are easier to
test and reason about.

Modern interactive operations may inspect `inputResponses` and `requestState`
when re-entered. That state belongs to the current retry request; it is not a
live connection session.

## Hands-on checkpoint

**Execution boundary:**

> In-memory MCP. The server lifespan still starts and stops normally; only the
> process and network boundaries are removed.

Run the focused lifespan exercise from the repository root. It creates one
application-lifetime repository, serves two requests through it, and then
verifies one shutdown:

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python verify_context_lifespan.py
```

Expected output:

```
lifespan: one startup served two requests, then one shutdown ran
tool schema: ticket_id is public; repository remains internal
```

The complete runnable exercise is
[`verify_context_lifespan.py`](labs/verify_context_lifespan.py). The existing
domain and protocol test suites remain useful for layer isolation, but this
exercise directly proves the state lifetimes taught here.

Read
[`../concepts/17-application-lifespan.md`](../../01-mcp-concepts/guides/17-application-lifespan.md)
and [`../concepts/18-process-runtime.md`](../../01-mcp-concepts/guides/18-process-runtime.md).

**Say it professionally:**

> I separate application, request, continuation, and durable business state.
> Modern MCP removes connection sessions, so cross-request state uses explicit
> authorized handles or external storage rather than worker-local memory.

## Official references

- [Architecture](https://modelcontextprotocol.io/specification/2026-07-28/architecture)
- [MRTR](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [FastMCP dependency injection](https://gofastmcp.com/servers/dependency-injection)
- [FastMCP lifespan](https://gofastmcp.com/servers/lifespan)

