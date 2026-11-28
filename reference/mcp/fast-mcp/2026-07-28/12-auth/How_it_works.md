[_prompt_for_learning_streamable_mcp](../../attachments/auth/_prompt_for_learning_streamable_mcp.md)

## 4. HOW IT WORKS (MECHANISM)

![](../../assets/auth/mcp_streamable_http_sequence.png)
------------------------------------------------------------------------

### Overview

MCP Streamable HTTP uses standard HTTP/1.1.
No WebSockets. No persistent TCP socket.
Two channels run simultaneously once connected:

- A POST channel for sending requests.
- A GET channel (SSE stream) for receiving events.

------------------------------------------------------------------------

### Step-by-step breakdown

#### Phase 1 — Connection and session init

Step 1. Client sends POST /mcp with an `initialize`
JSON-RPC message.
🔑 Jargon: JSON-RPC — a lightweight protocol for
remote procedure calls using JSON payloads.

Step 2. Server responds 200 OK.
Response header includes:
`Mcp-Session-Id: <uuid>`
🔑 Jargon: Mcp-Session-Id — a server-issued token
that identifies this conversation's state.

Step 3. Client opens a persistent GET /mcp request.
Header must include: `Mcp-Session-Id: <uuid>`
This is the SSE stream channel.
🔑 Jargon: SSE (Server-Sent Events) — a one-way
HTTP channel where the server pushes events to
the client continuously over one open connection.

Step 4. Server replies 200 with:
`Content-Type: text/event-stream`
Connection stays open. Client now receives events.

------------------------------------------------------------------------

#### Phase 2 — Tool call + chunk streaming (Tool 1)

Step 5. Client sends POST /mcp with a `tools/call`
message targeting `stream_data` tool.

Step 6. Server routes the call to the tool handler.

Step 7. Tool handler yields chunks via async generator.
🔑 Jargon: async generator — a Python function
using `yield` inside `async def`; produces values
one at a time without blocking.

Step 8. Server wraps each chunk as an SSE event and
pushes it over the open GET stream:
`data: {"chunk": "row 1..10"}`

Step 9. After last chunk, server sends a done signal:
`data: {"isError": false, "done": true}`

------------------------------------------------------------------------

#### Phase 3 — Bidirectional elicitation (Tool 2)

Step 10. Client sends POST /mcp for `batch_process`.

Step 11. Server routes to handler; processing begins.

Step 12. Server streams progress over SSE:
`data: {"progress": "rows 1–50 processed"}`

Step 13. Server sends an elicitation event asking the
client to make a decision mid-call:
`data: {"elicitation": "continue?", ...}`
🔑 Jargon: elicitation — a server-initiated
request for input from the client during an
active tool call (multi-turn within one request).

Step 14. Client replies with a new POST /mcp containing
the elicitation answer:
`{"action": "continue", "batch_size": 25}`

Step 15. Handler receives the reply and resumes with
new batch_size = 25.

Step 16. Tool yields remaining chunks (rows 51–100).

Step 17. Server streams final chunks + done signal
over SSE.

------------------------------------------------------------------------

#### Phase 4 — Session teardown

Step 18. Client sends DELETE /mcp with session header.

Step 19. Server deletes session state, returns 200 OK.

------------------------------------------------------------------------

### Transport summary table

┌──────────────┬──────────────────────┬────────────────────────┐
│ Direction │ HTTP method │ Purpose │
├──────────────┼──────────────────────┼────────────────────────┤
│ Client→Server│ POST /mcp │ Send requests/replies │
│ Server→Client│ GET /mcp (SSE)       │ Push chunks + events │
│ Client→Server│ DELETE /mcp │ End session │
└──────────────┴──────────────────────┴────────────────────────┘

------------------------------------------------------------------------

### Key mechanism facts

- Every message carries `Mcp-Session-Id` to correlate
  state server-side.
- The SSE channel (GET) stays open for the entire
  session lifetime.
- POSTs are short-lived; they carry requests and
  elicitation replies.
- Streaming uses Python async generators on the server.
- Elicitation suspends the tool handler via asyncio
  until the client POST arrives.

------------------------------------------------------------------------

### Summary

| Concept          | One-line reminder                         |
|------------------|-------------------------------------------|
| Mcp-Session-Id   | Token linking all requests to one session |
| SSE stream (GET) | Always-open push channel                  |
| POST /mcp        | One-shot request from client              |
| Async generator  | Yields chunks without blocking            |
| Elicitation      | Server pauses tool, asks client a Q       |

------------------------------------------------------------------------

Next: Chunk 4 → §05 BASIC EXAMPLE
Type "next" to continue.