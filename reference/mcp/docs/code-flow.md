# MCP Lifecycle Studio: Code Flow and Technical Concepts

In this project:

- `mcp-studio-client` is the MCP client.
- `mcp-studio-server` is the MCP server.
- FastAPI and Uvicorn host the server as an HTTP application.
- The MCP Python SDK implements the protocol rules on both sides.
- The tracing framework records the exchanges without implementing those rules
  again.

## 2. The layers involved

The easiest way to reason about the application is as a stack. Each layer has a
different responsibility.

```text
┌──────────────────────────────────────────────────────────────┐
│ Application intent: initialize, list tools, call "add"       │
├──────────────────────────────────────────────────────────────┤
│ MCP: lifecycle, capabilities, tools, resources, prompts      │
├──────────────────────────────────────────────────────────────┤
│ JSON-RPC 2.0: method, params, id, result, error              │
├──────────────────────────────────────────────────────────────┤
│ Streamable HTTP: POST, GET event stream, DELETE, session ID  │
├──────────────────────────────────────────────────────────────┤
│ ASGI / AnyIO: asynchronous messages and object streams       │
├──────────────────────────────────────────────────────────────┤
│ TCP/IP: bytes moving between 127.0.0.1 ports                 │
└──────────────────────────────────────────────────────────────┘
```

- **Application intent** is the work the application wants performed.
    - Add two numbers by calling `add` tool.

- **MCP** defines the protocol-level meaning and interaction.
    - Sends a tools/call request for the tool named `add`.
    - `add` should generally be called an MCP tool, not necessarily a function.
    - MCP tools are not necessarily programming-language functions.

- **JSON-RPC 2.0** defines the message envelope.
    - Represents the MCP request using fields such as method, params, and id.

- **Streamable HTTP** defines how MCP JSON-RPC messages are transported.
    - Uses HTTP POST for client messages and may use an HTTP GET event stream
      for server messages.
    - It can also manage an MCP session ID.

- ASGI/AnyIO provides asynchronous implementation plumbing.
    - ASGI(Asynchronous Server Gateway Interface) represents HTTP activity as
      asynchronous events.
    - AnyIO provides tasks, synchronization, and in-memory object streams.
    - [Learn more about ASGI/AnyIO](understanding-asgi.md)

- TCP/IP carries the underlying network data.
    - Transfers bytes between IP addresses and ports — even when both
      endpoints use 127.0.0.1

**Practical MCP combinations**

```
**Async Python MCP server**
    Streamable HTTP → ASGI → AnyIO → asyncio or Trio

**Simpler async Python server**
    Streamable HTTP → ASGI → asyncio directly

**Synchronous Python server**
    HTTP → WSGI/native server → threads → synchronous handlers

**Non-Python server**
    HTTP → Node.js / Go / Java / Rust runtime
```

**Example:**

```text
Your application
    │  “Call add with 2 and 3”
    ▼
MCP
    │  tools/call
    ▼
JSON-RPC
    │  {"method":"tools/call","params":{"name":"add",...},"id":7}
    ▼
HTTP
    │  POST /mcp  + session ID
    ▼
ASGI / AnyIO
    │  request event → async handler → response event
    ▼
TCP/IP
       raw bytes sent to 127.0.0.1:<port>

       Server computes 2 + 3

TCP/IP → ASGI → HTTP → JSON-RPC → MCP → Application
                                           result = 5
```


## 2. CORE CONCEPTS

### 2.1 MCP is the domain protocol

MCP assigns meaning to methods such as:

- `initialize`
- `notifications/initialized`
- `tools/list`
- `tools/call`

It also defines capability objects, tool schemas, content blocks, resource
URIs, prompts, progress notifications, logging, and other protocol concepts.

### 2.2 JSON-RPC is the message envelope

MCP messages use JSON-RPC 2.0. A request has a method, optional parameters, and
an identifier:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": {
      "a": 20,
      "b": 22
    }
  }
}
```

The matching result uses the same `id`:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "structuredContent": {
      "a": 20.0,
      "b": 22.0,
      "sum": 42.0
    },
    "isError": false
  }
}
```

The identifier lets a client match responses to requests even when several
requests are in flight concurrently.

A notification deliberately has no `id`:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

```text
Client                          Server
  │                               │
  │── initialize ────────────────>│  Handshake + capability
  │<─ initialize result ──────────│  exchange
  │                               │
  │── tools/list ────────────────>│  Discover available tools
  │<─ tools/list result ──────────│
  │                               │
  │── tools/call ────────────────>│  Invoke a tool
  │<─ tools/call result ──────────│
  │                               │
  │── shutdown ──────────────────>│  Graceful close
  │<─ (close) ────────────────────│
```

No response is expected for a notification. That is why the server returns an
HTTP acknowledgement but no JSON-RPC result for this message.

An unsuccessful JSON-RPC request contains `error` instead of `result`.

**Protocol errors are separate from HTTP status codes:**
HTTP reports whether the transport exchange worked,
while JSON-RPC reports whether the requested operation worked.

### 2.3 Streamable HTTP carries JSON-RPC

JSON-RPC describes message shapes but does not require a particular transport.
This project uses MCP Streamable HTTP:

- `POST /mcp/` sends JSON-RPC requests, notifications, and results.
- `GET /mcp/` can keep an event stream open for server-initiated messages.
- `DELETE /mcp/` terminates a stateful MCP session.

The server returns `Mcp-Session-Id` after initialization. Later requests send
the same value back, allowing the server to find the correct session.

The `Mcp-Protocol-Version` header states the protocol version selected during
initialization.

`json_response=True` asks the MCP server to return ordinary JSON responses for
request/response exchanges. The transport can still use a Server-Sent Events
(SSE) stream for asynchronous server-to-client traffic.

### 2.4 ASGI connects Python web components

ASGI is the asynchronous interface between Uvicorn, FastAPI, middleware, and
the mounted MCP application. An ASGI application is called with:

```python
await app(scope, receive, send)
```

- `scope` describes the connection: method, path, headers, and connection type.
- `receive()` yields request body chunks and disconnect events.
- `send(message)` emits response status, headers, and body chunks.

Because the tracing middleware wraps `receive` and `send`, it can observe every
HTTP request handled by the mounted MCP application without knowing which MCP
method is inside the body.

### 2.5 AnyIO streams connect the client transport to ClientSession

The MCP HTTP transport converts network responses into typed SDK messages and
places them on asynchronous object streams. `ClientSession` consumes one stream
and writes to another.

The project places transparent proxies around those streams:

```text
ClientSession
    │
    ├── TracedSendStream ──> MCP HTTP transport ──> network
    │
    └── TracedReceiveStream <─ MCP HTTP transport <─ network
```

This captures parsed JSON-RPC objects at the point where they enter or leave
the high-level client.

## 3. Repository architecture

```text
mcp-studio/
├── pyproject.toml
├── uv.lock
├── README.md
├── docs/
│   └── code-flow.md
├── src/mcp_studio/
│   ├── client.py
│   ├── server.py
│   └── tracing.py
└── tests/
    └── test_tracing.py
```

### `pyproject.toml`

This is the package and dependency definition. It pins the MCP SDK, FastAPI,
and Uvicorn, defines development dependencies, and exposes two command-line
entry points:

```toml
mcp-studio-server = "mcp_studio.server:main"
mcp-studio-client = "mcp_studio.client:main"
```

`uv sync` resolves the project and installs it into `.venv`. `uv.lock` records
the exact transitive dependency graph so another machine can reproduce the
environment.

### `.env` and `.env.example`

`.env.example` is the safe, tracked configuration template. `.env` contains
local values and is ignored by Git because environment files commonly contain
credentials.

Both executable modules call `load_dotenv()` before reading module-level
configuration. `python-dotenv` searches for `.env`, parses its `KEY=value`
entries, and adds missing values to `os.environ`. It does not replace variables
already exported by the parent shell unless explicitly configured to do so.

Configuration precedence is:

```text
client command-line option
  → existing shell environment variable
  → value loaded from .env
  → hard-coded safe default
```

The server has no command-line configuration layer, so its shell or `.env`
values take precedence over code defaults.

### `server.py`

This module builds two applications:

1. `mcp`, a `FastMCP` protocol server.
2. `app`, a FastAPI ASGI application that hosts it.

The final composition is:

```text
Uvicorn
  └── FastAPI app
        ├── GET /health
        └── /mcp mount
              └── TraceASGIMiddleware
                    └── FastMCP Streamable HTTP app
```

`streamable_http_path="/"` matters because FastAPI already supplies the
external `/mcp` mount. The nested MCP application therefore handles `/` inside
that mount, producing the public endpoint `/mcp/`.

`stateless_http=False` creates stateful sessions. This is what makes the session
identifier and final `DELETE` visible.

The tools are ordinary typed Python functions decorated with `@mcp.tool()`:

```python
@mcp.tool()
def add(a: float, b: float) -> dict[str, float]:
    return {"a": a, "b": b, "sum": a + b}
```

FastMCP uses the function name, docstring, parameter annotations, and return
annotation to generate the tool description, input JSON Schema, and output JSON
Schema returned by `tools/list`.

The FastAPI lifespan starts `mcp.session_manager.run()` before requests are
accepted and stops it during application shutdown. Starting a stateful
Streamable HTTP application without its session manager would leave the route
unable to create and manage sessions.

### `client.py`

`run_lifecycle` intentionally performs a small but complete session:

1. Create a transport connection.
2. Wrap its read and write streams with tracers.
3. Create `ClientSession`.
4. Initialize and negotiate features.
5. List tools.
6. Call one tool.
7. Exit the session context.
8. Exit the transport context, which terminates the HTTP session.

The nested `async with` blocks encode ownership:

```python
async with streamable_http_client(url) as (read, write, get_session_id):
    async with ClientSession(traced_read, traced_write) as session:
        ...
```

Resources are closed in reverse order. `ClientSession` stops its message
processing first. The outer HTTP transport then sends `DELETE` while it still
owns the connection and session ID.

`asyncio.run()` creates an event loop for the command-line program. The SDK uses
asynchronous I/O so it can wait for network traffic without blocking the whole
process.

### `learning.py`

`LearningController` adds an optional teaching layer around the client
lifecycle. It is disabled by default, so each `checkpoint` immediately returns
and normal execution is uninterrupted.

When `MCP_LEARNING_MODE=true`, each checkpoint prints a JSON snapshot containing
the step name and relevant state. Two break styles are available:

- `pause` uses `asyncio.to_thread(input, ...)` to wait for Enter without
  blocking the event loop that services MCP transport tasks.
- `debugger` calls Python's `breakpoint()`, allowing `step` and `snapshot` to be
  inspected in pdb or an attached IDE debugger.

The checkpoints surround transport creation, initialization, tool discovery,
tool invocation, client-session closure, and transport teardown. They do not
reimplement or modify the protocol; they pause immediately before or after SDK
operations.

One subtle boundary is initialization. `ClientSession.initialize()` sends the
`initialize` request, receives its result, and sends
`notifications/initialized` as one high-level SDK operation. The learning
controller therefore pauses before and after that operation, while the wire
tracer still shows all three individual JSON-RPC messages.

### `tracing.py`

This module contains the reusable observation framework. It is deliberately
independent of methods such as `tools/list` and `tools/call`.

`WireTracer` converts an event to a stable `TraceEvent`, prints pretty JSON to
standard error, and appends compact JSON to a JSON Lines file.

JSON Lines stores one complete JSON value per line. It is useful because events
can be appended as they occur and later processed one record at a time without
loading the entire file.

`_jsonable` normalizes:

- Pydantic SDK models through `model_dump`
- SDK `SessionMessage` wrappers through their `message` attribute
- byte strings as JSON when possible, otherwise as text
- nested dictionaries and sequences recursively

`TracedSendStream` records a message before forwarding `send`. This means the
trace represents the attempt to send, even if the network later fails.

`TracedReceiveStream` supports both `receive()` and asynchronous iteration
because the SDK uses the stream in both ways. It also delegates async
context-manager operations and unknown attributes to remain transparent.

`TraceASGIMiddleware` reads and buffers the complete HTTP request body, records
it, and then replays the same ASGI messages to FastMCP. On the response path it
collects body chunks, records the complete response, and forwards every chunk
to Uvicorn.

Header values capable of containing credentials are redacted unless
`MCP_TRACE_SHOW_SECRETS=1` is explicitly set.

## 4. Complete lifecycle walkthrough

The following sequence includes both protocol messages and transport events.

```text
ClientSession       Client HTTP transport       FastMCP server
     │                        │                         │
     │ initialize             │                         │
     │───────────────────────>│ POST initialize         │
     │                        │────────────────────────>│
     │                        │ 200 + session + result  │
     │ initialize result      │<────────────────────────│
     │<───────────────────────│                         │
     │ initialized notice     │ POST notification       │
     │───────────────────────>│────────────────────────>│
     │                        │ 202 acknowledgement     │
     │                        │<────────────────────────│
     │                        │ GET event stream        │
     │                        │────────────────────────>│
     │ tools/list             │ POST tools/list         │
     │───────────────────────>│────────────────────────>│
     │ list result            │<────────────────────────│
     │<───────────────────────│                         │
     │ tools/call             │ POST tools/call         │
     │───────────────────────>│────────────────────────>│
     │ call result            │<────────────────────────│
     │<───────────────────────│                         │
     │ close                  │ DELETE + session ID     │
     │───────────────────────>│────────────────────────>│
     │                        │ 200; event stream ends  │
     │                        │<────────────────────────│
```

### Step 1: Uvicorn starts the application

The server command invokes `server.main()`, which calls `uvicorn.run`. Uvicorn
imports the FastAPI application and enters its lifespan. The lifespan enters
the MCP session manager and then yields control, meaning the application is
ready to receive traffic.

### Step 2: the client creates transport infrastructure

`streamable_http_client` creates an HTTP client, internal tasks, and the AnyIO
streams used by `ClientSession`. At this point there is transport
infrastructure, but MCP negotiation has not happened yet.

### Step 3: `initialize`

`session.initialize()` creates request ID `0` and sends:

```json
{
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {},
    "clientInfo": {
      "name": "mcp",
      "version": "0.1.0"
    }
  },
  "jsonrpc": "2.0",
  "id": 0
}
```

The server selects a compatible protocol version, creates a session ID, and
returns its capabilities and identity. The observed server capabilities
include tools, prompts, and resources. A capability says what a peer supports;
it does not necessarily mean the corresponding list contains items.

The server's advertised version is the MCP SDK version because no separate
application version was supplied to FastMCP.

### Step 4: `notifications/initialized`

After accepting the initialization result, the client sends
`notifications/initialized`. This changes the session from negotiation to
normal operation. It is a notification, so there is no JSON-RPC result. HTTP
`202 Accepted` confirms transport-level acceptance.

### Step 5: the event stream

The client transport may open `GET /mcp/` with `Accept: text/event-stream`.
This gives the server a channel for messages it initiates rather than direct
responses to a client request. It can carry notifications, progress, logging,
or requests for client-supported features.

This GET can remain open while later POST requests occur on other connections.
That is normal asynchronous behavior, not a duplicate session.

### Step 6: `tools/list`

`session.list_tools()` sends request ID `1`. FastMCP inspects registered
functions and returns tool metadata and JSON Schemas.

For `add`, the schema states that `a` and `b` are required numbers. A client can
use that schema to validate or construct arguments before invoking the tool.
The source of truth remains the Python type annotations.

### Step 7: `tools/call`

`session.call_tool("add", {"a": 20, "b": 22})` sends request ID `2`. FastMCP:

1. Resolves the registered tool by name.
2. Validates arguments against the generated input model.
3. Calls the Python function.
4. Validates and serializes its return value.
5. Produces MCP content blocks and structured content.

The result contains both:

- `content`, portable MCP content blocks that clients can render or pass to a
  model.
- `structuredContent`, the machine-readable object described by the output
  schema.

`isError: false` means the tool execution succeeded.

### Step 8: graceful session termination

Leaving the transport context sends:

```text
DELETE /mcp/
Mcp-Session-Id: <the negotiated session>
Mcp-Protocol-Version: 2025-11-25
```

The server removes the session and ends its associated event stream.

There is no JSON-RPC `shutdown` method in this MCP lifecycle. The `DELETE`
request is the graceful session-termination mechanism for stateful Streamable
HTTP. Separately, stopping Uvicorn ends the entire server process through the
FastAPI lifespan.

## 5. How to read the traces

Client traces and server traces intentionally show different views:

- `traces/client.jsonl` records typed JSON-RPC entering and leaving
  `ClientSession`, plus local lifecycle milestones.
- `traces/server.jsonl` records HTTP requests and responses, including headers,
  session information, empty acknowledgements, the event stream, and DELETE.

Seeing the same logical operation in both files is expected:

```text
client JSON-RPC send
    ↓ serialized by the SDK
server HTTP request
    ↓ handled by FastMCP
server HTTP response
    ↓ parsed by the SDK
client JSON-RPC receive
```

Important trace fields:

| Field            | Meaning                                                 |
|------------------|---------------------------------------------------------|
| `sequence`       | Order within that tracer process                        |
| `timestamp`      | UTC wall-clock time for comparison across processes     |
| `elapsed_ms`     | Time since that tracer was created                      |
| `side`           | `client` or `server`                                    |
| `layer`          | `application`, `lifecycle`, `jsonrpc`, or `http`        |
| `direction`      | Logical flow direction                                  |
| `event`          | Local milestone, send/receive, or HTTP status/path      |
| `correlation_id` | JSON-RPC request ID, MCP session ID, or unique event ID |
| `data`           | Normalized headers, body, SDK model, or metadata        |

Sequence numbers cannot be compared directly across the two processes because
each tracer has its own counter. Use timestamps, JSON-RPC IDs, and session IDs
to correlate them.

## 6. Why future calls are traced automatically

A fragile design would place a log statement around every operation:

```python
log("calling add")
await session.call_tool("add", ...)
log("called add")
```

That only covers calls remembered by the developer. A newly added method could
silently bypass logging.

This project instead uses boundary interception:

```text
all client protocol calls ──> traced streams ──> HTTP transport
all server MCP traffic ─────> ASGI middleware ─> FastMCP
```

Every call must cross those boundaries, so the framework is open for new
operations but closed to repeated tracing changes. This is the same basic idea
used by HTTP access logs, database instrumentation, and distributed tracing
agents.

For example, adding a new tool requires only its business logic:

```python
@mcp.tool()
def multiply(a: float, b: float) -> dict[str, float]:
    """Multiply two numbers."""
    return {"product": a * b}
```

Calling it uses the normal SDK API:

```python
result = await session.call_tool(
    "multiply",
    arguments={"a": 6, "b": 7},
)
```

The existing wrappers automatically capture the updated `tools/list`,
`tools/call`, result, HTTP traffic, schemas, and session headers.

The same principle applies to resources, prompts, notifications, and future
protocol methods because tracing does not branch on method names.

## 7. Concurrency and ordering

The application is asynchronous. Several things may be active at once:

- the client receive loop
- an open server-to-client event stream
- one or more POST requests
- FastMCP request handling
- Uvicorn connection tasks

Therefore, traces describe observed event order, not a single global sequence.
JSON-RPC IDs provide request/response correlation, and `Mcp-Session-Id`
provides session correlation.

`WireTracer.record` currently writes synchronously. That keeps this learning
project simple and ensures each line is flushed immediately, but a
high-throughput production service would usually send events through a queue to
an asynchronous or external log processor.

## 8. Validation, schemas, and serialization

FastMCP and the SDK use Pydantic models. Pydantic turns Python types into:

- runtime validation rules
- JSON Schema
- JSON-compatible serialized values

For example, `a: float` accepts JSON numbers and the return type
`dict[str, float]` describes an object whose values are numbers.

`model_dump(mode="json", by_alias=True)` is used in tracing because SDK models
often expose Python-friendly attribute names while the wire protocol requires
aliases such as `protocolVersion` and `serverInfo`.

The tracer observes serialized protocol meaning, while the tool function stays
focused on ordinary Python inputs and outputs.

## 9. Error boundaries

Errors can arise at several distinct layers:

| Layer        | Example                                   | Observable form                |
|--------------|-------------------------------------------|--------------------------------|
| Tool         | Tool raises or returns an execution error | MCP call result with `isError` |
| MCP/JSON-RPC | Unknown method or invalid request         | JSON-RPC `error` object        |
| HTTP         | Wrong route or unacceptable media type    | HTTP 4xx/5xx                   |
| Session      | Missing or expired session ID             | HTTP or JSON-RPC session error |
| Network      | Server unavailable                        | Client transport exception     |
| Process      | Startup configuration failure             | Uvicorn/lifespan error         |

Keeping these layers separate makes diagnosis much faster. An HTTP `200` does
not by itself prove a tool succeeded; inspect the JSON-RPC result and
`isError`. Conversely, a network connection failure occurs before JSON-RPC can
return any error.

## 10. Security and operational considerations

The tracer records complete bodies. That is ideal for learning but can expose:

- tool arguments and results
- private resource contents
- personally identifiable information
- authentication credentials

Authorization and cookie headers are redacted by default. Body fields are not
selectively redacted. Do not enable `MCP_TRACE_SHOW_SECRETS=1` or retain raw
trace files in an untrusted environment.

For production use, consider:

- field-level body redaction
- maximum captured body sizes
- log rotation and retention policies
- asynchronous trace exporting
- access controls on trace files
- TLS and MCP authentication
- explicit CORS policy for browser clients
- metrics alongside detailed event traces

The middleware buffers complete request and response bodies to make them easy
to inspect. That trades memory for clarity. A production tracer should cap or
stream large payloads, especially resources and long-lived event streams.

## 11. Suggested experiments

These exercises make the protocol behavior concrete:

1. Call `echo` and correlate request ID `2` in both trace files.
2. Add `multiply`, restart the server, and observe its generated schema in
   `tools/list` without changing `tracing.py`.
3. Pass an invalid argument and compare transport success with protocol-level
   validation failure.
4. Change `stateless_http` to `True` and compare session headers and teardown.
5. Set `json_response=False` and observe how response delivery changes.
6. Add a resource and compare `resources/list` with `resources/read`.
7. Add a server notification and watch it arrive over the event stream.

## 12. Mental model to keep

When reading or extending the code, keep this chain in mind:

```text
Python method call
  → MCP operation
  → JSON-RPC object
  → HTTP request or event-stream message
  → ASGI events
  → FastMCP dispatch
  → typed Python tool
  → the same layers in reverse for the result
```

The SDK owns protocol correctness. FastAPI owns application composition.
Uvicorn owns network serving. The tracing framework observes stable boundaries.
The tool functions own business logic. Keeping those responsibilities separate
is what makes the project understandable now and extensible later.
