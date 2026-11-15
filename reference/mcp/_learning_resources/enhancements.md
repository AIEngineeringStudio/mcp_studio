# Summary

## One thing I got right that I'd keep

The Strategy pattern for elicitation is the strongest
design decision here. PlanStrategy, AlwaysContinue,
and CallbackStrategy are genuinely interchangeable —
swapping them in tests or in the CLI requires zero
changes to handlers.py or mcp_client.py. That boundary
held up cleanly.

## A few things I'd change, grouped by severity.

```
  Issue                        Severity  Fix effort
  ─────────────────────────────────────────────────
  TraceBus not multi-worker    HIGH      Redis backend
  elicit_futures not safe      HIGH      same
  No elicitation timeout       HIGH      asyncio.wait_for
  parent_id never wired        MEDIUM    thread through _emit
  New DB conn per query        MEDIUM    connection pool
  Protocol not enforced        LOW       smoke test
  config at import time        LOW       pydantic-settings
  Hardcoded localhost in UI    LOW       env var
  No structured logging        LOW       structlog
```

### Severity 1 — would cause real problems in production

```
Single shared TraceBus singleton

  Current:  bus = TraceBus()  in trace_bus.py — one global
            object in the process.
            
  Problem:  TraceBus singleton not multi-worker safe.
            If the bridge ever runs with multiple workers
            (gunicorn -w 4), each worker has its own bus.
            A subscriber in worker A never sees events
            emitted in worker B.
            
  Fix:      Redis Pub/Sub or a process-safe queue as the
            backend. For single-worker dev it's fine, but
            the code doesn't make that constraint visible.
            
          → AbstractTraceBus interface with two implementations:
            InProcessTraceBus (asyncio, single worker)
            RedisTraceBus     (Redis Pub/Sub, any number of workers)
            make_bus() selects at startup via APP_USE_REDIS.

elicit_futures dict has the same problem

  Current:  _elicit_futures: dict in bridge.py global scope.
  
  Problem:  elicit_futures not multi-worker safe
            Same multi-worker race. POST /elicit lands on
            worker B, Future lives in worker A → 404.
            
  Fix:      Same Redis fix, or enforce single-worker and document it loudly.
  
          → Same split: _InProcessFutureStore (asyncio.Future dict)
            vs _RedisFutureStore (Redis blpop list per run_id).
            Constraint is now explicit and documented.

No timeout on elicitation futures

  Current:  The asyncio.Future waits forever if the browser
            tab closes mid-stream.
  Problem:  No elicitation timeout
            The MCP server call never returns. Tool hangs.
            The queue entry in TraceBus leaks.
  Fix:      asyncio.wait_for(fut, timeout=120) + cleanup.
  
          → asyncio.wait_for(fut, timeout=cfg.elicit_timeout_seconds)
            Emits an ERROR trace node on timeout. Controlled via
            APP_ELICIT_TIMEOUT_SECONDS (default 120s).
```

### Severity 2 — correct but brittle

```
TraceEvent parent_id is never wired

  I defined it in trace_models.py to build a real tree
  (child nodes nested under their parent) but I never
  wire it up in bridge.py. The UI renders everything
  at depth=0 instead of a true call tree.
  
  Fix:  Pass parent_id through _run_tool and thread it
        through every _emit() call.
        
      → _emit() now returns the TraceEvent it created.
        Every subsequent _emit() in the same run passes
        parent_id=<parent_event>.event_id.
        buildTree() in React reconstructs the nested structure
        from the flat SSE stream using parent_id.
        TraceNode is now recursive — children render indented.

StreamContext Protocol not verified/enforced at startup

  user_service.py defines a Protocol so the service is
  decoupled from FastMCP's Context. But Python Protocols
  are structural — nothing enforces it at startup.
  If FastMCP renames report_progress the service silently
  breaks at runtime.
  
  Fix:  Add a small smoke-test or runtime isinstance check
        in the lifespan function.
        
      → _verify_context_protocol() in server.py lifespan. 
         Checks for required method names on Context at startup.  
         Raises TypeError before any tool is callable if FastMCP  
         ever drops a required method.  
        

New DB connection per query. UserRepository opens a new connection per query

  Every count() and fetch_page() call does
  AsyncConnection.connect(). Under load that is one TCP
  handshake + auth round-trip per batch.
  
  Fix:  Use psycopg_pool.AsyncConnectionPool, created once
        in lifespan() and injected into the repo.
        
      → DatabasePool wraps psycopg_pool.AsyncConnectionPool.  
        Pool created once in lifespan(), injected into repo.  
        UserRepository.count() and fetch_page() borrow from  
        the pool, not open a new connection.  
        
        
```

### Severity 3 — design choices I'd reconsider

```
Sharing app/ between server and bridge via one Docker image

  It works but it couples the bridge's deployment to the
  server's. A schema change in domain.py breaks both.
  I'd separate them into two proper packages with a shared
  models library, or at least make the coupling explicit
  in the pyproject.toml.

config.py uses module-level os.environ.get()

  Values are read at import time. You cannot override them
  in tests without patching os.environ before the import.
  
  Fix: Use pydantic-settings BaseSettings — values are
       read lazily and can be overridden cleanly in tests.
       
     → pydantic-settings BaseSettings with APP_ prefix.
       Values read lazily via get_settings() / @lru_cache.
       Tests can call get_settings.cache_clear() and set
       env vars without import-order issues.  
        

The React UI hardcodes localhost:8001

  Fine for local dev, but the bridge URL should come from
  an env var injected at build time (VITE_BRIDGE_URL or
  similar) so the same image works in staging.
 
  → Bridge URL is an editable input in the app header.
    Shared as globalBridgeUrl prop into every ToolPanel.
  
No structured logging on the server

  Currently everything is print(). In production you want
  JSON logs with run_id, actor, and timestamp fields so
  you can correlate a trace in the UI with a log line in
  Datadog / CloudWatch.
  
  Fix: structlog or the stdlib logging + a JSON formatter,
       with run_id as a context variable.
       
     → structlog with JSONRenderer on both server.py and
       bridge.py. Every log line carries run_id, tool,
       elapsed_ms etc. as structured fields. 
```