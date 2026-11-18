# MCP SERVER WITH STREAMABLE HTTP TRANSPORT

## Chunk 8 / 8 — §13 to §18


**What's in this chunk:**

| Section | Content                                                  |
|---------|----------------------------------------------------------|
| §13     | 3 exercises: Easy / Medium / Hard                        |
| §14     | 5 understanding questions (answer to get feedback)       |
| §15     | Top 5 bugs + broken vs fixed code                        |
| §16     | Next topics table + project recommendation               |
| §17     | 15 interview questions (Beginner → System Design)        |
| §18     | Full summary, all jargon, top 5 concepts, reminder table |

```
Chunk 8 / 8 delivered. Sections §13–§18 complete.
All 18 sections of the tutorial are now done.
```

---

## 13. PRACTICE EXERCISES

---

### Easy — Single Streaming Tool

**Task:**
Build an MCP server with one tool: `stream_numbers`.
It streams integers from 1 to N, one per second.

**Constraints:**

- N passed as a tool argument.
- Each chunk is a plain integer (as text).
- Use Streamable HTTP transport.
- Docker required.

**Correct solution looks like:**

```
Client calls stream_numbers(n=5)
Server yields: 1 \n 2 \n 3 \n 4 \n 5
Connection closes cleanly.
```

---

### Medium — Bidirectional Batch Tool

**Task:**
Build a tool `process_rows` that:

1. Accepts a list of DB row IDs.
2. Streams progress back per row.
3. After every 10 rows, sends an elicitation:
   `"Continue? (yes/no)"`.
4. If client replies `"no"`, stops immediately.
5. If client replies `"yes"`, continues.

**Constraints:**

- Use PostgreSQL with seed data (100+ rows).
- Use structured logging (JSON).
- Use LiteLLM to summarise each batch.
- Separate client container.

**Correct solution looks like:**

```
Client sends: process_rows(ids=[1..100])
Server streams:
  {"status":"processing","row_id":1}
  ...
  {"status":"elicit","message":"Continue? (yes/no)"}
Client replies: yes
Server continues...
  {"status":"done","total":100}
```

---

### Hard — Multi-Turn Agent Pipeline

**Task:**
Build a two-tool MCP server:

- `Tool 1`: `stream_report` — queries DB, streams
  a summarised report line-by-line via LiteLLM.
- `Tool 2`: `interactive_pipeline` — bidirectional:
    - Accepts a dataset name.
    - Streams row-level analysis.
    - Elicits user for filter criteria mid-stream.
    - Re-queries DB using new filter.
    - Streams second pass results.
    - Sends final summary via LLM.

**Constraints:**

- FastAPI gateway with Nginx reverse proxy.
- Clean Architecture + Ports & Adapters.
- OpenAI Agent SDK orchestrates tool calls.
- Full Docker Compose stack.
- JWT auth on all endpoints.
- Structured JSON logging throughout.

**Correct solution looks like:**

```
Agent calls interactive_pipeline(dataset="sales")
Server streams analysis chunks...
Server elicits: {"filter": "region?"}
Client replies: {"region": "EMEA"}
Server re-queries, streams filtered results...
Server sends: {"summary": "EMEA total: $4.2M"}
```

---

## 14. CHECK UNDERSTANDING

Answer each question. Reply with your answers and
I will give feedback.

---

**Q1 — Definition:**
What is the key difference between
**Streamable HTTP** transport and classic
**HTTP+SSE** transport in MCP?

---

**Q2 — Mechanism:**
When a server sends an **elicitation** mid-stream,
what must the client do to resume the same
tool call? Walk through each step.

---

**Q3 — Application:**
You are processing 1 million DB rows.
The user may want to stop early.
Which MCP pattern do you use, and why?

---

**Q4 — Trade-offs:**
A teammate suggests replacing streaming with
polling (client asks "done yet?" every second).
List 2 reasons streaming is better
and 1 reason polling might be preferred.

---

**Q5 — Scenario:**
Your streaming tool works locally but hangs
in production behind Nginx.
List 3 Nginx settings you would check first.

---

## 15. DEBUGGING

---

### Common Bugs Table

```
┌──────────────────────┬──────────────────────┬────────────────────────┬─────────────────────────────┐
│ Bug                  │ Cause                │ Error / Symptom        │ Fix                         │
├──────────────────────┼──────────────────────┼────────────────────────┼─────────────────────────────┤
│ Stream hangs at      │ Nginx buffers the    │ Client receives        │ Set proxy_buffering off;    │
│ Nginx boundary       │ entire response      │ nothing until EOF      │ proxy_read_timeout 3600s    │
├──────────────────────┼──────────────────────┼────────────────────────┼─────────────────────────────┤
│ Elicitation never    │ Client does not      │ Server waits forever;  │ Client must POST reply to   │
│ receives a reply     │ POST to elicit URL   │ request timeout        │ /elicit/{session_id}        │
├──────────────────────┼──────────────────────┼────────────────────────┼─────────────────────────────┤
│ Chunks arrive as     │ Missing             │ Entire body delivered  │ Add Content-Type:           │
│ one big blob         │ Content-Type header  │ at once                │ text/event-stream           │
├──────────────────────┼──────────────────────┼────────────────────────┼─────────────────────────────┤
│ Session not found    │ Sticky session not   │ 404 on elicit reply    │ Enable ip_hash or use       │
│ on elicit reply      │ configured in LB     │                        │ Redis session store         │
├──────────────────────┼──────────────────────┼────────────────────────┼─────────────────────────────┤
│ Generator not        │ async def missing    │ TypeError: object is   │ Change to                   │
│ streaming            │ yield keyword        │ not an iterator        │ async def + yield chunks    │
└──────────────────────┴──────────────────────┴────────────────────────┴─────────────────────────────┘
```

---

### Broken vs Fixed Code

#### Bug 1 — Missing `yield` (not streaming)

```python
# ❌ BROKEN — returns all at once
@app.post("/stream")
async def stream_tool():
    results = []
    for i in range(10):
        results.append(f"chunk {i}\n")
    return results  # sends all at once
```

```python
# ✅ FIXED — yields one chunk at a time
from fastapi.responses import StreamingResponse


@app.post("/stream")
async def stream_tool():
    async def generator():
        for i in range(10):
            yield f"chunk {i}\n"  # streams each chunk
            await asyncio.sleep(0.1)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream"  # tells client to stream
    )
```

**Why it happens:** Forgetting `yield` collects all
results in memory and sends one response body.

---

#### Bug 2 — Nginx buffering

```nginx
# ❌ BROKEN — Nginx buffers the whole stream
location /mcp/ {
    proxy_pass http://mcp_server:8000;
}
```

```nginx
# ✅ FIXED — Nginx passes chunks immediately
location /mcp/ {
    proxy_pass http://mcp_server:8000;
    proxy_buffering off;                 # disable buffering
    proxy_read_timeout 3600s;              # allow long streams
    proxy_http_version 1.1;               # required for keep-alive
    chunked_transfer_encoding on;         # allow chunked encoding
}
```

**Why it happens:** Nginx default buffers the entire
upstream response before forwarding to the client.

---

## 16. WHAT TO LEARN NEXT

---

### Next Topics Table

```
┌──────────────────────────┬──────────────────────────────────┬─────────────┐
│ Next Topic               │ Why it matters                   │ Difficulty  │
├──────────────────────────┼──────────────────────────────────┼─────────────┤
│ OpenAI Agent SDK         │ Orchestrate multi-tool MCP calls │ Intermediate│
│ (multi-agent pipelines)  │ with planning + memory           │             │
├──────────────────────────┼──────────────────────────────────┼─────────────┤
│ WebSockets               │ Full-duplex alternative to SSE;  │ Intermediate│
│                          │ better for high-frequency data   │             │
├──────────────────────────┼──────────────────────────────────┼─────────────┤
│ Redis Streams +          │ Persist & replay MCP events;     │ Advanced    │
│ Event Sourcing           │ required for distributed scale   │             │
└──────────────────────────┴──────────────────────────────────┴─────────────┘
```

---

### Practice Tools / Platforms

- **Postman** — test SSE streaming endpoints manually.
- **k6.io** — load test streaming connections.

---

### Recommended Project

> Build a **live AI pipeline dashboard**:
> - User uploads a CSV.
> - MCP server streams row-by-row analysis via LLM.
> - User can pause, change batch size, and resume.
> - Results saved to PostgreSQL.
> - Frontend shows real-time progress bar.

This forces you to use: streaming, elicitation,
bidirectional comms, DB, Docker, and Nginx together.

---

## 17. INTERVIEW QUESTIONS

---

### Beginner

**Q: What is MCP?**
A: Model Context Protocol — a standard for AI models
to call external tools over a defined transport.

**Q: What is Streamable HTTP?**
A: An HTTP transport where the server sends data
incrementally using chunked encoding or SSE,
instead of one complete response.

**Q: What does `yield` do in a Python async generator?**
A: Pauses the function and sends one value to the
caller; resumes on next iteration.

**Q: What HTTP header tells the client to expect
a stream?**
A: `Content-Type: text/event-stream`

**Q: What is an elicitation in MCP?**
A: A mid-stream server request asking the client
for input before continuing processing.

---

### Intermediate

**Q: How does a client resume a tool call after
an elicitation?**
A: The client POSTs a reply to the elicit endpoint
with the session ID and its response payload.

**Q: Why does Nginx break streaming by default?**
A: `proxy_buffering on` (default) collects the full
upstream response before forwarding. Fix: set
`proxy_buffering off`.

**Q: What is the role of `session_id` in
bidirectional streaming?**
A: It links the elicit reply back to the correct
suspended generator on the server.

**Q: When would you use Redis for MCP sessions?**
A: When running multiple server replicas — session
state must be shared across instances.

**Q: What is backpressure in streaming?**
A: When the client cannot consume chunks as fast as
the server produces them; the server must slow down
or buffer.

---

### Advanced

**Q: How do you guarantee exactly-once delivery
of streamed chunks if the connection drops?**
A: Assign sequence numbers to chunks. Client
tracks last received sequence. On reconnect,
server replays from that sequence using a
persistent event log (e.g., Redis Streams).

**Q: How do you horizontally scale a stateful
MCP streaming server?**
A: Store session state in Redis. Use sticky sessions
(Nginx `ip_hash`) OR move session lookup to a
shared store so any replica can handle elicit
replies.

**Q: What are the security risks of elicitation
and how do you mitigate them?**
A: Risk: client injects malicious input mid-stream.
Mitigate: validate and sanitise all elicit replies;
authenticate with JWT; rate-limit elicit endpoints.

---

### System Design / Enterprise

**Q: Design a streaming MCP server that processes
10 million rows per day with < 1s latency
per chunk.**

Key points:

1. PostgreSQL with read replicas + connection pool.
2. Async FastAPI + async generator streaming.
3. Redis for session state.
4. Nginx with `proxy_buffering off`.
5. Horizontal scaling via Docker Swarm / K8s.
6. Prometheus + Grafana to monitor chunk latency.

---

**Q: A downstream LLM call inside a streaming
tool is slow and blocks chunk delivery.
How do you fix it?**

Key points:

1. Run LLM call in a background task
   (`asyncio.create_task`).
2. Stream interim chunks (progress updates)
   while LLM processes.
3. Send LLM result as final chunk when ready.
4. Use LiteLLM streaming mode so LLM tokens
   are streamed too.

---

## 18. SUMMARY (REINFORCEMENT)

---

### Key Points by Section

- **§0** — Requires: HTTP, async Python, Docker,
  PostgreSQL, SSE basics.
- **§1** — MCP = protocol; Streamable HTTP =
  transport; elicitation = mid-stream user input.
- **§2** — Used for LLM tool calls, real-time
  pipelines, interactive AI agents.
- **§3** — Core blocks: MCP server, transport,
  tool, session, elicitation, generator.
- **§4** — Client → POST → server opens generator
  → yields chunks → elicits if needed →
  client replies → generator resumes → closes.
- **§5** — Basic: FastAPI + StreamingResponse +
  `yield` + Docker.
- **§6** — Intermediate: bidirectional tool,
  session store, elicitation endpoint.
- **§7** — Security: JWT + input validation.
  Scale: Redis sessions + sticky LB.
  Reliability: sequence numbers + replay.
- **§8** — Enterprise: Anthropic, LangChain,
  Harvey AI all use streaming MCP patterns.
- **§9** — Always: buffer off, timeouts set,
  sessions stored externally, chunks numbered.
- **§10** — Case study: LLM coding assistant
  streaming multi-file analysis with elicitation.
- **§11** — Streamable HTTP vs WebSocket vs
  long-polling: streaming wins for AI pipelines.
- **§12** — Top mistakes: missing yield, no
  proxy_buffering off, no session ID, sync code
  in async path, no timeout.
- **§13** — Exercises: easy=single stream,
  medium=bidirectional batch, hard=agent pipeline.
- **§14** — 5 questions tested definition,
  mechanism, application, trade-offs, scenario.
- **§15** — Top bugs: Nginx buffering, missing
  yield, no elicit reply, session mismatch,
  missing Content-Type.
- **§16** — Next: Agent SDK, WebSockets,
  Redis Streams.
- **§17** — Interview: beginner→advanced→
  system design covered.

---

### All Jargon Terms

| Term                   | Definition                                          |
|------------------------|-----------------------------------------------------|
| **MCP**                | Model Context Protocol — AI tool call standard      |
| **Streamable HTTP**    | HTTP transport with incremental chunk delivery      |
| **SSE**                | Server-Sent Events — one-way server→client stream   |
| **Elicitation**        | Server pauses stream to request client input        |
| **Session ID**         | Token linking elicit reply to suspended generator   |
| **Async generator**    | Python function using `yield` inside `async def`    |
| **Backpressure**       | Client too slow to consume server chunks            |
| **Sticky session**     | LB routes same client to same server replica        |
| **Chunked encoding**   | HTTP sends body in variable-size pieces             |
| **Ports & Adapters**   | Architecture pattern: core logic isolated from I/O  |
| **LiteLLM**            | Python lib to swap LLM providers with one interface |
| **Clean Architecture** | Layers: entities → use cases → adapters → infra     |

---

### 5 Most Important Concepts

1. **`yield` inside `async def`** = streaming.
   Without it, nothing streams.

2. **`proxy_buffering off`** in Nginx =
   mandatory for streaming to reach the client.

3. **Session ID** = the key that links an
   elicitation reply to a suspended generator.

4. **Redis session store** = required for
   horizontal scaling of stateful streams.

5. **Sequence numbers on chunks** = the only
   reliable way to recover from dropped connections.

---

### Concept Reminder Table

```
┌────────────────────────┬──────────────────────────────────────────┐
│ Concept                │ One-line reminder                        │
├────────────────────────┼──────────────────────────────────────────┤
│ yield                  │ Sends one chunk; pauses; waits for next  │
│ proxy_buffering off    │ Nginx must not hold chunks back          │
│ Session ID             │ Ties elicit reply to correct generator   │
│ Redis sessions         │ Share state across server replicas       │
│ Sequence numbers       │ Resume streams after disconnection       │
│ Content-Type: SSE      │ Tells client to read chunks as stream    │
│ Elicitation            │ Server asks client mid-stream for input  │
│ Clean Architecture     │ Keep DB logic outside core business code │
│ LiteLLM                │ Swap any LLM without changing your code  │
│ Backpressure           │ Slow down server when client lags behind │
└────────────────────────┴──────────────────────────────────────────┘
```

---

*Chunk 8 / 8 complete. All sections §13–§18 covered.*

**Recommended next step:**
Answer the 5 questions in §14.
Reply here and I will review each answer.