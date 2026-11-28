# Code Walkthrough — MCP Streaming Dashboard

**Audience:** Junior engineers with basic Python knowledge.  
**Goal:** Understand every file, every pattern, and every decision in this
codebase.

---


## Key terms to memorize

| Term          | Definition                                        |
|---------------|---------------------------------------------------|
| MCP           | Model Context Protocol — a standard for tool      |
|               | communication between client and server           |
| Elicitation   | Server pauses and asks the client a question      |
|               | mid-tool-call                                     |
| Context (ctx) | Object injected by FastMCP giving access to       |
|               | logging, progress, and elicitation                |
| Lifespan      | Async startup/shutdown scope — holds shared state |
|               | like DB connections                               |
| Data chunk    | A batch of rows sent via ctx.info() as a log msg  |

## Design pattern applied → where

1. Repository pattern user_repo.py
    - All SQL in one class. Service never writes SQL.
    - To swap PostgreSQL for SQLite: replace this file only.

2. Service layer user_service.py
    - All business logic (loop, elicitation, validation).
    - Zero FastMCP or psycopg imports.
    - Testable in isolation with a fake repo.

3. Dependency injection server.py lifespan()
    - db → repo → service built in one place.
    - Every tool receives a fully-wired service via ctx.

4. Strategy pattern strategies.py
    - ElicitStrategy abstract base class.
    - 4 concrete classes: PlanStrategy, AlwaysContinue,
    - AlwaysStop, CallbackStrategy.
    - Swap strategy at construction time — handlers.py and
    - mcp_client.py are untouched.

## React UI features

1. Healthcheck tool
    - one - click ping, shows DB count
2. Stream users
    - shows each DATA_CHUNK as it arrives,
    - progress bar in log, table grows live
3. Interactive stream
    - pauses after each batch and renders
    - an ElicitDialog — you pick action
    - (continue/stop/decline/cancel) and
    - next batch size, then click Reply

## UI trace tree — design doc mapping

1. 🤖 AGENT = autonomous reasoning nodes (strategy selection, elicitation
   waiting)
2. ⚖️ GATEWAY = enforcement / validation (bridge ingress, errors)
3. 🔧 MCP = tool execution (MCPClient calls, server log lines, data chunks,
   progress)

**Each node shows:**

- INPUT → what this layer received
- PROCESSING → SQL, log text, or narrative
- OUTPUT → return value or batch rows (table)

Timestamp + elapsed time from run start on every node. Click header to
collapse/expand.

**Interactive stream tool:**

- When the server calls ctx.elicit(), the UI renders an ElicitPrompt dialog.
- You pick action + next_batch_size and click Reply.
- The UI POSTs to /elicit/{run_id}, which resolves the asyncio.
- Future in the bridge, and the server loop continues.

## Package Structure

**From streamable-http-transport**

```bash
tree --dirsfirst -C -a -I '.venv|node_modules|cache|test_*'
```
> - `tree --dirsfirst`: Lists directories before files.
> - `tree -C`: Highlights output with colors for better readability.
> - `tree -I 'pattern'`: Ignores files matching a specific pattern 
> - `tree -a`: Shows all files, including hidden
> - `tree -L level`: Limits the depth of the directory tree


```
streamable-http-transport/
├── _learning_resources/
│    └── walkthrough_doc.md
├── db/
│   └── init/
│       └── 001_seed.sql
├── server/
│   ├── app/   
│   │   ├── bridge/
│   │   │   ├── __init__.py
│   │   │   ├── bridge.py         ← FastAPI bridge. Exposes REST + SSE (/run, /events(→ SSE stream of TraceEvents), /elicit (resolves the pending asyncio. Future so the server continues from where it paused.) endpoints the browser can reach. Runs alongside the MCP server on port 8001. Calls MCPClient internally (real code, no mock).
│   │   │   ├── trace_bus.py      ← async pub/sub event queue, fan-out to SSE clients. Bridge emits events. SSE generator subscribes per run_id. Each run gets its own queue — no mixing.
│   │   │   └── trace_models.py   ← TraceEvent dataclass (actor/input/output)
│   │   ├── client/
│   │   │   ├── __init__.py
│   │   │   ├── handlers.py       ← log, progress, elicit handler factories
│   │   │   ├── mcp_client.py     ← MCPClient wrapper
│   │   │   ├── plan_parser.py    ← parses ELICIT_PLAN string
│   │   │   └── strategies.py     ← ElicitStrategy + 4 concrete classes
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── connection.py     ← psycopg connection factory
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── domain.py         ← User, StreamControl, StreamSummary
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   └── user_repo.py      ← ALL SQL lives here (Repository)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── user_service.py   ← ALL business logic (Service Layer)
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   └── user_tools.py     ← thin @mcp.tool wrappers only
│   │   ├── __init__.py
│   │   ├── config.py             ← env vars, constants
│   │   └── server.py             ← bootstrap + Dependency Injection wiring
│   ├── ENV_SETUP.md              ← Install dependencies (Local)
│   ├── Dockerfile     
│   ├── pyproject.toml
│   └── uv.lock
├── ui/                           ← Connects to bridge via SSE.
│   ├── src/
│   │ ├── App.jsx
│   │ └── main.jsx
│   ├── vite.config.js
│   ├── index.html
│   ├── package-lock.json
│   └── package.json
├── docker-compose.yml
├── .gitignore
└── README.md 
```

## Table of Contents

1. [What this system does](#1-what-this-system-does)
2. [How the pieces connect](#2-how-the-pieces-connect)
3. [Technical concepts you need first](#3-technical-concepts-you-need-first)
4. [Directory structure explained](#4-directory-structure-explained)
5. [Layer 1 — Configuration](#5-layer-1--configuration)
6. [Layer 2 — Database](#6-layer-2--database)
7. [Layer 3 — Repository](#7-layer-3--repository)
8. [Layer 4 — Domain models](#8-layer-4--domain-models)
9. [Layer 5 — Service](#9-layer-5--service)
10. [Layer 6 — MCP tools](#10-layer-6--mcp-tools)
11. [Layer 7 — MCP server bootstrap](#11-layer-7--mcp-server-bootstrap)
12. [Layer 8 — Client strategies](#12-layer-8--client-strategies)
13. [Layer 9 — Client handlers](#13-layer-9--client-handlers)
14. [Layer 10 — MCP client wrapper](#14-layer-10--mcp-client-wrapper)
15. [Layer 11 — Trace system](#15-layer-11--trace-system)
16. [Layer 12 — HTTP bridge](#16-layer-12--http-bridge)
17. [Layer 13 — React UI](#17-layer-13--react-ui)
18. [Infrastructure — Docker](#18-infrastructure--docker)
19. [Design patterns reference](#19-design-patterns-reference)
20. [Data flow walkthrough](#20-data-flow-walkthrough)
21. [Glossary](#21-glossary)

---

## 1. What this system does

This project is a **user search service** built on top of a PostgreSQL database.
It does three things that are unusual and worth learning:

1. **Streams data in batches** — instead of waiting for all results and
   returning
   them at once, it sends rows to the client as they are fetched, batch by
   batch.

2. **Supports elicitation** — the server can pause mid-stream, ask the client
   a question ("should I continue?"), wait for the answer, then resume. This
   is bidirectional communication inside a single tool call.

3. **Traces every layer** — a real-time dashboard in the browser shows every
   function call, what it received, what it did, and what it returned — with
   timestamps and a nested call tree.

The system is also designed to demonstrate enterprise software patterns: how
to separate concerns, inject dependencies, and make code testable and
replaceable.

---

## 2. How the pieces connect

```
Browser (React UI)
       │
       │  HTTP + Server-Sent Events (SSE)
       ▼
FastAPI Bridge  :8001          ← your HTTP entry-point
       │
       │  MCP protocol over HTTP
       ▼
FastMCP Server  :8000          ← tool execution engine
       │
       │  SQL (psycopg)
       ▼
PostgreSQL  :5432              ← data store
```

**Three processes run simultaneously** (all started by Docker):

| Process        | Port | Responsibility                                                        |
|----------------|------|-----------------------------------------------------------------------|
| PostgreSQL     | 5432 | Stores the `app_user` table                                           |
| MCP server     | 8000 | Executes tools, queries DB, streams data                              |
| FastAPI bridge | 8001 | Accepts browser requests, relays to MCP server, pushes events via SSE |

The React UI is a **fourth process** run separately by Node.js on port 5173.
It talks only to the bridge — never directly to the MCP server or the database.

---

## 3. Technical concepts you need first

### 3.1 What is a protocol?

A protocol is a set of rules two programs agree on for communicating.
HTTP is a protocol for web requests. MCP (Model Context Protocol) is a
protocol specifically for AI tools — it defines how a client asks a server
to run a tool and how the server sends back results.

### 3.2 What is async / await?

Normal code runs one line at a time. If line 3 does a database query that
takes 200ms, the program sits idle for 200ms before running line 4.

```python
# synchronous — blocks while waiting
rows = db.fetch()  # waits 200ms doing nothing
print(rows)  # only runs after the wait
```

Async code can pause at a waiting point and do other work:

```python
# asynchronous — yields control while waiting
rows = await db.fetch()  # pauses HERE, lets other code run
print(rows)  # resumes when the DB responds
```

`async def` means: "this function can pause".  
`await` means: "pause here and wait for this to finish".

This is critical for a server — while one request waits for the DB, the
server can handle other requests. Without async, a slow DB query would
freeze the entire server.

### 3.3 What is a class and an instance?

A **class** is a blueprint. An **instance** is one real object built from it.

```python
class Car:
    def __init__(self, colour):
        self.colour = colour  # stored on this instance

    def describe(self):
        return f"A {self.colour} car"


red_car = Car("red")  # one instance
blue_car = Car("blue")  # another instance
print(red_car.describe())  # "A red car"
```

`self` always refers to the specific instance the method is running on.
`__init__` is the constructor — it runs automatically when you create a new
instance.

### 3.4 What is a decorator?

A decorator is a function that wraps another function, modifying it.

```python
@mcp.tool  # this is a decorator
async def my_tool():
    ...
```

This is shorthand for `my_tool = mcp.tool(my_tool)`. In this codebase,
`@mcp.tool` registers the function as a callable MCP tool. Without it,
the function is just a plain Python function the server ignores.

### 3.5 What is a dataclass?

A dataclass is a shortcut to create a class that mainly holds data.

```python
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str


u = User(id=1, name="Alice", email="alice@example.com")
print(u.name)  # "Alice"
```

Without `@dataclass` you would have to write `__init__` manually.
The decorator generates it for you.

### 3.6 What is dependency injection?

Dependency injection (DI) means: instead of a class creating the things
it needs, those things are passed in from outside.

```python
# WITHOUT DI — hard to test, tightly coupled
class UserService:
    def __init__(self):
        self.repo = UserRepository()  # creates its own — cannot swap it


# WITH DI — easy to test, loosely coupled
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo  # receives it — can be swapped
```

In tests you pass in a fake repository. In production you pass in the real
one. The service code is identical in both cases.

### 3.7 What is a Protocol (structural typing)?

Python's `Protocol` lets you define an interface without inheritance.
Any class that has the right methods automatically satisfies it.

```python
from typing import Protocol


class Printable(Protocol):
    def print(self) -> None: ...


class Invoice:
    def print(self):  # Invoice is a Printable — no inheritance needed
        print("Invoice!")
```

This codebase uses it to decouple `UserService` from FastMCP's `Context`
class. The service only requires something with `info()`, `elicit()` etc. —
it does not care what class provides them.

### 3.8 What is Server-Sent Events (SSE)?

SSE is a way for a server to push data to a browser over a long-lived HTTP
connection. The browser opens one connection and the server keeps sending
events down it until done.

```
Browser → GET /events/abc123     (opens connection, waits)
Server  ← data: {"label": "batch 1 sent"}\n\n
Server  ← data: {"label": "batch 2 sent"}\n\n
Server  ← data: {"type": "run_complete"}\n\n
                                 (connection closes)
```

This is how the trace dashboard updates in real time — each trace event
is pushed as an SSE message.

### 3.9 What is a connection pool?

Opening a new database connection for every query is expensive — it requires
a TCP handshake and authentication round-trip every time. A connection pool
keeps a set of already-open connections and lends them out:

```
Pool (10 connections always open)
    ├── conn-1  ← lent to query A, returned after
    ├── conn-2  ← lent to query B, returned after
    └── conn-3  ← available
```

Queries borrow a connection, use it, and return it. Much faster than
opening a new connection every time.

### 3.10 What is the Strategy pattern?

The Strategy pattern defines a family of interchangeable algorithms behind
one interface. The code that uses the strategy does not know or care which
concrete one it gets.

```
ElicitStrategy (interface)
    ├── PlanStrategy        — follows a pre-defined script
    ├── AlwaysContinueStrategy — always says "continue"
    ├── AlwaysStopStrategy  — always says "stop"
    └── CallbackStrategy    — asks a callback function (e.g. the UI)
```

The client code receives an `ElicitStrategy` and calls `strategy.decide()`.
Which concrete class is behind it is decided at startup.

---

## 4. Directory structure explained

```
streamable-http-mcp/
│
├── docker-compose.yml        ← defines and wires all services
├── db/init/001_seed.sql      ← creates and seeds the app_user table
│
├── server/                   ← one Python package (server + bridge)
│   ├── Dockerfile            ← how to containerise the server
│   ├── pyproject.toml        ← Python dependencies
│   └── app/
│       ├── config.py         ← all env vars in one place
│       ├── server.py         ← MCP server entry-point
│       │
│       ├── models/domain.py  ← plain data containers (no logic)
│       ├── db/connection.py  ← connection pool
│       ├── repositories/     ← SQL queries
│       ├── services/         ← business logic
│       ├── tools/            ← MCP tool definitions
│       ├── client/           ← MCP client (strategies, handlers)
│       └── bridge/           ← FastAPI HTTP bridge + trace system
│
└── ui/                       ← React frontend (Vite)
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        └── App.jsx
```

**Why is `client/` inside `server/`?**  
Both the client code and the bridge need shared modules (`config.py`,
`models/domain.py`, `client/strategies.py`). Keeping everything in one
Python package avoids duplicating those files.

---

## 5. Layer 1 — Configuration

**File:** `server/app/config.py`

### What problem does it solve?

Configuration values like database passwords and server ports should never
be hardcoded. They need to change between environments (dev, staging,
production) without changing code. Environment variables are the standard
solution — but reading them inline with `os.environ.get()` scattered across
20 files creates three problems:

1. You cannot validate them — a typo in `APP_PORT="abc"` is only discovered
   at runtime when `int()` crashes.
2. You cannot override them in tests without patching at the right import time.
3. There is no single place to see all configuration.

### The solution: pydantic-settings

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_dsn: str = "postgresql://..."
    port: int = 8000
```

`BaseSettings` reads `APP_DB_DSN` and `APP_PORT` from environment variables
automatically (because of `env_prefix = "APP_"`). It validates each value
against the declared type. If `APP_PORT=abc`, it raises a clear error at
startup.

### The @lru_cache pattern

```python
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

`@lru_cache` memoizes the function — it runs once and caches the result.
Every subsequent call returns the same `Settings` object without reading
the environment again. This is important: if environment variables were
read at every call, a test that changes `os.environ` mid-run could produce
inconsistent results.

To reset in tests: `get_settings.cache_clear()`.

### Key fields

| Field                    | Env var                      | Purpose                                        |
|--------------------------|------------------------------|------------------------------------------------|
| `db_dsn`                 | `APP_DB_DSN`                 | PostgreSQL connection string                   |
| `host` / `port`          | `APP_HOST` / `APP_PORT`      | MCP server bind address                        |
| `bridge_port`            | `APP_BRIDGE_PORT`            | FastAPI bridge port                            |
| `server_url`             | `APP_SERVER_URL`             | URL the bridge uses to reach the MCP server    |
| `elicit_timeout_seconds` | `APP_ELICIT_TIMEOUT_SECONDS` | How long to wait for a UI elicitation reply    |
| `use_redis`              | `APP_USE_REDIS`              | Switch between in-process and Redis-backed bus |
| `redis_url`              | `APP_REDIS_URL`              | Redis connection string                        |

---

## 6. Layer 2 — Database

**File:** `server/app/db/connection.py`

### What problem does it solve?

The original code opened a new PostgreSQL connection for every single query:

```python
# OLD — one new TCP connection per query (slow)
async def fetch_users(...):
    conn = await AsyncConnection.connect(dsn)
    ...
```

A TCP connection requires a handshake and authentication. At 20 queries per
second this becomes a major bottleneck.

### The solution: connection pool

```python
class DatabasePool:
    @classmethod
    async def create(cls, dsn, min_size=2, max_size=10):
        pool = AsyncConnectionPool(
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
        )
        await pool.open(wait=True)
        return cls(pool)
```

`AsyncConnectionPool` keeps between 2 and 10 connections open permanently.
Queries borrow a connection using an async context manager:

```python
async with self._pool.connection() as conn:
    await conn.execute(sql, params)
```

When the `async with` block exits, the connection is automatically returned
to the pool — not closed.

### Why `dict_row`?

By default, psycopg returns rows as tuples: `(1, "Alice", "alice@example.com")`.
`dict_row` makes it return dictionaries: `{"id": 1, "name": "Alice", ...}`.
Column access by name (`row["id"]`) is far more readable and refactor-safe
than access by position (`row[0]`).

### The ping method

```python
async def ping(self) -> bool:
    try:
        async with self.connection() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        return False
```

`SELECT 1` is the cheapest possible query — it asks the DB for nothing, just
checks the connection is alive. Used by the healthcheck tool.

---

## 7. Layer 3 — Repository

**File:** `server/app/repositories/user_repo.py`

### What is the Repository pattern?

The Repository pattern puts all database queries for one entity into a single
class. The rest of the codebase never writes SQL — it calls methods on the
repository.

Benefits:

- One place to look when a query is wrong.
- Swap PostgreSQL for SQLite by replacing this one file.
- Test the service layer with a fake repository that returns hard-coded data.

### The class

```python
class UserRepository:
    _COUNT_SQL = """
        SELECT COUNT(*) AS total
        FROM app_user
        WHERE full_name ILIKE %(pattern)s
           OR email     ILIKE %(pattern)s
    """

    def __init__(self, pool: DatabasePool) -> None:
        self._pool = pool  # injected — not created here
```

`ILIKE` is PostgreSQL's case-insensitive `LIKE`. `%(pattern)s` is a
parameterised placeholder — psycopg substitutes the actual value safely,
preventing SQL injection.

### Pagination with LIMIT / OFFSET

```python
_FETCH_SQL = """
    ...
    ORDER BY id
    LIMIT  %(limit)s
    OFFSET %(offset)s
"""
```

`LIMIT 10 OFFSET 0` returns rows 1–10.  
`LIMIT 10 OFFSET 10` returns rows 11–20.  
`LIMIT 5  OFFSET 20` returns rows 21–25.

The service increments `offset` by `len(rows)` after each batch.

### from_row factory method

```python
@classmethod
def from_row(cls, row: dict[str, Any]) -> "User":
    return cls(
        id=int(row["id"]),
        full_name=row["full_name"],
        ...
    )
```

`@classmethod` receives the class itself (`cls`) rather than an instance.
It acts as an alternative constructor — "build a User from a DB row dict".
This keeps the conversion logic inside the domain model, not scattered
across the repository.

---

## 8. Layer 4 — Domain models

**File:** `server/app/models/domain.py`

Domain models are plain data containers. They have no database imports, no
framework imports, no HTTP logic. They represent the real-world concepts your
system works with.

### User

```python
@dataclass(frozen=True)
class User:
    id: int
    full_name: str
    email: str
    department: str
    city: str
    is_active: bool
    created_at: datetime
```

`frozen=True` makes the dataclass immutable — once created, its fields cannot
be changed. This prevents accidental mutation and makes the object safe to
pass around freely.

### StreamControl

```python
@dataclass
class StreamControl:
    action: Literal["continue", "stop"]
    next_batch_size: int
```

This is what the client sends back during elicitation.
`Literal["continue", "stop"]`
means the `action` field can only hold one of those two exact strings — anything
else raises a validation error. FastMCP uses this type annotation to build a
JSON schema and sends it to the client so it knows exactly what shape of data
to return.

### StreamSummary

```python
@dataclass
class StreamSummary:
    ok: bool
    mode: str
    batches_sent: int
    rows_sent: int
    ...
```

This is the final return value of a streaming tool call. The service builds
it and the tool layer converts it to a dict with `asdict(summary)` before
returning it to the MCP client.

---

## 9. Layer 5 — Service

**File:** `server/app/services/user_service.py`

### What is a service layer?

The service layer owns all business logic — the rules of the system. It has
no knowledge of HTTP, MCP, or SQL. It:

- Calls the repository to get data.
- Decides how many rows to fetch per batch.
- Handles elicitation responses.
- Emits progress updates.

This separation means: if you switch from FastMCP to a different framework,
or from PostgreSQL to MongoDB, the service code is unchanged.

### The StreamContext Protocol

```python
class StreamContext(Protocol):
    async def info(self, message: str) -> None: ...

    async def warning(self, message: str) -> None: ...

    async def report_progress(self, progress, total, message) -> None: ...

    async def elicit(self, message, response_type) -> Any: ...
```

The service needs to send log messages and progress updates and ask questions
— but it cannot import FastMCP's `Context` directly without coupling itself
to that framework.

The `Protocol` solution: define only the methods the service needs. FastMCP's
`Context` happens to have all these methods, so it satisfies the protocol
without any explicit inheritance. In tests you can pass a fake object that
also has these methods.

### stream_users — the main loop

```python
async def stream_users(self, ctx, query, batch_size, max_rows):
    total = await self._repo.count(query)
    target = min(total, max_rows)  # never exceed max_rows

    processed = 0
    offset = 0

    while processed < target:
        remaining = target - processed
        limit = min(batch_size, remaining)  # don't overfetch on last batch
        batch = await self._repo.fetch_page(query, limit, offset)
        if not batch:
            break  # DB returned nothing — stop

        await self._emit_chunk(ctx, ...)  # send data NOW, don't wait
        processed += len(batch)
        offset += len(batch)
        await ctx.report_progress(processed, target, ...)
        await asyncio.sleep(0.25)  # small delay between batches
```

**Why `min(batch_size, remaining)` on the last batch?**  
Suppose `target=25` and `batch_size=10`:

- Batch 1: limit=10, rows 1–10
- Batch 2: limit=10, rows 11–20
- Batch 3: `remaining=5`, so `limit=min(10,5)=5`, rows 21–25

Without this cap, batch 3 would fetch rows 21–30 — five extra rows beyond the
limit.

### interactive_stream_users — adding elicitation

The loop is identical to `stream_users` except after each batch it calls:

```python
result = await ctx.elicit(
    message=f"Sent batch {batch_num}. Continue?",
    response_type=StreamControl,
)
```

`ctx.elicit()` pauses execution here — the whole async function suspends —
until the client sends back a `StreamControl`. The three outcomes:

| `result.action`             | Meaning                 | What the service does                |
|-----------------------------|-------------------------|--------------------------------------|
| `"cancel"`                  | Client aborted          | Return `ok=False, cancelled=True`    |
| `"decline"`                 | Client stopped politely | Return with `stopped_by_client=True` |
| `"continue"`                | Client wants more       | Update `batch_size`, loop again      |
| `"stop"` (in `result.data`) | Client is done          | Break the loop, return summary       |

### _emit_chunk helper

```python
@staticmethod
async def _emit_chunk(ctx, chunk):
    payload = {
        "type": "data_chunk",
        "batch_number": chunk.batch_number,
        "rows": [asdict(u) for u in chunk.rows],
    }
    await ctx.info("DATA_CHUNK " + json.dumps(payload, default=str))
```

This sends a log message with a special prefix `DATA_CHUNK `. The client's
log handler detects this prefix and parses the JSON — a lightweight streaming
mechanism that piggybacks on the existing log channel.

`asdict(u)` converts a `User` dataclass to a plain dict so `json.dumps` can
serialise it. `default=str` handles any type that JSON cannot handle natively
(like `datetime`) by converting it to a string.

---

## 10. Layer 6 — MCP tools

**File:** `server/app/tools/user_tools.py`

### Why does this layer exist?

Each MCP tool function needs to be decorated with `@mcp.tool`. But if the
service logic lived inside the decorated functions, you would not be able to
test the logic without starting the entire MCP server.

The solution: tool functions are kept intentionally thin. They do exactly two
things:

1. Extract the injected service from the lifespan context.
2. Delegate to it.

```python
@mcp.tool
async def stream_users(query, batch_size, max_rows, ctx):
    summary = await _service(ctx).stream_users(
        ctx, query, batch_size, max_rows
    )
    return asdict(summary)
```

No logic. No SQL. No decisions. Just wiring.

### The _service helper

```python
def _service(ctx: Context) -> UserService:
    svc = ctx.lifespan_context.get("user_service")
    if svc is None:
        raise RuntimeError("UserService not found in lifespan context.")
    return svc
```

`ctx.lifespan_context` is a dict that was populated in `server.py`'s
`lifespan()` function. This is Dependency Injection in action — the service
was built once at startup and is retrieved here at call time.

### register_tools

```python
def register_tools(mcp: FastMCP) -> None:
    @mcp.tool
    async def healthcheck(ctx): ...

    @mcp.tool
    async def stream_users(...): ...

    @mcp.tool
    async def interactive_stream_users(...): ...
```

Functions are defined inside `register_tools` so that `mcp` is available
in their scope (via closure) without being a global variable. This makes the
module importable without a live MCP instance — useful in tests.

---

## 11. Layer 7 — MCP server bootstrap

**File:** `server/app/server.py`

### Responsibility

This file does exactly four things and nothing else:

1. Configure structured logging.
2. Verify the FastMCP `Context` still satisfies the `StreamContext` Protocol.
3. Build the dependency graph in `lifespan()`.
4. Create the `FastMCP` instance and register tools.

### lifespan — dependency injection root

```python
@asynccontextmanager
async def lifespan(_: FastMCP):
    cfg = get_settings()  # read config
    pool = await DatabasePool.create(cfg.db_dsn)  # layer 1: infra
    repo = UserRepository(pool)  # layer 2: data
    user_service = UserService(repo)  # layer 3: logic

    yield {"user_service": user_service}  # inject into every tool call

    await pool.close()  # teardown
```

`@asynccontextmanager` turns this generator function into an async context
manager. Code before `yield` runs at startup. The dict passed to `yield`
becomes `ctx.lifespan_context`. Code after `yield` runs at shutdown.

**Why build all layers here?**  
This is the Composition Root — the single place in the application where
the dependency graph is assembled. If you need to swap `UserRepository` for
a mock in tests, this is the only place to change.

### Protocol verification

```python
def _verify_context_protocol() -> None:
    required = {"info", "warning", "report_progress", "elicit"}
    missing = required - set(dir(Context))
    if missing:
        raise TypeError(f"FastMCP Context missing: {missing}")
```

Called at startup. If a future version of `fastmcp` renames `report_progress`
to `report_progress_update`, this check catches it immediately with a clear
error — not silently at the first tool call.

### Structured logging

```python
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)
log = structlog.get_logger()
log.info("server.startup", host=cfg.host, port=cfg.port)
```

Each log line is a JSON object:
`{"event": "server.startup", "host": "0.0.0.0", "port": 8000, "timestamp": "..."}`.
Machine-readable logs can be queried in tools like Datadog or CloudWatch.
Plain `print()` logs cannot.

---

## 12. Layer 8 — Client strategies

**File:** `server/app/client/strategies.py`

### What problem do strategies solve?

When the server sends an elicitation request, the client needs to respond.
But the response logic varies:

- In a CLI test: follow a pre-scripted plan.
- In automated tests: always continue or always stop.
- In the UI: wait for the human to click a button.

If all of this logic lived in one function, it would be a mess of `if/else`
branches. The Strategy pattern cleanly separates each algorithm.

### The abstract base class

```python
class ElicitStrategy(abc.ABC):
    @abc.abstractmethod
    async def decide(self, message, response_type, params,
                     context) -> ElicitResult:
        ...
```

`abc.ABC` and `@abc.abstractmethod` enforce the interface. You cannot
instantiate `ElicitStrategy` directly — you must subclass it and implement
`decide()`. If you forget, Python raises `TypeError` at instantiation time.

### PlanStrategy

```python
class PlanStrategy(ElicitStrategy):
    def __init__(self, plan: deque[tuple[str, int]]) -> None:
        self._plan = plan

    async def decide(self, message, response_type, params, context):
        action, batch_size = (
            self._plan.popleft() if self._plan else ("stop", 0)
        )
        return response_type(action=action, next_batch_size=batch_size)
```

A `deque` is a double-ended queue. `popleft()` removes and returns the
first item. The plan `"continue:8,continue:12,stop:0"` is parsed into:
`deque([("continue", 8), ("continue", 12), ("stop", 0)])`.

Each elicitation consumes one entry. When exhausted, it defaults to `"stop"`.

### CallbackStrategy

```python
class CallbackStrategy(ElicitStrategy):
    def __init__(self, callback: DecisionCallback) -> None:
        self._callback = callback

    async def decide(self, message, response_type, params, context):
        action, batch_size = await self._callback(message, params)
        return response_type(action=action, next_batch_size=batch_size)
```

The `callback` is an async function provided by the bridge. The bridge's
callback creates an `asyncio.Future`, posts it to a store, and then `await`s it.
When the browser hits `POST /elicit/{run_id}`, the future is resolved with
the user's choice, and `decide()` returns.

This is how human input flows into a paused async function — through a future
that bridges the gap between an HTTP request and a suspended coroutine.

---

## 13. Layer 9 — Client handlers

**File:** `server/app/client/handlers.py`

FastMCP's `Client` accepts three callback functions: one for log messages,
one for progress, one for elicitation. This file provides factories that
build those callbacks.

### make_log_handler

```python
def make_log_handler(on_chunk=None):
    async def handler(message: LogMessage) -> None:
        text = str(message.data)
        if text.startswith("DATA_CHUNK "):
            chunk = json.loads(text.removeprefix("DATA_CHUNK "))
            if on_chunk:
                on_chunk(chunk)
            return
        print(f"[client] server log: {text}")

    return handler
```

This is a **closure** — `handler` is a function returned by another function.
It "closes over" the `on_chunk` variable from the outer scope, remembering
it even after `make_log_handler` has returned.

The bridge passes `on_chunk=_on_chunk` so that every data chunk triggers a
trace event. The CLI client passes `on_chunk=None` and just prints.

### make_elicit_handler

```python
def make_elicit_handler(strategy: ElicitStrategy, on_elicit=None):
    async def handler(message, response_type, params, context):
        if on_elicit:
            on_elicit(message)
        return await strategy.decide(message, response_type, params, context)

    return handler
```

The elicitation handler delegates entirely to the strategy. `on_elicit` is
an optional side-effect hook — the bridge uses it to emit a trace event
before the strategy waits for the user's decision.

---

## 14. Layer 10 — MCP client wrapper

**File:** `server/app/client/mcp_client.py`

### What it wraps

FastMCP's `Client` is a low-level object. `MCPClient` wraps it to:

- Hide handler wiring from callers.
- Provide a `wait_until_ready()` retry loop for Docker startup ordering.
- Offer a clean `call_tool()` / `list_tools()` API.

```python
class MCPClient:
    def __init__(self, server_url, strategy, on_chunk=None, timeout=60.0):
        self._client = Client(
            server_url,
            log_handler=make_log_handler(on_chunk=on_chunk),
            progress_handler=make_progress_handler(),
            elicitation_handler=make_elicit_handler(strategy),
            timeout=timeout,
        )
```

### wait_until_ready

```python
async def wait_until_ready(self, attempts=30, delay=1.0):
    for attempt in range(1, attempts + 1):
        try:
            async with self._client:
                result = await self._client.call_tool("healthcheck")
                return
        except Exception as exc:
            await asyncio.sleep(delay)
    raise RuntimeError("Server not ready")
```

In Docker, services start in parallel. The bridge might start before the MCP
server is ready. This loop retries the healthcheck up to 30 times with a 1s
delay between attempts. Only raises if all attempts fail.

---

## 15. Layer 11 — Trace system

**Files:** `server/app/bridge/trace_models.py`, `trace_bus.py`

### TraceEvent

```python
@dataclass
class TraceEvent:
    event_id: str  # unique ID for this event
    parent_id: str | None  # ID of the parent event (builds the tree)
    run_id: str  # groups all events for one tool call
    actor: Actor  # AGENT | GATEWAY | MCP | DB
    phase: Phase  # INPUT | PROCESSING | OUTPUT | ERROR
    component: str  # e.g. "UserService", "MCPClient"
    label: str  # short human-readable title
    input: Any  # what this layer received
    output: Any  # what this layer returned
    detail: str  # extra narrative (SQL, log text, etc.)
    timestamp: float  # Unix timestamp with sub-second precision
```

`parent_id` is the key field for building the nested call tree. When the
React UI receives a flat list of events, it groups them by `parent_id` to
reconstruct the hierarchy.

### TraceBus — two implementations

The bus is an event router: producers emit events, consumers subscribe
to receive them.

**Why two implementations?**

If the bridge runs with one worker process, an in-process `asyncio.Queue`
works fine. But with multiple workers (e.g., `gunicorn -w 4`):

- Worker A handles `POST /run` → creates the run, emits events.
- Worker B handles `GET /events/{run_id}` → subscribes to the queue.
- The subscriber is in a different process and never sees events from worker A.

Redis Pub/Sub solves this: all workers publish to and subscribe from
the same Redis channel.

**InProcessTraceBus:**

```python
class InProcessTraceBus:
    def __init__(self):
        self._subs = defaultdict(list)  # run_id → [Queue, Queue, ...]

    async def emit(self, event):
        for q in self._subs.get(event.run_id, []):
            await q.put(event)  # push to every subscriber

    async def subscribe(self, run_id):
        q = asyncio.Queue()
        self._subs[run_id].append(q)
        try:
            while True:
                item = await q.get()
                if item is None:  # None = "stream ended" sentinel
                    return
                yield item
        finally:
            self._subs[run_id].remove(q)
```

The `subscribe` method is an **async generator** — it uses `yield` inside
an `async def`. Each `yield` sends one event to the caller. The generator
runs until it sees the `None` sentinel.

**RedisTraceBus** publishes JSON to a Redis channel `trace:{run_id}` and
subscribes via `pubsub.listen()`. Any worker can receive events from any
other worker.

---

## 16. Layer 12 — HTTP bridge

**File:** `server/app/bridge/bridge.py`

### Why does this layer exist?

Browsers cannot call MCP servers directly — MCP runs over a custom protocol.
The bridge is a standard HTTP/SSE API that any browser can call, which
internally translates those calls into real MCP operations.

### Three endpoints

**`POST /run`**

```python
@app.post("/run")
async def run_tool(req: RunRequest) -> RunResponse:
    run_id = str(uuid.uuid4())[:12]
    asyncio.create_task(
        _run_tool(run_id, req.tool, req.arguments, req.elicit_plan, ...)
    )
    return RunResponse(run_id=run_id)
```

Returns immediately with a `run_id`. The actual work happens in a background
`asyncio.Task`. This is non-blocking — the browser does not wait for the tool
to finish before it gets a response.

**`GET /events/{run_id}`**

```python
@app.get("/events/{run_id}")
async def events(run_id: str) -> StreamingResponse:
    async def _generator():
        async for event in bus.subscribe(run_id):
            yield f"data: {json.dumps(event.to_dict())}\n\n"
        yield 'data: {"type":"run_complete"}\n\n'

    return StreamingResponse(_generator(), media_type="text/event-stream")
```

An SSE stream. `StreamingResponse` keeps the HTTP connection open and sends
each `yield`ed string as it arrives. The browser's `EventSource` receives
them as individual message events.

**`POST /elicit/{run_id}`**

```python
@app.post("/elicit/{run_id}")
async def elicit_reply(run_id: str, reply: ElicitReply):
    ok = await store.resolve(run_id, (reply.action, reply.next_batch_size))
    if not ok:
        raise HTTPException(404, ...)
    return {"status": "accepted"}
```

Called by the browser when the user clicks "Reply" in the elicitation dialog.
`store.resolve()` finds the `asyncio.Future` that was created when the server
paused and calls `fut.set_result(value)`. This wakes up the suspended
`CallbackStrategy.decide()` coroutine, which returns the user's choice to
the service, which resumes the streaming loop.

### The elicitation timeout

```python
result = await asyncio.wait_for(fut, timeout=cfg.elicit_timeout_seconds)
```

`asyncio.wait_for` wraps the future with a timeout. If the browser tab is
closed or the user never replies within `elicit_timeout_seconds` (default 120s),
a `TimeoutError` is raised, an error trace event is emitted, and the run ends
cleanly rather than hanging forever.

### The _run_tool background task

This is the core of the bridge. It:

1. Emits a root trace event (the tree root).
2. Selects a strategy (PlanStrategy or CallbackStrategy).
3. Wires log, progress, and elicitation callbacks that emit trace events.
4. Creates a real `fastmcp.Client` and calls the tool.
5. Emits a final result trace event.
6. Calls `bus.close(run_id)` to send the EOF sentinel.

Every `_emit()` call passes `parent_id` so the trace tree is correctly nested.

---

## 17. Layer 13 — React UI

**File:** `ui/src/App.jsx`

### Key concepts

**State with useState:**

```javascript
const [events, setEvents] = useState([]);
```

`useState` returns the current value and a setter. When `setEvents` is called,
React re-renders the component with the new value. Never mutate state directly
(`events.push(...)`) — always use the setter.

**Side effects with useRef:**

```javascript
const esRef = useRef(null);
```

`useRef` holds a mutable value that does not trigger re-renders. Used here to
hold the `EventSource` object so it can be closed when a new run starts.

**buildTree — reconstructing the call tree:**

```javascript
function buildTree(events) {
    const byId = {};
    const roots = [];
    for (const ev of events) byId[ev.event_id] = { ...ev, children: [] };
    for (const ev of events) {
        if (ev.parent_id && byId[ev.parent_id])
            byId[ev.parent_id].children.push(byId[ev.event_id]);
        else
            roots.push(byId[ev.event_id]);
    }
    return roots;
}
```

Events arrive as a flat array over SSE. `buildTree` groups them by
`parent_id` into a tree. Root nodes have `parent_id === null`.

**TraceNode — recursive rendering:**

```javascript
function TraceNode({ node, depth }) {
    return (
        <div style={{ marginLeft: depth * 16 }}>
            <div onClick={() => setOpen(o => !o)}>
                {node.label}
            </div>
            {open && node.children.map(child => (
                <TraceNode node={child} depth={depth + 1} />
            ))}
        </div>
    );
}
```

A component that renders itself for each child — this is recursion in JSX.
Each level of depth adds 16px of left margin, producing the visual indentation.

**ElicitPrompt — the pause dialog:**

```javascript
const send = async () => {
    await fetch(`${bridgeUrl}/elicit/${runId}`, {
        method: "POST",
        body: JSON.stringify({ action, next_batch_size: batchSize }),
    });
    onReplied(action, batchSize);
};
```

When the user clicks "Reply", this `POST` request resolves the `asyncio.Future`
in the bridge, which wakes up the paused server coroutine.

**Vite proxy:**  
`vite.config.js` proxies `/run`, `/events`, `/elicit` to `localhost:8001`.
This means the browser fetches `/run` (same origin, no CORS), and Vite
transparently forwards it to the bridge. No CORS headers needed in development.

---

## 18. Infrastructure — Docker

**File:** `docker-compose.yml`

### What Docker Compose does

Docker Compose defines multiple containers and their relationships in one file.
`docker compose up --build` builds images and starts all containers.

### Services

**db**  
Runs PostgreSQL. The `healthcheck` block tells Docker how to check if the DB
is ready. Other services use `condition: service_healthy` to wait for it.

**server**  
Builds from `server/Dockerfile` using `uv`. Depends on `db` being healthy.
`APP_DB_DSN` points to the `db` container by its service name (`db:5432`).
Docker's internal DNS resolves `db` to the container's IP automatically.

**bridge**  
Uses the same Docker image as `server` but runs a different command:
`python -m app.bridge.bridge`. Shares the same Python package, so all
modules (`config.py`, `strategies.py`, etc.) are available.
`APP_SERVER_URL=http://server:8000/mcp` — again, `server` resolves via
Docker DNS.

**redis**  
Redis 7. Only needed when `APP_USE_REDIS=true`. The bridge and server both
reference it via `redis://redis:6379/0`.

### Port mapping

```yaml
ports:
  - "8001:8001"
```

Format is `host_port:container_port`. `8001:8001` means: traffic arriving
at port 8001 on your laptop is forwarded to port 8001 inside the container.

---

## 19. Design patterns reference

### Repository pattern

| Aspect               | Detail                                         |
|----------------------|------------------------------------------------|
| File                 | `repositories/user_repo.py`                    |
| What it encapsulates | All SQL for `app_user`                         |
| What it returns      | `User` domain objects, never raw dicts         |
| Why                  | Swap DB engine without touching business logic |

### Service layer

| Aspect                 | Detail                                             |
|------------------------|----------------------------------------------------|
| File                   | `services/user_service.py`                         |
| What it encapsulates   | Pagination loop, elicitation decisions, validation |
| Framework dependencies | Zero — uses `StreamContext` Protocol               |
| Why                    | Test business logic without MCP or DB              |

### Dependency injection

| Aspect           | Detail                                   |
|------------------|------------------------------------------|
| Composition root | `server.py` `lifespan()`                 |
| Injected into    | `ctx.lifespan_context["user_service"]`   |
| Why              | One place to change the dependency graph |

### Strategy pattern

| Aspect           | Detail                                                             |
|------------------|--------------------------------------------------------------------|
| Interface        | `ElicitStrategy.decide()`                                          |
| Concrete classes | `PlanStrategy`, `AlwaysContinue`, `AlwaysStop`, `CallbackStrategy` |
| Why              | Swap elicitation behaviour at runtime without changing client code |

---

## 20. Data flow walkthrough

Here is what happens, step by step, when you click "Run tool" for
`interactive_stream_users` in the browser:

```
Step 1  Browser POSTs /run to the bridge
        { tool: "interactive_stream_users",
          arguments: { query: "User", initial_batch_size: 5, max_rows: 30 } }

Step 2  Bridge creates run_id="abc123", starts background task _run_tool,
        returns { run_id: "abc123" } immediately

Step 3  Browser opens SSE connection  GET /events/abc123
        (stays open, waiting for events)

Step 4  _run_tool emits a root GATEWAY/INPUT trace event → SSE pushes it
        Browser adds it to the trace tree

Step 5  _run_tool builds a fastmcp.Client, connects to MCP server :8000

Step 6  Bridge calls  client.call_tool("interactive_stream_users", {...})
        MCP server receives the call, FastMCP routes it to the decorated function

Step 7  user_tools.py extracts UserService from lifespan_context
        Calls  service.interactive_stream_users(ctx, ...)

Step 8  Service calls  repo.count("User")  → 40 rows match
        target = min(40, 30) = 30

Step 9  Service fetches batch 1 (5 rows), calls ctx.info("DATA_CHUNK ...")
        Bridge's log handler intercepts it, emits MCP/OUTPUT trace event → SSE
        Browser renders batch 1 rows in the table

Step 10 Service calls ctx.report_progress(5, 30, "batch 1")
        Bridge's progress handler emits progress trace event → SSE
        Browser shows progress in the trace

Step 11 Service calls ctx.elicit("Sent batch 1. Continue?", StreamControl)
        Execution PAUSES here

Step 12 Bridge's elicit handler creates asyncio.Future, emits AGENT/INPUT
        trace event with "Waiting for user decision" → SSE
        Browser renders the ElicitPrompt dialog

Step 13 User selects action="continue", next_batch_size=8, clicks Reply
        Browser POSTs  /elicit/abc123  { action: "continue", next_batch_size: 8 }

Step 14 Bridge resolves the Future with ("continue", 8)
        ctx.elicit() returns, service resumes

Step 15 Service updates batch_size=8, loops back to fetch batch 2 (8 rows)
        Steps 9–14 repeat for batches 2, 3 etc.

Step 16 Eventually user clicks Reply with action="stop"
        Service breaks out of loop, returns StreamSummary

Step 17 MCP tool returns asdict(summary) to FastMCP
        FastMCP sends it back to the bridge's client.call_tool() call

Step 18 Bridge emits final MCP/OUTPUT trace event with the summary → SSE
        Calls bus.close(run_id) → SSE generator receives None sentinel
        SSE generator yields  data: {"type":"run_complete"}\n\n
        Browser closes EventSource, sets running=false
```

---

## 21. Glossary

| Term                 | Definition                                                                  |
|----------------------|-----------------------------------------------------------------------------|
| `async def`          | Function that can pause execution at `await` points                         |
| `await`              | Pause here and wait for the async operation to complete                     |
| `asyncio.Future`     | A placeholder for a value that will arrive later                            |
| `asyncio.Task`       | A coroutine running in the background                                       |
| ABC                  | Abstract Base Class — a class that defines an interface                     |
| Closure              | A function that remembers variables from its enclosing scope                |
| Composition root     | The single place where the dependency graph is assembled                    |
| Connection pool      | A set of pre-opened DB connections lent out to queries                      |
| Coroutine            | An `async def` function that has been called but not yet awaited            |
| dataclass            | Python class generated automatically from field type annotations            |
| Decorator            | A function that wraps another function, modifying its behaviour             |
| Dependency injection | Passing dependencies in rather than creating them internally                |
| DSN                  | Data Source Name — a connection string for a database                       |
| Elicitation          | Server pausing a tool call to ask the client a question                     |
| `frozen=True`        | Dataclass option that makes instances immutable                             |
| `ILIKE`              | PostgreSQL case-insensitive LIKE pattern match                              |
| `@lru_cache`         | Memoize a function — cache and return the first result every time           |
| MCP                  | Model Context Protocol — standard for AI tool communication                 |
| Protocol             | Python structural interface — satisfied by any class with the right methods |
| Pub/Sub              | Publish/Subscribe — broadcast events to multiple subscribers                |
| Repository           | Class that encapsulates all DB queries for one entity                       |
| `row_factory`        | psycopg option controlling how query rows are returned                      |
| Service layer        | Class that owns business logic, with no framework dependencies              |
| SSE                  | Server-Sent Events — server pushes a stream of messages to the browser      |
| Strategy pattern     | Family of interchangeable algorithms behind one interface                   |
| `structlog`          | Structured logging library — produces JSON log lines                        |
| Vite proxy           | Dev server feature that forwards browser requests to another port           |
