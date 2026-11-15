# PERSONAL AI ASSISTANT — INCREMENTAL BUILD PLAN

## Exercises every concept from all 8 MCP chunks

---

## PROJECT GOAL

```
Build an AI agent that:
  1. Reads local files      → MCP Filesystem Server
  2. Queries PostgreSQL     → MCP Database Server
  3. Sends email summaries  → MCP Email Server
  4. All behind FastAPI     → MCP Gateway
  5. Nginx reverse proxy    → Load balancing / routing
  6. Docker Compose         → Full local environment
```

---

## CONCEPT COVERAGE MAP

```
┌──────────┬──────────────────────────┬────────────────────┐
│ Chunk    │ Concept                  │ Covered In Phase   │
├──────────┼──────────────────────────┼────────────────────┤
│ §00–§02  │ MCP definition, terms    │ Phase 1            │
│ §03–§04  │ Architecture, lifecycle  │ Phase 1 + 2        │
│ §05–§06  │ Basic + intermediate     │ Phase 2 + 3        │
│ §07      │ Advanced (sec/scale/rel) │ Phase 4 + 5        │
│ §08–§10  │ Enterprise patterns      │ Phase 5 + 6        │
│ §11–§13  │ Comparison, mistakes     │ Phase 3 + 4        │
│ §14–§16  │ Debug, practice          │ Phase 6            │
│ §17–§18  │ Interview, summary       │ Phase 7 (review)   │
└──────────┴──────────────────────────┴────────────────────┘
```

---

## 7-PHASE INCREMENTAL BUILD

**What this gives you:**

7 phases. Each phase adds one layer to the same codebase. Nothing is thrown
away — you build incrementally.

**Why 7 phases and not 8 chunks:**

The chunks were teaching theory. The phases map theory to working code. Phase 7
has no new code — it is pure review against your own system.

**Every concept from every chunk is exercised:**

| Phase | Hardest concept it exercises                |
|-------|---------------------------------------------|
| 1     | MCP lifecycle, SSE transport                |
| 2     | Ports & Adapters, asyncpg, ToolError        |
| 3     | Multi-server agent, LiteLLM routing         |
| 4     | Gateway routing, auth middleware            |
| 5     | Circuit breaker, rate limiting, Redis       |
| 6     | OTEL traces, correlation IDs, health checks |
| 7     | Interview-level system design questions     |

**To begin, reply:**

```
Start Phase 1
```

---

### PHASE 1 — Skeleton + Filesystem MCP Server

**What you build:** One MCP server, one tool, Docker running.

```
Concepts exercised:
  §00 Prerequisites
  §01 MCP definition
  §02 Why it matters
  §03 Architecture (Client / Server / Transport)
  §04 Lifecycle (initialize → tools/call → shutdown)
```

**Deliverable:**

```
mcp-assistant/
├── docker-compose.yml
├── nginx/nginx.conf
├── servers/
│   └── filesystem/       ← MCP server: read_file tool
└── gateway/              ← FastAPI stub (health only)
```

**Verify:** Agent calls `read_file("notes.txt")` → returns
file contents.

---

### PHASE 2 — Database MCP Server + Ports & Adapters

**What you build:** Second MCP server, PostgreSQL, clean arch.

```
Concepts exercised:
  §05 Basic example (new tool, Docker, SSE transport)
  §06 Intermediate (Ports & Adapters, ToolError, asyncpg)
  §03 Resources (expose DB tables as MCP resources)
```

**Deliverable:**

```
servers/
├── filesystem/
└── database/             ← MCP server: run_query tool
    ├── domain/           ← entities
    ├── application/      ← use cases
    └── infrastructure/   ← asyncpg adapter (Ports/Adapters)
```

**Verify:** Agent calls `run_query("SELECT * FROM notes")`
→ returns rows as JSON.

---

### PHASE 3 — Email MCP Server + LiteLLM routing

**What you build:** Third MCP server, LiteLLM, multi-tool agent.

```
Concepts exercised:
  §05 Multi-server agent setup
  §06 Edge cases (tool not found, timeout, retry)
  §11 Comparison (MCP vs REST vs Function Calling)
```

**Deliverable:**

```
servers/
├── filesystem/
├── database/
└── email/                ← MCP server: send_email tool
agent/
└── agent.py              ← OpenAI Agent SDK + LiteLLM
```

**Verify:** Agent reads file → queries DB → sends email
summary in one prompt.

---

### PHASE 4 — FastAPI Gateway + Nginx Routing

**What you build:** Central gateway, request routing, logging.

```
Concepts exercised:
  §06 Gateway pattern
  §07 Security (Bearer auth middleware)
  §07 Optimization (async, connection pooling)
  §12 Common mistakes (missing Content-Type, no auth)
```

**Deliverable:**

```
gateway/
├── main.py               ← FastAPI entry point
├── routers/              ← /filesystem /database /email
├── middleware/           ← BearerAuthMiddleware
└── logging_cfg.py        ← structlog JSON logging
```

**Verify:**

```
POST /gateway/agent/run
  {"prompt": "Summarize notes.txt and email it to me"}
→ 200 OK  {"result": "Email sent."}
```

---

### PHASE 5 — Enterprise Hardening

**What you build:** Rate limiting, circuit breaker, retries.

```
Concepts exercised:
  §07 Security (mTLS, OAuth, rate limiting)
  §07 Reliability (circuit breaker, retries, replication)
  §07 Scaling (load balancing, Redis cache)
  §08 Enterprise patterns
  §09 Best practices
```

**Deliverable:**

```
gateway/
├── middleware/
│   ├── auth.py           ← Bearer + OAuth
│   ├── rate_limit.py     ← per-tool throttle (Redis)
│   └── circuit_breaker.py
infrastructure/
└── redis/                ← cache + rate limit state
```

**Verify:**

```
> 10 calls/min to same tool → 429 Too Many Requests
Circuit breaker open       → 503 Service Unavailable
```

---

### PHASE 6 — Observability + Debugging

**What you build:** Structured logs, OTEL traces, health checks.

```
Concepts exercised:
  §07 Optimization (bottleneck identification)
  §08 Enterprise (OTEL, audit trail, monitoring)
  §09 Best practices (correlation IDs, health checks)
  §15 Debugging (5 common bugs, fixed)
  §16 What to learn next
```

**Deliverable:**

```
gateway/
└── tracing.py            ← OTEL + structlog correlation ID
servers/*/
└── health.py             ← /health endpoint per server
docker-compose.yml        ← Jaeger for trace visualization
```

**Verify:**

```
GET /health
→ {"gateway": "ok", "filesystem": "ok",
   "database": "ok", "email": "ok"}

Every request log shows: correlation_id, tool_name,
latency_ms, status
```

---

### PHASE 7 — Review + Interview Prep

**What you do:** No new code. Trace through the full system
and answer the §14 and §17 questions against your own code.

```
Concepts exercised:
  §14 Check Understanding (5 questions)
  §17 Interview questions (all 4 levels)
  §18 Summary (all jargon, key concepts)
```

**Exercise:**

1. Draw the full system diagram from memory.
2. Answer: "What happens if the DB MCP server crashes
   while the agent is mid-call?"
3. Answer: "How would you add a 4th MCP server without
   changing the gateway?"

---

## FULL FINAL ARCHITECTURE

```
                    ┌──────────────┐
                    │   Client     │
                    │ (curl / app) │
                    └──────┬───────┘
                           │ HTTPS
                    ┌──────▼───────┐
                    │    Nginx     │
                    │ reverse proxy│
                    └──────┬───────┘
                           │ HTTP
                    ┌──────▼───────┐
                    │  FastAPI     │
                    │  Gateway     │◄── BearerAuth
                    │  :8000       │◄── RateLimit (Redis)
                    │              │◄── CircuitBreaker
                    │              │◄── CorrelationID log
                    └──┬───┬───┬───┘
                       │   │   │  SSE / stdio
          ┌────────────┘   │   └────────────┐
          ▼                ▼                ▼
  ┌───────────────┐ ┌─────────────┐ ┌──────────────┐
  │  Filesystem   │ │  Database   │ │   Email      │
  │  MCP Server   │ │  MCP Server │ │  MCP Server  │
  │  :8001        │ │  :8002      │ │  :8003       │
  └───────────────┘ └──────┬──────┘ └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  PostgreSQL  │
                    │  :5432       │
                    └──────────────┘
                           │
                    ┌──────▼───────┐
                    │    Redis     │
                    │  :6379       │
                    └──────────────┘
```

---

## PHASE SUMMARY

```
┌─────────┬──────────────────────────────┬───────────────┐
│ Phase   │ What you build               │ Chunks used   │
├─────────┼──────────────────────────────┼───────────────┤
│ 1       │ Filesystem MCP + Docker      │ §00–§04       │
│ 2       │ DB MCP + Ports & Adapters    │ §05–§06       │
│ 3       │ Email MCP + multi-tool agent │ §06, §11      │
│ 4       │ FastAPI gateway + Nginx      │ §06–§07, §12  │
│ 5       │ Rate limit + circuit breaker │ §07–§09       │
│ 6       │ OTEL + health + debugging    │ §08–§10, §15  │
│ 7       │ Review + interview prep      │ §14, §17–§18  │
└─────────┴──────────────────────────────┴───────────────┘
```

---

## HOW TO START

Reply with:

```
"Start Phase 1"
```

Each phase will deliver:

1. Full working code
2. Step-by-step instructions
3. Expected output
4. Inline comments on every line
5. Flow diagram of the phase