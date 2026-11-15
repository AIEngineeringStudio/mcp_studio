# MCP TUTORIAL — CHUNK 8 / 8

## SECTIONS: §17 – §18

---

## CHUNKS GENERATED: [8 / 8]

## ACTIVE CHUNK: [8 / 8]

## SECTIONS IN THIS CHUNK: [§17, §18]

---

## §17. INTERVIEW QUESTIONS

---

### Beginner (3–5 Questions)

---

**Q1. What is MCP?**

**MCP** (Model Context Protocol) is an open protocol that
standardizes how AI models connect to external tools,
data sources, and services using a client-server model.

---

**Q2. What are the three primitives MCP exposes?**

| Primitive     | Owned By | Description                          |
|---------------|----------|--------------------------------------|
| **Tools**     | Server   | Executable functions the model calls |
| **Resources** | Server   | Data the model can read              |
| **Prompts**   | Server   | Reusable prompt templates            |

---

**Q3. What is the difference between an MCP Host**
**and an MCP Client?**

- **Host** — the application (e.g. Claude Desktop, IDE).
  It manages the user session and orchestrates clients.
- **Client** — a 1:1 connector inside the host that
  maintains one connection to one MCP server.

---

**Q4. What transport protocols does MCP support?**

| Transport     | Use Case                           |
|---------------|------------------------------------|
| **stdio**     | Local process (CLI tools, scripts) |
| **SSE**       | Remote HTTP streaming              |
| **WebSocket** | Bidirectional real-time connection |

---

**Q5. What is a Tool Call in MCP?**

A structured JSON-RPC request from the model to the
server asking it to execute a named function and return
a result.

---

### Intermediate (3–5 Questions)

---

**Q6. Explain the MCP lifecycle.**

```
1. Host spawns Client
2. Client connects to Server (stdio / SSE / WS)
3. Client sends initialize request
4. Server responds with capabilities
5. Client sends initialized notification
6. Normal operation: tools/list, tools/call, etc.
7. Either side sends shutdown
```

---

**Q7. How does MCP differ from a REST API?**

| Feature        | MCP                   | REST API          |
|----------------|-----------------------|-------------------|
| Protocol       | JSON-RPC 2.0          | HTTP verbs        |
| Discovery      | Built-in (tools/list) | Manual / OpenAPI  |
| Streaming      | Native SSE / WS       | Optional          |
| AI integration | First-class           | Requires wrapping |
| State          | Session-based         | Stateless         |

---

**Q8. What is tool schema validation and why does**
**it matter?**

Each tool declares a **JSON Schema** for its input
parameters. The model uses this to construct valid
calls. Without it, the model may send malformed
arguments and the server has no contract to enforce.

---

**Q9. What is the role of a FastAPI Gateway in an**
**MCP architecture?**

The **FastAPI Gateway** acts as the HTTP entry point.
It routes requests to the correct MCP server, handles
auth, applies rate limiting, and normalizes responses
before they reach the AI model.

---

**Q10. How do you handle tool execution errors in MCP?**

```python
# Return isError=True in the tool result
return types.CallToolResult(
    isError=True,
    content=[types.TextContent(
        type="text",
        text=f"Error: {str(e)}"
    )]
)
```

The model receives the error as a tool result and can
decide to retry, ask for clarification, or escalate.

---

### Advanced (3–5 Questions)

---

**Q11. How would you implement auth in an MCP server**
**exposed over SSE?**

```
1. Client sends Bearer token in HTTP header
2. FastAPI dependency extracts + validates JWT
3. Identity injected into request context
4. Server enforces per-tool RBAC checks
5. Audit log records every tool invocation
```

Use **OAuth 2.0** or **API keys** depending on whether
the caller is a user or a service.

---

**Q12. How does sampling work in MCP and when**
**would you use it?**

**Sampling** lets the MCP server ask the host to run an
LLM completion on its behalf.

Use it when:

- The server needs to summarize retrieved data
- The server builds a sub-agent loop
- You want the server to generate structured output
  before returning to the main model

```
Server → requests/sampling/createMessage → Host
Host   → calls LLM → returns result → Server
Server → uses result in tool response
```

---

**Q13. How do you scale an MCP server to handle**
**10,000 concurrent tool calls?**

```
1. Run multiple server replicas in Docker / K8s
2. Place Nginx upstream load balancer in front
3. Use async handlers (asyncio) — never block
4. Add Redis cache for repeated read-only tool calls
5. Use connection pooling for DB (asyncpg + pgbouncer)
6. Add circuit breaker (e.g. tenacity) per tool
7. Emit Prometheus metrics per tool invocation
```

---

**Q14. What is the difference between a stateful and**
**stateless MCP server, and when do you use each?**

| Type          | State stored? | Use when                         |
|---------------|---------------|----------------------------------|
| **Stateless** | No            | Simple tools, easy to scale      |
| **Stateful**  | Yes (session) | Multi-turn workflows, file edits |

Stateful servers require **sticky sessions** or
**external session store** (e.g. Redis) to scale.

---

**Q15. How would you prevent prompt injection through**
**MCP tool results?**

```
1. Sanitize all tool output before returning
2. Never reflect raw user input back to the model
3. Use allowlists for expected result formats
4. Validate result shape against JSON Schema
5. Log all tool results for audit
6. Limit result size (max_tokens in response)
```

---

### System Design / Enterprise (2–3 Questions)

---

**Q16. Design an enterprise MCP platform that serves**
**50 internal AI agents across 10 business domains.**

```
┌─────────────────────────────────────────────────────┐
│                   AI Agent Layer                    │
│  Agent-1  Agent-2  Agent-3  ...  Agent-50           │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────▼──────────────┐
         │      MCP Gateway           │
         │  FastAPI + Nginx + Auth    │
         │  Rate Limiting + Routing   │
         └──┬──────┬──────┬───────┬──┘
            │      │      │       │
     ┌──────▼─┐ ┌──▼───┐ ┌▼────┐ ┌▼──────┐
     │ Domain │ │Domain│ │ ... │ │Domain │
     │ MCP #1 │ │MCP #2│ │     │ │MCP #10│
     │(Finance│ │ (HR) │ │     │ │(Legal)│
     └──┬─────┘ └──┬───┘ └──┬──┘ └──┬────┘
        │          │        │       │
     ┌──▼──────────▼────────▼───────▼──┐
     │        PostgreSQL / Redis        │
     │     Observability (OTEL)         │
     └──────────────────────────────────┘
```

Key decisions:

- **One MCP server per domain** → isolation + clear
  ownership
- **Central gateway** → single auth, rate limiting,
  routing
- **Shared observability layer** → trace every tool
  call end-to-end
- **Redis** → session store + tool result cache

---

**Q17. An MCP tool call is returning stale data.**
**How do you debug and fix it?**

```
Step 1 — Check structured logs
  → Find the tool invocation trace ID
  → Check what the server returned vs what was expected

Step 2 — Check cache layer
  → Was the result served from Redis?
  → Check TTL — may be too long for this data type

Step 3 — Check the data source
  → Is PostgreSQL returning fresh rows?
  → Check transaction isolation level

Step 4 — Fix
  → Reduce cache TTL for volatile tools
  → Add cache invalidation on write events
  → Add "last_updated" field to tool results
  → Alert if result age exceeds threshold
```

---

**Q18. How would you implement zero-downtime**
**deployment for an MCP server?**

```
1. Build new image → push to container registry
2. Deploy new replica alongside old one (blue/green)
3. Nginx upstream: add new, keep old
4. Run health check on new replica
5. Gradually shift traffic (canary: 5% → 25% → 100%)
6. Monitor error rate and p99 latency
7. If stable: remove old replica
8. If error spike: rollback by removing new replica
```

Use **Docker Swarm** or **Kubernetes** rolling update
strategy. MCP sessions are short-lived so mid-flight
disruption risk is low.

---

## §18. SUMMARY (REINFORCEMENT)

---

### Key Points — All Sections

**§00 Prerequisites**

- Need: Python, async, REST, JSON, Docker, basic AI
- Study first if missing: asyncio, JSON-RPC, REST

**§01 Define**

- MCP = open protocol for AI ↔ tool integration
- Transport: stdio / SSE / WebSocket
- Primitives: Tools, Resources, Prompts

**§02 Why It Matters**

- Replaces ad-hoc tool integrations
- Enables plug-and-play AI agents
- Used in: coding assistants, enterprise automation

**§03 Core Concepts**

- Host → Client → Server hierarchy
- JSON-RPC 2.0 message format
- Tool schema = JSON Schema contract
- Session lifecycle: init → operate → shutdown

**§04 How It Works**

- Client sends initialize → Server returns capabilities
- Model calls tools/list → builds tool menu
- Model calls tools/call → Server executes → returns
  result
- Errors flow back as isError=True tool results

**§05 Basic Example**

- Single MCP server with one echo tool
- FastMCP decorator pattern
- Stdio transport for local testing
- Structured logging from the start

**§06 Intermediate**

- Multi-tool server with PostgreSQL backend
- Ports and Adapters pattern for DB isolation
- Edge cases: empty results, DB errors, large payloads

**§07 Advanced Concepts**

- Security: JWT, RBAC, input sanitization, audit logs
- Scaling: Nginx, replicas, async, Redis cache
- Reliability: circuit breakers, retries, health checks
- Optimization: async DB, connection pooling, caching

**§08 Enterprise Usage**

- Cursor AI: IDE tools over stdio
- Salesforce AgentForce: CRM tools over SSE
- Bloomberg: financial data tools with strict auth

**§09 Best Practices**

- Always validate tool input with JSON Schema
- Always return structured errors (isError=True)
- Use async handlers — never block the event loop
- Log every tool call with trace ID
- Pin dependency versions

**§10 Case Study**

- Cursor AI: replaced custom tool pipeline with MCP
- Result: faster iteration, broader tool ecosystem

**§11 Comparison**

| Feature   | MCP      | REST API | LangChain Tools |
|-----------|----------|----------|-----------------|
| Discovery | Built-in | Manual   | Manual          |
| Streaming | Native   | Optional | Limited         |
| AI-native | Yes      | No       | Yes             |

**§12 Common Mistakes**

- Blocking async handlers → use await
- No input validation → add JSON Schema
- Returning raw errors → use isError=True
- No logging → add structlog
- Hardcoded config → use env vars / pydantic settings

**§13 Practice Exercises**

- Easy: echo tool server
- Medium: PostgreSQL query tool
- Hard: multi-server gateway with auth + caching

**§14 Check Understanding**

- Definition, mechanism, application, trade-offs,
  scenario-based questions

**§15 Debugging**

- ConnectionRefused: wrong transport / port
- ValidationError: schema mismatch
- Timeout: blocking sync call in async handler
- 401 Unauthorized: missing/invalid JWT
- Stale data: cache TTL too long

**§16 What to Learn Next**

- OpenAI Agents SDK → orchestrate multi-agent systems
- A2A Protocol → agent-to-agent communication
- LangGraph → stateful agent workflows

---

### All Jargon Terms

| Term                   | Definition                                                     |
|------------------------|----------------------------------------------------------------|
| **MCP**                | Model Context Protocol — open standard for AI tool integration |
| **Host**               | Application managing the AI session (e.g. Claude Desktop)      |
| **Client**             | Connector inside host, 1:1 with one MCP server                 |
| **Server**             | Process exposing tools/resources/prompts                       |
| **Tool**               | Executable function the model can call                         |
| **Resource**           | Read-only data the model can access                            |
| **Prompt**             | Reusable prompt template from server                           |
| **JSON-RPC 2.0**       | Protocol for structured remote procedure calls                 |
| **stdio**              | Standard I/O transport for local MCP servers                   |
| **SSE**                | Server-Sent Events — HTTP streaming transport                  |
| **FastMCP**            | Python decorator-based MCP server SDK                          |
| **Tool Schema**        | JSON Schema defining tool input parameters                     |
| **Sampling**           | Server-initiated LLM call through the host                     |
| **Capability**         | Feature a server declares during initialization                |
| **isError**            | Boolean flag marking a failed tool result                      |
| **RBAC**               | Role-Based Access Control                                      |
| **Circuit Breaker**    | Pattern to stop calling a failing service                      |
| **Ports and Adapters** | Architecture isolating business logic from I/O                 |
| **OTEL**               | OpenTelemetry — distributed tracing standard                   |
| **LiteLLM**            | Library to swap LLM providers transparently                    |
| **FastAPI**            | Python async web framework for the gateway layer               |
| **pgbouncer**          | PostgreSQL connection pooler                                   |
| **Blue/Green Deploy**  | Run old and new version in parallel, then switch               |
| **Canary Deploy**      | Gradually shift traffic to new version                         |
| **Sticky Session**     | Route same client to same server replica                       |

---

### 5 Most Important Concepts to Memorize

1. **MCP is a protocol, not a library.**
   It defines how hosts, clients, and servers communicate —
   any language can implement it.

2. **Three primitives: Tools, Resources, Prompts.**
   Tools = actions. Resources = data. Prompts = templates.

3. **Lifecycle: init → capabilities → operate → shutdown.**
   Every session follows this sequence exactly.

4. **Tool schema = contract.**
   JSON Schema on every tool is non-negotiable in
   production systems.

5. **Always async, always structured logs.**
   Blocking handlers kill throughput. Missing logs make
   debugging impossible.

---

### Quick Reference Table

```
┌─────────────────────────┬────────────────────────────────┐
│ Concept                 │ One-line reminder              │
├─────────────────────────┼────────────────────────────────┤
│ MCP                     │ Standard plug for AI tools     │
│ Host                    │ App that runs the AI session   │
│ Client                  │ 1:1 bridge to one server       │
│ Server                  │ Exposes tools/resources/prompts│
│ Tool                    │ Function the model can call    │
│ Resource                │ Data the model can read        │
│ Prompt                  │ Reusable template from server  │
│ JSON-RPC 2.0            │ Message format for all calls   │
│ stdio                   │ Local transport (pipe)         │
│ SSE                     │ Remote streaming transport     │
│ Tool Schema             │ JSON contract for tool inputs  │
│ Sampling                │ Server asks host to call LLM   │
│ isError                 │ Error flag in tool result      │
│ FastMCP                 │ Python SDK for MCP servers     │
│ Circuit Breaker         │ Stop calling a failing service │
│ Ports and Adapters      │ Isolate logic from DB/IO       │
│ OTEL                    │ Trace every call end-to-end    │
│ Blue/Green Deploy       │ Zero-downtime version switch   │
└─────────────────────────┴────────────────────────────────┘
```

---

## TUTORIAL COMPLETE — ALL 8 CHUNKS GENERATED ✓

```
┌───────┬───────────────────┬────────┐
│ Chunk │    Sections       │ Status │
├───────┼───────────────────┼────────┤
│   1   │    §00 – §02      │  ✓     │
│   2   │    §03 – §04      │  ✓     │
│   3   │    §05 – §06      │  ✓     │
│   4   │    §07 – §07      │  ✓     │
│   5   │    §08 – §10      │  ✓     │
│   6   │    §11 – §13      │  ✓     │
│   7   │    §14 – §16      │  ✓     │
│   8   │    §17 – §18      │  ✓     │
└───────┴───────────────────┴────────┘
```