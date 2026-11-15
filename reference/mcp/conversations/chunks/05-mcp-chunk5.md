# MCP Tutorial — Chunk 5 of 8

## SECTIONS: §08 Enterprise Usage · §09 Best Practices · §10 Case Study

---

## §08 ENTERPRISE USAGE

### How real companies use MCP in production

MCP lets enterprises connect AI agents to internal tools,
databases, and APIs through a standardized protocol.
Instead of custom integrations per tool, one MCP server
exposes multiple capabilities to any MCP-compatible client.

---

### Company Examples

#### 1. Replit — AI Coding Assistant

Replit uses MCP to connect its AI agent to the filesystem,
shell, and code execution environment inside its cloud IDE.

```
┌─────────────────────────────────────────────────────┐
│                   Replit Platform                   │
│                                                     │
│  ┌──────────┐    MCP      ┌────────────────────┐   │
│  │ AI Agent │◄───────────►│   MCP Server       │   │
│  │(Claude)  │             │  ┌──────────────┐  │   │
│  └──────────┘             │  │ filesystem   │  │   │
│                           │  │ shell_exec   │  │   │
│                           │  │ code_runner  │  │   │
│                           │  │ pkg_manager  │  │   │
│                           │  └──────────────┘  │   │
│                           └────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

Tools used: MCP SDK (Python), Claude API, Docker sandboxes,
FastAPI gateway, Nginx reverse proxy.

---

#### 2. Block (Square) — Internal Developer Tooling

Block connects AI agents to internal ticket systems,
deployment pipelines, and monitoring dashboards via MCP.

```
┌─────────────────────────────────────────────────────┐
│              Block Internal Platform                │
│                                                     │
│  ┌──────────┐    MCP      ┌────────────────────┐   │
│  │ Dev AI   │◄───────────►│   MCP Gateway      │   │
│  │ Agent    │             │  ┌──────────────┐  │   │
│  └──────────┘             │  │ Jira tools   │  │   │
│                           │  │ Datadog      │  │   │
│                           │  │ GitHub       │  │   │
│                           │  │ PagerDuty    │  │   │
│                           │  └──────────────┘  │   │
│                           └────────────────────┘   │
│                                    │               │
│                           ┌────────▼───────┐       │
│                           │  PostgreSQL DB  │       │
│                           └────────────────┘       │
└─────────────────────────────────────────────────────┘
```

Tools used: MCP SDK, LiteLLM, FastAPI, PostgreSQL,
OpenTelemetry for structured logging.

---

#### 3. Sourcegraph (Cody AI) — Code Search & Intelligence

Sourcegraph exposes code search, repository metadata,
and symbol lookup as MCP tools for its Cody AI agent.

```
┌─────────────────────────────────────────────────────┐
│               Sourcegraph Cody Platform             │
│                                                     │
│  ┌──────────┐    MCP      ┌────────────────────┐   │
│  │  Cody    │◄───────────►│   MCP Server       │   │
│  │  Agent   │             │  ┌──────────────┐  │   │
│  └──────────┘             │  │ code_search  │  │   │
│                           │  │ symbol_lookup│  │   │
│                           │  │ repo_context │  │   │
│                           │  │ diff_viewer  │  │   │
│                           │  └──────────────┘  │   │
│                           └────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

Tools used: MCP SDK (Go + Python), Anthropic API,
Redis caching, Nginx, Kubernetes for scaling.

---

### Enterprise Summary Table

```
┌────────────┬───────────────────┬─────────────────┬──────────────────────┐
│ Company    │ How they use it   │ Scale           │ Tools used           │
├────────────┼───────────────────┼─────────────────┼──────────────────────┤
│ Replit     │ IDE agent tools   │ Millions of     │ MCP SDK, Claude,     │
│            │ (fs, shell, run)  │ code runs/day   │ Docker, FastAPI      │
├────────────┼───────────────────┼─────────────────┼──────────────────────┤
│ Block      │ Internal devops   │ 1000s of eng.   │ MCP, LiteLLM,        │
│            │ agent tooling     │ daily users     │ Jira, Datadog        │
├────────────┼───────────────────┼─────────────────┼──────────────────────┤
│ Sourcegraph│ Code search and   │ Large mono-     │ MCP, Anthropic API,  │
│            │ AI code context   │ repo scale      │ Redis, Kubernetes    │
└────────────┴───────────────────┴─────────────────┴──────────────────────┘
```

---

### Enterprise Patterns Used

1. **MCP Gateway** — single FastAPI entry point routing
   all tool calls to registered MCP servers.
2. **Tool Registry** — database of available tools with
   versioning and permission scopes.
3. **Audit Logging** — every tool call logged with
   structured JSON (who, what, when, result).
4. **Rate Limiting** — Nginx limits tool calls per
   client to prevent abuse.
5. **Sandboxed Execution** — dangerous tools (shell,
   filesystem) run inside Docker containers.

---

## §09 BEST PRACTICES

### Industry-Standard Rules for MCP

---

### Rules Table

```
┌──────────────────────┬──────────────────────────┬───────────────────────┐
│ Practice             │ Reason                   │ Risk if ignored       │
├──────────────────────┼──────────────────────────┼───────────────────────┤
│ Validate all tool    │ LLMs can hallucinate or  │ Injection attacks,    │
│ inputs with Pydantic │ pass malformed args      │ server crashes        │
├──────────────────────┼──────────────────────────┼───────────────────────┤
│ Use structured       │ Debugging distributed    │ Silent failures,      │
│ logging (JSON)       │ tool calls is hard       │ no audit trail        │
├──────────────────────┼──────────────────────────┼───────────────────────┤
│ Authenticate every   │ MCP exposes real system  │ Unauthorized tool     │
│ MCP request (JWT/    │ capabilities             │ execution             │
│ API key)             │                          │                       │
├──────────────────────┼──────────────────────────┼───────────────────────┤
│ Version your tools   │ LLM prompts depend on    │ Breaking changes      │
│ (/v1/tools/...)      │ stable tool schemas      │ silently break agents │
├──────────────────────┼──────────────────────────┼───────────────────────┤
│ Return typed errors  │ Agent must know if tool  │ Agent loops or        │
│ not raw exceptions   │ failed and why           │ hallucinates fallback │
├──────────────────────┼──────────────────────────┼───────────────────────┤
│ Scope tool           │ Least-privilege reduces  │ Agent gains access    │
│ permissions tightly  │ blast radius of bugs     │ to unintended systems │
├──────────────────────┼──────────────────────────┼───────────────────────┤
│ Add timeouts to      │ Slow tools block the     │ Agent hangs, user     │
│ every tool handler   │ entire agent loop        │ session times out     │
├──────────────────────┼──────────────────────────┼───────────────────────┤
│ Write clear tool     │ LLM selects tools based  │ Wrong tool called,    │
│ descriptions         │ on descriptions alone    │ wrong result          │
├──────────────────────┼──────────────────────────┼───────────────────────┤
│ Run tools inside     │ Isolates side effects    │ Tool can corrupt host │
│ Docker containers    │ and resource usage       │ filesystem or network │
├──────────────────────┼──────────────────────────┼───────────────────────┤
│ Use LiteLLM for      │ Avoid vendor lock-in to  │ Switching LLMs        │
│ model abstraction    │ one LLM provider         │ requires full rewrite │
└──────────────────────┴──────────────────────────┴───────────────────────┘
```

---

### Practice: Pydantic Input Validation

```python
# tools/search_tool.py

from pydantic import BaseModel, Field, validator


# Define strict input schema for the tool
class SearchInput(BaseModel):
    query: str = Field(
        ...,
        min_length=1,  # Must not be empty
        max_length=500,  # Prevent overly long queries
        description="Search query string"
    )
    limit: int = Field(
        default=10,
        ge=1,  # Greater than or equal to 1
        le=100,  # Less than or equal to 100
        description="Max results to return"
    )

    @validator("query")
    def no_injection(cls, v):
        # Block basic SQL-style injection attempts
        forbidden = ["DROP", "DELETE", "--", ";"]
        for term in forbidden:
            if term.upper() in v.upper():
                raise ValueError(f"Forbidden term: {term}")
        return v
```

---

### Practice: Structured Logging

```python
# core/logging.py

import structlog  # pip: structlog

# Configure structlog to output JSON
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),  # JSON output
    ]
)

logger = structlog.get_logger()


# Usage inside a tool handler
def handle_tool_call(tool_name: str, args: dict):
    logger.info(
        "tool_called",
        tool=tool_name,  # Structured field
        args=args,  # Full args logged
        user_id="u_123"  # Caller identity
    )
```

Expected log output:

```json
{
  "event": "tool_called",
  "tool": "search_db",
  "args": {
    "query": "orders",
    "limit": 10
  },
  "user_id": "u_123",
  "level": "info",
  "timestamp": "2026-03-22T10:00:00Z"
}
```

---

### Practice: Typed Error Response

```python
# core/errors.py

from pydantic import BaseModel
from enum import Enum


class ErrorCode(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    INVALID_INPUT = "INVALID_INPUT"
    TIMEOUT = "TIMEOUT"
    UNAUTHORIZED = "UNAUTHORIZED"


class ToolError(BaseModel):
    """Structured error returned to the agent."""
    code: ErrorCode
    message: str  # Human-readable reason
    tool: str  # Which tool failed
    retryable: bool  # Can agent retry this?


# Example: tool raises structured error
def get_record(record_id: str) -> dict:
    if not record_id:
        return ToolError(
            code=ErrorCode.INVALID_INPUT,
            message="record_id is required",
            tool="get_record",
            retryable=False
        ).model_dump()
```

---

## §10 CASE STUDY

### Company: Replit — AI Agent with MCP Tool Access

---

#### 1. Company and Context

Replit is a cloud-based IDE used by millions of developers.
In 2024, Replit launched an AI agent ("Replit Agent") that
can read, write, and execute code inside user projects.

The challenge: the AI needed safe, controlled access to
the user's filesystem, shell, and package manager — without
hardcoding these integrations per LLM provider.

---

#### 2. Problem They Faced

- Replit had integrations directly baked into prompts.
- Switching LLMs (Claude → GPT-4 → Gemini) broke all
  tool logic.
- No standard way to expose tools to different AI models.
- Security risk: unrestricted shell access from AI.

---

#### 3. Solution They Implemented

Replit adopted MCP as the standard tool protocol.

They built an MCP server exposing:

| Tool          | What it does                     |
|---------------|----------------------------------|
| `read_file`   | Read file content from project   |
| `write_file`  | Write or overwrite a file        |
| `run_shell`   | Execute shell command in sandbox |
| `install_pkg` | Install npm/pip/cargo package    |
| `list_dir`    | List files in a directory        |

Every tool runs inside a Docker sandbox per user session.

```
┌─────────────────────────────────────────────────────────┐
│                    Replit Architecture                  │
│                                                         │
│  Browser                                                │
│    │                                                    │
│    ▼                                                    │
│  ┌────────────┐    HTTPS    ┌───────────────────────┐  │
│  │ Replit UI  │────────────►│  Nginx Reverse Proxy  │  │
│  └────────────┘             └──────────┬────────────┘  │
│                                        │               │
│                             ┌──────────▼────────────┐  │
│                             │   FastAPI Gateway      │  │
│                             │   (Auth + Rate Limit)  │  │
│                             └──────────┬────────────┘  │
│                                        │               │
│                  ┌─────────────────────▼─────────────┐ │
│                  │         LiteLLM Router             │ │
│                  │  (Claude / GPT-4 / Gemini)         │ │
│                  └─────────────────────┬─────────────┘ │
│                                        │               │
│                  ┌─────────────────────▼─────────────┐ │
│                  │         MCP Server                 │ │
│                  │  read_file │ write_file │ run_shell │ │
│                  └─────────────────────┬─────────────┘ │
│                                        │               │
│                  ┌─────────────────────▼─────────────┐ │
│                  │   Docker Sandbox (per user)        │ │
│                  │   Isolated filesystem + shell      │ │
│                  └────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

#### 4. Result / Outcome

- Switching LLMs no longer requires changing tool logic.
- Security incidents from shell access dropped significantly
  due to Docker sandbox isolation.
- New tools can be added to the MCP server without
  touching the AI layer.
- Structured logging via MCP gave full audit trail of
  every tool call per user session.

---

#### 5. Lessons Learned

1. MCP decouples the AI model from tool implementations.
2. Docker sandboxing is non-negotiable for shell tools.
3. Structured tool descriptions directly affect AI quality —
   vague descriptions lead to wrong tool selection.
4. Rate limiting at the gateway level prevents runaway
   agent loops from consuming all resources.
5. Typed error responses help the agent recover gracefully
   instead of retrying blind.

---

## 🔑 Jargon Summary — Chunk 5

| Term                   | Definition                                    |
|------------------------|-----------------------------------------------|
| **MCP Gateway**        | Single FastAPI entry point for all tool calls |
| **Tool Registry**      | DB of available tools with versions + perms   |
| **Sandbox**            | Isolated Docker container for safe execution  |
| **Structured Logging** | JSON log output with typed fields             |
| **Typed Error**        | Pydantic error model returned instead of raw  |
|                        | exception                                     |
| **Rate Limiting**      | Cap on requests/sec enforced at Nginx         |
| **LiteLLM**            | Abstraction layer to swap LLM providers       |
| **Least Privilege**    | Grant only minimum permissions needed         |
| **Audit Trail**        | Log of all actions for review/compliance      |
| **Tool Versioning**    | Namespaced tool URLs (/v1/tools/...) for      |
|                        | backward compatibility                        |

---

## STATUS

```
┌───────┬─────────────┬──────────┐
│ Chunk │ Sections    │ Status   │
├───────┼─────────────┼──────────┤
│   1   │ §00 – §02   │ ✅ Done  │
│   2   │ §03 – §04   │ ✅ Done  │
│   3   │ §05 – §06   │ ✅ Done  │
│   4   │ §07         │ ✅ Done  │
│   5   │ §08 – §10   │ ✅ Done  │
│   6   │ §11 – §13   │ ⬜ Next  │
│   7   │ §14 – §16   │ ⬜       │
│   8   │ §17 – §18   │ ⬜       │
└───────┴─────────────┴──────────┘
```

Reply **"chunk 6"** to continue with §11 Comparison,
§12 Common Mistakes, §13 Practice Exercises.

