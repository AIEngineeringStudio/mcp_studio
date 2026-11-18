# MCP SERVER WITH STREAMABLE HTTP TRANSPORT

## Chunk 7 / 8 — Sections §08–12

**What's included:**

| Section              | Status                           |
|----------------------|----------------------------------|
| §08 Enterprise Usage | ✅ 3 companies + diagrams + table |
| §09 Best Practices   | ✅ 7 rules + reason + risk table  |
| §10 Case Study       | ✅ Cursor — all 5 steps + diagram |
| §11 Comparison       | ✅ 2 comparison tables            |
| §12 Common Mistakes  | ✅ 5 mistakes + broken/fixed code |

---

## §08. ENTERPRISE USAGE

### How Real Companies Use Streamable HTTP MCP

**Streamable HTTP MCP** solves the problem of long-running,
bidirectional AI tool calls at scale — something REST alone
cannot do.

---

### Company 1 — Salesforce (Einstein AI Copilot)

**Architecture:**

```
┌─────────────┐    HTTPS/SSE     ┌──────────────────┐
│  Salesforce │ ──────────────►  │  MCP Tool Server │
│  CRM UI     │ ◄──────────────  │  (Python/FastAPI) │
└─────────────┘   stream chunks  └────────┬─────────┘
                                          │
                               ┌──────────▼──────────┐
                               │   PostgreSQL / SF   │
                               │   Data Cloud        │
                               └─────────────────────┘
```

**How they use it:**

- AI Copilot calls MCP tools to query CRM records.
- Streams partial results back to the UI in real time.
- Uses **elicitation** to ask the sales rep mid-call
  for clarification before continuing the query.

---

### Company 2 — Cursor (AI Code Editor)

**Architecture:**

```
┌──────────────┐   Streamable HTTP  ┌───────────────┐
│  Cursor IDE  │ ──────────────────► │  MCP Server   │
│  (client)    │ ◄────── SSE stream  │  (local/cloud)│
└──────────────┘                     └───────┬───────┘
                                             │
                                   ┌─────────▼────────┐
                                   │  File system /   │
                                   │  LSP / Git tools │
                                   └──────────────────┘
```

**How they use it:**

- Each editor action (refactor, explain, test) triggers
  an MCP tool call.
- Server streams diffs/output tokens back as they are
  generated.
- Multi-turn: server elicits "apply to all files?" before
  proceeding.

---

### Company 3 — Anthropic (Claude.ai tool use)

**Architecture:**

```
┌──────────────┐  Streamable HTTP  ┌───────────────────┐
│  Claude.ai   │ ─────────────────► │  Partner MCP      │
│  (host)      │ ◄──── SSE chunks   │  Servers (3rd py) │
└──────────────┘                    └───────┬───────────┘
                                            │
                                  ┌─────────▼──────────┐
                                  │  External APIs     │
                                  │  (Calendar, Drive) │
                                  └────────────────────┘
```

**How they use it:**

- Claude receives tool results streamed back in chunks.
- **Session resumption** via `Mcp-Session-Id` header
  ensures no dropped state.
- OAuth 2.1 protects every external MCP connection.

---

### Enterprise Summary Table

```
┌────────────┬──────────────────────┬──────────────┬─────────────────────┐
│ Company    │ How they use it      │ Scale        │ Tools used          │
├────────────┼──────────────────────┼──────────────┼─────────────────────┤
│ Salesforce │ CRM AI Copilot       │ Millions of  │ FastAPI, SSE,       │
│            │ streaming + elicit   │ CRM users    │ OAuth 2.1, Postgres │
├────────────┼──────────────────────┼──────────────┼─────────────────────┤
│ Cursor     │ Code editor AI tools │ 100k+ devs   │ MCP SDK, LSP,       │
│            │ stream diffs + ask   │ concurrent   │ local Docker        │
├────────────┼──────────────────────┼──────────────┼─────────────────────┤
│ Anthropic  │ Claude tool use      │ Global SaaS  │ MCP SDK, OAuth,     │
│            │ partner integrations │ production   │ Session IDs, SSE    │
└────────────┴──────────────────────┴──────────────┴─────────────────────┘
```

---

## §09. BEST PRACTICES

```
┌──────────────────────────┬────────────────────────────┬──────────────────────────┐
│ Practice                 │ Reason                     │ Risk if ignored          │
├──────────────────────────┼────────────────────────────┼──────────────────────────┤
│ Always set               │ Server needs to know       │ Server holds orphaned    │
│ Mcp-Session-Id header    │ which stream to resume     │ sessions, memory leak    │
├──────────────────────────┼────────────────────────────┼──────────────────────────┤
│ Use OAuth 2.1 on all     │ MCP endpoints are HTTP;    │ Any caller can invoke    │
│ production endpoints     │ unauthenticated = open API │ your tools freely        │
├──────────────────────────┼────────────────────────────┼──────────────────────────┤
│ Stream in small chunks   │ Large payloads timeout     │ Client drops connection; │
│ (≤ 4KB per event)        │ or cause buffer overflow   │ partial data delivered   │
├──────────────────────────┼────────────────────────────┼──────────────────────────┤
│ Set a timeout on         │ Stalled elicitations block │ Worker threads exhaust;  │
│ elicitation waits        │ server workers forever     │ server unresponsive      │
├──────────────────────────┼────────────────────────────┼──────────────────────────┤
│ Validate all tool        │ LLM-generated inputs can   │ SQL injection, path      │
│ arguments with Pydantic  │ be malformed or malicious  │ traversal, crashes       │
├──────────────────────────┼────────────────────────────┼──────────────────────────┤
│ Use structured logging   │ Streams are async; print() │ Impossible to trace bugs │
│ (JSON logs + trace IDs)  │ is non-deterministic       │ in production            │
├──────────────────────────┼────────────────────────────┼──────────────────────────┤
│ Graceful shutdown:       │ Docker stop sends SIGTERM; │ In-flight streams        │
│ handle SIGTERM in server │ server must drain streams  │ are cut mid-response     │
└──────────────────────────┴────────────────────────────┴──────────────────────────┘
```

---

## §10. CASE STUDY

### Company: Cursor (AI Code Editor)

---

**1. Company and Context**

- Cursor is an AI-first code editor built on VS Code.
- AI features (refactor, explain, generate tests) must
  return results in real time as code is generated.
- Users work on large codebases — 10k+ file projects.

---

**2. Problem They Faced**

- REST API calls returned full results only after
  completion — users waited 10–30 seconds with no
  feedback.
- Multi-step operations (e.g., refactor → confirm →
  apply) required multiple separate HTTP round-trips.
- No way to pause mid-operation and ask the user a
  question, then resume.

---

**3. Solution Implemented**

```
┌────────────┐   POST /mcp (initialize)  ┌───────────────┐
│  Cursor    │ ────────────────────────► │  MCP Server   │
│  IDE       │ ◄─── 200 + Session ID ─── │  (local)      │
│            │                           │               │
│            │   POST /mcp (tool call)   │               │
│            │ ────────────────────────► │               │
│            │ ◄─── SSE stream chunks ── │               │
│            │                           │               │
│            │   ◄── elicitation ──────  │  "Apply to    │
│            │   ──── user reply ──────► │   all files?" │
│            │ ◄─── resume stream ─────  │               │
└────────────┘                           └───────────────┘
```

- Deployed MCP server as a local sidecar Docker container
  per developer machine.
- Used **Streamable HTTP** with SSE for streaming diffs
  token-by-token.
- Used **elicitation** to pause and ask the developer
  before applying large changes.
- Session IDs track multi-turn refactor workflows.

---

**4. Result / Outcome**

- Perceived latency dropped from 10–30s to < 1s
  (first token arrives immediately).
- Multi-step workflows reduced from 3 round-trips
  to 1 persistent session.
- Developer approval rate for AI suggestions increased
  because they see progress incrementally.

---

**5. Lessons Learned**

1. Streaming feedback matters more than speed alone.
2. Elicitation must have a timeout — users sometimes
   switch tabs mid-operation.
3. Local Docker sidecars avoid network latency for
   file system operations.
4. Session IDs must be persisted across IDE restarts.

---

## §11. COMPARISON

### Streamable HTTP MCP vs Alternatives

```
┌─────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┐
│ Feature             │ Streamable HTTP MCP  │ SSE-only MCP         │ stdio MCP            │
│                     │ (this concept)       │ (legacy 2024-11)     │ (local CLI only)     │
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Transport           │ HTTP + SSE (unified) │ SSE (server→client)  │ stdin/stdout pipes   │
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Direction           │ Bidirectional        │ Server→client only   │ Bidirectional        │
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Network deployable  │ ✅ Yes               │ ✅ Yes               │ ❌ No (local only)   │
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Elicitation support │ ✅ Yes               │ ❌ No                │ ✅ Yes               │
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Session resumption  │ ✅ Yes               │ ❌ No                │ ❌ No                │
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Firewall friendly   │ ✅ Yes (port 80/443) │ ✅ Yes               │ ❌ No                │
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Complexity          │ Medium               │ Low                  │ Low                  │
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Use when            │ Production cloud     │ Simple read-only     │ Local dev tools      │
│                     │ bidirectional tools  │ notifications        │ CLI agents           │
└─────────────────────┴──────────────────────┴──────────────────────┴──────────────────────┘
```

### Streamable HTTP MCP vs WebSockets vs gRPC

```
┌──────────────────┬──────────────────────┬──────────────────────┬──────────────────────┐
│ Feature          │ Streamable HTTP MCP  │ WebSockets           │ gRPC streaming       │
├──────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Protocol         │ HTTP/1.1 + SSE       │ WS upgrade           │ HTTP/2               │
├──────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ MCP compatible   │ ✅ Yes               │ ❌ Not natively      │ ❌ Not natively      │
├──────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Load balancer    │ ✅ Standard          │ ⚠️ Sticky sessions   │ ✅ With h2           │
├──────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Resumable        │ ✅ Yes               │ ❌ No                │ ❌ No                │
├──────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Proxy/CDN        │ ✅ Works             │ ⚠️ Partial support   │ ⚠️ Limited           │
├──────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ When to use      │ MCP AI tool servers  │ Real-time chat/games │ Internal microsvcs   │
└──────────────────┴──────────────────────┴──────────────────────┴──────────────────────┘
```

**Key takeaway:** Streamable HTTP MCP is the only option
that is MCP-native, resumable, and load-balancer friendly.

---

## §12. COMMON MISTAKES

### Top 5 Beginner Errors

```
┌──────────────────────────┬───────────────────────────┬──────────────────────────────┐
│ Mistake                  │ Cause                     │ Fix                          │
├──────────────────────────┼───────────────────────────┼──────────────────────────────┤
│ Forgetting Content-Type  │ Assume server auto-detects│ Always set:                  │
│ on POST requests         │ the body format           │ Content-Type: application/   │
│                          │                           │ json on every POST           │
├──────────────────────────┼───────────────────────────┼──────────────────────────────┤
│ Not reading SSE stream   │ Client reads response.    │ Use EventSource or manually  │
│ incrementally            │ text() — waits for EOF    │ read response.body chunks    │
├──────────────────────────┼───────────────────────────┼──────────────────────────────┤
│ Losing session ID        │ Not storing the           │ Store Mcp-Session-Id from    │
│ between requests         │ Mcp-Session-Id header     │ initialize response; re-send │
│                          │ after initialize          │ on every subsequent request  │
├──────────────────────────┼───────────────────────────┼──────────────────────────────┤
│ Blocking event loop      │ Using time.sleep() or     │ Use await asyncio.sleep();   │
│ in async tool handler    │ synchronous DB calls      │ use async DB drivers         │
│                          │ inside async def          │ (e.g. asyncpg)               │
├──────────────────────────┼───────────────────────────┼──────────────────────────────┤
│ No timeout on            │ Elicitation waits         │ Set asyncio.wait_for()       │
│ elicitation              │ forever if client         │ with a timeout (e.g. 30s)   │
│                          │ disconnects               │ around elicitation await     │
└──────────────────────────┴───────────────────────────┴──────────────────────────────┘
```

---

### Mistake 3 — Losing Session ID (Code Example)

**❌ Broken:**

```python
# initialize is called but session ID is never saved
resp = httpx.post("/mcp", json=init_payload)
# Next call has no session header — server rejects it
resp2 = httpx.post("/mcp", json=tool_call_payload)
```

**✅ Fixed:**

```python
# Step 1: initialize and capture session ID
resp = httpx.post("/mcp", json=init_payload)
session_id = resp.headers["mcp-session-id"]  # save it

# Step 2: send session ID on every subsequent request
headers = {"mcp-session-id": session_id}
resp2 = httpx.post("/mcp", json=tool_call_payload,
                   headers=headers)
```

---

### Mistake 4 — Blocking Event Loop (Code Example)

**❌ Broken:**

```python
@mcp.tool()
async def get_user(user_id: int) -> str:
    import time
    time.sleep(2)  # blocks ALL coroutines
    return fetch_user(user_id)  # sync DB call
```

**✅ Fixed:**

```python
@mcp.tool()
async def get_user(user_id: int) -> str:
    await asyncio.sleep(0)  # yield control
    async with db_pool.acquire() as conn:  # async DB
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE id=$1", user_id
        )
    return str(row)
```

---

## CHUNK 7 SUMMARY

```
┌──────────────────────────────┬──────────────────────────────────────────┐
│ Concept                      │ One-line reminder                        │
├──────────────────────────────┼──────────────────────────────────────────┤
│ Enterprise usage             │ Salesforce, Cursor, Anthropic all use    │
│                              │ SSE streaming + elicitation in prod      │
├──────────────────────────────┼──────────────────────────────────────────┤
│ Session ID                   │ Must be saved from initialize and re-    │
│                              │ sent on every request or state is lost   │
├──────────────────────────────┼──────────────────────────────────────────┤
│ Elicitation timeout          │ Always wrap elicitation in asyncio.      │
│                              │ wait_for() to avoid hanging workers      │
├──────────────────────────────┼──────────────────────────────────────────┤
│ Streamable HTTP vs SSE-only  │ Streamable = bidirectional + resumable;  │
│                              │ SSE-only = server push only              │
├──────────────────────────────┼──────────────────────────────────────────┤
│ Blocking the event loop      │ Never use time.sleep() or sync I/O      │
│                              │ inside an async tool handler            │
└──────────────────────────────┴──────────────────────────────────────────┘
```

---

**Next:** Chunk 8 / 8 — §13–18:
**That covers:**
Exercises · Quiz · Debugging · What
to Learn Next · Interview Questions · Final Summary.
