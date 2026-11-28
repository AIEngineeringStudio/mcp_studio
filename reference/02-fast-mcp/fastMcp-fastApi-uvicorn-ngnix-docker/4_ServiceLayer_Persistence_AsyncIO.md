# Increment 4 — Service Layer, Persistence, and Async I/O

## Goal

Refactor this:

```
MCP handler
├── validates business rules
├── calculates result
├── accesses storage
├── formats response
└── handles protocol errors
```

into this:

```
MCP adapter
    │
    ▼
Application service
    │
    ▼
Repository interface
    │
    ▼
SQLite implementation
```

The responsibilities become:

| Layer          | Responsibility                               |
|----------------|----------------------------------------------|
| MCP adapter    | MCP schema, request context, protocol errors |
| Service        | Business rules and use-case orchestration    |
| Repository     | Persistence contract                         |
| SQLite adapter | SQL and database-specific details            |
| Domain model   | Structured application data                  |

This is the first step toward a maintainable production architecture.

---

## 1. Why We Need This Refactor

Our current tool resembles:

```python
@mcp.tool
def add(a: int, b: int) -> int:
    return a + b
```

That is acceptable for a trivial calculation.

Real tools tend to become this:

```python
@mcp.tool
async def create_order(...):
    validate_customer(...)
    calculate_tax(...)
    connect_to_database(...)
    insert_order(...)
    send_notification(...)
    format_response(...)
```

That creates a **fat handler**.

Problems:

- Business logic cannot be tested without MCP.
- Database code becomes coupled to the protocol.
- HTTP and MCP implementations duplicate logic.
- Infrastructure errors leak to clients.
- Replacing SQLite with PostgreSQL requires editing tool handlers.

The improved direction is:

```
MCP
FastAPI
CLI
Tests
   │
   └──────► same application service
```

---

# 2. Add Dependencies

```bash
uv add aiosqlite pydantic
```

We declare both directly because our application imports both directly.
Depending on FastMCP’s transitive Pydantic dependency would create an implicit
dependency.

`aiosqlite` provides awaitable SQLite connection and query
operations. [Aiosqlite](https://aiosqlite.omnilib.dev/en/stable/api.html?utm_source=chatgpt.com)

---

# 3. Project Structure

```
mcp-first-principles/
├── data/
│   └── calculations.db       generated at runtime
├── errors.py
├── models.py
├── repository.py
├── service.py
├── server.py
├── test_service.py
├── test_stdio_client.py
├── pyproject.toml
└── uv.lock
```

The dependency direction is important:

```
server.py
    │
    ▼
service.py
    │
    ▼
repository.py interface
    ▲
    │
SQLite repository implementation
```

The service knows about the repository **contract**, not MCP or SQLite
implementation details.

---

# 4. Create `models.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Operation = Literal["add", "multiply"]


class CalculationRecord(BaseModel):
    """A calculation persisted by the application."""

    model_config = ConfigDict(frozen=True)

    id: int
    operation: Operation
    a: int
    b: int
    result: int
    created_at: datetime
```

## Why use a model?

Avoid passing anonymous dictionaries throughout the application:

```python
{
    "id": 1,
    "operation": "add",
    "a": 20,
    "b": 22,
    "result": 42,
}
```

A model provides:

- A named domain concept
- Runtime validation
- Type-checker support
- Predictable serialization
- A stable return contract

Professional wording:

> “`CalculationRecord` is the application’s canonical representation of a
> persisted calculation.”

`frozen=True` makes instances immutable after creation.

---

# 5. Create `errors.py`

```python
class ArithmeticServiceError(Exception):
    """Base class for expected application-level errors."""


class InvalidOperandError(ArithmeticServiceError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Operand '{name}' must be an integer.")


class OperandOutOfRangeError(ArithmeticServiceError):
    def __init__(
            self,
            name: str,
            value: int,
            maximum_absolute_value: int,
    ) -> None:
        super().__init__(
            f"Operand '{name}' has value {value}. "
            f"Its absolute value must not exceed "
            f"{maximum_absolute_value}."
        )


class InvalidHistoryLimitError(ArithmeticServiceError):
    def __init__(self, limit: int) -> None:
        super().__init__(
            f"History limit must be between 1 and 100; received {limit}."
        )
```

These are **domain-facing errors**.

They do not mention:

- MCP
- HTTP
- JSON-RPC
- SQLite
- Status codes

That separation allows different adapters to translate the same application
error differently:

```
OperandOutOfRangeError
├── MCP adapter  → ToolError
├── HTTP adapter → HTTP 422
└── CLI adapter  → stderr message
```

---

# 6. Create `repository.py`

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, cast

import aiosqlite

from models import CalculationRecord, Operation


class CalculationRepository(Protocol):
    """Persistence contract required by the application service."""

    async def initialize(self) -> None:
        """Prepare the persistence mechanism."""

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
    """SQLite implementation of the calculation repository."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    async def initialize(self) -> None:
        self._database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        async with aiosqlite.connect(self._database_path) as database:
            await database.execute(
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
            await database.commit()

    async def save(
            self,
            operation: Operation,
            a: int,
            b: int,
            result: int,
    ) -> CalculationRecord:
        created_at = datetime.now(timezone.utc)

        async with aiosqlite.connect(self._database_path) as database:
            cursor = await database.execute(
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

            await database.commit()

            record_id = cursor.lastrowid
            await cursor.close()

        if record_id is None:
            raise RuntimeError(
                "SQLite did not return an identifier for the calculation."
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
        async with aiosqlite.connect(self._database_path) as database:
            database.row_factory = aiosqlite.Row

            cursor = await database.execute(
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

            rows = await cursor.fetchall()
            await cursor.close()

        return [
            CalculationRecord(
                id=row["id"],
                operation=cast(Operation, row["operation"]),
                a=row["operand_a"],
                b=row["operand_b"],
                result=row["result"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]


class InMemoryCalculationRepository:
    """Repository implementation used by isolated service tests."""

    def __init__(self) -> None:
        self._records: list[CalculationRecord] = []
        self._next_id = 1

    async def initialize(self) -> None:
        return None

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

## Why a `Protocol`?

```python
class CalculationRepository(Protocol):
```

This declares the behavior the service requires without forcing implementations
to inherit from a particular base class.

Both implementations satisfy the contract:

```
CalculationRepository
├── SQLiteCalculationRepository
└── InMemoryCalculationRepository
```

Professional wording:

> “The service depends on a persistence port defined through structural typing.”

This is an example of **dependency inversion**:

```
Bad:

Service ──► SQLite directly


Better:

Service ──► Repository contract
                ▲
                │
              SQLite
```

---

## Parameterized SQL

Notice this:

```python
VALUES(?, ?, ?, ?, ?)
```

with values supplied separately:

```python
(
    operation,
    a,
    b,
    result,
    created_at.isoformat(),
)
```

Do not construct SQL like this:

```python
sql = f"INSERT INTO calculations VALUES ('{operation}', {a}, {b})"
```

Parameterized queries keep data separate from SQL syntax and avoid injection
vulnerabilities caused by string-built
queries. [Python documentation](https://docs.python.org/3.12/library/sqlite3.html?utm_source=chatgpt.com)

---

# 7. Create `service.py`

```python
from __future__ import annotations

import asyncio

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
        self._initialization_lock = asyncio.Lock()
        self._initialized = False

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
        await self._ensure_initialized()
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
        await self._ensure_initialized()

        if not 1 <= limit <= 100:
            raise InvalidHistoryLimitError(limit)

        return await self._repository.list_recent(limit)

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        async with self._initialization_lock:
            if self._initialized:
                return

            await self._repository.initialize()
            self._initialized = True

    def _validate_operand(
            self,
            name: str,
            value: int,
    ) -> None:
        # bool is a subclass of int in Python, so use type(...) is int
        # when booleans should not be accepted as operands.
        if type(value) is not int:
            raise InvalidOperandError(name)

        if abs(value) > self.MAXIMUM_ABSOLUTE_OPERAND:
            raise OperandOutOfRangeError(
                name=name,
                value=value,
                maximum_absolute_value=self.MAXIMUM_ABSOLUTE_OPERAND,
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

## Why is calculation separated from persistence?

```python
result = self._compute(operation, a, b)
```

is synchronous because arithmetic does not wait for external I/O.

```python
return await self._repository.save(...)
```

is asynchronous because persistence involves an external resource.

```
CPU-only operation
    │
    └── ordinary def

I/O operation
    │
    └── async def + await
```

Do not make functions async merely to appear modern.

---

# 8. Async From First Principles

Calling an async function does not immediately execute it:

```python
coroutine = service.add(20, 22)
```

It creates a coroutine object.

Execution occurs when it is awaited:

```python
record = await service.add(20, 22)
```

Python’s event loop uses cooperative scheduling. When one task reaches an
`await` and waits for I/O, the loop can run other tasks. Async code therefore
improves I/O concurrency; it does not automatically provide CPU
parallelism. [Python documentation](https://docs.python.org/3/library/asyncio-task.html)

Conceptually:

```
Task A: database write
    │
    ├── send database operation
    ├── await result ─────────────┐
    │                             │
    │        event loop runs Task B
    │                             │
    └── resume when ready ◄───────┘
```

A blocking call behaves differently:

```
Task A performs blocking call
    │
    └── event-loop thread cannot process Task B
```

FastMCP supports async tools and resources. Its synchronous handlers are moved
to a thread pool, while native async handlers are preferable when using async
I/O libraries. [FastMCP](https://gofastmcp.com/servers/resources)

---

# 9. Temporary Lazy Initialization

The service currently contains:

```python
await self._ensure_initialized()
```

This is **lazy initialization**:

```
First request
├── create schema
└── execute request

Later requests
└── execute request
```

The lock prevents two concurrent first requests from initializing the repository
simultaneously.

```
Request A ──► acquires lock ──► initializes
Request B ──► waits for lock ──► sees initialized
```

This works for this increment, but it is not our final design.

Hidden weakness:

> The first real user request pays the initialization cost and can be the first
> place an initialization failure appears.

The production direction is:

```
Application startup
└── initialize infrastructure

Application requests
└── use ready infrastructure

Application shutdown
└── close infrastructure
```

The next increments replace lazy initialization with explicit lifespan
management.

---

# 10. Update `server.py`

```python
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ResourceError, ToolError

from errors import ArithmeticServiceError
from repository import SQLiteCalculationRepository
from service import ArithmeticService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent

database_path = Path(
    os.getenv(
        "CALC_DB_PATH",
        str(PROJECT_ROOT / "data" / "calculations.db"),
    )
)

repository = SQLiteCalculationRepository(database_path)
service = ArithmeticService(repository)

mcp = FastMCP(
    name="First Principles MCP",
    instructions=(
        "Use arithmetic tools to perform calculations. "
        "Read calculation-history resources when historical context "
        "is required."
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
        f"Executing multiplication request_id={ctx.request_id}"
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
    description="Returns recently persisted arithmetic calculations.",
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
        f"Reading calculation history request_id={ctx.request_id}"
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
    description="Create instructions for explaining a calculation.",
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
        "Show each step, explain the reasoning, state the final "
        "answer, and provide one similar practice problem."
    )


if __name__ == "__main__":
    logger.info(
        "Starting MCP server pid=%s database=%s",
        os.getpid(),
        database_path,
    )

    mcp.run(transport="stdio")
```

---

## The handler is now thin

The tool does four things:

```python
async def add(...):
    await ctx.info(...)  # request-level logging
    record = await service.add(a, b)  # delegate use case
    return record.model_dump(...)  # protocol representation
```

It does not know:

- Table names
- SQL statements
- Database connection mechanics
- Arithmetic validation rules
- How results are calculated

Professional wording:

> “The MCP component is a thin inbound adapter that delegates use-case execution
> to the application service.”

---

# 11. Request-Scoped Context

FastMCP injects `Context` automatically:

```python
async def add(
        a: int,
        b: int,
        ctx: Context,
)
```

The client sees only `a` and `b`. The injected dependency does not become part
of the callable MCP input schema. FastMCP context can provide request IDs,
logging, session information, transport information, and other request-scoped
behavior. [FastMCP](https://gofastmcp.com/servers/context)

This is **dependency injection**:

```
Client supplies:
├── a
└── b

FastMCP supplies:
└── ctx
```

Do not pass `Context` into the service:

```python
# Avoid this coupling
await service.add(a, b, ctx)
```

The service should not know that MCP exists.

---

# 12. Error Translation

The service raises:

```python
OperandOutOfRangeError
```

The MCP adapter translates it:

```python
except ArithmeticServiceError as exc:
raise ToolError(str(exc)) from exc
```

The error flow is:

```
Business-rule failure
        │
        ▼
ArithmeticServiceError
        │
        ▼
MCP adapter
        │
        ▼
ToolError
        │
        ▼
MCP error response
```

FastMCP converts regular exceptions and explicit `ToolError` values into MCP
errors. With `mask_error_details=True`, unexpected internal exception details
are masked, while intentionally raised `ToolError` messages remain visible to
clients. [FastMCP](https://gofastmcp.com/servers/tools?utm_source=chatgpt.com)

This distinction prevents errors such as these from leaking:

```
OperationalError: unable to open database file /internal/secret/path
```

while still allowing useful client-facing messages:

```
Operand 'a' has value 2000000.
Its absolute value must not exceed 1000000.
```

Professional wording:

> “Expected domain failures are translated at the protocol boundary; unexpected
> infrastructure failures are masked.”

---

# 13. Test the Service Without MCP

Create `test_service.py`:

```python
from __future__ import annotations

import unittest

from errors import OperandOutOfRangeError
from repository import InMemoryCalculationRepository
from service import ArithmeticService


class ArithmeticServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        repository = InMemoryCalculationRepository()
        self.service = ArithmeticService(repository)

    async def test_add_returns_and_persists_result(self) -> None:
        record = await self.service.add(20, 22)

        self.assertEqual(record.operation, "add")
        self.assertEqual(record.a, 20)
        self.assertEqual(record.b, 22)
        self.assertEqual(record.result, 42)

        history = await self.service.recent_calculations(10)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].id, record.id)

    async def test_multiply_returns_expected_result(self) -> None:
        record = await self.service.multiply(6, 7)

        self.assertEqual(record.result, 42)

    async def test_rejects_operand_outside_business_limit(self) -> None:
        with self.assertRaises(OperandOutOfRangeError):
            await self.service.add(1_000_001, 1)


if __name__ == "__main__":
    unittest.main()
```

Run it:

```bash
uv run python -m unittest -v test_service.py
```

Expected shape:

```
test_add_returns_and_persists_result ... ok
test_multiply_returns_expected_result ... ok
test_rejects_operand_outside_business_limit ... ok

Ran 3 tests
OK
```

This test does not start:

- FastMCP
- A subprocess
- SQLite
- Uvicorn
- HTTP

That is the benefit of isolating the application layer.

---

# 14. Update `test_stdio_client.py`

```python
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
from fastmcp.exceptions import ToolError

PROJECT_ROOT = Path(__file__).resolve().parent
SERVER_FILE = PROJECT_ROOT / "server.py"
DATABASE_FILE = PROJECT_ROOT / "data" / "calculations.db"


def text_content(item: Any) -> str:
    text = getattr(item, "text", None)
    return text if text is not None else str(item)


async def main() -> None:
    transport = PythonStdioTransport(
        str(SERVER_FILE),
        env={
            "APP_ENV": "development",
            "CALC_DB_PATH": str(DATABASE_FILE),
        },
    )

    async with Client(transport) as client:
        add_result = await client.call_tool(
            "add",
            {
                "a": 20,
                "b": 22,
            },
        )

        print("Add result:")
        print(add_result.data)

        multiply_result = await client.call_tool(
            "multiply",
            {
                "a": 6,
                "b": 7,
            },
        )

        print("\nMultiply result:")
        print(multiply_result.data)

        history = await client.read_resource(
            "history://calculations/recent/10"
        )

        print("\nRecent calculations:")
        for item in history:
            print(text_content(item))

        try:
            await client.call_tool(
                "add",
                {
                    "a": 2_000_000,
                    "b": 1,
                },
            )
        except ToolError as exc:
            print("\nExpected business error:")
            print(exc)


if __name__ == "__main__":
    asyncio.run(main())
```

Run:

```bash
uv run python test_stdio_client.py
```

Expected result shape:

```
Add result:
{
    'id': 1,
    'operation': 'add',
    'a': 20,
    'b': 22,
    'result': 42,
    'created_at': '...'
}

Multiply result:
{
    'id': 2,
    'operation': 'multiply',
    'a': 6,
    'b': 7,
    'result': 42,
    'created_at': '...'
}

Recent calculations:
[
  {
    "id": 2,
    "operation": "multiply",
    ...
  },
  {
    "id": 1,
    "operation": "add",
    ...
  }
]

Expected business error:
Operand 'a' has value 2000000...
```

Run the client again. The previous history should remain because SQLite persists
it on disk.

---

# 15. Coding Thought Process

## Step 1: Identify the use case

```
Calculate a result and record it.
```

This belongs to an application service.

## Step 2: Separate pure computation from side effects

```
Pure:
add or multiply numbers

Side effect:
persist calculation
```

## Step 3: Define the dependency as an interface

```python
class CalculationRepository(Protocol):
```

Do this before tying the service to SQLite.

## Step 4: Implement infrastructure behind that interface

```python
class SQLiteCalculationRepository:
```

## Step 5: Keep protocol translation at the edge

```
MCP inputs
    │
    ▼
Service call
    │
    ▼
Domain result
    │
    ▼
MCP-compatible output
```

## Step 6: Test the center independently

```
In-memory repository
        │
        ▼
Application service
```

## Step 7: Add integration testing around the outside

```
FastMCP client
    │
    ▼
stdio transport
    │
    ▼
MCP server
    │
    ▼
SQLite
```

This gives two test levels:

| Test                 | What it verifies                     |
|----------------------|--------------------------------------|
| Service test         | Business rules and orchestration     |
| MCP integration test | Protocol wiring and real persistence |

---

# 16. Professional Vocabulary

| Term                       | Meaning                                                 |
|----------------------------|---------------------------------------------------------|
| **Service layer**          | Coordinates application use cases                       |
| **Repository pattern**     | Abstracts persistence behind a domain-facing interface  |
| **Port**                   | Interface through which the application communicates    |
| **Adapter**                | Implementation connecting a port to external technology |
| **Inbound adapter**        | Entry point such as MCP, HTTP, or CLI                   |
| **Outbound adapter**       | Integration such as SQLite or an external API           |
| **Dependency inversion**   | High-level logic depends on abstractions                |
| **Fat handler**            | Protocol handler containing too many responsibilities   |
| **Thin handler**           | Handler limited to translation and delegation           |
| **Domain model**           | Structured representation of an application concept     |
| **Application error**      | Expected failure caused by business rules               |
| **Infrastructure error**   | Failure from a database, network, or filesystem         |
| **Error translation**      | Converting errors between architectural layers          |
| **Lazy initialization**    | Deferring setup until first use                         |
| **Cooperative scheduling** | Tasks yield control explicitly through awaits           |
| **I/O-bound**              | Mostly waiting for external operations                  |
| **CPU-bound**              | Mostly performing processor-intensive computation       |
| **Persistence port**       | Application-facing interface for durable storage        |
| **Structural typing**      | Compatibility based on implemented behavior             |
| **Composition root**       | Location where concrete dependencies are assembled      |

A professional summary:

> “I refactored the MCP implementation into a ports-and-adapters structure. MCP
> functions now act as thin inbound adapters, while an asynchronous application
> service owns business orchestration. Persistence is defined through a repository
> protocol and implemented using SQLite, which lets service tests substitute an
> in-memory adapter without starting the MCP runtime.”

---

# 17. Completion Check

```
[ ] aiosqlite and pydantic are direct project dependencies
[ ] Domain models are separate from MCP handlers
[ ] Application errors do not import FastMCP
[ ] Service does not import FastMCP or SQLite
[ ] Repository interface is represented by a Protocol
[ ] SQLite queries use parameter binding
[ ] Tool handlers are async
[ ] History resource performs async persistence access
[ ] Service tests run without MCP
[ ] stdio integration persists calculations
[ ] Expected errors become ToolError or ResourceError
[ ] Unexpected internal error details are masked
```

## Next increment

The next increment replaces stdio with **Streamable HTTP** and introduces the
ASGI boundary:

```
MCP client
    │ HTTP
    ▼
Uvicorn
    │ ASGI
    ▼
FastMCP HTTP application
    │
    ▼
Application service
```

FastAPI lifecycle composition follows immediately after that, where lazy
initialization will be removed and infrastructure startup and shutdown will
become explicit.