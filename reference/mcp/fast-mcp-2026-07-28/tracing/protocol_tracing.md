# Protocol tracing

## Decision 1: Where should we intercept JSON-RPC?

We want to capture the **complete JSON-RPC message**, not just a tool name,
arguments, or Python result.

For your FastMCP 4.2 ticket service, our target is:


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

`CLIENT OUT` and `SERVER IN` refer to requests, and
`SERVER OUT` and `CLIENT IN` refer to responses in this example.

### **One important difference from semantic tracing**

**A modern in-memory FastMCP connection does not necessarily generate JSON-RPC
messages.**

The current MCP Python SDK uses `DirectDispatcher` for modern in-process
connections. This bypasses serialization and the JSON-RPC wire layer. Forcing
`mode="legacy"` uses an in-memory JSON-RPC transport, but also changes the
protocol version and lifecycle behavior being tested.

This means we cannot truthfully promise identical JSON-RPC wire traces across
all three modes without changing how the in-memory test operates.

Recommendation is to keep your modern `in-memory` test as-is and use `STDIO`
and `HTTP` to learn real JSON-RPC protocol tracing.

## 2. Choose the interception layer

Overriding `ClientSession.send_request()` is an option, but it can't capture
full responses or reliably capture request ID's at the final envelope level.

Both the below options capture request IDs and full responses.

### STDIO Transport

Wrap the SDK's `SessionMessage` streams.

The official MCP Python SDK defines `JSONRPCDispatcher`, which accepts
`read_stream` and `write_stream` containing `SessionMessage` objects.

Each contains a parsed JSON-RPC message plus transport metadata.

### HTTP Transport

Capture HTTP JSON-RPC bodies and responses.

> The modern HTTP server has a separate request-handling path.
> Therefore, one stream wrapper is **not sufficient for every server transport
**.

For your project, I recommend implementing the stream interception first with
STDIO and then adding the modern HTTP interception.

## 3. How one protocol message flows

Using your `get_ticket("T-100")` test, the following is a synthetic modern
JSON-RPC request:

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
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

Our expected protocol trace is:

```
[CLIENT OUT] REQUEST
    id=7
    method=tools/call
    arguments={"ticket_id":"T-100"}

[SERVER IN] REQUEST
    id=7
    method=tools/call
    arguments={"ticket_id":"T-100"}

[SERVER OUT] RESPONSE
    id=7
    result={...}

[CLIENT IN] RESPONSE
    id=7
    result={...}
```

The important difference from semantic tracing is that we can now correlate
**the actual protocol request ID** rather than only the method name.

## 4. Failure and verification

Suppose the trace records `CLIENT OUT`, but there is no `SERVER IN`.

Possible causes include a broken STDIO pipe, a transport failure, or a rejected
HTTP request before protocol dispatch.

The trace should record the transport error and allow the original error to
propagate. Logging must never modify the JSON-RPC message, consume it without
forwarding it, or block indefinitely.

In STDIO mode, trace output must remain off protocol `stdout`.

For your first test, run `--transport stdio --focus tools`.
Success means every observed request has the expected client/server trace
entries and response IDs, and your existing ticket assertions still pass.
