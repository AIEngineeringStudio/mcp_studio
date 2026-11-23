# **Tracing MCP JSON-RPC messages on client and server**

The goal is to see **every JSON-RPC request, response, error, & notification**,
regardless of which transport carries it.

The tracing component should observe messages, create records, and **forward the
original messages unchanged**. It should not own tool execution or authorization
decisions.

## **1. Where should we capture the messages?**

Your test client supports three transport modes:

| Transport       | How messages travel                                        |
|-----------------|────────────────────────────────────────────────────────----|
| In-memory       | Between client and server within one Python process        |
| STDIO           | Through subprocess stdin/stdout                            |
| Streamable HTTP | Through HTTP requests and responses, including SSE streams |

> **Important distinction:**
> In-memory mode has no physical network wire. Modern in-process MCP dispatch
> can bypass JSON-RPC serialization entirely. We can trace logical requests and
> results, but these are not necessarily JSON-RPC envelopes.

### **The tracing points**

The important design choice is where to place the trace, based on what we want
to observe:

1. **Semantic boundary:**
   Observe application-level operations and results.

   Capture server requests, notifications, and operation results.
   Use FastMCP server middleware to understand what happens inside FastMCP.

   > **Limitation:** Client application tracing only captures explicitly
   > instrumented calls. Server middleware observes inbound requests and
   > notifications, but does not guarantee visibility into final serialized
   > JSON-RPC responses or transport-level failures.

2. **Protocol boundary:**
   Observe JSON-RPC request, response, error, and notification envelopes.

   Capture actual JSON-RPC envelopes sent and received, including request IDs.

   > **Limitation:** Does not guarantee exact serialized wire bytes.

3. **Transport/Wire boundary:**  
   Observe how messages are carried over STDIO or HTTP.
   What bytes or HTTP/SSE frames actually crossed the transport?

   Inspect `STDIO` framing, HTTP bodies, headers, and SSE events.

   > **Limitation:** Requires lower-level instrumentation.

Protocol tracing can reveal discovery, tool calls, resource reads, prompt
requests, notifications, and protocol errors.

For legacy MCP versions, it can also reveal the initialization handshake.
Modern` MCP 2026-07-28` uses per-request metadata instead.

We need four trace observations:

- **CLIENT OUT:** What the client sends.
- **SERVER IN:** What the server receives.
- **SERVER OUT:** What the server sends back.
- **CLIENT IN:** What the client receives.

`CLIENT OUT` and `SERVER IN` refer to requests,
while `SERVER OUT` and `CLIENT IN` refer to responses in this example.

Notifications can also travel in either direction.

```
   CLIENT SIDE                                  SERVER SIDE
   
   ┌────────────────────────────┐               ┌────────────────────────────┐
   │     Client Application     │               │    Server Application      │
   │    verify_primitives.py    │               │       get_ticket()         │
   │                            │               │                            │
   │ SEMANTIC: CALL / RESULT    │               │                            │
   └────────────────────────────┘               └────────────────────────────┘
          │            ▲                                ▲            │  
          │            │                                │            │ 
          ▼            │                                │            ▼
   ┌────────────────────────────┐               ┌────────────────────────────┐
   │      FastMCP Client        │               │      FastMCP Server        │
   │                            │               │                            │
   │       JSON-RPC Layer       │               │       JSON-RPC Layer       │
   │                            │               │                            │
   │     SEMANTIC BOUNDARY 1    │               │     SEMANTIC BOUNDARY 2    │
   │       (MIDDLEWARE)         │               │        (MIDDLEWARE )       │
   │                            │               │                            │
   │    [1] CLIENT-OUT TRACE    │               │   [2] SERVER-IN TRACE      │
   │    [4] CLIENT-IN TRACE     │               │   [3] SERVER-OUT TRACE     │
   │                            │               │                            │
   └────────────────────────────┘               └────────────────────────────┘
          │            ▲                                ▲            │
          │ PROTOCOL   │                                │ PROTOCOL   │
          │ BOUNDARY 1 │                                │ BOUNDARY 2 │
          ▼            │                                │            ▼
   ┌────────────────────────────┐               ┌────────────────────────────┐
   │      Client Transport      │               │      Server Transport      │
   │                            │-- REQUEST ---▶│                            │
   │        STDIO / HTTP        │◀-- RESPONSE --│        STDIO / HTTP        │
   └────────────────────────────┘               └────────────────────────────┘
```

**Semantic Boundary 2:**
`SEMANTIC: IN / DONE` trace is inside FastMCP server middleware, not at the
boundary between the server application and FastMCP.

**Important version-specific qualification:**
The MCP Python SDK's modern in-process client can use a `DirectDispatcher`,
which bypasses JSON-RPC framing entirely.

So for in-memory tests, trace logical operations.
For exact wire-format verification, use STDIO or HTTP.

## **3. What should one trace record contain?**

Use the same record structure for every transport:

```
TraceRecord
    +-- timestamp
    +-- side           client | server
    +-- direction      OUT | IN
    +-- transport      in-memory | stdio | http
    +-- connection_id
    +-- message_type   request | response | error | notification
    +-- rpc_id         optional
    +-- method         optional
    +-- payload
    +-- error          optional
```

### Example: your `get_ticket` tool

Your client calls `get_ticket` with `ticket_id="T-100"`.

Here is an illustrative JSON-RPC request using MCP protocol version
`2026-07-28`:

```
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "get_ticket",
    "arguments": {
      "ticket_id": "T-100"
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientInfo": {
        "name": "lesson-1-client",
        "version": "1.0"
      },
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

The request ID and client version are synthetic examples, not captured output.
The request envelope follows the current MCP specification.

For this one call, your trace should show something like:

```
CLIENT OUT  id=7  tools/call
SERVER IN   id=7  tools/call

SERVER:
  get_ticket("T-100")
  -> {"id":"T-100","title":"Cannot sign in","status":"open"}

SERVER OUT  id=7  result
CLIENT IN   id=7  result
```

This tells you that the message reached the server, the tool ran, and a response
returned. The JSON-RPC `id` correlates request and response. Include a
connection identifier because an ID alone is not globally unique.

## **4. How transport changes what you trace**

**In-memory**

Observe logical requests and results in the dispatcher. Do not claim the trace
represents serialized network bytes.

**STDIO**

Observe complete JSON-RPC lines sent to the subprocess and received from it.
Store trace output separately or send it to `stderr`. Never write trace text to
the MCP server's `stdout`, because that channel must contain only valid protocol
messages.

**Streamable HTTP**

Observe JSON-RPC request bodies, response bodies, and each SSE event when
streaming is used. Capture relevant HTTP status codes and protocol headers too.
A simple tool-call logger will not show problems that occur during HTTP
validation.

## **5. What happens when something fails?**

Suppose the client sends a request and then times out.

```
CLIENT OUT  [captured]
     |
     v
SERVER IN   [captured]
     |
     v
get_ticket() completed
     |
     v
SERVER OUT  [captured]
     |
     X  response interrupted
     |
CLIENT IN   [missing]
```

The four observations help isolate where the exchange failed. Here, the server
produced a response, but the client did not receive it.

For recovery, retain the error or stream-close event, correlate it with the
request, and check whether a retry is safe. Your `get_ticket` is read-only, so
retrying it is simpler than retrying a tool that changes data.

Also redact credentials and sensitive tool arguments before writing trace files.
Trace logs should not become a second, less-protected copy of application data.
