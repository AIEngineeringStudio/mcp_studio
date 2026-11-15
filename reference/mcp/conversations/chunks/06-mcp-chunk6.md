# MCP Tutorial — Chunk 6 of 8

## CHUNKS GENERATED: [6 / 8]

## ACTIVE CHUNK: [6 / 8]

## SECTIONS IN THIS CHUNK: [§11, §12, §13]

---

## §11. COMPARISON

MCP compared to two related integration protocols.

**Alternatives compared:**

- **REST API** — standard HTTP request/response interface
- **OpenAPI / Function Calling** — LLM tool schema via JSON spec

---

### Comparison Table

```
┌──────────────────┬──────────────────────┬──────────────────┬──────────────────┐
│ Feature          │ MCP                  │ REST API         │ Function Calling │
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ Protocol         │ JSON-RPC 2.0 over    │ HTTP             │ LLM-native JSON  │
│                  │ stdio / SSE          │                  │ schema           │
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ Discovery        │ Built-in (list_tools)│ Manual / OpenAPI │ Manual schema    │
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ LLM awareness    │ Native — LLM reads   │ None by default  │ Native           │
│                  │ tool schemas auto    │                  │                  │
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ Transport        │ stdio, SSE, HTTP     │ HTTP only        │ In-memory / HTTP │
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ State / sessions │ Stateful sessions    │ Stateless        │ Stateless        │
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ Auth             │ Per-transport        │ OAuth, API keys  │ No standard      │
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ Streaming        │ Native SSE support   │ Manual SSE / WS  │ Token streaming  │
│                  │                      │                  │ only             │
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ Schema format    │ JSON Schema per tool │ OpenAPI YAML/    │ JSON Schema per  │
│                  │                      │ JSON             │ function         │
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ Portability      │ Any MCP client       │ Any HTTP client  │ Vendor-locked    │
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ Multi-tool batch │ Yes (one session)    │ No               │ Parallel calls   │
│                  │                      │                  │ (model-dependent)│
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ Pros             │ LLM-native, portable,│ Universal, simple│ Tight LLM        │
│                  │ tool discovery auto  │ tooling, mature  │ integration      │
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ Cons             │ Newer ecosystem,     │ No LLM awareness,│ Vendor-locked,   │
│                  │ fewer tools/clients  │ manual schema    │ no portability   │
├──────────────────┼──────────────────────┼──────────────────┼──────────────────┤
│ When to use      │ LLM agents needing   │ General APIs,    │ Single-vendor    │
│                  │ pluggable tools      │ non-LLM systems  │ LLM projects     │
└──────────────────┴──────────────────────┴──────────────────┴──────────────────┘
```

---

### Decision Flow

```
Need LLM to call tools?
        │
        ▼
  Portability needed?
   ┌────┴────┐
  YES       NO
   │         │
   ▼         ▼
  MCP    OpenAI
         Function
         Calling
         
Already have REST APIs + no LLM?
        │
        ▼
   Use REST API
   (wrap in MCP server later if needed)
```

---

## §12. COMMON MISTAKES

### Mistake 1 — Forgetting to return `isError: true` on tool failure

**What:** Raising a Python exception inside a tool handler instead
of returning a structured error response.

**Why it happens:** Developers treat MCP tools like regular
functions.

**How to fix:** Always catch exceptions and return:

```python
return [TextContent(
    type="text",
    text=f"Error: {str(e)}"
)], True  # second value = isError flag
```

---

### Mistake 2 — Blocking the event loop in async handlers

**What:** Calling `time.sleep()` or a synchronous DB call inside
an `async def` tool handler.

**Why it happens:** Mixing sync and async code without awareness.

**How to fix:** Use `await asyncio.sleep()` and async DB drivers
(e.g., `asyncpg`, `databases`).

```python
# WRONG
@server.call_tool()
async def handle(name, args):
    time.sleep(2)  # blocks event loop


# CORRECT
@server.call_tool()
async def handle(name, args):
    await asyncio.sleep(2)
```

---

### Mistake 3 — Not validating tool input arguments

**What:** Trusting that the LLM passes correct argument types.

**Why it happens:** LLMs can hallucinate or mis-type arguments.

**How to fix:** Use **Pydantic** models to validate all inputs.

```python
from pydantic import BaseModel


class QueryArgs(BaseModel):
    table: str
    limit: int = 10


args = QueryArgs(**raw_args)  # raises ValidationError if bad
```

---

### Mistake 4 — Exposing secrets in tool descriptions

**What:** Putting API keys, DB URLs, or internal paths in tool
`description` fields that the LLM reads.

**Why it happens:** Descriptions are set at server startup where
config is accessible.

**How to fix:** Keep descriptions generic. Load secrets via
environment variables only inside handler logic.

```python
# WRONG
description = "Query DB at postgres://user:pass@host/db"

# CORRECT
description = "Query the application database for records."
```

---

### Mistake 5 — Using stdio transport in production

**What:** Running an MCP server with `stdio` transport in a
Docker/cloud environment.

**Why it happens:** stdio is the default in most quickstart docs.

**How to fix:** Use **SSE** or **Streamable HTTP** transport for
networked / multi-client deployments.

```python
# WRONG for production
mcp.run(transport="stdio")

# CORRECT for production
uvicorn.run(app, host="0.0.0.0", port=8000)
# (FastAPI + SSE transport)
```

---

### Mistakes Summary Table

```
┌───────────────────────┬────────────────────────────┬─────────────────────────┐
│ Mistake               │ Cause                      │ Fix                     │
├───────────────────────┼────────────────────────────┼─────────────────────────┤
│ No isError on failure │ Treating tool like a        │ Return isError=True      │
│                       │ regular function            │ with error message       │
├───────────────────────┼────────────────────────────┼─────────────────────────┤
│ Blocking event loop   │ Mixing sync/async code      │ Use await + async libs  │
├───────────────────────┼────────────────────────────┼─────────────────────────┤
│ No input validation   │ Trusting LLM arg types      │ Validate with Pydantic  │
├───────────────────────┼────────────────────────────┼─────────────────────────┤
│ Secrets in tool desc  │ Config accessible at        │ Keep descriptions       │
│                       │ server startup              │ generic; use env vars   │
├───────────────────────┼────────────────────────────┼─────────────────────────┤
│ stdio in production   │ Default from quickstart     │ Use SSE / HTTP          │
│                       │ docs                        │ transport               │
└───────────────────────┴────────────────────────────┴─────────────────────────┘
```

---

## §13. PRACTICE EXERCISES

---

### Easy — Build a single-tool MCP server

**Task:**
Build an MCP server with one tool: `get_current_time`.
The tool takes no arguments and returns the current UTC time
as a string.

**Constraints / Requirements:**

- Use Python + `mcp` SDK
- Use SSE transport via FastAPI + uvicorn
- Run inside Docker
- Use structured logging (`structlog`)
- Tool must return ISO 8601 format: `2025-01-15T10:30:00Z`

**What a correct solution looks like:**

```
MCP client calls: get_current_time()
Server returns:   {"time": "2025-01-15T10:30:00Z"}
Log output:       {"event": "tool_called", "tool": "get_current_time"}
Docker container: starts, exposes port 8000
```

---

### Medium — Multi-tool MCP server with PostgreSQL

**Task:**
Build an MCP server with 3 tools backed by a PostgreSQL database:

1. `list_tables` — returns all table names in the DB
2. `describe_table` — takes `table_name`, returns column info
3. `run_select` — takes `table_name` + optional `limit`,
   returns rows as JSON

**Constraints / Requirements:**

- Use `asyncpg` for async DB access
- Use **Ports and Adapters** pattern for DB layer
- Use Pydantic to validate all tool arguments
- Return `isError: True` on DB errors
- Run in Docker Compose (MCP server + PostgreSQL)
- Use Nginx as reverse proxy in front of uvicorn
- Use structured logging with request IDs

**What a correct solution looks like:**

```
list_tables()       → ["users", "orders", "products"]
describe_table(     → [{"col":"id","type":"int"},
  table_name="users")  {"col":"email","type":"varchar"}]
run_select(         → [{"id":1,"email":"a@b.com"},...]
  table_name="users",
  limit=5)
```

---

### Hard — Agent-powered MCP gateway with LiteLLM routing

**Task:**
Build a production-grade MCP gateway that:

1. Exposes multiple MCP servers behind one FastAPI gateway
2. Uses OpenAI Agent SDK to orchestrate tool calls
3. Routes LLM calls through **LiteLLM** (default: OpenAI GPT-4o;
   fallback: Anthropic Claude)
4. Persists all tool call logs to PostgreSQL
5. Enforces per-tool rate limiting (max 10 calls/min/tool)
6. Supports health checks per downstream MCP server
7. Runs in Docker Compose with Nginx, uvicorn, PostgreSQL

**Constraints / Requirements:**

- Clean Architecture: domain / application / infrastructure layers
- Ports and Adapters for all DB and MCP server calls
- Structured logging with correlation IDs on every request
- Config via environment variables only (no hardcoded values)
- Full Docker Compose setup with `docker-compose up` working

**What a correct solution looks like:**

```
POST /agent/run  {"prompt": "List all users from the DB"}
  → Agent calls: run_select(table_name="users")
  → Returns: [{"id":1,...}, ...]
  → DB log entry created with tool name, args, result, latency

GET /health
  → {"gateway": "ok", "mcp_servers": {"db_server": "ok"}}

Rate limit exceeded:
  → 429 Too Many Requests
  → {"error": "Rate limit exceeded for tool: run_select"}
```

---

🔑 **Jargon Summary — Chunk 6**

| Term                   | Definition                                              |
|------------------------|---------------------------------------------------------|
| **isError**            | MCP flag returned with tool result to signal failure    |
| **stdio transport**    | Process-level communication via stdin/stdout            |
| **SSE transport**      | Server-Sent Events over HTTP for real-time streaming    |
| **Ports and Adapters** | Pattern isolating business logic from infrastructure    |
| **LiteLLM**            | Library for routing calls across multiple LLM providers |
| **Pydantic**           | Python library for data validation using type hints     |
| **asyncpg**            | Async PostgreSQL driver for Python                      |
| **correlation ID**     | Unique ID attached to a request for tracing across logs |
| **rate limiting**      | Throttling requests to prevent abuse or overload        |

---

> ✅ Chunk 6 complete. Next: Chunk 7 → §14 (Check Understanding),
> §15 (Debugging), §16 (What to Learn Next)