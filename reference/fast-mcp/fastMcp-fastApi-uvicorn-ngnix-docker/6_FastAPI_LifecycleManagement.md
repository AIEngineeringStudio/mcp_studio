# Increment 6 — FastAPI Lifecycle Management

## Goal

Make FastAPI the application’s **composition root** and lifecycle owner:

```
Uvicorn process
    │
    ▼
FastAPI lifespan
├── Start SQLite repository
├── Mark application ready
├── Start FastMCP lifespan
│
├── /health/live
├── /health/ready
└── /mcp
│
└── Shutdown in reverse order
    ├── Stop FastMCP
    └── Close SQLite repository
```

FastAPI recommends its `lifespan` context manager for startup and shutdown work. Code before `yield` runs before requests are served; code after `yield` runs during shutdown. [FastAPI](https://fastapi.tiangolo.com/advanced/events/)

---

## 1. Add FastAPI and testing support

```bash
uv add fastapi httpx
```

`httpx` is included explicitly because FastAPI’s `TestClient` depends on an HTTP client implementation.

Updated structure:

```
mcp-first-principles/
├── app.py
├── server.py
├── service.py
├── repository.py
├── models.py
├── errors.py
├── test_app.py
├── test_service.py
├── test_http_client.py
├── data/
├── pyproject.toml
└── uv.lock
```

---

# 2. Remove Lazy Initialization

The previous service performed:

```python
await self._ensure_initialized()
```

That was a temporary design. It meant the first real request could fail because database startup had never been tested.

We now want:

```
Process startup
    │
    ├── Open database
    ├── Create schema
    └── Become ready

Only then:
    └── Accept application traffic
```

Starlette does not begin serving incoming requests until the application lifespan startup has completed. [Starlette](https://www.starlette.io/lifespan/)

---

# 3. Update `repository.py`

We will keep one SQLite connection open for the lifetime of each application process.

```python
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, cast

import aiosqlite

from models import CalculationRecord, Operation


class CalculationRepository(Protocol):
    """Persistence operations required by the application service."""

    async def save(
        self,
        operation: Operation,
        a: int,
        b: int,
        result: int,
    ) -> CalculationRecord:
        """Persist and return a calculation."""

    async def list_recent(
        self,
        limit: int,
    ) -> list[CalculationRecord]:
        """Return recent calculations, newest first."""


class SQLiteCalculationRepository:
    """Lifecycle-managed SQLite repository."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._connection: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    @property
    def started(self) -> bool:
        """Return whether the repository currently has a connection."""
        return self._connection is not None

    async def start(self) -> None:
        """Open the database and prepare its schema."""

        if self._connection is not None:
            return

        self._database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        connection = await aiosqlite.connect(
            self._database_path
        )

        connection.row_factory = aiosqlite.Row

        try:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS calculations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    operand_a INTEGER NOT NULL,
                    operand_b INTEGER NOT NULL,
                    result INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            await connection.commit()
        except BaseException:
            await connection.close()
            raise

        self._connection = connection

    async def close(self) -> None:
        """Complete queued work and close the database connection."""

        connection = self._connection
        self._connection = None

        if connection is not None:
            await connection.close()

    async def ping(self) -> None:
        """Verify that the database connection can execute a query."""

        connection = self._require_connection()

        cursor = await connection.execute("SELECT 1")

        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()

        if row is None or row[0] != 1:
            raise RuntimeError(
                "SQLite readiness query returned an invalid result."
            )

    async def save(
        self,
        operation: Operation,
        a: int,
        b: int,
        result: int,
    ) -> CalculationRecord:
        connection = self._require_connection()
        created_at = datetime.now(timezone.utc)

        # Keep execute + commit as one logical write transaction.
        async with self._write_lock:
            try:
                cursor = await connection.execute(
                    """
                    INSERT INTO calculations (
                        operation,
                        operand_a,
                        operand_b,
                        result,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        operation,
                        a,
                        b,
                        result,
                        created_at.isoformat(),
                    ),
                )

                try:
                    record_id = cursor.lastrowid
                finally:
                    await cursor.close()

                await connection.commit()
            except BaseException:
                await connection.rollback()
                raise

        if record_id is None:
            raise RuntimeError(
                "SQLite did not return a calculation identifier."
            )

        return CalculationRecord(
            id=record_id,
            operation=operation,
            a=a,
            b=b,
            result=result,
            created_at=created_at,
        )

    async def list_recent(
        self,
        limit: int,
    ) -> list[CalculationRecord]:
        connection = self._require_connection()

        cursor = await connection.execute(
            """
            SELECT
                id,
                operation,
                operand_a,
                operand_b,
                result,
                created_at
            FROM calculations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

        try:
            rows = await cursor.fetchall()
        finally:
            await cursor.close()

        return [
            CalculationRecord(
                id=row["id"],
                operation=cast(Operation, row["operation"]),
                a=row["operand_a"],
                b=row["operand_b"],
                result=row["result"],
                created_at=datetime.fromisoformat(
                    row["created_at"]
                ),
            )
            for row in rows
        ]

    def _require_connection(self) -> aiosqlite.Connection:
        connection = self._connection

        if connection is None:
            raise RuntimeError(
                "Calculation repository has not been started."
            )

        return connection


class InMemoryCalculationRepository:
    """Repository implementation for isolated service tests."""

    def __init__(self) -> None:
        self._records: list[CalculationRecord] = []
        self._next_id = 1

    async def save(
        self,
        operation: Operation,
        a: int,
        b: int,
        result: int,
    ) -> CalculationRecord:
        record = CalculationRecord(
            id=self._next_id,
            operation=operation,
            a=a,
            b=b,
            result=result,
            created_at=datetime.now(timezone.utc),
        )

        self._next_id += 1
        self._records.append(record)

        return record

    async def list_recent(
        self,
        limit: int,
    ) -> list[CalculationRecord]:
        return list(reversed(self._records[-limit:]))
```

`aiosqlite.Connection.close()` completes queued operations and closes the connection. An explicitly managed connection must be closed so its helper thread can terminate correctly. [Aiosqlite](https://aiosqlite.omnilib.dev/en/stable/changelog.html?utm_source=chatgpt.com)

---

## Why use a write lock?

A database write is not just one statement:

```
Execute INSERT
    │
    ▼
Read inserted ID
    │
    ▼
Commit transaction
```

We do not want two coroutines interleaving those transaction boundaries on the same connection.

```python
async with self._write_lock:
```

This provides **in-process write serialization**.

It does not provide distributed locking across several worker processes. Each worker would have its own Python lock and SQLite connection.

---

# 4. Simplify `service.py`

Remove:

- `_initialization_lock`
- `_initialized`
- `_ensure_initialized()`
- Calls to `_ensure_initialized()`

The resulting service becomes:

```python
from __future__ import annotations

from errors import (
    InvalidHistoryLimitError,
    InvalidOperandError,
    OperandOutOfRangeError,
)
from models import CalculationRecord, Operation
from repository import CalculationRepository


class ArithmeticService:
    """Application service for arithmetic use cases."""

    MAXIMUM_ABSOLUTE_OPERAND = 1_000_000

    def __init__(
        self,
        repository: CalculationRepository,
    ) -> None:
        self._repository = repository

    async def add(
        self,
        a: int,
        b: int,
    ) -> CalculationRecord:
        return await self.calculate("add", a, b)

    async def multiply(
        self,
        a: int,
        b: int,
    ) -> CalculationRecord:
        return await self.calculate("multiply", a, b)

    async def calculate(
        self,
        operation: Operation,
        a: int,
        b: int,
    ) -> CalculationRecord:
        self._validate_operand("a", a)
        self._validate_operand("b", b)

        result = self._compute(operation, a, b)

        return await self._repository.save(
            operation=operation,
            a=a,
            b=b,
            result=result,
        )

    async def recent_calculations(
        self,
        limit: int,
    ) -> list[CalculationRecord]:
        if not 1 <= limit <= 100:
            raise InvalidHistoryLimitError(limit)

        return await self._repository.list_recent(limit)

    def _validate_operand(
        self,
        name: str,
        value: int,
    ) -> None:
        if type(value) is not int:
            raise InvalidOperandError(name)

        if abs(value) > self.MAXIMUM_ABSOLUTE_OPERAND:
            raise OperandOutOfRangeError(
                name=name,
                value=value,
                maximum_absolute_value=(
                    self.MAXIMUM_ABSOLUTE_OPERAND
                ),
            )

    @staticmethod
    def _compute(
        operation: Operation,
        a: int,
        b: int,
    ) -> int:
        if operation == "add":
            return a + b

        return a * b
```

The service now assumes its dependencies are ready.

Professional wording:

> “Infrastructure readiness is a precondition established by the application lifecycle, not a responsibility of individual use cases.”

---

# 5. Turn `server.py` Into an MCP Factory

The previous module created a global repository and service during import. That prevented FastAPI from owning dependency construction.

Replace it with:

```python
from __future__ import annotations

import json

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError

from errors import ArithmeticServiceError
from service import ArithmeticService


def create_mcp(
    service: ArithmeticService,
) -> FastMCP:
    """Create an MCP server bound to an application service."""

    mcp = FastMCP(
        name="First Principles MCP",
        instructions=(
            "Use arithmetic tools to perform calculations. "
            "Use calculation-history resources when historical "
            "context is required."
        ),
        mask_error_details=True,
    )

    @mcp.tool
    async def add(
        a: int,
        b: int,
        ctx: Context,
    ) -> dict:
        """Add two integers and persist the calculation."""

        await ctx.info(
            f"Executing addition request_id={ctx.request_id}"
        )

        try:
            record = await service.add(a, b)
        except ArithmeticServiceError as exc:
            raise ToolError(str(exc)) from exc

        return record.model_dump(mode="json")

    @mcp.tool
    async def multiply(
        a: int,
        b: int,
        ctx: Context,
    ) -> dict:
        """Multiply two integers and persist the calculation."""

        await ctx.info(
            f"Executing multiplication request_id="
            f"{ctx.request_id}"
        )

        try:
            record = await service.multiply(a, b)
        except ArithmeticServiceError as exc:
            raise ToolError(str(exc)) from exc

        return record.model_dump(mode="json")

    @mcp.resource(
        uri="history://calculations/recent/{limit}",
        name="RecentCalculations",
        title="Recent Arithmetic Calculations",
        description=(
            "Returns recently persisted arithmetic calculations."
        ),
        mime_type="application/json",
        annotations={
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )
    async def recent_calculations(
        limit: int,
        ctx: Context,
    ) -> str:
        """Return recent calculations in newest-first order."""

        await ctx.info(
            f"Reading calculation history request_id="
            f"{ctx.request_id}"
        )

        try:
            records = await service.recent_calculations(limit)
        except ArithmeticServiceError as exc:
            raise ResourceError(str(exc)) from exc

        return json.dumps(
            [
                record.model_dump(mode="json")
                for record in records
            ],
            indent=2,
        )

    @mcp.prompt(
        name="explain_arithmetic",
        title="Explain an Arithmetic Calculation",
        description=(
            "Create instructions for explaining a calculation."
        ),
    )
    def explain_arithmetic(
        operation: str,
        a: int,
        b: int,
        audience: str = "beginner",
    ) -> str:
        """Create a structured arithmetic explanation request."""

        return (
            f"Explain how to {operation} {a} and {b} "
            f"to a {audience} audience.\n\n"
            "Show each step, explain the reasoning, state the "
            "final answer, and provide one similar practice problem."
        )

    return mcp
```

The service is injected when the MCP server is constructed:

```
SQLite repository
       │
       ▼
Arithmetic service
       │
       ▼
create_mcp(service)
```

This is **constructor-time dependency injection** through an application factory.

---

# 6. Create the FastAPI Composition Root

Replace `app.py` with:

```python
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastmcp.utilities.lifespan import combine_lifespans

from repository import SQLiteCalculationRepository
from server import create_mcp
from service import ArithmeticService


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent


def create_application(
    database_path: Path | None = None,
) -> FastAPI:
    """Construct and wire the complete ASGI application."""

    resolved_database_path = database_path or Path(
        os.getenv(
            "CALC_DB_PATH",
            str(PROJECT_ROOT / "data" / "calculations.db"),
        )
    )

    # ------------------------------------------------------------------
    # Construct application dependencies
    # ------------------------------------------------------------------

    repository = SQLiteCalculationRepository(
        resolved_database_path
    )

    service = ArithmeticService(repository)
    mcp = create_mcp(service)

    # path="/" because the complete child application is mounted at /mcp.
    mcp_app = mcp.http_app(
        path="/",
        stateless_http=True,
        host_origin_protection=True,
        allowed_hosts=[
            "127.0.0.1",
            "localhost",
            "testserver",
        ],
        allowed_origins=[],
    )

    # ------------------------------------------------------------------
    # Define application lifecycle
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def application_lifespan(
        application: FastAPI,
    ):
        application.state.ready = False

        logger.info(
            "Starting application database=%s",
            resolved_database_path,
        )

        # Startup barrier:
        # If this fails, the application does not become ready.
        await repository.start()

        application.state.ready = True
        logger.info("Application startup completed")

        try:
            yield
        finally:
            # Stop advertising readiness before releasing dependencies.
            application.state.ready = False

            logger.info("Application shutdown started")
            await repository.close()
            logger.info("Application shutdown completed")

    combined_lifespan = combine_lifespans(
        application_lifespan,
        mcp_app.lifespan,
    )

    application = FastAPI(
        title="First Principles MCP Service",
        version="0.1.0",
        lifespan=combined_lifespan,
    )

    # Exposed for diagnostics and controlled tests.
    application.state.ready = False
    application.state.repository = repository
    application.state.service = service

    # ------------------------------------------------------------------
    # Operational endpoints
    # ------------------------------------------------------------------

    @application.get(
        "/health/live",
        include_in_schema=False,
    )
    async def liveness() -> dict[str, str]:
        return {
            "status": "alive",
        }

    @application.get(
        "/health/ready",
        include_in_schema=False,
    )
    async def readiness(
        request: Request,
    ) -> JSONResponse:
        if not request.app.state.ready:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "not-ready",
                    "database": "not-started",
                },
            )

        try:
            await repository.ping()
        except Exception:
            logger.exception("Database readiness check failed")

            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "not-ready",
                    "database": "unavailable",
                },
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "database": "available",
            },
        )

    # ------------------------------------------------------------------
    # MCP subapplication
    # ------------------------------------------------------------------

    application.mount("/mcp", mcp_app)

    return application


app = create_application()
```

---

# 7. Why Combine Two Lifespans?

There are now two lifecycle owners:

```
Application lifespan
├── SQLite connection
└── readiness state

FastMCP lifespan
└── MCP transport/session infrastructure
```

Mounted subapplications do not automatically receive their own lifespan startup. FastMCP therefore requires the MCP application lifespan to be passed to or combined with the parent FastAPI lifespan. [FastMCP](https://gofastmcp.com/integrations/fastapi)

We use:

```python
combine_lifespans(
    application_lifespan,
    mcp_app.lifespan,
)
```

FastMCP enters combined lifespans in argument order and exits them in reverse, last-in-first-out order. [FastMCP](https://gofastmcp.com/python-sdk/fastmcp-utilities-lifespan)

Result:

```
Startup
1. Start repository
2. Start FastMCP

Shutdown
1. Stop FastMCP
2. Close repository
```

That shutdown order matters. MCP request handling stops before its required database is closed.

Professional wording:

> “Dependency acquisition follows declaration order, while teardown follows LIFO ordering.”

---

# 8. Why `path="/"`?

The parent mounts the MCP child here:

```python
application.mount("/mcp", mcp_app)
```

Therefore the child application should expose MCP at its own root:

```python
mcp.http_app(path="/")
```

Conceptual route composition:

```
Parent mount path:  /mcp
Child route path:   /
Final route:        /mcp
```

Using both:

```python
mcp.http_app(path="/mcp")
application.mount("/mcp", mcp_app)
```

could produce an unintended nested route:

```
/mcp/mcp
```

FastMCP’s official FastAPI mounting pattern uses `path="/"` when the child application is mounted at `/mcp`. [FastMCP](https://gofastmcp.com/integrations/fastapi)

---

# 9. Liveness vs Readiness

## Liveness

```http
GET /health/live
```

Answers:

> “Is this application process capable of answering requests?”

It deliberately does not query SQLite.

```json
{
  "status": "alive"
}
```

## Readiness

```http
GET /health/ready
```

Answers:

> “Should new application traffic be sent here?”

It checks:

- Startup completed
- Repository is marked ready
- SQLite can execute a lightweight query

```json
{
  "status": "ready",
  "database": "available"
}
```

A liveness failure is generally interpreted as a reason to restart a process or container. A readiness failure should stop new traffic without necessarily restarting it. Backing-service checks therefore usually belong in readiness, not liveness. [Kubernetes](https://v1-35.docs.kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/?utm_source=chatgpt.com)

The hidden operational risk is putting every external dependency into liveness:

```
Database has temporary outage
    │
    ▼
Every application instance fails liveness
    │
    ▼
Every application instance restarts
    │
    ▼
Outage becomes worse
```

---

# 10. Startup Failure Is Fail-Fast

Suppose the database directory cannot be created:

```
Application startup
    │
    ▼
repository.start()
    │
    ▼
PermissionError
```

The error is not converted into:

```
Application running but every tool call fails
```

Instead, startup itself fails.

```
Uvicorn starts process
    │
    ▼
FastAPI lifespan fails
    │
    ▼
Application does not become ready
```

Professional wording:

> “Required infrastructure is validated behind a startup barrier, allowing the process to fail fast rather than accept traffic in a degraded unknown state.”

---

# 11. Run the Application

```bash
uv run uvicorn app:app \
  --host 127.0.0.1 \
  --port 8000
```

Expected startup sequence:

```
Starting application database=...
Application startup completed
Uvicorn running on http://127.0.0.1:8000
```

Check liveness:

```bash
curl -i http://127.0.0.1:8000/health/live
```

Expected:

```http
HTTP/1.1 200 OK
content-type: application/json

{"status":"alive"}
```

Check readiness:

```bash
curl -i http://127.0.0.1:8000/health/ready
```

Expected:

```http
HTTP/1.1 200 OK
content-type: application/json

{"status":"ready","database":"available"}
```

The existing MCP client should continue using:

```python
MCP_URL = "http://127.0.0.1:8000/mcp"
```

---

# 12. Test the Lifespan

Create `test_app.py`:

```python
from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app import create_application


class ApplicationLifecycleTests(unittest.TestCase):
    def test_lifespan_and_health_endpoints(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database_path = (
                Path(temporary_directory) / "test.db"
            )

            application = create_application(database_path)
            repository = application.state.repository

            # Lifespan has not started.
            self.assertFalse(repository.started)
            self.assertFalse(application.state.ready)

            with TestClient(application) as client:
                # Entering TestClient starts the application lifespan.
                self.assertTrue(repository.started)
                self.assertTrue(application.state.ready)

                live_response = client.get("/health/live")

                self.assertEqual(
                    live_response.status_code,
                    200,
                )
                self.assertEqual(
                    live_response.json(),
                    {
                        "status": "alive",
                    },
                )

                ready_response = client.get("/health/ready")

                self.assertEqual(
                    ready_response.status_code,
                    200,
                )
                self.assertEqual(
                    ready_response.json(),
                    {
                        "status": "ready",
                        "database": "available",
                    },
                )

            # Exiting TestClient runs lifespan teardown.
            self.assertFalse(repository.started)
            self.assertFalse(application.state.ready)


if __name__ == "__main__":
    unittest.main()
```

Run:

```bash
uv run python -m unittest -v test_app.py
```

FastAPI’s `TestClient` must be used as a context manager when the test needs startup and shutdown lifespan behavior. [FastAPI](https://fastapi.tiangolo.com/advanced/testing-events/)

---

# 13. Coding Thought Process

## Step 1: Identify process-scoped dependencies

Ask:

> “Which objects should exist once per application process rather than once per request?”

For this application:

```
SQLite connection
Arithmetic service
MCP registry
MCP transport infrastructure
```

---

## Step 2: Construct them in one place

```python
repository = SQLiteCalculationRepository(...)
service = ArithmeticService(repository)
mcp = create_mcp(service)
```

This is the **composition root**.

Do not scatter construction across:

- Tool handlers
- Resources
- Middleware
- Health endpoints
- Import-time globals

---

## Step 3: Define acquisition and release as a pair

```python
await repository.start()

try:
    yield
finally:
    await repository.close()
```

This structure makes cleanup run during normal shutdown and most exceptional exits.

---

## Step 4: Combine framework lifecycles explicitly

FastAPI and FastMCP both have startup requirements.

Do not silently discard either one:

```python
# Wrong: FastMCP lifecycle is lost
application = FastAPI(
    lifespan=application_lifespan
)
application.mount("/mcp", mcp_app)
```

Use:

```python
combined_lifespan = combine_lifespans(
    application_lifespan,
    mcp_app.lifespan,
)
```

---

## Step 5: Separate process health from dependency health

```
Liveness
└── Is the process responsive?

Readiness
└── Can the process handle useful work?
```

---

## Step 6: Test entry and exit

A lifecycle test should verify all three states:

```
Before startup
    repository closed

During runtime
    repository open

After shutdown
    repository closed
```

Testing only the middle state misses resource leaks.

---

# 14. Professional Vocabulary

| Term | Meaning |
|---|---|
| **Lifespan** | ASGI startup and shutdown lifecycle |
| **Startup barrier** | Work that must complete before requests are accepted |
| **Teardown** | Resource cleanup during shutdown |
| **Composition root** | Central place where concrete dependencies are constructed |
| **Process-scoped dependency** | Resource shared for one application process |
| **Fail-fast** | Abort startup immediately when a mandatory dependency fails |
| **Graceful shutdown** | Stop accepting work and release resources cleanly |
| **LIFO teardown** | Last resource started is the first resource stopped |
| **Liveness** | Whether the process should remain running |
| **Readiness** | Whether the process should receive traffic |
| **Health probe** | Automated check of application operational state |
| **Subapplication** | ASGI application mounted inside another application |
| **Mount prefix** | Parent URL segment applied to a child application |
| **Application state** | Process-level state exposed through the ASGI application |
| **Resource acquisition** | Opening connections, clients, files, or pools |
| **Connection leak** | Resource that remains open after it should have closed |
| **Dependency graph** | Relationships between constructed application components |

Professional summary:

> “I introduced FastAPI as the application composition and lifecycle owner. Infrastructure is now acquired during ASGI startup and released during LIFO teardown. FastAPI and FastMCP lifespans are explicitly combined, while separate liveness and readiness endpoints expose process health and dependency availability.”

---

# Completion Check

```
[ ] FastAPI and httpx are direct dependencies
[ ] Service no longer performs lazy initialization
[ ] Repository has explicit start and close methods
[ ] Repository fails when used before startup
[ ] MCP server is created through a factory
[ ] FastAPI is the composition root
[ ] FastAPI and FastMCP lifespans are combined
[ ] MCP child path is "/" before mounting
[ ] Final MCP endpoint remains /mcp
[ ] Liveness does not query SQLite
[ ] Readiness verifies SQLite
[ ] Startup failure prevents readiness
[ ] Shutdown marks the app unready before closing SQLite
[ ] Tests verify before, during, and after lifespan states
```

## Next increment

The next increment focuses on **Uvicorn process behavior**:

```
Signals
├── SIGTERM
└── SIGINT

Uvicorn
├── Graceful shutdown
├── Request draining
├── Timeout configuration
├── Logging configuration
└── Worker processes

FastAPI lifespan
└── Deterministic cleanup per worker
```

We will also examine why SQLite constrains worker scaling before putting Nginx in front of the service.