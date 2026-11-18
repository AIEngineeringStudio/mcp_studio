# MCP SERVER WITH STREAMABLE HTTP TRANSPORT

## CHUNK 2 / 8 — Sections §02 and §03

---

- CHUNKS GENERATED : [2 / 8]
- ACTIVE CHUNK     : [2 / 8]
- SECTIONS         : [§02, §03]

---

## §02. WHY IT MATTERS

### Real-World Purpose

**MCP with Streamable HTTP** solves a core problem:
> How does an AI agent communicate with external tools
> in real time, without waiting for a full response?

Traditional HTTP: client sends request → waits → gets
full response. This blocks the UI and wastes time.

**Streamable HTTP MCP** allows:

- Server to push partial results as they are ready.
- Client to reply mid-stream (bidirectional).
- Long-running tasks to report progress live.

---

### Where It Is Used in Industry

- **AI agent pipelines** — LLM tools that call APIs
  and stream results back to the agent.
- **Data processing systems** — batch jobs that report
  row-by-row progress.
- **Enterprise dashboards** — live ETL status feeds.
- **DevOps tooling** — CI/CD pipelines streaming logs.
- **Financial systems** — streaming trade confirmations.

---

### 3 Concrete Use Cases

```
┌──────────────────────┬─────────────────────┬──────────────────────────┐
│ Use Case             │ Industry            │ Problem It Solves        │
├──────────────────────┼─────────────────────┼──────────────────────────┤
│ AI agent calls DB    │ Enterprise SaaS     │ Agent waits 30s for full │
│ tool, streams rows   │                     │ result — now streams row │
│ as they arrive       │                     │ by row, stays responsive │
├──────────────────────┼─────────────────────┼──────────────────────────┤
│ Data migration tool  │ FinTech / HealthTech│ No visibility into batch │
│ reports progress,    │                     │ progress; user can now   │
│ asks user to pause   │                     │ pause/resize mid-run     │
│ or resize batch      │                     │                          │
├──────────────────────┼─────────────────────┼──────────────────────────┤
│ LLM document         │ Legal / Research    │ Full doc summary blocks  │
│ summariser streams   │                     │ UI for 60s; streaming    │
│ paragraph by para.   │                     │ shows output instantly   │
└──────────────────────┴─────────────────────┴──────────────────────────┘
```

---

## §03. CORE CONCEPTS (FOUNDATION)

### Topic List

1. HTTP as a Transport Layer
2. Server-Sent Events (SSE)
3. The MCP Protocol
4. MCP Session
5. MCP Tool
6. Streaming vs. Batch
7. Elicitation (Mid-stream Client Reply)
8. Bidirectional Communication

---

### Block 1 — HTTP as a Transport Layer

🔑 **Transport Layer** — the communication channel
between client and server (how bytes travel).

**Standard HTTP flow:**

```
Client ──[POST /tool]──► Server
Client ◄──[200 + body]── Server
```

- One request → one complete response.
- Client is blocked until server finishes.

**Problem for AI tools:**

- Tool may take 30–60 seconds.
- Client has no progress signal.
- Client cannot send new input mid-way.

---

### Block 2 — Server-Sent Events (SSE)

🔑 **SSE (Server-Sent Events)** — a standard where the
server keeps the HTTP connection open and pushes
multiple messages to the client over time.

**SSE message format (plain text):**

```
data: {"chunk": "row 1 processed"}\n\n
data: {"chunk": "row 2 processed"}\n\n
data: [DONE]\n\n
```

- Uses a single long-lived HTTP connection.
- Server pushes; client reads.
- Client CANNOT send data back on same connection.

**Analogy:** SSE = a radio broadcast. You receive it.
You cannot talk back on the same channel.

---

### Block 3 — The MCP Protocol

🔑 **MCP (Model Context Protocol)** — Anthropic's open
standard for connecting AI models to external tools,
data sources, and services.

**Key roles:**

```
┌─────────────┐        MCP messages         ┌─────────────┐
│  MCP Client │ ◄──────────────────────────► │  MCP Server │
│  (AI agent) │                              │  (your tool)│
└─────────────┘                              └─────────────┘
```

- Client = the AI model or agent that calls tools.
- Server = the backend that executes the tool logic.
- Messages follow the MCP JSON-RPC 2.0 format.

🔑 **JSON-RPC 2.0** — a lightweight remote procedure
call protocol using JSON messages.

**Example MCP tool call message:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "stream_data",
    "arguments": {
      "batch_size": 10
    }
  }
}
```

---

### Block 4 — MCP Session

🔑 **MCP Session** — a stateful connection between one
client and one server. Tracks context across
multiple tool calls.

**Session lifecycle:**

```
1. Client sends  → initialize request
2. Server sends  → initialized response
3. Client sends  → tool call(s)
4. Server sends  → results / streams
5. Either side   → closes connection
```

- Each session has a unique **session ID**.
- Session state lives in server memory (or Redis
  in production).

---

### Block 5 — MCP Tool

🔑 **MCP Tool** — a named function the server exposes
that the AI client can call.

**Tool definition structure:**

```python
{
    "name": "stream_rows",  # tool name
    "description": "Stream DB rows",  # what it does
    "inputSchema": {  # expected inputs
        "type": "object",
        "properties": {
            "batch_size": {"type": "integer"}
        }
    }
}
```

- Tools are registered on the MCP server at startup.
- Client discovers tools via `tools/list` call.

---

### Block 6 — Streaming vs. Batch

```
┌─────────────────┬────────────────────┬──────────────────────┐
│ Mode            │ How it works       │ Best for             │
├─────────────────┼────────────────────┼──────────────────────┤
│ Batch           │ Wait for all data, │ Small datasets,      │
│                 │ send one response  │ fast operations      │
├─────────────────┼────────────────────┼──────────────────────┤
│ Streaming       │ Send chunks as     │ Large data, long     │
│ (server→client) │ they are ready     │ jobs, live feedback  │
├─────────────────┼────────────────────┼──────────────────────┤
│ Bidirectional   │ Server streams +   │ Interactive batch    │
│ Streaming       │ client replies     │ jobs, agent dialogs  │
│                 │ mid-stream         │                      │
└─────────────────┴────────────────────┴──────────────────────┘
```

**Streaming in MCP uses SSE** for server → client.
**Client replies** go back via a separate POST request
to the same session endpoint.

---

### Block 7 — Elicitation

🔑 **Elicitation** — the server pauses mid-tool-call
and asks the client for input before continuing.

**Flow:**

```
Server ──[stream: "processed 50 rows"]──► Client
Server ──[elicit: "continue? new batch?"]► Client
Client ──[POST reply: "yes, batch=20"]───► Server
Server resumes processing with new batch size
```

- Defined in MCP spec as `sampling/createMessage`
  or custom elicitation messages.
- Allows human-in-the-loop control over long tasks.

**Analogy:** Elicitation = a chef asking mid-recipe,
"Do you want more salt?" before finishing the dish.

---

### Block 8 — Bidirectional Communication

🔑 **Bidirectional Communication** — both client and
server can send messages at any time within a
single logical tool call.

**How MCP achieves this over HTTP:**

```
┌──────────┐  POST /session/{id}/message  ┌──────────┐
│  Client  │ ─────────────────────────►   │  Server  │
│          │                              │          │
│          │  SSE stream (data chunks)    │          │
│          │ ◄─────────────────────────── │          │
│          │                              │          │
│          │  POST /session/{id}/reply    │          │
│          │ ─────────────────────────►   │          │
└──────────┘                              └──────────┘
```

- **Outbound** (server → client): SSE stream.
- **Inbound** (client → server): separate POST to
  session endpoint.
- Server uses an **asyncio Queue** to receive the
  client reply and resume the stream.

🔑 **asyncio Queue** — Python async data structure
that lets one coroutine wait for data from another.

---

### How All Blocks Connect

```
┌──────────────────────────────────────────────────┐
│                  MCP SESSION                     │
│                                                  │
│  ┌──────────┐    tool call     ┌──────────────┐  │
│  │  Client  │ ───────────────► │  MCP Server  │  │
│  │  (agent) │                  │              │  │
│  │          │ ◄── SSE stream ─ │  MCP Tool    │  │
│  │          │   (chunks/elicit)│  (business   │  │
│  │          │                  │   logic)     │  │
│  │          │ ── POST reply ─► │              │  │
│  │          │                  │  asyncio Q   │  │
│  └──────────┘                  └──────────────┘  │
│                     HTTP Transport               │
└──────────────────────────────────────────────────┘
```

**Reading order:**

1. HTTP Transport → carries all messages
2. MCP Session → scopes the conversation
3. MCP Tool → defines what server can do
4. SSE → server pushes stream chunks
5. Elicitation → server asks client mid-stream
6. asyncio Queue → server receives client reply
7. Bidirectional → full loop complete

---

## SUMMARY — §02 + §03

Chunk 2/8 is ready. Here is what was covered:

**§02 — Why It Matters**

- Real-world purpose of Streamable HTTP MCP.
- Industry use areas listed.
- 3 concrete use cases in a table.

**§03 — Core Concepts**

- 8 building blocks defined and explained.
- Each block has an example and analogy.
- Final diagram shows how all blocks connect.

---

- **Streamable HTTP MCP** solves the blocking-response
  problem for long-running AI tool calls.
- Used in AI pipelines, data processing, dashboards.
- **3 building blocks of streaming:** SSE (push),
  POST reply (pull), asyncio Queue (internal relay).
- **Elicitation** = server pauses and asks client
  for input mid-call.
- **Bidirectional** = SSE (out) + POST (in) together.

**Key terms introduced this chunk:**

| Term                | One-line definition                              |
|---------------------|--------------------------------------------------|
| **Transport Layer** | Channel that carries bytes between client/server |
| **SSE**             | Server keeps connection open, pushes chunks      |
| **MCP Protocol**    | Anthropic's standard for AI ↔ tool communication |
| **JSON-RPC 2.0**    | Lightweight JSON-based remote call format        |
| **MCP Session**     | Stateful connection scoped to one client         |
| **MCP Tool**        | Named function the server exposes to the agent   |
| **Elicitation**     | Server pauses mid-call to ask client for input   |
| **asyncio Queue**   | Python async relay between coroutines            |

---

Ready for **Chunk 3 / §04 — How It Works (sequence diagram)**? Type
`next` to continue.
---

## NEXT

```
Chunk 3 / 8  →  §04 How It Works (sequence diagram)
```