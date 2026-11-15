# MCP Tutorial — Chunk 3 of 8

## CHUNKS GENERATED: [3 / 8]

## ACTIVE CHUNK: [3 / 8]

## SECTIONS IN THIS CHUNK: [§05, §06]

---

## §05. BASIC EXAMPLE

**Goal**: Build a minimal MCP server that exposes one tool:
`get_current_time`. A connected LLM agent calls it and returns
the current UTC time.

Here is the §05–§06 flow diagram for quick visual reference:

![mcp_chunk3_architecture.svg](../../assets/chunks/mcp_chunk3.png)

---

### Project structure

```
mcp-basic/
├── docker-compose.yml
├── pyproject.toml
└── src/
    └── server.py
```

---

### Step 1 — Setup and install dependencies

**`pyproject.toml`**

```toml
[project]
name = "mcp-basic"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]>=1.0.0", # MCP Python SDK
    "uvicorn>=0.29.0", # ASGI server
    "structlog>=24.0.0", # Structured logging
]
```

**`docker-compose.yml`**

```yaml
services:
  mcp-server:
    image: ghcr.io/astral-sh/uv:python3.12-bookworm-slim
    working_dir: /app
    volumes:
      - .:/app
    # uv runs the server directly — no venv step needed
    command: >
      uv run --project /app
      uvicorn src.server:app
      --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
```

**Install locally (optional — for IDE support)**

```bash
uv sync
```

---

### Step 2 — Write the core logic

**`src/server.py`**

```python
# ── Imports ──────────────────────────────────────────────
from datetime import datetime, timezone  # std-lib time
import structlog  # structured logging
from mcp.server.fastmcp import FastMCP  # MCP high-level API

# ── Logger ───────────────────────────────────────────────
# structlog writes JSON lines — easy to parse in production
log = structlog.get_logger()

# ── MCP server instance ──────────────────────────────────
# FastMCP wraps the low-level MCP SDK.
# `name` is the server identity sent to the LLM host.
mcp = FastMCP(name="basic-time-server")


# ── Tool definition ──────────────────────────────────────
# @mcp.tool() registers this function as an MCP tool.
# The docstring becomes the tool description the LLM reads.
@mcp.tool()
def get_current_time() -> dict:
    """Return the current UTC date and time."""
    now = datetime.now(timezone.utc)
    log.info("tool_called", tool="get_current_time", ts=now.isoformat())
    # The dict return is serialised to JSON for the LLM
    return {"utc_time": now.isoformat()}


# ── ASGI app ─────────────────────────────────────────────
# mcp.http_app() exposes the server over HTTP/SSE transport.
# uvicorn receives this `app` object.
app = mcp.http_app()
```

---

### Step 3 — Run and verify output

**Start the server**

```bash
docker compose up
```

**Call the tool manually (curl)**

```bash
# 1. Open SSE stream
curl -N http://localhost:8000/sse

# 2. In a second terminal: call the tool via JSON-RPC
curl -X POST http://localhost:8000/messages \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_current_time",
      "arguments": {}
    }
  }'
```

**Expected JSON-RPC response**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"utc_time\": \"2025-06-01T12:34:56.789012+00:00\"}"
      }
    ]
  }
}
```

**Expected structured log line (stdout)**

```json
{
  "event": "tool_called",
  "tool": "get_current_time",
  "ts": "2025-06-01T12:34:56.789012+00:00",
  "level": "info"
}
```

---

### §05 Flow diagram

```
User / LLM host
      │
      │  HTTP POST /messages  (JSON-RPC: tools/call)
      ▼
┌─────────────────────┐
│  FastMCP HTTP layer  │  ← receives JSON-RPC request
│  (uvicorn + ASGI)   │
└────────┬────────────┘
         │  deserialise + route
         ▼
┌─────────────────────┐
│  get_current_time() │  ← tool function executes
│  returns dict       │
└────────┬────────────┘
         │  serialise to JSON
         ▼
┌─────────────────────┐
│  JSON-RPC response  │  ← sent back to caller
└─────────────────────┘
```

---

## §06. INTERMEDIATE LEVEL

**Goal**: A multi-tool MCP server backed by PostgreSQL.
Exposes two tools:

| Tool          | What it does                      |
|---------------|-----------------------------------|
| `create_note` | Insert a note into the DB         |
| `list_notes`  | Retrieve all notes (newest first) |

Uses **Clean Architecture** + **Ports and Adapters** for DB.

---

### Project structure

```
mcp-notes/
├── docker-compose.yml
├── pyproject.toml
├── nginx/
│   └── nginx.conf
└── src/
    ├── domain/
    │   └── note.py          # Entity (pure Python)
    ├── ports/
    │   └── note_repo.py     # Repository interface (port)
    ├── adapters/
    │   └── postgres_repo.py # PostgreSQL adapter
    ├── server.py            # MCP tools + FastAPI gateway
    └── db.py                # Connection pool setup
```

---

### Step 1 — Setup and install dependencies

**`pyproject.toml`**

```toml
[project]
name = "mcp-notes"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]>=1.0.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.29.0",
    "asyncpg>=0.29.0", # async PostgreSQL driver
    "structlog>=24.0.0",
    "pydantic>=2.7.0",
]
```

**`docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: notes
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U app -d notes" ]
      interval: 5s
      retries: 5

  mcp-server:
    image: ghcr.io/astral-sh/uv:python3.12-bookworm-slim
    working_dir: /app
    volumes:
      - .:/app
    environment:
      DATABASE_URL: "postgresql://app:secret@postgres:5432/notes"
    command: >
      uv run --project /app
      uvicorn src.server:app
      --host 0.0.0.0 --port 8000
    depends_on:
      postgres:
        condition: service_healthy

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    depends_on:
      - mcp-server
```

**`nginx/nginx.conf`**

```nginx
events {
}

http {
    upstream mcp {
        server mcp-server:8000;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://mcp;
            # Required for SSE: disable response buffering
            proxy_buffering off;
            proxy_cache off;
            # SSE keep-alive
            proxy_read_timeout 3600s;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }
    }
}
```

---

### Step 2 — Write the core logic

**`src/domain/note.py`** — pure domain entity, no framework deps

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Note:
    id: int | None  # None until persisted
    content: str  # note body
    created_at: datetime  # set by DB on insert
```

---

**`src/ports/note_repo.py`** — abstract port (interface)

```python
from abc import ABC, abstractmethod
from src.domain.note import Note


class NoteRepository(ABC):
    """Port: defines what the app needs from storage."""

    @abstractmethod
    async def create(self, content: str) -> Note:
        """Persist a new note and return it."""
        ...

    @abstractmethod
    async def list_all(self) -> list[Note]:
        """Return all notes, newest first."""
        ...
```

---

**`src/db.py`** — async connection pool

```python
import os
import asyncpg  # async postgres driver
import structlog

log = structlog.get_logger()

_pool: asyncpg.Pool | None = None  # module-level singleton


async def get_pool() -> asyncpg.Pool:
    """Return (or create) the shared connection pool."""
    global _pool
    if _pool is None:
        url = os.environ["DATABASE_URL"]  # fail fast if missing
        _pool = await asyncpg.create_pool(
            dsn=url,
            min_size=2,  # keep 2 connections warm
            max_size=10,  # hard cap
        )
        log.info("db_pool_created", min=2, max=10)
    return _pool
```

---

**`src/adapters/postgres_repo.py`** — concrete adapter

```python
import asyncpg
import structlog
from src.domain.note import Note
from src.ports.note_repo import NoteRepository

log = structlog.get_logger()


class PostgresNoteRepository(NoteRepository):
    """Adapter: fulfils the NoteRepository port via asyncpg."""

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool  # injected — no direct import of get_pool

    async def create(self, content: str) -> Note:
        async with self._pool.acquire() as conn:
            # RETURNING gives us the generated id + timestamp
            row = await conn.fetchrow(
                """
                INSERT INTO notes (content)
                VALUES ($1)
                RETURNING id, content, created_at
                """,
                content,
            )
        log.info("note_created", id=row["id"])
        return Note(
            id=row["id"],
            content=row["content"],
            created_at=row["created_at"],
        )

    async def list_all(self) -> list[Note]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, content, created_at "
                "FROM notes ORDER BY created_at DESC"
            )
        log.info("notes_listed", count=len(rows))
        return [
            Note(id=r["id"], content=r["content"],
                 created_at=r["created_at"])
            for r in rows
        ]
```

---

**`src/server.py`** — MCP tools + startup wiring

```python
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from src.db import get_pool
from src.adapters.postgres_repo import PostgresNoteRepository

log = structlog.get_logger()
mcp = FastMCP(name="notes-server")

# Module-level repo — populated on startup
repo: PostgresNoteRepository | None = None


# ── Startup / shutdown (lifespan) ────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Init DB pool before serving; close on shutdown."""
    global repo
    pool = await get_pool()
    # Create table if it doesn't exist yet
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id         SERIAL PRIMARY KEY,
                content    TEXT        NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
    repo = PostgresNoteRepository(pool)
    log.info("server_ready")
    yield  # server runs here
    await pool.close()  # clean shutdown
    log.info("server_shutdown")


# ── MCP Tools ────────────────────────────────────────────
@mcp.tool()
async def create_note(content: str) -> dict:
    """Create and persist a new note."""
    note = await repo.create(content)  # delegates to adapter
    return {
        "id": note.id,
        "content": note.content,
        "created_at": note.created_at.isoformat(),
    }


@mcp.tool()
async def list_notes() -> list[dict]:
    """Return all notes, newest first."""
    notes = await repo.list_all()
    return [
        {
            "id": n.id,
            "content": n.content,
            "created_at": n.created_at.isoformat(),
        }
        for n in notes
    ]


# ── Mount MCP onto FastAPI ───────────────────────────────
# mcp.http_app() returns an ASGI app with /sse + /messages
app = FastAPI(lifespan=lifespan)
app.mount("/", mcp.http_app())
```

---

### Step 3 — Run and verify output

```bash
docker compose up
```

**Create a note**

```bash
curl -X POST http://localhost/messages \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "create_note",
      "arguments": {"content": "MCP is stateless per request"}
    }
  }'
```

**Expected response**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"id\": 1, \"content\": \"MCP is stateless per request\",
        \
        "created_at\": \"2025-06-01T12:00:00+00:00\"}"
      }
    ]
  }
}
```

**List notes**

```bash
curl -X POST http://localhost/messages \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0","id":2,
    "method":"tools/call",
    "params":{"name":"list_notes","arguments":{}}
  }'
```

**Expected structured logs (order of events)**

```
{"event":"db_pool_created","min":2,"max":10}
{"event":"server_ready"}
{"event":"note_created","id":1}
{"event":"notes_listed","count":1}
```

---

### §06 Architecture diagram

```
Nginx (port 80)
      │
      │  reverse proxy (SSE-safe)
      ▼
FastAPI + FastMCP  (port 8000)
      │
      ├── /sse        ← SSE stream endpoint
      └── /messages   ← JSON-RPC tool calls
              │
              │  create_note / list_notes
              ▼
      NoteRepository (port / interface)
              │
              │  PostgresNoteRepository (adapter)
              ▼
      asyncpg pool
              │
              ▼
      PostgreSQL 16 (port 5432)
```

---

### §06 Edge cases

| Scenario            | Behavior                         | Why                             |
|---------------------|----------------------------------|---------------------------------|
| DB not reachable    | Server fails on startup          | `get_pool()` raises immediately |
| Empty notes table   | `list_notes` returns `[]`        | `fetchall` returns empty list   |
| `content` is empty  | Tool succeeds; blank row saved   | No validation yet — see §07     |
| Pool exhausted      | Request waits up to pool timeout | asyncpg queues acquire() calls  |
| Duplicate `content` | Second row created (no UNIQUE)   | No uniqueness constraint set    |

---

### §06 Key limitations

1. **No input validation** — `content` is not length-checked or
   sanitised before insert. Fixed in §07 with Pydantic models.

2. **No authentication** — any caller can create or read notes.
   Fixed in §07 with token-based auth middleware.

3. **No pagination** — `list_notes` loads all rows into memory.
   At scale, add `LIMIT` / `OFFSET` or cursor-based pagination.

---

## 🔑 Jargon Summary

| Term                | Definition                                       |
|---------------------|--------------------------------------------------|
| **FastMCP**         | High-level MCP SDK class; wraps low-level SDK    |
| **Port**            | Abstract interface your app depends on           |
| **Adapter**         | Concrete implementation of a Port                |
| **asyncpg**         | Async Python driver for PostgreSQL               |
| **lifespan**        | FastAPI hook for startup / shutdown logic        |
| **SSE**             | Server-Sent Events; HTTP transport for MCP       |
| **JSON-RPC**        | Protocol used to call MCP tools over HTTP        |
| **Connection pool** | Pre-opened DB connections shared across requests |
| **RETURNING**       | SQL clause to get generated columns after INSERT |