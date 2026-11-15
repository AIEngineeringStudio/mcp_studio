
## Summary of all 10 diagrams and which documentation section each one supports:

1. Diagram 1 — System overview. The three running processes and how they
   connect.
    [System overview](pngs/d1_system_overview.png)

2. Diagram 2 — Layer architecture. The full software stack from browser to
   database, showing which file lives at each layer and what it is responsible
   for.
    [Layer architecture](pngs/d2_layer_architecture.png)

3. Diagram 3 — Dependency injection. How objects are built at startup and flow
   down to every tool call through the lifespan context.
    [Dependency injection](pngs/d3_dependency_injection.png)

4. Diagram 4 — Strategy pattern. The four concrete elicitation strategies and
   when each one is used.
    [Strategy pattern](pngs/d4_strategy_pattern.png)

5. Diagram 5 — Streaming vs normal. The visual difference between a blocking
   response and a streaming one, showing why streaming matters for user
   experience.
    [Streaming vs normal](pngs/d5_streaming_vs_normal.png)

6. Diagram 6 — Elicitation sequence. The exact back-and-forth between server and
   client during an interactive stream, including how the asyncio.Future bridges
   an HTTP POST to a suspended coroutine.
    [Elicitation sequence](pngs/d6_elicitation_sequence.png)

7. Diagram 7 — Connection pool. The before/after showing why opening one
   connection per query is slow and how the pool fixes it.
    [Connection pool](pngs/d7_connection_pool.png)

8. Diagram 8 — Trace bus: in-process vs Redis. Why the in-process bus breaks
   with multiple workers and how Redis solves it.
    [Trace bus](pngs/d8_trace_bus.png)

9. Diagram 9 — Pagination loop. How LIMIT and OFFSET work together to fetch 25
   rows in three batches without duplicates or gaps.
    [Pagination loop](pngs/d9_pagination.png)

10. Diagram 10 — Full end-to-end flow. The complete 18-step journey of a single
    interactive_stream_users call from browser click to final SSE close, with
    each layer colour-coded.
    [Full end-to-end flow](pngs/d10_end_to_end_flow.png)

```
Diagram  Section  What it shows
───────────────────────────────────────────────────────────
  1      §2       System overview — four processes, ports,
                  and the connections between them

  2      §4       Layer architecture — every file in the
                  stack from browser down to PostgreSQL

  3      §11      Dependency injection — how objects are
                  built once in lifespan() and flow into
                  every tool call via lifespan_context

  4      §12      Strategy pattern — the four concrete
                  ElicitStrategy classes and when each is
                  chosen at construction time

  5      §9       Streaming vs normal — why the user sees
                  data immediately instead of waiting

  6      §16      Elicitation sequence — the full
                  browser ↔ bridge ↔ MCP server exchange
                  including how asyncio.Future bridges an
                  HTTP POST to a suspended coroutine

  7      §6       Connection pool — before/after showing
                  why one connection per query is slow

  8      §15      Trace bus — in-process asyncio.Queue vs
                  Redis Pub/Sub, and why Redis is needed
                  for multiple workers

  9      §7       Pagination — how LIMIT/OFFSET steps
                  through rows in three batches without
                  duplicates or overfetch

 10      §20      Full end-to-end flow — the complete
                  18-step journey of one interactive
                  stream_users call, all layers visible
```