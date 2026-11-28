<!--
  CHUNKS GENERATED        : [5 / 8]
  ACTIVE CHUNK            : [5 / 8]
  SECTIONS IN THIS CHUNK  : [§06]
-->

# §06 — Intermediate Level: Bidirectional Streaming Tool

---

## Overview

```
Tool 1 : stream_chunks  → server sends chunks → client prints them
Tool 2 : process_batch  → server sends progress → server elicits
                        → client replies continue/stop + new size
                        → server resumes or halts
```

Here is the bidirectional flow visualized inline:

![](../../assets/streamable/bidirectional_tool2_flow.png)

---

## Project Structure

```
mcp-intermediate/
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── server/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── src/
│   │   ├── main.py                  # FastAPI + MCP mount
│   │   ├── mcp_server.py            # Tool definitions
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── chunk_streamer.py    # Tool 1
│   │   │   └── batch_processor.py  # Tool 2 (bidirectional)
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── port.py              # Repository interface (Port)
│   │   │   └── adapter.py           # PostgreSQL adapter
│   │   └── seed.py                  # 100+ seed records
└── client/
    ├── Dockerfile
    ├── pyproject.toml
    └── src/
        └── client.py
```

---

## Step 1 — docker-compose.yml

```yaml
# docker-compose.yml
# Orchestrates: postgres, server, client, nginx

version: "3.9"

services:

  # ── PostgreSQL ──────────────────────────────────────────────
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: mcp
      POSTGRES_PASSWORD: mcp_pass
      POSTGRES_DB: mcp_db
    ports:
      - "5432:5432"
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U mcp" ]
      interval: 5s
      timeout: 3s
      retries: 10

  # ── MCP Server ──────────────────────────────────────────────
  server:
    build: ./server
    environment:
      DATABASE_URL: postgresql://mcp:mcp_pass@postgres:5432/mcp_db
      LOG_LEVEL: INFO
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8000:8000"

  # ── MCP Client ──────────────────────────────────────────────
  client:
    build: ./client
    environment:
      MCP_SERVER_URL: http://nginx/mcp
    depends_on:
      - nginx

  # ── Nginx reverse proxy ─────────────────────────────────────
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    depends_on:
      - server
```

---

## Step 2 — nginx/nginx.conf

```nginx
# nginx/nginx.conf
# Proxies /mcp/* → server:8000
# Disables buffering so SSE chunks reach the client immediately

events {
}

http {
    upstream mcp_backend {
        server server:8000;
    }

    server {
        listen 80;

        location /mcp {
            proxy_pass http://mcp_backend;
            proxy_http_version 1.1;

            # ── Required for SSE / streaming ─────────────────
            proxy_set_header Connection "";
            proxy_buffering off;           # send chunks immediately
            proxy_cache off;
            chunked_transfer_encoding on;

            # ── Standard proxy headers ────────────────────────
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            # ── Keep connection alive for long-running tools ──
            proxy_read_timeout 300s;
        }
    }
}
```

---

## Step 3 — server/pyproject.toml

```toml
# server/pyproject.toml

[project]
name = "mcp-server-intermediate"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "mcp[cli]>=1.6", # MCP SDK with streamable HTTP
    "asyncpg>=0.29", # async PostgreSQL driver
    "structlog>=24.1", # structured logging
    "python-dotenv>=1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Step 4 — server/Dockerfile

```dockerfile
# server/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# Install uv (fast package installer)
RUN pip install uv

COPY pyproject.toml .
COPY src/ ./src/

# Install dependencies using uv
RUN uv pip install --system -e .

# Run seed then start server
CMD ["sh", "-c", "python src/seed.py && uvicorn src.main:app \
     --host 0.0.0.0 --port 8000 --log-level info"]
```

---

## Step 5 — server/src/db/port.py

```python
# src/db/port.py
# PORT  = abstract interface (Clean Architecture)
# All DB calls go through this interface.
# The adapter (adapter.py) implements it.

from abc import ABC, abstractmethod
from typing import AsyncIterator


class RecordPort(ABC):
    """Abstract repository for records table."""

    @abstractmethod
    async def fetch_batch(
            self,
            offset: int,
            limit: int,
    ) -> list[dict]:
        """Return a page of records from the DB."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Return total number of records."""
        ...
```

---

## Step 6 — server/src/db/adapter.py

```python
# src/db/adapter.py
# ADAPTER = concrete implementation of RecordPort using asyncpg

import asyncpg
import structlog

from .port import RecordPort

log = structlog.get_logger(__name__)


class PostgresRecordAdapter(RecordPort):
    """Reads records from PostgreSQL."""

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Open connection pool. Called once at startup."""
        self._pool = await asyncpg.create_pool(self._dsn)
        log.info("db.connected", dsn=self._dsn)

    async def fetch_batch(
            self,
            offset: int,
            limit: int,
    ) -> list[dict]:
        """SELECT limit rows starting at offset."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, name, value "
                "FROM records "
                "ORDER BY id "
                "LIMIT $1 OFFSET $2",
                limit,
                offset,
            )
        # Convert asyncpg Record → plain dict
        return [dict(r) for r in rows]

    async def count(self) -> int:
        """COUNT(*) from records."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT COUNT(*) AS n FROM records")
        return row["n"]
```

---

## Step 7 — server/src/seed.py

```python
# src/seed.py
# Inserts 100 seed rows into PostgreSQL.
# Run once at container startup.

import asyncio
import os
import asyncpg
import structlog

log = structlog.get_logger(__name__)

DSN = os.environ["DATABASE_URL"]


async def seed() -> None:
    conn = await asyncpg.connect(DSN)

    # Create table if it doesn't exist
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id    SERIAL PRIMARY KEY,
            name  TEXT    NOT NULL,
            value INTEGER NOT NULL
        )
    """)

    # Skip if already seeded
    count = await conn.fetchval("SELECT COUNT(*) FROM records")
    if count >= 100:
        log.info("seed.skipped", existing=count)
        await conn.close()
        return

    # Insert 100 rows
    rows = [
        (f"record_{i:03d}", i * 7 % 100)
        for i in range(1, 101)
    ]
    await conn.executemany(
        "INSERT INTO records (name, value) VALUES ($1, $2)",
        rows,
    )
    log.info("seed.done", inserted=100)
    await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
```

---

## Step 8 — server/src/tools/chunk_streamer.py  (Tool 1)

```python
# src/tools/chunk_streamer.py
# TOOL 1: stream_chunks
#
# The server streams N text chunks to the client.
# Each chunk is yielded as a separate SSE event.
# The client prints each chunk as it arrives.

import asyncio
import structlog
from mcp.server.fastmcp import FastMCP

log = structlog.get_logger(__name__)


def register(mcp: FastMCP) -> None:
    """Attach stream_chunks tool to the MCP server."""

    @mcp.tool()
    async def stream_chunks(
            message: str,
            count: int = 5,
    ):
        """
        Stream `count` numbered chunks of `message` to the client.

        Args:
            message : text to repeat in each chunk
            count   : how many chunks to send (default 5)
        """
        log.info("tool.stream_chunks.start",
                 message=message, count=count)

        # Yield each chunk as a plain string.
        # The MCP SDK transmits each yield as a separate SSE event.
        for i in range(1, count + 1):
            chunk = f"[chunk {i}/{count}] {message}"
            log.debug("tool.stream_chunks.yield", chunk=chunk)

            yield chunk  # ← SSE chunk to client

            await asyncio.sleep(0.3)  # simulate processing time

        log.info("tool.stream_chunks.done", count=count)
```

---

## Step 9 — server/src/tools/batch_processor.py  (Tool 2)

```python
# src/tools/batch_processor.py
# TOOL 2: process_batch
#
# Bidirectional interaction:
#   1. Server reads a batch of rows from DB.
#   2. Server streams progress events to client.
#   3. Server ELICITS (asks) the client:
#        "Continue? New batch size?"
#   4. Client replies with:
#        action = "continue" | "stop"
#        new_batch_size = int
#   5. Server loops or halts based on reply.

import asyncio
import structlog
from mcp.server.fastmcp import FastMCP, Context

from db.adapter import PostgresRecordAdapter

log = structlog.get_logger(__name__)


def register(mcp: FastMCP, db: PostgresRecordAdapter) -> None:
    """Attach process_batch tool to the MCP server."""

    @mcp.tool()
    async def process_batch(
            ctx: Context,  # ← MCP context (needed for elicit)
            batch_size: int = 10,
    ):
        """
        Process all DB records in batches.
        After each batch, ask the client whether to continue
        and what the next batch size should be.

        Args:
            batch_size : initial number of rows per batch
        """
        total = await db.count()  # total rows in DB
        offset = 0  # current position
        current_batch = batch_size  # may change per reply

        log.info("tool.process_batch.start",
                 total=total, batch_size=batch_size)

        while offset < total:

            # ── 1. Fetch one batch from DB ────────────────────
            rows = await db.fetch_batch(
                offset=offset,
                limit=current_batch,
            )
            offset += len(rows)

            # ── 2. Stream progress to client ──────────────────
            for row in rows:
                progress_msg = (
                    f"Processed row {row['id']}: "
                    f"{row['name']} = {row['value']}"
                )
                log.debug("tool.process_batch.row", **row)
                yield progress_msg  # ← stream to client

            # ── 3. Elicit decision from client ────────────────
            # ctx.elicit() sends a structured request to the client.
            # The client must reply with matching JSON fields.
            elicit_msg = (
                f"Processed {offset}/{total} rows. "
                f"Continue? If yes, set new batch size."
            )

            reply = await ctx.elicit(
                message=elicit_msg,
                schema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["continue", "stop"],
                            "description": "continue or stop processing",
                        },
                        "new_batch_size": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "description": "rows per next batch",
                        },
                    },
                    "required": ["action", "new_batch_size"],
                },
            )

            log.info("tool.process_batch.elicit_reply", reply=reply)

            # ── 4. Act on client reply ────────────────────────
            if reply.get("action") == "stop":
                yield f"Stopped by client at offset {offset}."
                log.info("tool.process_batch.stopped",
                         offset=offset)
                return  # end the tool call

            # Update batch size for next iteration
            current_batch = reply.get("new_batch_size", current_batch)

            await asyncio.sleep(0.1)  # simulate work

        # ── 5. All rows done ──────────────────────────────────
        yield f"All {total} rows processed."
        log.info("tool.process_batch.complete", total=total)
```

---

## Step 10 — server/src/mcp_server.py

```python
# src/mcp_server.py
# Assembles the MCP server.
# Registers both tools.
# Returns the server instance for FastAPI to mount.

import os
import structlog
from mcp.server.fastmcp import FastMCP

from db.adapter import PostgresRecordAdapter
from tools import chunk_streamer, batch_processor

log = structlog.get_logger(__name__)

# ── Create MCP server instance ────────────────────────────────
mcp = FastMCP(
    name="mcp-intermediate",
    # stateless_http=True uses Streamable HTTP transport
)

# ── Database adapter (Ports & Adapters pattern) ───────────────
db = PostgresRecordAdapter(dsn=os.environ["DATABASE_URL"])


async def startup() -> None:
    """Called by FastAPI on startup."""
    await db.connect()
    log.info("mcp_server.db_ready")


# ── Register tools ────────────────────────────────────────────
chunk_streamer.register(mcp)
batch_processor.register(mcp, db)

log.info("mcp_server.tools_registered",
         tools=["stream_chunks", "process_batch"])
```

---

## Step 11 — server/src/main.py

```python
# src/main.py
# FastAPI application.
# Mounts MCP server at /mcp.
# Configures structured logging.

import structlog
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from mcp_server import mcp, startup

# ── Structured logging setup ──────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup logic before serving requests."""
    await startup()
    yield


# ── FastAPI app ───────────────────────────────────────────────
app = FastAPI(
    title="MCP Intermediate Server",
    lifespan=lifespan,
)

# Mount the MCP server under /mcp
# All MCP requests (POST /mcp, GET /mcp/sse) are handled here.
app.mount("/mcp", mcp.streamable_http_app())

log.info("app.ready", mount="/mcp")
```

---

## Step 12 — client/pyproject.toml

```toml
# client/pyproject.toml

[project]
name = "mcp-client-intermediate"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "mcp[cli]>=1.6",
    "structlog>=24.1",
    "httpx>=0.27",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Step 13 — client/Dockerfile

```dockerfile
# client/Dockerfile

FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
COPY src/ ./src/

RUN uv pip install --system -e .

CMD ["python", "src/client.py"]
```

---

## Step 14 — client/src/client.py

```python
# src/client.py
# MCP client.
#
# 1. Connects to server via Streamable HTTP.
# 2. Calls stream_chunks  → prints each chunk as it arrives.
# 3. Calls process_batch  → prints progress, answers elicit.

import asyncio
import os
import structlog

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

log = structlog.get_logger(__name__)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

SERVER_URL = os.environ.get(
    "MCP_SERVER_URL", "http://localhost/mcp"
)


async def handle_elicit(message: str, schema: dict) -> dict:
    """
    Called when the server sends an elicitation request.
    In production this would prompt a human or an LLM.
    Here we simulate a decision:
      - First call  → continue with batch_size=5
      - Second call → continue with batch_size=20
      - Third call  → stop
    """
    handle_elicit._call_count = getattr(
        handle_elicit, "_call_count", 0
    ) + 1
    n = handle_elicit._call_count

    log.info("client.elicit_received",
             message=message, call_number=n)

    if n == 1:
        reply = {"action": "continue", "new_batch_size": 5}
    elif n == 2:
        reply = {"action": "continue", "new_batch_size": 20}
    else:
        reply = {"action": "stop", "new_batch_size": 10}

    log.info("client.elicit_reply", reply=reply)
    return reply


async def demo_stream_chunks(session: ClientSession) -> None:
    """Call Tool 1: stream chunks and print each one."""
    log.info("client.tool1.start")

    # call_tool returns an async generator when the tool yields
    async for chunk in session.call_tool(
            "stream_chunks",
            arguments={
                "message": "Hello from intermediate demo",
                "count": 4,
            },
    ):
        # Each iteration = one chunk yielded by the server
        print(f"  CHUNK  → {chunk}")

    log.info("client.tool1.done")


async def demo_process_batch(session: ClientSession) -> None:
    """Call Tool 2: bidirectional batch processing."""
    log.info("client.tool2.start")

    async for event in session.call_tool(
            "process_batch",
            arguments={"batch_size": 10},
            # Pass the elicitation handler so the SDK can
            # route elicit requests back to our function
            elicit_handler=handle_elicit,
    ):
        # event is either a progress string or a final result
        print(f"  EVENT  → {event}")

    log.info("client.tool2.done")


async def main() -> None:
    log.info("client.start", server=SERVER_URL)

    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            # Negotiate capabilities
            await session.initialize()
            log.info("client.session_ready")

            # ── Tool 1: chunk streaming ───────────────────────
            print("\n=== Tool 1: stream_chunks ===")
            await demo_stream_chunks(session)

            # ── Tool 2: bidirectional processing ─────────────
            print("\n=== Tool 2: process_batch (bidirectional) ===")
            await demo_process_batch(session)

    log.info("client.done")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Step 15 — Run and Verify

```bash
# 1. Build and start all containers
docker compose up --build

# 2. Watch client output (separate terminal)
docker compose logs -f client

# 3. Expected output ─────────────────────────────────────────

=== Tool 1: stream_chunks ===
  CHUNK  → [chunk 1/4] Hello from intermediate demo
  CHUNK  → [chunk 2/4] Hello from intermediate demo
  CHUNK  → [chunk 3/4] Hello from intermediate demo
  CHUNK  → [chunk 4/4] Hello from intermediate demo

=== Tool 2: process_batch (bidirectional) ===
  EVENT  → Processed row 1: record_001 = 7
  EVENT  → Processed row 2: record_002 = 14
  ...
  EVENT  → Processed row 10: record_010 = 0
  # [elicit sent to client → reply: continue, size=5]
  EVENT  → Processed row 11: record_011 = 7
  ...
  EVENT  → Processed row 15: record_015 = 35
  # [elicit sent to client → reply: continue, size=20]
  EVENT  → Processed row 16: record_016 = 42
  ...
  EVENT  → Processed row 35: record_035 = 45
  # [elicit sent to client → reply: stop]
  EVENT  → Stopped by client at offset 35.
```

---

## §06 Flow Diagram — Bidirectional Interaction

```
CLIENT                     NGINX                    SERVER (Tool 2)
  │                          │                           │
  │── POST /mcp/call ────────►│── forward ───────────────►│
  │                          │                           │ fetch batch 1 (10 rows)
  │◄── SSE: row 1..10 ───────◄│◄── yield row events ─────│
  │                          │                           │
  │                          │             elicit() ─────►│ (server asks client)
  │◄── SSE: elicit request ──◄│◄──────────────────────────│
  │                          │                           │
  │── elicit reply ──────────►│── forward ───────────────►│
  │   {action:continue,       │                           │ update batch_size=5
  │    new_batch_size:5}      │                           │ fetch batch 2 (5 rows)
  │                          │                           │
  │◄── SSE: row 11..15 ──────◄│◄── yield row events ─────│
  │                          │                           │
  │                          │             elicit() ─────►│ (server asks again)
  │◄── SSE: elicit request ──◄│◄──────────────────────────│
  │                          │                           │
  │── elicit reply ──────────►│── forward ───────────────►│
  │   {action:stop, …}        │                           │ yield "Stopped."
  │                          │                           │ return
  │◄── SSE: "Stopped." ──────◄│◄──────────────────────────│
  │◄── SSE: [stream end] ────◄│◄──────────────────────────│
```

---

## Edge Cases

| # | Scenario                                     | Behavior                                                                          | Why                                                                  |
|---|----------------------------------------------|-----------------------------------------------------------------------------------|----------------------------------------------------------------------|
| 1 | Client sends `action="stop"` on first elicit | Tool yields "Stopped." and returns immediately                                    | `return` exits the async generator                                   |
| 2 | DB returns fewer rows than `batch_size`      | Loop ends naturally; no elicit after last batch                                   | `offset >= total` exits the while loop                               |
| 3 | Client sends `new_batch_size=0`              | Schema rejects it (`minimum: 1`); MCP returns validation error                    | JSON Schema enforced by MCP SDK                                      |
| 4 | Network drops mid-stream                     | Client receives `asyncio.CancelledError`; server's generator is garbage-collected | No explicit cleanup needed; generator finalizer runs                 |
| 5 | Client never replies to elicit (timeout)     | Server blocks on `await ctx.elicit()` until timeout; raises `TimeoutError`        | Add `asyncio.wait_for(..., timeout=30)` around elicit for production |

---

## Key Limitations

1. **Single HTTP connection per tool call.** Elicitation round-trips share the
   same long-lived SSE connection. If the proxy closes idle connections, the
   elicit reply never arrives. Set `proxy_read_timeout` high enough (≥ 300s).

2. **No partial failure recovery.** If the server crashes mid-batch, the
   client has no way to resume from the last committed offset. Add a
   `checkpoint` field to the elicit reply and persist it in Redis or
   PostgreSQL for production use.

3. **Sequential batches only.** The current design processes one batch at a
   time. For parallel batch processing, you need multiple concurrent tool
   calls, each with its own session.

---

## Scenario Table

```
┌──────────────────────┬────────────────────────────┬──────────────────────────┐
│ Scenario             │ Behavior                   │ Why                      │
├──────────────────────┼────────────────────────────┼──────────────────────────┤
│ action = "stop"      │ Server yields stop msg,    │ Explicit return in async  │
│                      │ closes stream              │ generator                │
├──────────────────────┼────────────────────────────┼──────────────────────────┤
│ Last batch is        │ No elicit after last batch │ while offset < total      │
│ partial              │                            │ exits naturally          │
├──────────────────────┼────────────────────────────┼──────────────────────────┤
│ new_batch_size = 0   │ MCP SDK returns schema     │ JSON Schema minimum:1    │
│                      │ validation error           │                          │
├──────────────────────┼────────────────────────────┼──────────────────────────┤
│ Proxy closes idle    │ elicit() blocks forever    │ proxy_read_timeout not   │
│ connection           │ then TimeoutError          │ set high enough          │
└──────────────────────┴────────────────────────────┴──────────────────────────┘
```

---

## Summary

```
KEY FILES IN THIS CHUNK
────────────────────────────────────────────
chunk_streamer.py   Tool 1 — server yields chunks
batch_processor.py  Tool 2 — bidirectional elicitation
client.py           handle_elicit() answers server
nginx.conf          proxy_buffering off (required for SSE)
db/port.py          Port interface (Clean Architecture)
db/adapter.py       PostgreSQL adapter
```
```
KEY TERMS INTRODUCED
────────────────────────────────────────────
ctx.elicit()        Server sends structured question to client
elicit_handler      Client function that returns JSON reply
proxy_buffering off Nginx directive that passes SSE immediately
Port                Abstract interface for DB calls
Adapter             Concrete implementation of the Port
```

```
┌──────────────────────┬──────────────────────────────────────────────┐
│ Concept              │ One-line reminder                            │
├──────────────────────┼──────────────────────────────────────────────┤
│ Tool 1 (stream)      │ Server yields chunks; client prints on       │
│                      │ arrival                                      │
├──────────────────────┼──────────────────────────────────────────────┤
│ Tool 2 (bidirectional│ Server yields progress, elicits reply,       │
│                      │ continues or stops                           │
├──────────────────────┼──────────────────────────────────────────────┤
│ ctx.elicit()         │ Sends structured schema to client and blocks │
│                      │ until reply arrives                          │
├──────────────────────┼──────────────────────────────────────────────┤
│ elicit_handler       │ Client-side function that returns JSON reply │
├──────────────────────┼──────────────────────────────────────────────┤
│ proxy_buffering off  │ Required in nginx for SSE chunks to          │
│                      │ pass through immediately                     │
├──────────────────────┼──────────────────────────────────────────────┤
│ Ports & Adapters     │ RecordPort = interface; PostgresAdapter =    │
│                      │ concrete DB implementation                   │
└──────────────────────┴──────────────────────────────────────────────┘
```


NEXT: Type "chunk 6" for §07 — Advanced Concepts
(Security, Scaling, Reliability, Optimization, Trade-offs)
