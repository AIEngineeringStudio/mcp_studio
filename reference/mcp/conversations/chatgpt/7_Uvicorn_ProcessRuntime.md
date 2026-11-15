# Increment 7 — Uvicorn Process Runtime

## Goal

Understand the layer that owns the operating-system process:

```text
Process manager
    │
    ├── receives signals
    ├── starts workers
    ├── monitors workers
    └── restarts failed workers
          │
          ▼
      Uvicorn worker
          │
          ├── event loop
          ├── listening socket
          ├── HTTP connections
          └── ASGI lifespan
                │
                ▼
            FastAPI + FastMCP
```

No business logic changes in this increment. We are focusing on:

- Application factories
- Signals
- Request draining
- Graceful-shutdown timeouts
- Worker isolation
- Concurrency limits
- SQLite’s scaling constraints

---

# 1. Use an Application Factory

Our current module ends with:

```python
app = create_application()
```

That creates application objects when the module is imported.

Instead, let Uvicorn invoke the factory explicitly.

Remove this line from `app.py`:

```python
app = create_application()
```

Run the application using:

```bash
uv run uvicorn app:create_application \
  --factory \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 1 \
  --lifespan on \
  --timeout-keep-alive 5 \
  --timeout-graceful-shutdown 20 \
  --log-level info
```

`--factory` tells Uvicorn that the imported attribute is a zero-argument
callable that returns the ASGI application. Uvicorn supports factory loading
explicitly, and an import string is required for worker or reload
modes. [GitHub](https://raw.githubusercontent.com/encode/uvicorn/master/docs/settings.md)

Conceptually:

```text
Uvicorn process starts
    │
    ▼
Import app:create_application
    │
    ▼
Call create_application()
    │
    ▼
Receive FastAPI ASGI application
    │
    ▼
Run its lifespan
```

Professional wording:

> “Uvicorn invokes an application factory inside each worker, giving every
> process an independently constructed dependency graph.”

---

# 2. Add Process Diagnostics

Temporarily add two diagnostic endpoints inside `create_application()` in
`app.py`.

Add these imports:

```python
import asyncio
import os

from fastapi import FastAPI, Query, Request, status
```

Then add the endpoints before mounting the MCP application:

```python
@application.get(
    "/debug/process",
    include_in_schema=False,
)
async def process_information() -> dict[str, int]:
    """Return the process serving the current request."""

    return {
        "worker_pid": os.getpid(),
        "parent_pid": os.getppid(),
    }


@application.get(
    "/debug/slow",
    include_in_schema=False,
)
async def slow_request(
        seconds: float = Query(
            default=5.0,
            ge=0.0,
            le=30.0,
        ),
) -> dict[str, int | float]:
    """Provide a controlled request for shutdown experiments."""

    worker_pid = os.getpid()

    await asyncio.sleep(seconds)

    return {
        "worker_pid": worker_pid,
        "slept_seconds": seconds,
    }
```

These are temporary observability hooks. Remove or protect them before public
deployment.

---

# 3. Include the Worker PID in Lifecycle Logs

Update the lifespan logging:

```python
@asynccontextmanager
async def application_lifespan(
        application: FastAPI,
):
    worker_pid = os.getpid()

    application.state.ready = False
    application.state.worker_pid = worker_pid

    logger.info(
        "Worker startup started pid=%s database=%s",
        worker_pid,
        resolved_database_path,
    )

    await repository.start()

    application.state.ready = True

    logger.info(
        "Worker startup completed pid=%s",
        worker_pid,
    )

    try:
        yield
    finally:
        application.state.ready = False

        logger.info(
            "Worker shutdown started pid=%s",
            worker_pid,
        )

        await repository.close()

        logger.info(
            "Worker shutdown completed pid=%s",
            worker_pid,
        )
```

This proves that lifespan is **process-local**:

```text
Worker 1001
├── own lifespan
├── own repository object
├── own SQLite connection
└── own service object

Worker 1002
├── own lifespan
├── own repository object
├── own SQLite connection
└── own service object
```

With multiple workers, FastAPI startup executes separately in every server
process. FastAPI’s worker example shows each worker reporting its own
application startup
sequence. [FastAPI](https://fastapi.tiangolo.com/deployment/server-workers/)

---

# 4. Single-Worker Runtime

Start the service:

```bash
uv run uvicorn app:create_application \
  --factory \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 1 \
  --lifespan on \
  --timeout-keep-alive 5 \
  --timeout-graceful-shutdown 20 \
  --log-level info
```

Check the process:

```bash
curl http://127.0.0.1:8000/debug/process
```

Example:

```json
{
  "worker_pid": 42100,
  "parent_pid": 41950
}
```

With one worker, that worker owns:

- One Python interpreter
- One event loop
- One FastAPI application
- One FastMCP registry
- One SQLite connection
- Many concurrent asynchronous request tasks

```text
One worker process
└── One event loop
    ├── request task A
    ├── request task B
    ├── MCP task C
    └── readiness task D
```

Async concurrency allows tasks waiting on I/O to be interleaved. It does not
make CPU-bound Python code execute in parallel inside one worker.

---

# 5. Signals and Graceful Shutdown

## Normal shutdown sequence

When Uvicorn begins graceful shutdown, it stops normal connection acceptance,
allows active responses and background tasks to complete, and then runs the ASGI
lifespan teardown. Requests must finish within the configured graceful-shutdown
timeout. [GitHub](https://raw.githubusercontent.com/encode/uvicorn/master/docs/server-behavior.md)

```text
Shutdown signal
    │
    ▼
Uvicorn stops accepting normal new work
    │
    ▼
Active HTTP requests drain
    │
    ▼
Background tasks complete
    │
    ▼
FastAPI lifespan teardown
    │
    ├── ready = False
    └── repository.close()
    │
    ▼
Event loop stops
    │
    ▼
Worker process exits
```

Typical signals are:

| Signal    | Common source                                         |
|-----------|-------------------------------------------------------|
| `SIGINT`  | `Ctrl+C` in a terminal                                |
| `SIGTERM` | Container runtime, service manager, deployment system |
| `SIGKILL` | Forced termination with no cleanup opportunity        |

`SIGKILL` cannot be intercepted. Code after the lifespan `yield` will not run
when a process is killed that way.

---

# 6. Hands-On Graceful-Shutdown Experiment

## Terminal 1

Start Uvicorn:

```bash
uv run uvicorn app:create_application \
  --factory \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 1 \
  --lifespan on \
  --timeout-graceful-shutdown 20
```

## Terminal 2

Start a ten-second request:

```bash
curl "http://127.0.0.1:8000/debug/slow?seconds=10"
```

## Terminal 1

While the request is running, press:

```text
Ctrl+C
```

Expected sequence:

```text
Shutting down
Waiting for connections to close
Worker shutdown started
Worker shutdown completed
Application shutdown complete
```

The request should be allowed to finish because its ten-second duration is
shorter than the twenty-second graceful-shutdown timeout. Uvicorn’s graceful
shutdown waits for existing responses and background tasks, subject to
configured timeout
limits. [GitHub](https://raw.githubusercontent.com/encode/uvicorn/master/docs/server-behavior.md)

Professional wording:

> “The process received a termination signal, stopped admitting work, drained
> the in-flight request, and then executed deterministic lifespan teardown.”

---

# 7. Experiment With an Insufficient Timeout

Start Uvicorn with:

```bash
uv run uvicorn app:create_application \
  --factory \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 1 \
  --lifespan on \
  --timeout-graceful-shutdown 3
```

Start a ten-second request:

```bash
curl "http://127.0.0.1:8000/debug/slow?seconds=10"
```

Then press `Ctrl+C`.

The shutdown timeout is now shorter than the request duration. Uvicorn begins
terminating remaining requests after the graceful-shutdown deadline
expires. [GitHub](https://raw.githubusercontent.com/encode/uvicorn/master/docs/settings.md)

This demonstrates a deployment requirement:

```text
Outer shutdown allowance
must be greater than
Uvicorn graceful-shutdown timeout
```

For example:

```text
Container termination grace: 30 seconds
Uvicorn graceful timeout:      20 seconds
Application cleanup budget:    included within those 20 seconds
```

Bad configuration:

```text
Container sends SIGTERM
    │
    ├── gives process 10 seconds
    │
    └── Uvicorn expects up to 20 seconds
            │
            ▼
Container sends SIGKILL before cleanup completes
```

Professional term:

> **Shutdown budget alignment**

---

# 8. Keep-Alive Timeout Is Not a Request Timeout

We configured:

```bash
--timeout-keep-alive 5
```

This controls how long an idle persistent HTTP connection remains open **between
requests**. It does not limit how long a running MCP tool may execute. Uvicorn’s
default keep-alive timeout is five
seconds. [GitHub](https://raw.githubusercontent.com/encode/uvicorn/master/docs/server-behavior.md)

```text
HTTP connection
├── Request 1
├── Response 1
├── idle period       ← keep-alive timeout applies here
├── Request 2
└── Response 2
```

It does not mean:

```text
MCP tool may run for only five seconds
```

A tool execution timeout must be implemented separately, usually around the
service call:

```python
import asyncio

record = await asyncio.wait_for(
    service.add(a, b),
    timeout=10.0,
)
```

Do not add that blindly. A timeout contract requires decisions about
cancellation, database transactions, external API calls, and whether the
operation may still complete after the client stops waiting.

---

# 9. Multiple Workers

Try:

```bash
uv run uvicorn app:create_application \
  --factory \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 4 \
  --lifespan on \
  --timeout-graceful-shutdown 20
```

Uvicorn’s built-in process manager starts a parent process plus the requested
number of worker processes. It uses the multiprocessing `spawn` strategy rather
than pre-fork and monitors child processes for unexpected
failure. [GitHub](https://raw.githubusercontent.com/encode/uvicorn/master/docs/deployment/index.md)

You should see four independent startup sequences:

```text
Worker startup completed pid=50101
Worker startup completed pid=50102
Worker startup completed pid=50103
Worker startup completed pid=50104
```

Architecture:

```text
Uvicorn parent process
├── Worker 50101
├── Worker 50102
├── Worker 50103
└── Worker 50104
```

Each worker has its own memory:

```text
Not shared:
├── Python objects
├── FastAPI application state
├── FastMCP server objects
├── asyncio locks
├── caches
└── database connections

Potentially shared externally:
├── SQLite file
├── network service
├── Redis
└── PostgreSQL
```

Professional wording:

> “Worker replication provides process-level parallelism, but it does not
> provide shared in-memory state.”

---

# 10. Probe Worker Distribution

Create `probe_workers.py`:

```python
from __future__ import annotations

import asyncio
from collections import Counter

import httpx

PROCESS_URL = "http://127.0.0.1:8000/debug/process"


async def fetch_process(
        client: httpx.AsyncClient,
) -> int:
    response = await client.get(PROCESS_URL)
    response.raise_for_status()

    payload = response.json()
    return int(payload["worker_pid"])


async def main() -> None:
    limits = httpx.Limits(
        max_connections=20,
        max_keepalive_connections=0,
    )

    async with httpx.AsyncClient(
            limits=limits,
            timeout=5.0,
    ) as client:
        worker_pids = await asyncio.gather(
            *[
                fetch_process(client)
                for _ in range(40)
            ]
        )

    counts = Counter(worker_pids)

    print("Worker request counts:")

    for worker_pid, request_count in sorted(counts.items()):
        print(
            f"- pid={worker_pid}: "
            f"{request_count} requests"
        )


if __name__ == "__main__":
    asyncio.run(main())
```

Run:

```bash
uv run python probe_workers.py
```

Example:

```text
Worker request counts:
- pid=50101: 8 requests
- pid=50102: 12 requests
- pid=50103: 9 requests
- pid=50104: 11 requests
```

The distribution is not guaranteed to be equal. The operating system and server
socket scheduling determine which worker accepts each connection.

---

# 11. Every Worker Runs the Lifespan

With four workers, our startup behavior becomes:

```text
Worker 1 → opens SQLite connection
Worker 2 → opens SQLite connection
Worker 3 → opens SQLite connection
Worker 4 → opens SQLite connection
```

The startup code is not run once for the entire Uvicorn deployment. It runs once
per worker process. FastAPI’s official worker output demonstrates each worker
separately waiting for and completing application
startup. [FastAPI](https://fastapi.tiangolo.com/deployment/server-workers/)

This makes certain startup operations unsafe:

```python
# Dangerous when several workers execute it concurrently.
await perform_one - time - database - migration()
await create_initial_administrator()
await charge_subscription()
await publish_deployment_event()
```

Process-local startup should normally contain idempotent operations such as:

```text
Open this worker's database connection
Create this worker's HTTP client
Start this worker's cache
Validate configuration
```

One-time deployment work belongs in a separate migration or release step.

Professional wording:

> “ASGI lifespan is worker-scoped, so deployment-wide initialization must not be
> hidden inside application startup.”

---

# 12. Why the Python Lock No Longer Protects SQLite

Our repository contains:

```python
self._write_lock = asyncio.Lock()
```

With one worker:

```text
Request A ─┐
           ├── same asyncio.Lock
Request B ─┘
```

With four workers:

```text
Worker 1 → Lock 1
Worker 2 → Lock 2
Worker 3 → Lock 3
Worker 4 → Lock 4
```

The locks do not communicate across processes.

```text
Worker 1 acquires Lock 1
Worker 2 acquires Lock 2

Both may now attempt SQLite writes.
```

This is the distinction between:

- **In-process synchronization**
- **Inter-process synchronization**
- **Database transaction coordination**

Professional wording:

> “An asyncio lock serializes coroutines within one event loop; it is not a
> distributed or inter-process lock.”

---

# 13. SQLite Is the Scaling Constraint

SQLite permits several readers, but concurrent write transactions contend for
database locks. Python’s SQLite interface waits up to its configured timeout and
then raises `OperationalError` if a lock remains
unavailable. [Python documentation](https://docs.python.org/3/library/sqlite3.html)

Write-Ahead Logging can improve reader/writer concurrency because readers do not
block writers and a writer does not block readers. However, WAL introduces
checkpointing, can still return `SQLITE_BUSY`, and requires every process using
the database to be on the same host rather than a network
filesystem. [SQLite](https://www.sqlite.org/wal.html)

Therefore:

```text
More Uvicorn workers
does not automatically mean
more SQLite write throughput
```

Our application writes on every `add` and `multiply` call. That makes the
database a likely bottleneck before CPU capacity becomes a bottleneck.

Current recommendation:

```text
Development:
workers = 1
SQLite

Small single-host deployment:
workers = 1
SQLite with monitoring

Horizontal or write-heavy deployment:
multiple application instances
PostgreSQL or another client-server database
```

The weak assumption to reject is:

> “Four CPU cores means I should configure four workers.”

Worker count must follow measured bottlenecks, database capacity, memory use,
and deployment topology—not CPU count alone.

---

# 14. Optional SQLite Hardening for Local Experiments

For controlled multi-process experiments on one machine, update the connection
creation in `repository.start()`:

```python
connection = await aiosqlite.connect(
    self._database_path,
    timeout=10.0,
)

connection.row_factory = aiosqlite.Row
```

Then enable WAL before creating the table:

```python
journal_cursor = await connection.execute(
    "PRAGMA journal_mode=WAL"
)

try:
    await journal_cursor.fetchone()
finally:
    await journal_cursor.close()

await connection.execute(
    "PRAGMA busy_timeout=10000"
)
```

The resulting startup section is:

```python
connection = await aiosqlite.connect(
    self._database_path,
    timeout=10.0,
)

connection.row_factory = aiosqlite.Row

try:
    journal_cursor = await connection.execute(
        "PRAGMA journal_mode=WAL"
    )

    try:
        await journal_cursor.fetchone()
    finally:
        await journal_cursor.close()

    await connection.execute(
        "PRAGMA busy_timeout=10000"
    )

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
```

This reduces immediate lock failures; it does not turn SQLite into a distributed
database. WAL files require shared memory and are unsuitable when application
instances are on separate hosts or using ordinary network
filesystems. [SQLite](https://www.sqlite.org/wal.html)

---

# 15. Concurrency Limits

Uvicorn supports:

```bash
--limit-concurrency N
```

Once the limit is reached, excess requests receive an immediate
`503 Service Unavailable`; they are not queued for later execution. Idle
keep-alive connections also consume part of the limit. Uvicorn’s socket backlog
is a separate operating-system-level
setting. [GitHub](https://raw.githubusercontent.com/encode/uvicorn/master/docs/server-behavior.md)

```text
limit-concurrency
└── Application-level admission control
    └── Excess request gets HTTP 503

backlog
└── Kernel socket accept queue
    └── Excess connection may time out or fail
```

Do not guess a value such as:

```bash
--limit-concurrency 1000
```

A useful limit should be derived from:

- Memory per active request
- Database capacity
- External API capacity
- Maximum acceptable latency
- Number of workers
- Expected streaming connections

Also avoid:

```bash
--limit-concurrency 1
```

Current Uvicorn behavior counts the current connection in the concurrency
calculation, so a value of one can reject every
request. [GitHub](https://raw.githubusercontent.com/encode/uvicorn/master/docs/server-behavior.md)

For now, leave the limit unset and measure first.

---

# 16. Maximum Requests

Uvicorn also supports:

```bash
--limit-max-requests 10000
```

A worker exits after serving the configured number of requests. With a process
manager, that worker can be replaced, limiting the effect of gradual memory
leaks. Current Uvicorn also supports jitter so several workers do not all
restart
simultaneously. [GitHub](https://raw.githubusercontent.com/encode/uvicorn/master/docs/settings.md)

Example:

```bash
--limit-max-requests 10000 \
--limit-max-requests-jitter 1000
```

This is defensive recycling, not a substitute for fixing memory leaks.

Professional wording:

> “Worker recycling bounds long-term process growth but does not correct the
> underlying leak.”

We will not enable it until we have monitoring that can show whether process
memory is actually increasing.

---

# 17. Reload and Workers Are Different

Development:

```bash
uv run uvicorn app:create_application \
  --factory \
  --reload
```

Production-style worker experiment:

```bash
uv run uvicorn app:create_application \
  --factory \
  --workers 4
```

Uvicorn does not permit `--reload` and `--workers` together. Reload monitors
source files and restarts development processes; workers provide runtime process
replication. [GitHub](https://raw.githubusercontent.com/encode/uvicorn/master/docs/settings.md)

```text
Reload
└── Developer convenience

Workers
└── Process replication and parallelism
```

Do not use reload in production.

---

# 18. Logging Layers

The current system has three useful logging categories:

```text
Uvicorn error log
├── startup
├── shutdown
├── process failures
└── server errors

Uvicorn access log
├── client address
├── method
├── path
└── status code

Application log
├── repository startup
├── readiness failures
├── worker PID
└── business/infrastructure events
```

Uvicorn provides configurable log levels, access logging, and external logging
configuration
files. [GitHub](https://raw.githubusercontent.com/encode/uvicorn/master/docs/settings.md)

A useful operational log should include:

```text
timestamp
severity
service
worker_pid
request_id
operation
duration
outcome
```

Avoid logging:

```text
access tokens
API keys
authorization headers
complete user prompts
sensitive tool arguments
database credentials
```

---

# 19. Recommended Runtime for the Current Build

Use one worker:

```bash
uv run uvicorn app:create_application \
  --factory \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 1 \
  --lifespan on \
  --timeout-keep-alive 5 \
  --timeout-graceful-shutdown 20 \
  --log-level info
```

Rationale:

```text
workers=1
├── one SQLite connection
├── one in-process write lock
├── predictable lifespan
├── no cross-process SQLite contention
└── adequate async concurrency for learning
```

Multiple workers are valid as an experiment, but they are not yet our production
configuration.

FastAPI’s deployment guidance notes that multiple workers provide process
replication and CPU parallelism, while container orchestration commonly uses one
Uvicorn process per container and scales through additional containers
instead. [FastAPI](https://fastapi.tiangolo.com/deployment/server-workers/)

---

# 20. Failure Experiments

## Worker startup failure

Set an invalid database path:

```bash
CALC_DB_PATH=/restricted/calculations.db \
uv run uvicorn app:create_application \
  --factory \
  --workers 1
```

Expected layer:

```text
Worker process starts
    │
    ▼
FastAPI lifespan starts
    │
    ▼
Repository startup fails
    │
    ▼
Worker startup fails
```

---

## Worker forced termination

Find the worker PID:

```bash
curl http://127.0.0.1:8000/debug/process
```

Then, on Unix-like systems:

```bash
kill -9 <worker-pid>
```

Expected:

- No graceful lifespan teardown
- No repository shutdown log
- With a multi-worker Uvicorn process manager, the failed child should be
  detected and replaced. Uvicorn’s built-in manager monitors workers and
  restarts children that die
  unexpectedly. [GitHub](https://raw.githubusercontent.com/encode/uvicorn/master/docs/deployment/index.md)

---

## Database contention

Start four workers, then execute many concurrent arithmetic tool calls.

Possible outcomes:

```text
Low contention
└── all writes succeed

Moderate contention
└── some writes wait

Excessive contention
└── SQLite lock timeout
    └── OperationalError
```

That is an infrastructure-capacity failure, not an MCP protocol failure.

Professional diagnosis:

> “The HTTP and MCP layers completed dispatch successfully, but persistence
> failed because concurrent worker processes contended for SQLite’s write lock.”

---

# Professional Vocabulary

| Term                          | Meaning                                              |
|-------------------------------|------------------------------------------------------|
| **Application factory**       | Callable that constructs and returns an application  |
| **Worker**                    | Independent process serving application requests     |
| **Process manager**           | Parent process responsible for worker supervision    |
| **Signal**                    | Operating-system notification sent to a process      |
| **Request draining**          | Allowing in-flight work to finish during shutdown    |
| **Shutdown budget**           | Maximum time available for draining and cleanup      |
| **Grace period**              | Time between termination request and forced killing  |
| **Worker replication**        | Running multiple copies of an application process    |
| **Process isolation**         | Workers do not share ordinary Python memory          |
| **Worker-local state**        | State that exists in only one worker                 |
| **Admission control**         | Rejecting load beyond known capacity                 |
| **Backpressure**              | Preventing incoming load from overwhelming a service |
| **Socket backlog**            | Kernel queue of accepted-but-unhandled connections   |
| **Worker recycling**          | Replacing a process after a defined amount of work   |
| **Write contention**          | Several actors competing for exclusive write access  |
| **Busy timeout**              | Time SQLite waits for a lock before failing          |
| **WAL**                       | Write-Ahead Logging mode                             |
| **Process parallelism**       | Work executing in separate OS processes              |
| **Idempotent startup**        | Startup operation safe to repeat in each worker      |
| **Shutdown budget alignment** | Coordinating nested process-termination timeouts     |

Professional summary:

> “I configured Uvicorn as the explicit process runtime using an ASGI
> application factory. I validated graceful request draining, lifespan teardown,
> and worker-local dependency construction. Multiple workers provide process
> parallelism, but each worker owns independent Python state and a separate SQLite
> connection, so database write contention—not CPU capacity—is currently the
> primary scaling constraint.”

# Completion Check

```text
[ ] Uvicorn loads create_application with --factory
[ ] Import-time global app construction is removed
[ ] Worker PID is visible in lifecycle logs
[ ] Process diagnostic endpoint returns PID information
[ ] Slow-request experiment demonstrates request draining
[ ] Graceful-shutdown timeout is understood
[ ] Keep-alive timeout is not confused with tool timeout
[ ] Multiple workers produce separate startup sequences
[ ] Each worker has its own repository connection
[ ] asyncio.Lock is understood as process-local
[ ] SQLite remains configured with one production worker
[ ] Reload and workers are not used together
[ ] Forced termination is distinguished from graceful shutdown
```

## Next increment

The next increment puts **Nginx in front of Uvicorn**:

```text
MCP client
    │
    │ public HTTP
    ▼
Nginx
├── request limits
├── proxy headers
├── buffering decisions
├── connection timeouts
└── TLS boundary
    │
    │ private upstream HTTP
    ▼
Uvicorn
    │
    ▼
FastAPI / FastMCP
```

The important issue will be preserving Streamable HTTP and SSE behavior while
preventing clients from connecting directly to Uvicorn.