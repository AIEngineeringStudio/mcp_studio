# Async I/O and concurrent requests

**Outcome:** Explain where async helps and why shared mutable state needs a separate design.

**Prerequisites:** [07: The first client and in-memory testing](07-in-memory-client.md).

## Waiting is different from computing

A ticket lookup may spend most of its time waiting for a database. Async I/O
lets the event loop do other work during that wait. It does not make a CPU-heavy
calculation faster merely because its function uses `async def`.

```
Request A: start ---- await database ------- resume
Request B:             start -- await -- resume
Event loop: switches work at cooperative suspension points
```

Blocking calls inside an async handler can prevent other requests from
progressing. Use an asynchronous dependency where appropriate, or explicitly
offload blocking work according to the framework's supported mechanism.

## Concurrency changes ownership questions

Suppose two calls both read “ticket is open,” then both close it and send a
notification. A Python dictionary shared across tasks does not make that
sequence atomic. An asyncio lock can coordinate tasks in one event loop,
but another worker process has its own lock.

Database constraints, transactions, and durable operation records address
different boundaries. Choose a mechanism based on where the conflicting work
can execute.

## Request-scoped identity

Do not store the current user in a module-level mutable variable. A concurrent
request can overwrite it before an awaited operation resumes. Pass verified
identity explicitly through service calls or use a properly scoped context
mechanism.

Python `ContextVar` supports context-local values. Set/reset tokens restore
the prior scope. Values can propagate into child tasks, so creating background
tasks also needs deliberate lifetime and identity handling. Do not assume
arbitrary framework boundaries preserve context exactly as expected.

A context variable is not a database transaction, authorization check, or
distributed state store.

## Cancellation and cleanup

A request can be cancelled while waiting. Acquired resources must be released
through context managers or `finally` blocks. Do not broadly swallow
cancellation and continue an expensive operation unknowingly.

At the same time, cancellation does not prove that a remote write was undone.
An upstream service may have committed before the cancellation arrived.
That outcome belongs to retry/reconciliation design.

## Worked design choice

For a local fixture lookup, a synchronous function is enough. When the handler
begins waiting on an async database driver, an async service becomes useful.
If it performs CPU-heavy document analysis, consider a worker system or process
boundary rather than blocking the serving event loop.

Introduce each change because the workload requires it. A beginner's first
tool does not require a pool, task queue, or background worker.

## Observe concurrent waiting

This complete example uses only Python's standard library:

```python
import asyncio


async def lookup(ticket_id: str) -> str:
    print(f"start {ticket_id}")
    await asyncio.sleep(0.1)
    print(f"finish {ticket_id}")
    return ticket_id


async def main() -> None:
    results = await asyncio.gather(lookup("T-100"), lookup("T-101"))
    print(results)


asyncio.run(main())
```

Both calls begin before either finishes because each yields control at
`await asyncio.sleep(...)`. Replace that wait with CPU-heavy work and the event
loop does not gain the same concurrency benefit.

**Professional articulation:**

> “Async I/O improves concurrency during waiting. Correct shared-state
> behavior still requires explicit ownership and atomic operations.”

## Sources and next step

- [Archived service and async example](../fastMcp-fastApi-uvicorn-ngnix-docker/4_ServiceLayer_Persistence_AsyncIO.md)
- [Archived request-context authentication notes](../auth/04B-MCP_server-AuthN.md)
- [Official reference](https://docs.python.org/3/library/asyncio-task.html) — checked 2026-11-15.

Next: [Service layers and persistence](16-service-persistence.md).

