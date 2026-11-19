# Application lifespan and dependency ownership

**Outcome:** Assign startup and shutdown responsibility for shared dependencies.

**Prerequisites:** [15: Async I/O and concurrent requests](15-async-concurrency.md), [16: Service layers and persistence](16-service-persistence.md).

## Who opens the database pool

Creating a new connection pool inside every tool call wastes resources.
Creating it at import time can hide failures and complicate testing.
Application lifespan gives long-lived dependencies an explicit owner.

```
start process
    |
validate settings
    |
open dependencies
    |
serve requests
    |
stop accepting work
    |
drain / cancel bounded work
    |
close dependencies
```

A lifespan is the period during which an application is active. The
composition root is the place that constructs and connects its dependencies.

## FastAPI is a composition option

A standalone FastMCP application may already provide the lifecycle hooks your
service needs. FastAPI becomes useful when one service must combine MCP with
other HTTP routes, health endpoints, or application middleware.

Do not add FastAPI solely because MCP uses HTTP. An ASGI server can run an ASGI
application without FastAPI. ASGI is the Python interface between an async
application and its serving runtime.

## Mounted application lifecycle

Mounting a child application does not automatically establish every required
startup/shutdown relationship in every framework configuration. Follow the
pinned FastMCP/FastAPI integration documentation and test both acquisition and
release.

An endpoint can appear reachable while its dependency was never initialized.
A green TCP connection or liveness response therefore does not establish that
MCP operations are ready.

## Readiness and liveness

Liveness asks whether the process is functioning enough to remain running.
Readiness asks whether it can serve the intended traffic. A database outage
may make the service unready without proving that restarting every instance
will help.

During graceful shutdown, stop accepting new work, allow bounded completion,
then close dependencies. Cleanup order matters: closing a pool before active
handlers release connections can create unnecessary failures.

## A failure walkthrough

Configuration names a nonexistent database. Startup attempts to initialize
the repository and fails. The application should fail clearly before marking
itself ready. Deferring this failure until the first user's call makes the
system harder to operate and teach.

For a test, enter the application lifespan, assert readiness and dependency
availability, leave the lifespan, then assert closure. This validates ownership
rather than only checking a route response.

**Production extension:**

> Use typed startup settings and a composed lifecycle after the basic handler
> and client are understood. The initial in-memory lab intentionally has no
> database dependency to manage.

## See acquisition and cleanup paired together

This framework-neutral pattern shows the ownership idea:

```python
from contextlib import asynccontextmanager


@asynccontextmanager
async def application_lifespan():
    settings = load_and_validate_settings()
    pool = await open_database_pool(settings.database_url)
    try:
        yield {"pool": pool}
    finally:
        await pool.close()
```

The names `load_and_validate_settings` and `open_database_pool` represent
application-specific functions. The important sequence is complete: validate,
acquire once, serve work, and release in `finally`. Use the lifecycle API of
the pinned framework when turning this model into runnable application code.

**Professional articulation:**

> “The composition root owns shared dependencies and pairs acquisition with
> cleanup. Readiness reflects whether those dependencies can support traffic.”

## Sources and next step

- [Archived FastAPI lifecycle example](../fastMcp-fastApi-uvicorn-ngnix-docker/6_FastAPI_LifecycleManagement.md)
- [Archived MCP walkthrough](../walk-through-docs/walkthrough_doc.md)
- [Official reference](https://fastapi.tiangolo.com/advanced/events/) — checked 2026-11-15.

Next: [Uvicorn, workers, and process state](18-process-runtime.md).

