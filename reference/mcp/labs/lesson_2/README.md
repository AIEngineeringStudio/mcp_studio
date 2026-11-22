# **Tracing MCP JSON-RPC messages on client and server**

The goal is to see **every JSON-RPC request, response, error, & notification**,
regardless of which transport carries it.

The tracing component should observe messages, create records, and **forward the
original messages unchanged**. It should not own tool execution or authorization
decisions.

## **1. Where should we capture the messages?**

Your test client supports three transport modes:

| Transport       | How messages travel                                        |
|-----------------|------------------------------------------------------------|
| In-memory       | Between client and server within one Python process        |
| STDIO           | Through subprocess stdin/stdout                            |
| Streamable HTTP | Through HTTP requests and responses, including SSE streams |

**Important distinction:** In-memory mode has no physical network wire. We can
still inspect the logical JSON-RPC messages that pass between the client and
server.

### **The tracing point**

```
                 CLIENT PROCESS
+----------------------------------------+
| Client application                     |
|   client.call_tool("get_ticket", ...)  |
|                |                       |
|         MCP Client Session             |
|                |                       |
|        [1] CLIENT OUT TRACE            |
|                |                       |
+----------------|-----------------------+
                 |
       +---------v---------+
       | Transport         |
       | In-memory         |
       | STDIO             |
       | Streamable HTTP   |
       +---------+---------+
                 |
+----------------v-----------------------+
|        [2] SERVER IN TRACE             |
|                |                       |
|         MCP Server Session             |
|                |                       |
|         get_ticket("T-100")             |
|                |                       |
|        [3] SERVER OUT TRACE            |
+----------------|-----------------------+
                 |
          Same transport
                 |
+----------------v-----------------------+
|        [4] CLIENT IN TRACE             |
|                |                       |
|         Client receives result         |
+----------------------------------------+
```

We need four trace observations:

- **Client OUT:** What the client sends.
- **Server IN:** What the server receives.
- **Server OUT:** What the server sends back.
- **Client IN:** What the client receives.

The important design choice is to trace **MCP messages near the
session/transport boundary**, rather than only tracing individual Python tool
functions.

That gives us visibility into discovery, lifecycle negotiation, tool calls,
resource reads, prompt requests, notifications, and protocol errors.

## **2. Three ways to implement the trace**

1. **Application logging**:
   Captures logs in `call_tool()`, `read_resource()`, `get_prompt()`

   **Limitation:** Misses protocol messages generated internally

2. **Semantic tracing:** What operation did the application perform?

   Capture server requests, notifications, and operation results.
   Use FastMCP server middleware to understand what happens inside FastMCP.

   **Limitation:** Misses protocol messages generated internally.

3. **Protocol tracing:** What JSON-RPC message did the MCP session send or
   receive?

   Capture actual JSON-RPC envelopes sent and received, including request IDs.

   **Limitation:** Does not guarantee exact serialized wire bytes.

4. **Transport/Wire tracing:**  What bytes or HTTP/SSE frames actually crossed
   the transport?

   Inspect `STDIO` framing, HTTP bodies, headers, and SSE events.

   **Limitation:** Requires lower-level instrumentation.

**Why this order?** Because semantic tracing establishes that both application
boundaries are observable. When we later add JSON-RPC tracing, we can focus
entirely on request IDs, envelope serialization, notifications, and
transport-specific behavior rather than debugging two layers at the same time.

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
+-- side          client | server
+-- direction     OUT | IN
+-- transport     in-memory | stdio | http
+-- connection_id
+-- rpc_id
+-- method
+-- payload
+-- error
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

## **6. Where this fits in your two files**

In `server(2).py`, the relevant extension point for semantic tracing is
`mcp.add_middleware(...)`. In `verify_primitives(2).py`, `client_source()`
selects the transport, while the client session handles the protocol exchange.

For **complete wire tracing**, the next design decision is how to observe the
lower-level message send/receive path on each side without changing application
behavior. Server middleware alone is not enough, and I would avoid inventing a
universal FastMCP client hook without verifying its exact API.

To verify the design, run your existing `tools` test once per transport and
compare the four trace observations for the same `get_ticket("T-100")` call.

**Next topic:** Designing a trace wrapper around MCP message streams, and
identifying the exact client and server insertion points in FastMCP 4.2.