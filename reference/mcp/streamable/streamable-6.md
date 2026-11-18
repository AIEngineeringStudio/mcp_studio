

# §07 — ADVANCED CONCEPTS

<!-- CHUNK: 6/8 | SECTION: §07 -->

---

## 7.1 Security

### Basic Protections

| Protection           | How to apply                        | Why it matters                    |
|----------------------|-------------------------------------|-----------------------------------|
| **HTTPS only**       | TLS termination at Nginx            | Prevents MITM attacks on streams  |
| **Auth header**      | `Authorization: Bearer <token>`     | Verifies caller identity          |
| **CORS policy**      | Nginx `add_header Access-Control-*` | Blocks browser-based abuse        |
| **Input validation** | Pydantic models on all tool args    | Prevents injection via tool calls |
| **Rate limiting**    | Nginx `limit_req_zone`              | Blocks brute-force / DDoS         |

Here is the flow diagram covering §07’s major subsystems and how they interact:

![](../../assets/streamable/advanced_concepts_overview.png)




```nginx
# nginx.conf — rate limiting + TLS headers
limit_req_zone $binary_remote_addr zone=mcp:10m rate=30r/m;

server {
    listen 443 ssl;
    ssl_certificate /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options nosniff always;

    location /mcp {
        limit_req zone=mcp burst=10 nodelay;
        proxy_pass http://mcp_server:8000;
        proxy_set_header Authorization $http_authorization;
    }
}
```

### Advanced Protections

| Protection             | Mechanism                             | Implementation                        |
|------------------------|---------------------------------------|---------------------------------------|
| **JWT validation**     | Verify signature + expiry per request | `python-jose` library in FastAPI      |
| **Scope-based authz**  | Token claims gate individual tools    | Check `"scopes"` claim in JWT payload |
| **Session binding**    | `mcp-session-id` tied to JWT `sub`    | Server stores mapping in Redis        |
| **Request signing**    | HMAC-SHA256 on body + timestamp       | Prevents replay attacks               |
| **Secrets management** | Vault / AWS Secrets Manager           | No secrets in env files or images     |

```python
# server/auth.py — JWT scope guard
from jose import jwt, JWTError
from fastapi import HTTPException, Header

SECRET = "your-secret-key"
ALG = "HS256"


def require_scope(required: str):
    """
    Factory — returns a FastAPI dependency that enforces
    a specific JWT scope on the incoming request.
    """

    def guard(authorization: str = Header(...)):
        try:
            # Strip 'Bearer ' prefix and decode token
            token = authorization.removeprefix("Bearer ")
            claims = jwt.decode(token, SECRET, algorithms=[ALG])
            scopes = claims.get("scopes", [])

            if required not in scopes:  # scope must be present
                raise HTTPException(403, "Insufficient scope")

        except JWTError as exc:
            raise HTTPException(401, f"Invalid token: {exc}")

    return guard
```

### Common Vulnerabilities and Fixes

| Vulnerability           | Root cause                         | Fix                                  |
|-------------------------|------------------------------------|--------------------------------------|
| **Session hijacking**   | `mcp-session-id` in URL param      | Always send ID in header, not URL    |
| **Prompt injection**    | Tool args passed raw to LLM        | Sanitise/escape before LLM context   |
| **SSRF via tool calls** | Tool fetches attacker-supplied URL | Allowlist valid URL patterns         |
| **Broken stream auth**  | Auth checked only on first chunk   | Re-validate JWT on every SSE event   |
| **Unbounded streaming** | No max tokens / time limit         | Set `max_tokens` + server-side timer |

---

## 7.2 Scaling

### Load Balancing

```
🔑 Jargon: sticky session — routing all requests from
           the same client to the same server instance.
```

MCP uses **stateful sessions** (`mcp-session-id`).
A plain round-robin load balancer breaks sessions
across restarts. Two solutions:

| Strategy            | How it works                        | Tradeoff                      |
|---------------------|-------------------------------------|-------------------------------|
| **Sticky sessions** | Nginx `ip_hash` or cookie routing   | Simple; fails if node dies    |
| **External state**  | Session state in Redis; any node OK | Robust; adds Redis dependency |

```nginx
# nginx.conf — upstream with sticky sessions (ip_hash)
upstream mcp_cluster {
    ip_hash;                        # same client IP → same server
    server mcp_server_1:8000;
    server mcp_server_2:8000;
    server mcp_server_3:8000;
}
```

```python
# server/session_store.py — Redis-backed session (external state)
import redis.asyncio as aioredis
import json

pool = aioredis.ConnectionPool.from_url("redis://redis:6379")


async def save_session(session_id: str, data: dict) -> None:
    async with aioredis.Redis(connection_pool=pool) as r:
        # TTL = 1 hour; any node can read/write session
        await r.setex(
            f"session:{session_id}",
            3600,
            json.dumps(data),
        )


async def load_session(session_id: str) -> dict | None:
    async with aioredis.Redis(connection_pool=pool) as r:
        raw = await r.get(f"session:{session_id}")
        return json.loads(raw) if raw else None
```

### Caching Strategies

| What to cache           | Where           | TTL     | Invalidation trigger |
|-------------------------|-----------------|---------|----------------------|
| Tool schema definitions | In-process dict | Forever | Server restart       |
| DB row batches (Tool 2) | Redis           | 5 min   | Row update event     |
| JWT public keys         | In-process      | 1 hour  | Key rotation webhook |
| Elicitation prompt text | Redis           | 30 min  | Config change        |

```python
# server/cache.py — simple async Redis cache helper
import redis.asyncio as aioredis
import json, hashlib

pool = aioredis.ConnectionPool.from_url("redis://redis:6379")


async def cached(key: str, ttl: int, fetch_fn):
    """
    Return cached JSON value, or call fetch_fn(),
    store result, then return it.
    """
    async with aioredis.Redis(connection_pool=pool) as r:
        hit = await r.get(key)
        if hit:
            return json.loads(hit)  # cache hit

        value = await fetch_fn()  # cache miss
        await r.setex(key, ttl, json.dumps(value))
        return value
```

### Sharding

```
🔑 Jargon: sharding — splitting data into named
           partitions, each owned by one server.
```

For large datasets (e.g. Tool 2 processes 10 M rows):

| Approach            | Key formula                     | When to use                     |
|---------------------|---------------------------------|---------------------------------|
| **Hash sharding**   | `shard = hash(session_id) % N`  | Even distribution, stateless    |
| **Range sharding**  | `shard = row_id // BUCKET_SIZE` | Sequential scans, sorted output |
| **Tenant sharding** | `shard = tenant_id`             | Multi-tenant SaaS isolation     |

```python
# server/shard.py — consistent hash shard router
import hashlib


def get_shard(session_id: str, num_shards: int = 4) -> int:
    """Return shard index (0..N-1) for a given session."""
    digest = hashlib.md5(session_id.encode()).hexdigest()
    return int(digest, 16) % num_shards
```

---

## 7.3 Reliability

### Fault Tolerance

```
🔑 Jargon: circuit breaker — stops calling a failing
           service after N errors, resumes after cooldown.
```

| Technique              | What it prevents            | Tool / Pattern                     |
|------------------------|-----------------------------|------------------------------------|
| **Circuit breaker**    | Cascading DB/LLM failures   | `tenacity` + custom state machine  |
| **Timeout on streams** | Zombie SSE connections      | `asyncio.wait_for(gen, timeout=N)` |
| **Retry w/ backoff**   | Transient DB/network errors | `tenacity.retry` decorator         |
| **Health check**       | Traffic to dead containers  | Docker `HEALTHCHECK` + Nginx       |

```python
# server/resilience.py — retry + circuit breaker
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


@retry(
    stop=stop_after_attempt(3),  # try 3 times max
    wait=wait_exponential(min=0.5, max=4),  # 0.5s, 1s, 2s, …
    retry=retry_if_exception_type(Exception),
)
async def fetch_rows_with_retry(offset: int, limit: int):
    """Fetch DB rows; retry up to 3× on any exception."""
    return await fetch_rows(offset, limit)  # your DB call
```

### Replication

```
🔑 Jargon: read replica — a DB copy that accepts only
           SELECT queries, reducing load on the primary.
```

```python
# server/db.py — primary/replica routing (Ports & Adapters)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Writes → primary
primary = create_async_engine("postgresql+asyncpg://primary/db")

# Reads  → replica (horizontal scale)
replica = create_async_engine("postgresql+asyncpg://replica/db")


def write_session() -> AsyncSession:
    return AsyncSession(primary)


def read_session() -> AsyncSession:
    return AsyncSession(replica)
```

### Recovery Strategies

| Failure scenario          | Detection                           | Recovery action                        |
|---------------------------|-------------------------------------|----------------------------------------|
| Container crash           | Docker restart policy `always`      | Auto-restart; health probe retries     |
| Session lost (node death) | Client gets 404 on `mcp-session-id` | Client sends `initialize` again        |
| Redis unavailable         | `ConnectionError` in cache layer    | Fall through to DB; log alert          |
| SSE stream dropped        | Client `EventSource.onerror`        | Client reconnects with `Last-Event-ID` |
| DB primary failure        | SQLAlchemy connection error         | Promote replica; update DNS            |

---

## 7.4 Optimization

### Performance Improvements

| Optimization           | Where to apply           | Expected gain                     |
|------------------------|--------------------------|-----------------------------------|
| **Async DB driver**    | `asyncpg` not `psycopg2` | 3–5× throughput on concurrent Qs  |
| **DB connection pool** | `pool_size=20` on engine | Eliminates connection setup cost  |
| **Batch DB reads**     | Fetch 100 rows at once   | 100× fewer round trips            |
| **Chunk size tuning**  | Increase SSE chunk size  | Fewer HTTP frames, lower overhead |
| **Gzip on SSE body**   | Nginx `gzip on`          | 60–80% bandwidth reduction        |
| **uvicorn workers**    | `--workers 4`            | Saturates multi-core host         |

```python
# server/db.py — tuned async engine
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@db/mydb",
    pool_size=20,  # keep 20 connections warm
    max_overflow=10,  # allow 10 extra under burst
    pool_pre_ping=True,  # check connection health before use
    echo=False,  # disable SQL logging in production
)
```

### Bottleneck Identification

```
🔑 Jargon: flame graph — a visual stack trace that shows
           which functions consume the most CPU time.
```

1. Add **structured timing logs** at each pipeline stage:
   ```python
   import time, structlog
   log = structlog.get_logger()

   t0 = time.perf_counter()
   rows = await fetch_rows(offset, limit)
   log.info("db_fetch", duration_ms=(time.perf_counter()-t0)*1000,
            rows=len(rows))
   ```
2. Export metrics to **Prometheus** + **Grafana**:
    - Track: SSE events/sec, DB query latency, elicitation round-trip time.
3. Profile with **py-spy** for CPU flame graphs:
   ```bash
   pip install py-spy
   py-spy record -o profile.svg --pid <uvicorn-pid>
   ```
4. Common bottlenecks found in practice:

| Bottleneck                   | Symptom                     | Fix                           |
|------------------------------|-----------------------------|-------------------------------|
| Synchronous DB call in async | Worker blocked; CPU idle    | Switch to `asyncpg`           |
| No DB index on `id`          | Batch fetch grows O(N)      | `CREATE INDEX ON records(id)` |
| SSE flush too frequent       | High syscall overhead       | Buffer N chunks before flush  |
| Missing connection pool      | New TCP handshake per query | Set `pool_size` on engine     |

---

## 7.5 Trade-offs

```
┌──────────────────────────┬────────────────────┬───────────────────────┬─────────────────────────────┐
│ Approach                 │ Pros               │ Cons                  │ When to use                 │
├──────────────────────────┼────────────────────┼───────────────────────┼─────────────────────────────┤
│ Sticky sessions (Nginx)  │ Simple; zero extra │ Node death = session  │ Small teams; low HA         │
│                          │ infra              │ loss                  │ requirement                 │
├──────────────────────────┼────────────────────┼───────────────────────┼─────────────────────────────┤
│ Redis session store      │ Any node handles   │ Redis becomes SPOF    │ Production; multi-node      │
│                          │ any session        │ unless clustered      │ deployments                 │
├──────────────────────────┼────────────────────┼───────────────────────┼─────────────────────────────┤
│ Small SSE chunks         │ Low first-byte     │ High frame count;     │ Interactive UIs needing     │
│                          │ latency            │ more syscalls         │ live feedback               │
├──────────────────────────┼────────────────────┼───────────────────────┼─────────────────────────────┤
│ Large SSE chunks         │ Better throughput; │ Higher first-byte     │ Bulk data transfer          │
│                          │ fewer frames       │ latency               │ (Tool 2 batch rows)         │
├──────────────────────────┼────────────────────┼───────────────────────┼─────────────────────────────┤
│ In-process cache         │ Zero latency;      │ Not shared across     │ Immutable data (schemas,    │
│                          │ no network hop     │ workers               │ JWT public keys)            │
├──────────────────────────┼────────────────────┼───────────────────────┼─────────────────────────────┤
│ Redis cache              │ Shared; survives   │ Network latency;      │ Shared mutable data         │
│                          │ worker restart     │ serialization cost    │ (batch rows, prompts)       │
├──────────────────────────┼────────────────────┼───────────────────────┼─────────────────────────────┤
│ Single uvicorn process   │ Simple debugging   │ Single-core; no       │ Development only            │
│                          │                    │ fault isolation       │                             │
├──────────────────────────┼────────────────────┼───────────────────────┼─────────────────────────────┤
│ Multiple uvicorn workers │ Multi-core; fault  │ No shared memory;     │ Production under load       │
│                          │ isolated           │ need external state   │                             │
└──────────────────────────┴────────────────────┴───────────────────────┴─────────────────────────────┘
```

---

## Summary

- **Security**: JWT scopes gate tools; re-validate every SSE event; sanitise
  tool args.
- **Scaling**: MCP sessions are stateful → use Redis or sticky sessions under a
  load balancer.
- **Reliability**: Use retry+backoff for DB, circuit breaker for downstream,
  Docker restart policy.
- **Optimization**: `asyncpg` + connection pool + batch reads eliminate the
  three most common bottlenecks.
- **Key trade-off**: sticky sessions = simple but fragile; Redis sessions =
  robust but adds infra.

```
CHUNK STATUS
────────────────────────────────────────────
✅ Chunk 1 — §00–§01  Prerequisites + Define
✅ Chunk 2 — §02–§03  Why It Matters + Core Concepts
✅ Chunk 3 — §04      How It Works
✅ Chunk 4 — §05      Basic Example
✅ Chunk 5 — §06      Intermediate Level
✅ Chunk 6 — §07      Advanced Concepts  ← YOU ARE HERE
⬜ Chunk 7 — §08–§12  Enterprise + Best Practices +
                      Case Study + Comparison +
                      Common Mistakes
⬜ Chunk 8 — §13–§18  Exercises + Quiz + Debugging +
                      Next + Interview + Summary
────────────────────────────────────────────

```

---
<!-- NEXT: Chunk 7 — §08–§12 Enterprise, Best Practices,
     Case Study, Comparison, Common Mistakes -->