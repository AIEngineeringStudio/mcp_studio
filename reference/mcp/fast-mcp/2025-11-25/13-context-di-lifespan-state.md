# Lesson 13 — Context, Dependency Injection, Lifespan, and Request State

This lesson is a shift in level.

So far we mostly learned things that appear **on the MCP wire**:

```
tools/call
resources/read
prompts/get
progress
elicitation
authorization
```

Now we learn how to structure the **server implementation behind that wire contract**.

The most important distinction:

> **Context, dependency injection, middleware, and lifespan are FastMCP/application architecture concepts. They are not new MCP protocol primitives.**

At the MCP level, the client still sees ordinary Tools, Resources, Prompts, arguments, results, and metadata. FastMCP's dependency parameters are deliberately excluded from the MCP-facing schema. [FastMCP](https://gofastmcp.com/servers/dependency-injection)

---

# 1. First principle: protocol inputs are not implementation dependencies

Suppose our Tool is:

```python
get_inventory(sku)
```

At MCP level, its contract might be:

```json
{
  "name": "get_inventory",
  "inputSchema": {
    "type": "object",
    "properties": {
      "sku": {
        "type": "string"
      }
    },
    "required": ["sku"]
  }
}
```

The client provides:

```json
{
  "sku": "ABC-1001"
}
```

But the implementation might also need:

```
database pool
authenticated user
request ID
logger
configuration
HTTP client
cache
```

Those are **not Tool arguments**.

```
MCP CONTRACT

get_inventory(
    sku
)


SERVER IMPLEMENTATION

get_inventory(
    sku,
    database,
    user,
    request_context,
    config,
    ...
)
```

The second group belongs to runtime infrastructure.

---

# 2. Why exposing dependencies as Tool arguments is wrong

Bad:

```python
@mcp.tool
def get_inventory(
    sku: str,
    database_url: str,
    api_key: str,
    tenant_id: str,
):
    ...
```

Now your model/client must somehow provide:

```
database_url
api_key
tenant_id
```

That creates several problems:

```
implementation details leak into API
security credentials become model inputs
Tool schema becomes noisy
callers control infrastructure configuration
testing becomes awkward
```

What you actually want:

```
CLIENT CONTROLS
sku


SERVER CONTROLS
database
credentials
authenticated identity
configuration
```

Dependency injection gives you that separation.

---

# 3. Dependency Injection from first principles

Without DI:

```python
DATABASE = Database(...)


@mcp.tool
def get_inventory(sku: str):
    return DATABASE.lookup(sku)
```

This works.

But `get_inventory()` now depends on a hidden global:

```
get_inventory
      │
      ▼
global DATABASE
```

Testing becomes awkward:

```
How do I replace DATABASE?
```

Dependency injection reverses ownership:

```
get_inventory
      │
      ▼
"I require an InventoryRepository"

framework
      │
      ▼
provides InventoryRepository
```

This is **Inversion of Control**.

Instead of the Tool locating its dependencies:

```python
repo = find_repository()
```

the runtime provides them:

```python
def get_inventory(
    sku: str,
    repo=Depends(get_repo),
):
```

Professional phrase:

> **“Dependency injection separates capability logic from dependency construction and lifecycle management.”**

---

# 4. FastMCP `Depends`

FastMCP supports:

```python
from fastmcp.dependencies import Depends
```

Example:

```python
def get_config() -> dict:
    return {
        "api_url": "https://api.example.com",
    }


@mcp.tool
async def search(
    query: str,
    config: dict = Depends(get_config),
) -> str:
    return (
        f"Searching {query} "
        f"using {config['api_url']}"
    )
```

The client sees only:

```
query
```

not:

```
config
```

FastMCP resolves dependency parameters at runtime and removes them from the MCP schema. Dependencies can themselves depend on other dependencies, forming a dependency graph. [FastMCP](https://gofastmcp.com/servers/dependency-injection)

---

# 5. Dependency graph

Suppose:

```
Tool
 │
 ├── UserRepository
 │      │
 │      └── Database
 │
 └── OrderRepository
        │
        └── Database
```

FastMCP can resolve:

```python
def get_database():
    ...


def get_user_repo(
    db=Depends(get_database),
):
    ...


def get_order_repo(
    db=Depends(get_database),
):
    ...


@mcp.tool
async def process_order(
    order_id: str,
    users=Depends(get_user_repo),
    orders=Depends(get_order_repo),
):
    ...
```

FastMCP caches dependencies **per request**, so the shared `get_database` dependency is resolved once for that request even though two downstream dependencies need it. [FastMCP](https://gofastmcp.com/servers/dependency-injection)

Conceptually:

```
             process_order
              /          \
             ▼            ▼
       UserRepository   OrderRepository
             \            /
              ▼          ▼
               Database
                  │
             resolved once
```

This is called a:

> **dependency graph**

---

# 6. Lifetimes are the core design problem

Every server object has a lifetime.

Think in three buckets:

```
SERVER LIFETIME
────────────────
database pool
shared HTTP client
configuration
ML model
cache client


REQUEST LIFETIME
────────────────
request context
authenticated identity
request ID
DB transaction/connection
temporary cache


DURABLE BUSINESS LIFETIME
─────────────────────────
customers
orders
workflows
conversation state
job records
```

If you put something in the wrong lifetime, bugs follow.

---

# 7. FastMCP Lifespan

Suppose creating a database pool is expensive.

Bad:

```python
@mcp.tool
async def get_inventory(sku: str):
    pool = await create_pool()

    try:
        ...
    finally:
        await pool.close()
```

Every Tool call does:

```
connect
query
disconnect
```

Instead:

```
SERVER START

create pool
    │
    ▼

request
request
request
request
    │
    ▼

SERVER STOP

close pool
```

FastMCP's lifespan runs once when the server starts and performs cleanup when the server stops. The object yielded by the lifespan becomes accessible to request handlers. FastMCP recommends `try/finally` for reliable teardown. [FastMCP](https://gofastmcp.com/servers/lifespan)

---

# 8. Basic lifespan example

```python
from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan


@lifespan
async def app_lifespan(server):
    print("START")

    resource = {
        "connection_pool": "ready"
    }

    try:
        yield {
            "resource": resource
        }

    finally:
        print("STOP")


mcp = FastMCP(
    "Server",
    lifespan=app_lifespan,
)
```

Conceptually:

```
FastMCP process starts
        │
        ▼
enter lifespan
        │
        ▼
yield dependencies
        │
        ├── request
        ├── request
        ├── request
        │
        ▼
server shuts down
        │
        ▼
finally
```

---

# 9. `Context`

FastMCP's `Context` represents the current MCP request.

Each request gets its own context object, and context-scoped state does not automatically carry into later requests. FastMCP currently recommends explicit `CurrentContext()` dependency injection, while type-hint injection remains supported. [FastMCP](https://gofastmcp.com/servers/context)

Preferred style:

```python
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context


@mcp.tool
async def process(
    value: str,
    ctx: Context = CurrentContext(),
) -> str:
    await ctx.info(
        f"Processing {value}"
    )

    return value.upper()
```

Client-visible schema:

```
value: string
```

Not:

```
value
ctx
```

---

# 10. What `Context` really represents

Think:

```
                  Context

                    │
        ┌───────────┼───────────┐
        │           │           │
      request     FastMCP     runtime
      state       server      facilities
        │                       │
        │                       ├── progress
        │                       ├── logging
        │                       └── MCP behavior
        │
        └── lifespan context
```

FastMCP exposes request-scoped functionality through `Context`, including state and access to lifespan-provided data. [FastMCP](https://gofastmcp.com/servers/context)

Do not think:

```
Context = global server object
```

It is fundamentally request-oriented.

---

# 11. Complete working example

Let's build something closer to a real server.

We want:

```
Tool:
get_inventory(sku)

Tool:
set_inventory(sku, units)
```

Architecture:

```
                         FastMCP

                      server lifespan
                            │
                            ▼
                    InventoryService
                     shared instance
                            │
                      ┌─────┴─────┐
                      ▼           ▼
                  request A   request B
                      │           │
                      ▼           ▼
                    Tool        Tool
```

Create `architecture_server.py`:

```python
import asyncio
from uuid import uuid4

from fastmcp import FastMCP
from fastmcp.dependencies import (
    CurrentContext,
    Depends,
)
from fastmcp.server.context import Context
from fastmcp.server.lifespan import lifespan
from fastmcp.server.middleware import (
    Middleware,
    MiddlewareContext,
)


class InventoryService:
    def __init__(self):
        self._inventory = {
            "ABC-1001": 27,
            "XYZ-2002": 0,
        }

        self._lock = asyncio.Lock()

    async def get(
        self,
        sku: str,
    ) -> int:
        return self._inventory.get(
            sku,
            0,
        )

    async def set(
        self,
        sku: str,
        units: int,
    ) -> None:

        async with self._lock:
            self._inventory[sku] = units


@lifespan
async def app_lifespan(server):
    inventory = InventoryService()

    print(
        "Inventory service started"
    )

    try:
        yield {
            "inventory": inventory,
        }

    finally:
        print(
            "Inventory service stopped"
        )


mcp = FastMCP(
    "ArchitectureDemo",
    lifespan=app_lifespan,
)


class RequestIdMiddleware(Middleware):

    async def on_request(
        self,
        context: MiddlewareContext,
        call_next,
    ):
        if context.fastmcp_context:
            await context.fastmcp_context.set_state(
                "request_id",
                str(uuid4()),
            )

        return await call_next(
            context
        )


mcp.add_middleware(
    RequestIdMiddleware()
)


def get_inventory_service(
    ctx: Context = CurrentContext(),
) -> InventoryService:

    return ctx.lifespan_context[
        "inventory"
    ]


@mcp.tool
async def get_inventory(
    sku: str,
    inventory: InventoryService = Depends(
        get_inventory_service
    ),
    ctx: Context = CurrentContext(),
) -> dict:

    request_id = await ctx.get_state(
        "request_id"
    )

    units = await inventory.get(
        sku
    )

    return {
        "request_id": request_id,
        "sku": sku,
        "units": units,
    }


@mcp.tool
async def set_inventory(
    sku: str,
    units: int,
    inventory: InventoryService = Depends(
        get_inventory_service
    ),
    ctx: Context = CurrentContext(),
) -> dict:

    request_id = await ctx.get_state(
        "request_id"
    )

    await inventory.set(
        sku,
        units,
    )

    return {
        "request_id": request_id,
        "sku": sku,
        "units": units,
    }


if __name__ == "__main__":
    mcp.run()
```

The important point is not the dictionary.

It's the lifetime architecture.

---

# 12. Peel this example apart

The MCP client sees:

```
get_inventory(
    sku
)

set_inventory(
    sku,
    units
)
```

It does **not** see:

```
InventoryService
Context
request_id
lifespan
Middleware
asyncio.Lock
```

Those are implementation concerns.

```
                     CLIENT

                tools/call
              sku="ABC-1001"
                     │
                     ▼
                FastMCP
                     │
          ┌──────────┼───────────┐
          │          │           │
      middleware    DI        Context
          │          │           │
      request ID     │           │
                     ▼           │
             InventoryService ◄──┘
                     │
                     ▼
              Tool function
                     │
                     ▼
                MCP result
```

That separation is what you want.

---

# 13. Request State

Notice:

```python
await ctx.set_state(
    "request_id",
    ...
)
```

Then later:

```python
request_id = await ctx.get_state(
    "request_id"
)
```

FastMCP request state exists specifically to pass data through the middleware → handler pipeline within one MCP request. It is discarded when that request completes. [FastMCP](https://gofastmcp.com/servers/context)

Think:

```
REQUEST #1
──────────
middleware
    │
    └── request_id=A
            │
            ▼
          Tool

request finishes
state discarded


REQUEST #2
──────────
middleware
    │
    └── request_id=B
            │
            ▼
          Tool
```

Therefore:

```
ctx state
≠
database
```

---

# 14. Why request state exists

Without request state:

```python
async def middleware(...):
    user = resolve_user(...)
```

Then the Tool separately does:

```python
user = resolve_user(...)
```

Duplicated work.

Better:

```
Middleware

resolve user once
      │
      ▼
ctx.set_state("user", user)
      │
      ▼
Tool
      │
      ▼
ctx.get_state("user")
```

FastMCP explicitly identifies middleware-to-handler communication as a common request-state use case. [FastMCP](https://gofastmcp.com/servers/context)

---

# 15. Lifespan state vs request state

Keep these completely separate:

```
LIFESPAN CONTEXT
────────────────

lifetime:
server process

examples:
database pool
HTTP client
configuration
shared service


REQUEST STATE
─────────────

lifetime:
one MCP request

examples:
request ID
resolved user
authorization decision
temporary transaction
request-local cache
```

A professional explanation:

> **“Lifespan context owns server-scoped dependencies; request state carries ephemeral data through one request pipeline.”**

---

# 16. Don't put request-specific data in lifespan state

Bad:

```python
lifespan_context[
    "current_user"
] = "alice"
```

Why?

Suppose:

```
request A
user=Alice

request B
user=Bob
```

concurrently:

```
             shared lifespan

              current_user
                   │
         ┌─────────┴─────────┐
         │                   │
      request A           request B
      Alice               Bob
```

They overwrite each other.

This is a classic **shared mutable state** bug.

User identity belongs in:

```
request-scoped state
```

or a request dependency.

---

# 17. Don't create expensive infrastructure per request

The opposite error:

```python
async def get_database():
    return await create_database_pool()
```

for every Tool invocation.

A pool is designed to be shared.

Better:

```
lifespan

create pool ONCE
      │
      ▼
request dependency

acquire one connection
      │
      ▼
Tool
      │
      ▼
release connection
```

This gives us two distinct concepts:

```
CONNECTION POOL
server-scoped


CONNECTION
request-scoped
```

---

# 18. Per-request resource dependency

FastMCP `Depends()` can wrap an async context manager. Cleanup runs after the component finishes, including error paths. [FastMCP](https://gofastmcp.com/servers/dependency-injection)

Conceptually:

```python
from contextlib import (
    asynccontextmanager,
)


@asynccontextmanager
async def get_connection():
    connection = await pool.acquire()

    try:
        yield connection

    finally:
        await pool.release(
            connection
        )
```

Then:

```python
@mcp.tool
async def get_customer(
    customer_id: str,
    db=Depends(get_connection),
):
    return await db.fetch_customer(
        customer_id
    )
```

Lifetime:

```
Tool call starts
      │
      ▼
acquire connection
      │
      ▼
Tool executes
      │
      ├── success
      │
      └── exception
             │
             ▼
release connection
```

Professional term:

> **request-scoped resource**

---

# 19. Dependency cache vs application cache

Do not confuse:

```
FastMCP dependency caching
```

with:

```
Redis/cache database
```

FastMCP dependency caching means:

```
within THIS request

get_database()
called by dependency A
and dependency B

      │
      ▼
execute provider once
reuse result
```

It is about **dependency resolution**, not data caching. FastMCP's dependency graph is cached per request. [FastMCP](https://gofastmcp.com/servers/dependency-injection)

---

# 20. `CurrentContext()` vs `get_context()`

Preferred at component boundaries:

```python
async def tool(
    ctx: Context = CurrentContext(),
):
```

Sometimes a deeply nested helper needs access:

```python
from fastmcp.server.dependencies import (
    get_context,
)


async def helper():
    ctx = get_context()

    await ctx.info(
        "helper running"
    )
```

FastMCP documents both. `get_context()` only works during active server request execution; using it outside a request raises an error. [FastMCP](https://gofastmcp.com/servers/context)

Design guidance:

```
Prefer explicit dependency
when practical.

Use contextual lookup
when passing Context through
many helper layers becomes noise.
```

---

# 21. Why explicit dependencies usually scale better

Compare:

```python
async def service():
    ctx = get_context()
    db = get_database_somehow()
    config = global_config
```

Everything is hidden.

Versus:

```python
async def service(
    db,
    config,
):
```

Dependencies are visible.

This improves:

```
testability
reasoning
type checking
reuse
dependency boundaries
```

Professional term:

> **explicit dependency surface**

Use contextual lookup for genuinely contextual facilities, not as a substitute for architecture.

---

# 22. HTTP request dependencies

FastMCP can also inject HTTP-specific infrastructure:

```python
from fastmcp.dependencies import (
    CurrentRequest,
)
from starlette.requests import Request


@mcp.tool
async def client_info(
    request: Request = CurrentRequest(),
) -> dict:

    return {
        "user_agent":
            request.headers.get(
                "user-agent"
            )
    }
```

But this works only in an HTTP request context; it is not portable to stdio or code that no longer has a live HTTP request. FastMCP separately offers `CurrentHeaders()`/header helpers where graceful transport-independent fallback is preferable. [FastMCP](https://gofastmcp.com/servers/dependency-injection)

This introduces an important design smell:

```
Tool unnecessarily depends
on HTTP Request
        │
        ▼
Tool becomes transport-coupled
```

Avoid that unless the Tool genuinely needs HTTP details.

---

# 23. Transport coupling

Good:

```python
@mcp.tool
async def calculate_tax(
    amount: float,
):
```

Works over:

```
stdio
HTTP
in-memory
```

Less portable:

```python
@mcp.tool
async def calculate_tax(
    amount: float,
    request: Request = CurrentRequest(),
):
```

Now implementation depends on:

```
HTTP
```

Professional phrase:

> **“Keep domain services transport-agnostic and isolate transport-specific dependencies at the boundary.”**

---

# 24. Authentication dependency

From the previous lesson:

```python
from fastmcp.dependencies import (
    CurrentAccessToken,
)
from fastmcp.server.auth import (
    AccessToken,
)


@mcp.tool
async def my_profile(
    token: AccessToken = CurrentAccessToken(),
) -> dict:

    return {
        "user_id":
            token.claims["sub"]
    }
```

The MCP Tool schema still contains no:

```
token
```

Authentication identity is runtime infrastructure, not caller-provided Tool input. FastMCP supports direct access-token and token-claim dependencies. [FastMCP](https://gofastmcp.com/servers/dependency-injection)

---

# 25. Concurrency changes everything

Suppose your HTTP server receives:

```
100 requests simultaneously
```

They may all access the same lifespan object:

```
InventoryService
```

```
                  shared service

                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
   request A       request B       request C
```

Therefore a lifespan dependency must be either:

```
safe for concurrent use
```

or protected appropriately.

---

# 26. Race condition example

Bad shared counter:

```python
class Counter:

    def __init__(self):
        self.value = 0

    async def increment(self):
        old = self.value

        await asyncio.sleep(0)

        self.value = old + 1
```

Two requests:

```
value = 10


Request A              Request B

read 10                read 10
  │                       │
await                   await
  │                       │
write 11               write 11
```

Expected:

```
12
```

Actual:

```
11
```

That's a **race condition**.

---

# 27. Critical sections

Protect shared mutation:

```python
class Counter:

    def __init__(self):
        self.value = 0
        self.lock = asyncio.Lock()

    async def increment(self):

        async with self.lock:
            old = self.value

            await asyncio.sleep(0)

            self.value = old + 1
```

The protected section is called a:

> **critical section**

Conceptually:

```
request A
   │
 acquire lock
   │
 mutation
   │
 release
   │
               request B
                  │
               acquire
                  │
               mutation
```

But do not reflexively lock everything. Prefer dependencies already designed for concurrency, such as database connection pools and properly designed HTTP clients.

---

# 28. Shared mutable memory has another production problem

Suppose your server runs:

```
4 workers
```

Each worker gets:

```
its own Python process
```

Therefore:

```
Worker A inventory dict
≠
Worker B inventory dict
≠
Worker C inventory dict
```

So this:

```python
INVENTORY = {}
```

is not durable distributed state.

Use:

```
database
Redis
object store
other shared persistence
```

for business state that must remain consistent across replicas.

Professional term:

> **process-local state**

---

# 29. Lifespan does not mean globally unique

Important:

```
lifespan runs once
```

means:

```
once per running server instance/process
```

Architecturally:

```
load balancer
    │
    ├── worker A
    │      └── lifespan A
    │
    ├── worker B
    │      └── lifespan B
    │
    └── worker C
           └── lifespan C
```

FastMCP documents lifespan as server-level setup/teardown that runs once for that server instance, regardless of how many clients connect. [FastMCP](https://gofastmcp.com/servers/lifespan)

Do not use lifespan memory as a distributed singleton.

---

# 30. A production-shaped architecture

Instead of this:

```python
@mcp.tool
async def create_order(...):
    # auth
    # SQL
    # API calls
    # logs
    # business rules
    # everything
```

aim for:

```
MCP COMPONENT
thin adapter
      │
      ▼
APPLICATION SERVICE
business workflow
      │
      ├── repository
      ├── API client
      └── policy
           │
           ▼
INFRASTRUCTURE
database / HTTP / queues
```

Example:

```python
@mcp.tool
async def create_order(
    product_id: str,
    quantity: int,
    service: OrderService = Depends(
        get_order_service
    ),
):
    return await service.create(
        product_id,
        quantity,
    )
```

The Tool handles:

```
MCP-facing contract
```

The service handles:

```
business logic
```

The repository handles:

```
persistence
```

Professional term:

> **layered architecture**

---

# 31. Middleware vs Dependency Injection

These overlap but solve different problems.

Use **middleware** for:

```
every request / broad request classes

logging
timing
authentication
rate limits
request IDs
auditing
```

Use **dependencies** for:

```
specific handler requirements

repository
database connection
tenant
configuration
HTTP client
application service
```

FastMCP middleware wraps request execution and can put values into request state for later handlers. [FastMCP](https://gofastmcp.com/servers/middleware)

Mental model:

```
MIDDLEWARE
horizontal concern


DEPENDENCY
vertical requirement
```

---

# 32. A realistic request

Putting everything together:

```
CLIENT
  │
  │ tools/call
  ▼
FastMCP
  │
  ▼
Auth middleware
  │
  ▼
Request-ID middleware
  │
  └── ctx.state.request_id
  │
  ▼
Dependency graph
  │
  ├── authenticated principal
  ├── database connection
  └── OrderService
  │
  ▼
Tool adapter
  │
  ▼
business service
  │
  ▼
repository / API
  │
  ▼
result
  │
  ▼
dependency cleanup
  │
  ▼
middleware response path
  │
  ▼
MCP ToolResult
```

This is much closer to a production MCP server than:

```python
@mcp.tool
def foo():
    ...
```

---

# 33. Common lifetime mistakes

| Mistake | Problem |
|---|---|
| DB pool created per request | expensive churn |
| DB connection stored forever | leak/contention |
| current user stored in lifespan | cross-request contamination |
| business data stored only in Python dict | breaks across workers/restarts |
| HTTP `Request` used deep in business logic | transport coupling |
| dependency secretly accessed through globals | poor testability |
| shared mutable object without concurrency design | race conditions |
| request state used for durable workflow data | disappears after request |

---

# 34. Protocol → FastMCP abstraction map

| Concern | MCP protocol level | FastMCP |
|---|---|---|
| Tool input | `arguments` | normal function parameters |
| Request metadata | request/meta/transport state | `Context` / dependencies |
| Runtime service | implementation concern | `Depends()` |
| Dependency graph | implementation concern | nested dependencies |
| Per-request dependency caching | implementation concern | automatic |
| Server startup | process concern | lifespan |
| Server shutdown | process concern | lifespan teardown |
| Shared server dependency | process concern | `lifespan_context` |
| Request state | implementation concern | `ctx.set_state/get_state` |
| HTTP request | transport concern | `CurrentRequest()` |
| Auth token | security context | `CurrentAccessToken()` |
| Cross-cutting behavior | implementation concern | middleware |

This distinction is central:

> **FastMCP's architecture enriches your Python runtime without expanding your public MCP Tool schema.** [FastMCP](https://gofastmcp.com/servers/dependency-injection)

---

# 35. Professional vocabulary

Be comfortable with these terms:

| Term | Meaning |
|---|---|
| **Dependency injection** | Runtime supplies required dependencies |
| **Inversion of Control** | Component does not construct/control its dependencies |
| **Dependency graph** | Relationships between dependent services |
| **Provider/factory** | Function that creates or resolves a dependency |
| **Request scope** | Lifetime of one request |
| **Server/process scope** | Lifetime of one server process |
| **Lifespan** | Server startup/teardown lifecycle |
| **Teardown/finalizer** | Cleanup executed when scope ends |
| **Connection pool** | Shared manager of reusable connections |
| **Request-scoped connection** | Connection acquired for one operation |
| **Shared mutable state** | State accessible and modifiable concurrently |
| **Race condition** | Result depends incorrectly on execution timing |
| **Critical section** | Region requiring exclusive synchronization |
| **Re-entrant** | Safe to invoke concurrently/repeatedly |
| **Process-local state** | State existing only in one server process |
| **Transport coupling** | Business code depending on HTTP/stdio details |
| **Cross-cutting concern** | Behavior affecting many operations, e.g. logging/auth |
| **Thin adapter** | Small protocol-facing layer delegating to domain code |

A strong explanation:

> **“MCP defines the external capability contract, while FastMCP's dependency system manages implementation-time concerns. I use lifespan for expensive server-scoped resources such as connection pools, request dependencies for connections and authenticated identity, Context state for ephemeral middleware-to-handler data, and external persistence for state that must survive requests or replicas. Dependency parameters are excluded from the MCP schema, which keeps the protocol surface independent of infrastructure.”** [FastMCP](https://gofastmcp.com/servers/context)

---

# Hands-on assignment

Take `architecture_server.py` and extend it in this order:

1. Add a `Config` object to lifespan.
2. Add a second shared service that depends on that configuration.
3. Create a `Depends()` provider for each service.
4. Add middleware generating one `request_id` per request.
5. Call two Tools concurrently and verify the IDs differ.
6. Verify both calls share the same lifespan `InventoryService`.
7. Add an intentionally unsafe shared counter and reproduce a race.
8. Protect it with `asyncio.Lock`.
9. Replace the in-memory inventory dict with a simulated repository.
10. Make the Tool a thin adapter around an `InventoryService`.
11. Add an async-context-manager dependency and print its acquire/cleanup sequence.
12. Inspect `tools/list` and verify **none** of the injected dependencies appear in `inputSchema`.

The core test is being able to explain:

```
Tool argument
    ≠
dependency
    ≠
Context
    ≠
request state
    ≠
lifespan state
    ≠
durable business state
```

Each has a different owner and lifetime.

## Next lesson — Middleware and the Request Pipeline

The logical next lesson is a deep dive into **FastMCP middleware**:

```
request pipeline
call_next()
middleware ordering

logging
timing
rate limiting
error handling
retries
response limiting
caching

custom middleware
request mutation
response transformation

why auth/caching middleware can create security bugs
```

We'll implement the same Tool behind several middleware layers and walk one request through the stack from entry to final MCP result.