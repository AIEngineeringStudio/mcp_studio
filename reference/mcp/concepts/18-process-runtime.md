# Uvicorn, workers, and process state

**Outcome:** Separate the HTTP runtime from the application and reason about multiple workers.

**Prerequisites:** [11: Streamable HTTP](11-streamable-http.md), [17: Application lifespan and dependency ownership](17-application-lifespan.md).

## The application does not own every layer

Uvicorn accepts network connections, handles HTTP, and calls an ASGI application.
The application routes work and performs MCP processing. The business service
owns domain behavior.

```text
socket --> Uvicorn --> ASGI application --> MCP handler --> service
```

This explains why “the server” can mean several things in conversation.
Name the layer when debugging.

## One worker has its own memory

A worker is an operating-system process. Four workers do not share an ordinary
Python dictionary, asyncio lock, or database pool. Each process generally
constructs its own instances.

If each worker opens a pool of ten connections, four workers can consume
forty database connections before accounting for other services. Multiplying
workers can move the bottleneck to storage.

Development reload starts/restarts processes as source changes. It is not a
production scaling strategy and should not be confused with a pool of workers.

## Stateless protocol versus stateful application

Modern MCP requests are self-contained at the protocol level. That does not
mean the application has no state. Ticket records, operation outcomes, quotas,
and pending approvals still require explicit ownership.

A request routed to worker B cannot find an intent stored only in worker A's
dictionary. Use durable shared state or a deliberately designed alternative.
Legacy protocol sessions introduce additional routing constraints, which are
a separate compatibility concern.

## Graceful shutdown

A termination signal starts a shutdown sequence. The runtime allows a bounded
period for active requests before closing down. Coordinate that timeout with
the orchestrator's termination grace period and downstream operation limits.

A very short deadline can interrupt responses after a write has committed.
A very long deadline can delay deployment or leave failing instances active.
Use measured workloads to choose the bound.

## Inspect the right evidence

When throughput is low, inspect event-loop blocking, CPU time, pool wait time,
and upstream latency before adding workers. When state seems to disappear,
record the worker process identity and where that state is stored.

Temporary diagnostic routes can help a local exercise, but internal process
and configuration information should not become an unauthenticated public API.

## Worked capacity reasoning

Assume one request occupies a database connection for 200 milliseconds.
Increasing workers may help only while the database and connection budget have
headroom. If all requests wait on a slow external API, adding workers without
timeouts and limits may amplify load without improving completion time.

**Professional articulation:**

> “Workers scale process capacity, but they also multiply process-local
> resources. Shared business state must be designed independently.”

## Sources and next step

- [Archive: conversations/chatgpt/7_Uvicorn_ProcessRuntime.md](../../conversations/chatgpt/7_Uvicorn_ProcessRuntime.md)
- [Archive: conversations/chatgpt/5_StreamableHttp_Uvicorn.md](../../conversations/chatgpt/5_StreamableHttp_Uvicorn.md)
- [Official runtime settings](https://github.com/Kludex/uvicorn/blob/main/docs/settings.md) — checked 2026-11-15.

Next: [Host validation, Origin, and CORS](19-origin-cors.md).

