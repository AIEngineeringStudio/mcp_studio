# §04 — How It Works: Streamable HTTP Transport

---

## Chunk progress

```
- CHUNKS GENERATED : [3 / 8]
- ACTIVE CHUNK     : [3 / 8]
- SECTION          : [§04]
```

---

## Overview

Streamable HTTP transport runs over standard HTTP/1.1 or HTTP/2.
The same POST endpoint handles ALL message types:
tool calls, streaming chunks, and elicitation requests.

Here is the sequence diagram for the full bidirectional flow:

![](../../assets/streamable/mcp_streamable_http_basic_flow.png)

---

## Step-by-step mechanism

```
Step 1 — Client sends HTTP POST to /mcp endpoint
         Body: JSON-RPC 2.0 message (tool call)

Step 2 — Server validates the request
         Checks: method, params, auth headers

Step 3 — Server opens a streaming response
         Header: Content-Type: text/event-stream
         Header: Transfer-Encoding: chunked
         This keeps the HTTP connection OPEN

Step 4 — Server begins writing SSE events
         Format: data: <json>\n\n
         Each event = one chunk / one progress update

Step 5 — [Optional] Server sends elicitation event
         Type: "elicitation/request"
         Payload: question + allowed response schema

Step 6 — Client reads the elicitation event
         Client POSTs reply to same /mcp endpoint
         Session tracked via Mcp-Session-Id header

Step 7 — Server receives client reply
         Server continues or stops based on reply

Step 8 — Server sends final result event
         Type: "result"
         Followed by: data: [DONE]\n\n

Step 9 — HTTP connection closes
```

---

## Protocol format per SSE event

```
# Each server-sent event looks like this:

data: {"jsonrpc":"2.0","id":"abc","method":"stream/chunk","params":{"chunk":"row 1 done"}}

data: {"jsonrpc":"2.0","id":"abc","method":"elicitation/request","params":{"message":"Continue?","schema":{"type":"boolean"}}}

data: {"jsonrpc":"2.0","id":"abc","result":{"status":"done","rows":100}}

data: [DONE]
```

---

## Session tracking

```
┌─────────────────────────────────────────────────────┐
│  First request (no session):                        │
│    POST /mcp                                        │
│    Mcp-Session-Id: (absent)                         │
│                                                     │
│  Server responds with:                              │
│    Mcp-Session-Id: sess-xyz-789   ← new ID          │
│                                                     │
│  All follow-up replies use:                         │
│    POST /mcp                                        │
│    Mcp-Session-Id: sess-xyz-789   ← same ID         │
└─────────────────────────────────────────────────────┘
```

---

## Message routing table

```
┌────────────────────┬──────────────────┬─────────────────────────┐
│ Event type         │ Direction        │ Purpose                 │
├────────────────────┼──────────────────┼─────────────────────────┤
│ tools/call         │ Client → Server  │ Initiate a tool         │
│ stream/chunk       │ Server → Client  │ One chunk of output     │
│ elicitation/request│ Server → Client  │ Ask client a question   │
│ elicitation/result │ Client → Server  │ Client's answer         │
│ result             │ Server → Client  │ Final tool result       │
│ error              │ Server → Client  │ Tool or protocol error  │
└────────────────────┴──────────────────┴─────────────────────────┘
```

---

## Transport layer stack

```
┌───────────────────────────────────┐
│        MCP Application Layer      │  ← Tool logic lives here
├───────────────────────────────────┤
│        JSON-RPC 2.0 Layer         │  ← Message framing
├───────────────────────────────────┤
│   SSE (Server-Sent Events) Layer  │  ← Streaming format
├───────────────────────────────────┤
│         HTTP/1.1 or HTTP/2        │  ← Transport
├───────────────────────────────────┤
│              TCP/IP               │  ← Network
└───────────────────────────────────┘
```

---

## Elicitation sub-flow (zoomed in)

```
CLIENT                          SERVER
  │                                │
  │── POST /mcp (tool call) ──────►│
  │                                │ process first batch
  │◄── SSE: stream/chunk ───────── │ (rows 1–10)
  │◄── SSE: stream/chunk ───────── │ (rows 11–20)
  │                                │
  │◄── SSE: elicitation/request ── │ "Continue? New batch size?"
  │                                │
  │── POST /mcp (reply) ──────────►│  {continue: true, batch: 50}
  │   Mcp-Session-Id: sess-xyz     │
  │                                │ resumes with batch=50
  │◄── SSE: stream/chunk ───────── │ (rows 21–70)
  │◄── SSE: result ─────────────── │ done
  │◄── SSE: [DONE] ─────────────── │
```

---

## Key design decisions

```
┌────────────────────────┬────────────────────────────────────────┐
│ Decision               │ Reason                                 │
├────────────────────────┼────────────────────────────────────────┤
│ Single POST endpoint   │ Firewall-friendly; no WebSocket needed │
│ SSE for server→client  │ Built-in browser support; no upgrade   │
│ Session header         │ Ties multi-turn replies to same tool   │
│ JSON-RPC 2.0 framing   │ Standardised error + ID handling       │
│ [DONE] sentinel        │ Signals stream end without HTTP close  │
└────────────────────────┴────────────────────────────────────────┘
```

---

## Summary

- Every tool call starts with a **POST** to `/mcp`.
- Client sends ONE POST to open the tool call.
- The server holds the connection open using **SSE**.
- Chunks arrive as `data:` events until `[DONE]`.
- Elicitation pauses the stream; client replies via
  a new POST with the same **session ID**.
- Server resumes after receiving the client reply.
- The protocol is layered: HTTP → SSE → JSON-RPC → MCP.
- [DONE] sentinel closes the stream cleanly.


## Key terms recap

┌────────────────────┬─────────────────────────────────────┐
│ Term               │ One-line reminder                   │
├────────────────────┼─────────────────────────────────────┤
│ SSE                │ Server pushes events over open HTTP │
│ Mcp-Session-Id     │ Header that ties multi-turn replies │
│ elicitation/request│ Server pauses stream to ask client  │
│ [DONE] sentinel    │ Signals end of stream               │
│ JSON-RPC 2.0       │ Message framing format used by MCP  │
└────────────────────┴─────────────────────────────────────┘

## Next chunk

Chunk 4 / §05 — Basic Example
- Full working code for all containers
- Docker setup
- Seed data + expected output