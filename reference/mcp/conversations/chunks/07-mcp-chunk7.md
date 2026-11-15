# MCP TUTORIAL — CHUNK 7 OF 8

## SECTIONS: §14 CHECK UNDERSTANDING · §15 DEBUGGING · §16 WHAT TO LEARN NEXT

---

## §14. CHECK UNDERSTANDING

Answer each question before moving to §15.

---

**Q1 — Definition**

> What is the difference between an MCP **Tool** and an MCP **Resource**?
> When would you use each one?

---

**Q2 — Mechanism**

> Trace the exact message flow when an LLM agent calls an MCP tool
> named `search_documents` hosted on a remote MCP server.
>
> List every step: from the agent deciding to call the tool,
> to the agent receiving the result.

---

**Q3 — Application**

> You are building an enterprise assistant that must:
> - Read files from S3
> - Query a PostgreSQL database
> - Send a Slack notification
>
> How would you structure this as an MCP system?
> Name the servers, tools, and transports you would use.

---

**Q4 — Trade-offs**

> Compare **stdio transport** vs **SSE transport** for MCP.
>
> - When is stdio the right choice?
> - When does SSE become necessary?
> - What breaks if you use stdio in a multi-user production system?

---

**Q5 — Scenario-based**

> Your MCP server is deployed in Docker behind an Nginx reverse proxy.
> An agent sends a tool call. The call never returns.
> No error is shown in the agent logs.
>
> List 5 specific places you would check to diagnose the issue,
> in order of most likely cause.

---

## §15. DEBUGGING

### 5 Most Common MCP Bugs

```
┌──────────────────────┬────────────────────────┬──────────────────────────────┬──────────────────────────────────┐
│ Bug                  │ Cause                  │ Error Message                │ Fix                              │
├──────────────────────┼────────────────────────┼──────────────────────────────┼──────────────────────────────────┤
│ Tool not found       │ Tool not registered    │ Tool 'x' not found           │ Add @mcp.tool() decorator;       │
│                      │ in server              │                              │ verify server started            │
├──────────────────────┼────────────────────────┼──────────────────────────────┼──────────────────────────────────┤
│ Schema mismatch      │ Agent sends wrong      │ ValidationError: field       │ Match Pydantic model to          │
│                      │ param types            │ required / wrong type        │ tool signature exactly           │
├──────────────────────┼────────────────────────┼──────────────────────────────┼──────────────────────────────────┤
│ SSE connection drops │ Nginx proxy timeout    │ Connection reset /           │ Set proxy_read_timeout 3600s     │
│                      │ on idle streams        │ 504 Gateway Timeout          │ in Nginx config                  │
├──────────────────────┼────────────────────────┼──────────────────────────────┼──────────────────────────────────┤
│ DB connection pool   │ Too many concurrent    │ TimeoutError: QueuePool      │ Tune pool_size, max_overflow     │
│ exhausted            │ tool calls             │ limit overflow               │ in SQLAlchemy engine             │
├──────────────────────┼────────────────────────┼──────────────────────────────┼──────────────────────────────────┤
│ Tool returns None    │ Missing return         │ No error — agent hangs       │ Always return a value;           │
│                      │ statement in handler   │ or gets null result          │ add return type annotation       │
└──────────────────────┴────────────────────────┴──────────────────────────────┴──────────────────────────────────┘
```

---

### Bug 1 — Tool Not Registered

**Broken:**

```python
# server.py

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("demo-server")


# ❌ Missing @mcp.tool() decorator — tool never registers
def search_documents(query: str) -> str:
    return f"Results for: {query}"
```

**Fixed:**

```python
# server.py

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("demo-server")


# ✅ Decorator registers the tool with the MCP server
@mcp.tool()
def search_documents(query: str) -> str:
    """Search internal documents by query string."""
    return f"Results for: {query}"
```

**Why it happens:**
FastMCP only knows about tools that are explicitly decorated.
Without `@mcp.tool()`, the function is invisible to the protocol.

---

### Bug 2 — Schema Mismatch

**Broken:**

```python
# Agent sends: {"query": 123, "limit": "ten"}
# Tool expects: query: str, limit: int

@mcp.tool()
def search_documents(query: str, limit: int) -> str:
    # ❌ Pydantic will raise ValidationError
    #    because agent sent wrong types
    return f"{query[:limit]}"
```

**Fixed:**

```python
from pydantic import BaseModel


# ✅ Define explicit input model with type coercion
class SearchInput(BaseModel):
    query: str  # will coerce int → str if needed
    limit: int  # will coerce "10" → 10 if needed


@mcp.tool()
def search_documents(input: SearchInput) -> str:
    return f"{input.query[:input.limit]}"
```

**Why it happens:**
LLMs generate JSON arguments. Type coercion is not guaranteed.
Always validate with Pydantic models.

---

### Bug 3 — SSE Connection Drops (Nginx Timeout)

**Broken Nginx config:**

```nginx
# nginx.conf

location /mcp/ {
    proxy_pass http://mcp_server:8000/;
    # ❌ Default timeout is 60s
    # SSE connections are long-lived — they time out
}
```

**Fixed:**

```nginx
# nginx.conf

location /mcp/ {
    proxy_pass http://mcp_server:8000/;

    # ✅ Keep SSE connections alive for up to 1 hour
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;

    # ✅ Required for SSE streaming — disable buffering
    proxy_buffering off;

    # ✅ Set correct headers for event stream
    proxy_set_header Connection '';
    proxy_http_version 1.1;
}
```

**Why it happens:**
Nginx default proxy timeout is 60 seconds.
SSE streams stay open indefinitely — Nginx kills them silently.

---

### Bug 4 — DB Connection Pool Exhausted

**Broken:**

```python
# database.py

from sqlalchemy import create_engine

# ❌ Default pool_size=5, max_overflow=10
# Under load, all connections are consumed
engine = create_engine("postgresql+asyncpg://user:pass@db/mydb")
```

**Fixed:**

```python
# database.py

from sqlalchemy.ext.asyncio import create_async_engine

# ✅ Tune pool for concurrent tool call load
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@db/mydb",
    pool_size=20,  # base connections kept open
    max_overflow=40,  # extra connections allowed under burst
    pool_timeout=30,  # seconds to wait before raising error
    pool_recycle=1800,  # recycle connections every 30 min
)
```

**Why it happens:**
Each concurrent tool call acquires a DB connection.
Default pool is too small for production workloads.

---

### Bug 5 — Tool Returns None (Agent Hangs)

**Broken:**

```python
@mcp.tool()
def get_user(user_id: int):  # ❌ No return type annotation
    user = db.query(User).get(user_id)
    if user:
        return user.name
    # ❌ No return for the None case — returns None implicitly
```

**Fixed:**

```python
@mcp.tool()
def get_user(user_id: int) -> str:  # ✅ Explicit return type
    user = db.query(User).get(user_id)
    if user:
        return user.name
    # ✅ Always return a value — never None
    return f"User {user_id} not found"
```

**Why it happens:**
MCP protocol expects a serializable result.
`None` breaks JSON serialization or causes the agent to stall
waiting for a valid response.

---

## §16. WHAT TO LEARN NEXT

```
┌──────────────────────────┬────────────────────────────────────────┬─────────────────┐
│ Next Topic               │ Why it matters                         │ Difficulty      │
├──────────────────────────┼────────────────────────────────────────┼─────────────────┤
│ OpenAI Agents SDK        │ MCP tools are consumed by agents.      │ Intermediate    │
│ (multi-agent systems)    │ Learn how to orchestrate multiple      │                 │
│                          │ agents that share MCP servers.         │                 │
├──────────────────────────┼────────────────────────────────────────┼─────────────────┤
│ LangGraph / LangChain    │ Production agent frameworks that       │ Intermediate    │
│                          │ integrate with MCP natively.           │ → Advanced      │
│                          │ Learn stateful agent workflows.        │                 │
├──────────────────────────┼────────────────────────────────────────┼─────────────────┤
│ Vector Databases         │ MCP Resources often serve semantic     │ Intermediate    │
│ (pgvector, Qdrant)       │ search results. Learn how embeddings   │                 │
│                          │ and vector search power agent memory.  │                 │
└──────────────────────────┴────────────────────────────────────────┴─────────────────┘
```

---

### Tools / Platforms to Practice

1. **Claude Desktop** — Connect local MCP servers via stdio.
   Test tool calls interactively without writing an agent.

2. **LangSmith** — Trace agent + MCP tool call chains.
   Debug what the LLM sent and what the server returned.

---

### Project to Build

**"Personal AI Assistant with MCP Backend"**

Build an agent that:

1. Reads your local files via an MCP **Filesystem server**
2. Queries a PostgreSQL DB via an MCP **Database server**
3. Sends email summaries via an MCP **Email server**
4. Exposes all servers behind a FastAPI gateway + Nginx
5. Runs entirely in Docker Compose

This project covers: MCP servers, transports, tool design,
gateway routing, Docker networking, and agent integration.

---

## CHUNK STATUS

```
┌───────┬───────────────────┬──────────┐
│ Chunk │ Sections          │ Status   │
├───────┼───────────────────┼──────────┤
│   1   │ §00 – §02         │ ✅ Done  │
│   2   │ §03 – §04         │ ✅ Done  │
│   3   │ §05 – §06         │ ✅ Done  │
│   4   │ §07               │ ✅ Done  │
│   5   │ §08 – §10         │ ✅ Done  │
│   6   │ §11 – §13         │ ✅ Done  │
│   7   │ §14 – §16         │ ✅ Done  │
│   8   │ §17 – §18         │ ⏳ Next  │
└───────┴───────────────────┴──────────┘
```

---

## 🔑 JARGON SUMMARY

- **Tool** — callable function exposed by an MCP server
- **Resource** — readable data endpoint exposed by an MCP server
- **SSE (Server-Sent Events)** — HTTP streaming transport for MCP
- **stdio transport** — process-level transport for local MCP servers
- **Connection pool** — pre-allocated set of DB connections
- **pool_size** — number of persistent connections kept open
- **max_overflow** — extra connections allowed above pool_size
- **Pydantic** — Python validation library used for MCP tool schemas
- **proxy_buffering** — Nginx feature that must be OFF for SSE streams
- **pgvector** — PostgreSQL extension for vector/embedding search
- **LangGraph** — framework for stateful multi-agent workflows
- **LangSmith** — observability platform for LLM + agent tracing