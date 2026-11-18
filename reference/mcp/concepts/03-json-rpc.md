# JSON-RPC requests, responses, and notifications

**Outcome:** Read a message envelope and distinguish request identity from
business identity.

**Prerequisites:
** [02: Host, client, model, and server](02-host-client-server.md).

## MCP has two layers

```
┌────────────────────────────────────────────┐
│ Data layer                                 │
│                                            │
│ JSON-RPC messages                          │
│ lifecycle                                  │
│ tools, resources, prompts, notifications   │
│ sampling / elicitation / roots             │
└────────────────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────┐
│ Transport layer                            │
│                                            │
│ stdio                                      │
│ Streamable HTTP                            │
└────────────────────────────────────────────┘
```

The **data layer** defines what messages mean.

The **transport layer** defines **how messages travel**.

### Transport Layer

Transport carries JSON-RPC messages.

MCP's two standard transports:

- `stdio` for local process communication and
- `Streamable HTTP` for network communication.

| Transport       | Use Case                    |
|-----------------|-----------------------------|
| stdio           | Local process tools         |
| Streamable HTTP | HTTP streaming of responses |

```
 Client
  │
  │ JSON-RPC
  ▼
 Transport
  │
  ▼
 Server
```

```
┌─────────────────┬──────────────────────────────────────────────────────────┐
│ TRANSPORT       │ DETAILS                                                  │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ Streamable HTTP │ Single HTTP endpoint.                                    │
│                 │                                                          │
│                 │ POST for client → server messages;                       │
│                 │ optional GET opens an SSE-formatted event stream         │
│                 │ for server→client messages.                              │
│                 │                                                          │
│                 │ Best for: remote/deployed servers, scaling.              │
├─────────────────┼──────────────────────────────────────────────────────────┤
│ stdio           │ Standard input/output pipes                              │
│                 │                                                          │
│                 │ HOW IT WORKS:                                            │
│                 │ • Client spawns server as subprocess                     │
│                 │ • Communication via stdin/stdout                         │
│                 │                                                          │
│                 │ Best for: local tools, IDE plugins, CLIs.                │
│                 │ Do NOT print logs to stdout — it's the wire.             │
└─────────────────┴──────────────────────────────────────────────────────────┘

LEGACY / DEPRECATED:
"HTTP+SSE" — a separate, older transport (distinct GET-SSE and POST endpoints).
Still seen in some clients for backward compatibility, but new servers 
should not implement it.

HTTP+SSE is superseded by Streamable HTTP. 
```

#### Important distinction:

A `tools/call` is **NOT an HTTP operation**.
It is an **MCP protocol operation** that could travel over `stdio` or `HTTP`

The same logical tool can be used through either transport.
The transport changes **how messages travel**, not what the tool does.

## The message in the transport

JSON is a data representation.

JSON-RPC adds a convention for requesting a method and matching its response.
MCP protocol messages use `JSON-RPC 2.0`.

MCP assigns meanings to methods such as`tools/call`.

| Category   | Feature                    | Description               | 
|------------|----------------------------|---------------------------| 
| ✓ Core     | Message type: Request      | Requires response         | 
| ✓ Core     | Message type: Notification | Fire-and-forget           | 
| ~ Advanced | Logging to Client          | Server logs forwarded     |  
| IC         | Debug/Message logging      | Debugging message traffic | 

MCP supports two message types.

The following is an envelope illustration, not a complete modern MCP request:
required version/capability metadata is added in guide 04.

1. **request:** expects a response.

    ```
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │ JSON-RPC 2.0 REQUEST                                                        │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │   {                                                                         │
    │     "jsonrpc": "2.0",        // Always "2.0"                                │
    │     "id": 1                  // Request ID (for matching response)          │
    │     "method": "tools/call",  // The method being called                     │
    │     "params": {...},         // Method parameters                           │
    │   }                                                                         │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘
    ```

A **method** identifies the operation, for example:

```
┌─────────────────────┬───────────────────────────────────────────────────────┐
│ METHOD              │ PURPOSE                                               │
├─────────────────────┼───────────────────────────────────────────────────────┤
│ initialize          │ Start session, negotiate capabilities                 │
│ tools/list          │ Get available tools                                   │
│ tools/call          │ Execute a tool                                        │
│ resources/list      │ Get available resources                               │
│ resources/read      │ Read a resource's content                             │
│ prompts/list        │ Get available prompts                                 │
│ prompts/get         │ Get a prompt template                                 │
│ notifications/*     │ Various fire-and-forget notifications                 │
│ ping                │ Keep connection alive                                 │
└─────────────────────┴───────────────────────────────────────────────────────┘
```

**Note:**
> > That naming convention is worth internalizing.


The outer method is `tools/call`. The application tool's name lives inside
`params.name`. There is no requirement for an HTTP route named
`/get_ticket`.

The matching result uses the same `id`:

The `id` lets a client match responses to requests even when several
requests are in flight concurrently.

    ```
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │ JSON-RPC 2.0 SUCCESS RESPONSE                                               │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │   {                                                                         │
    │     "jsonrpc": "2.0",        // Always "2.0"                                │
    │     "id": 1,                 // Matches request ID                          │
    │     "result": {                                                             │
    │         "structuredContent": { "x": 1, "y": 2, "sum": 3 },                  │
    │         "isError": false                                                    │
    │     }                                                                       │
    │   }                                                                         │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘
    ```

### Correlation

If request 17 finishes after request 18, the client still knows which result
belongs to which call because each response carries its matching ID.
Correlation means connecting related events; it does not imply ordering.

```
Client                       Server
  | ---- request id=17 ------> |
  | ---- request id=18 ------> |
  | <--- response id=18 ------ |
  | <--- response id=17 ------ |
```

A JSON-RPC ID identifies a request. Ticket ID T-100 identifies a domain
record. An operation ID used to prevent repeated writes identifies a business
operation. These identifiers must not be substituted for one another.

## Notifications and errors

**notification:** is one-way.
Used for:

- progress/update
- log/message
- resource/changed

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

A notification deliberately has no request `id` and expects no JSON-RPC
response. Progress is one example of notification-style information. Do not
send a response to a notification merely because it arrived over a stream.

**error:**
An unsuccessful JSON-RPC request contains `error` instead of `result`.

An RPC error indicates that the requested protocol operation could not be
handled normally. A tool can also run and report an application-level failure.
Transport failure is a third possibility: the client may receive no usable
RPC response at all.

    ```
    ┌──────────────┬────────────────────────────────┬────────────────────────────┐
    │ LAYER        │ EXAMPLE                        │ OBSERVABLE FORM            │
    ├──────────────┼────────────────────────────────┼────────────────────────────┤
    │ Tool         │ Tool raises or returns an error│ Call result, isError:true  │
    │ MCP/JSON-RPC │ Unknown method, bad request    │ JSON-RPC error object      │
    │ HTTP         │ Wrong route, bad media type    │ HTTP 4xx/5xx               │
    │ Network      │ Server unreachable             │ Client transport exception │
    │ Process      │ Startup/config failure         │ Runtime/lifespan error     │
    └──────────────┴────────────────────────────────┴────────────────────────────┘
    ```

    ```
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │ JSON-RPC 2.0 ERROR RESPONSE                                                 │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │   {                                                                         │
    │     "jsonrpc": "2.0",                                                       │
    │     "id": 1,                                                                │
    │     "error": {                                                              │
    │       "code": -32600,        // Error code                                  │
    │       "message": "Invalid Request",                                         │
    │       "data": {...}          // Optional additional info                    │
    │     }                                                                       │
    │   }                                                                         │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘
    ```

For example, an unknown RPC method, a known tool rejecting a nonexistent
ticket, and a disconnected socket require different investigations. Later
guides address retry policy; retrying every error conceals incorrect inputs
and can repeat side effects.

**Key distinction:** Protocol errors are separate from HTTP errors

    - HTTP `200 OK` reports whether the transport exchange worked.
      It does not by itself prove a tool call succeeded — check `isError`
    - JSON-RPC `result/error` reports whether the requested operation worked.

## Serialization

On the wire, field names follow the protocol schema, including fields such
as `structuredContent`. Python libraries may expose snake_case names.
The library's model serializer bridges those representations. Guessing a wire
field from a Python attribute is unsafe.

JSON examples must contain valid JSON: comments and Python values such as
`True` are not JSON. A Python dictionary printed to a terminal is not
necessarily a serialized protocol message.

**Worked observation:**

> Capture two independent calls in a client trace. Follow the request ID to
> its response, then follow the ticket ID into the application. They answer
> different debugging questions.

**Professional articulation:**

> “JSON-RPC supplies the request envelope and correlation ID; MCP defines the
> operations carried in that envelope.”

## Sources and next step

- [Archive: docs/code-flow.md](../../docs/code-flow.md)
- [Archive: conversations/chunks/02-mcp-chunk2.md](../../conversations/chunks/02-mcp-chunk2.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/index) —
  checked 2026-11-15.

Next: [Protocol versions and capability discovery](04-versions-discovery.md).

