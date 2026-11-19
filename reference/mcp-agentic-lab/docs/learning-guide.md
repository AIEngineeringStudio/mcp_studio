# MCP Agentic Lab: Teaching and Learning Guide

This guide explains the repository as a system: the concepts it demonstrates,
why each abstraction exists, how control and data move through the code, and how
to learn by changing it. Read it once from top to bottom, then use the module
walkthroughs and labs as a reference.

## 1. What you will learn

By the end, you should be able to explain and demonstrate:

- what MCP hosts, clients, servers, tools, resources, and prompts do;
- how MCP uses JSON-RPC messages without being tied to one transport;
- how stdio and Streamable HTTP carry the same protocol differently;
- how the official Python SDK derives tool schemas from Python types;
- how a client discovers capabilities and invokes a tool;
- how to observe traffic at raw, decoded, logging, and tracing layers;
- how plan/act/observe agent loops use MCP tools;
- why model, agent, transport, and server concerns are kept separate;
- where validation, redaction, timeouts, policy, and authorization belong;
- how to extend this lab with new tools or a real model provider.

### Progression at a glance

Do not try to master every layer at once. Use this sequence:

| Level | Focus | Completion evidence |
|---|---|---|
| 0: Orientation | Run the examples and identify components | You can point to host, client, transport, and server |
| 1: Novice | Tools, JSON-RPC, stdio, schemas | You add and call a tested tool |
| 2: Intermediate | HTTP, resources, prompts, errors, recording | You compare both transports and diagnose a failure |
| 3: Advanced | Agent loop, model adapters, tracing, policy | A real or simulated model safely uses multiple tools |
| 4: Expert | Security, scaling, resilience, governance | You can design a production-ready MCP platform |

Each later section labels the level where the material becomes important. The
full staged curriculum is in section 20.

### Guide map

1. **Level 0 — Orientation:** setup and the core mental model.
2. **Level 1 — Foundations:** capabilities, JSON-RPC, repository structure, and
   the layered architecture.
3. **Level 1 — Implementation:** configuration, server, client, and the complete
   stdio flow.
4. **Level 2 — Transports and observability:** Streamable HTTP, wire recording,
   middleware, logs, and traces.
5. **Level 3 — Agentic systems:** model/tool interfaces, plan-act-observe, safety
   boundaries, and tests.
6. **Levels 0–4 — Practice:** staged curriculum, labs, and mastery checks.
7. **Levels 3–4 — Engineering judgment:** debugging, tradeoffs, production
   security, and a final mastery project.

# Part I — Level 0: Orientation

This part assumes no MCP knowledge. Its goal is to let you run the system and
build a correct mental picture before studying implementation details.

## 2. Prerequisites and first run `[Level 0]`

You should be comfortable with basic Python functions, classes, type hints,
`async`/`await`, and JSON. You do not need prior MCP or OpenTelemetry knowledge.

Install and verify the project:

```bash
cd /Users/sreedhar/Desktop/codebases/mcp-agentic-lab
cp .env.example .env
uv sync --all-extras
uv run pytest
```

Run the default stdio interaction:

```bash
MCP_LAB_TRACE_EXPORTER=none uv run mcp-lab-client
```

Expected high-level result:

```
Available tools: add, divide
...
"result": 15.0
```

Run the agent demo:

```bash
MCP_LAB_TRACE_EXPORTER=none uv run mcp-lab-agent "Add 20 and 22"
```

Expected result:

```
The result is 42.0.
```

Disabling console trace export in these first commands makes the functional
output easier to read. Tracing is covered later.

## 3. The core mental model `[Level 0]`

MCP separates the application that wants capabilities from the application that
provides them.

```
┌──────────────────────────────────────────────────────────────────┐
│ Host application                                                 │
│                                                                  │
│  user ──► agent/model ──► MCP client                             │
└───────────────────────────────┬──────────────────────────────────┘
                                │ MCP messages
                   stdio or Streamable HTTP
                                │
┌───────────────────────────────▼──────────────────────────────────┐
│ MCP server                                                       │
│                                                                  │
│  capability discovery ──► tools / resources / prompts            │
└──────────────────────────────────────────────────────────────────┘
```

The roles are:

- **Host**: the user-facing application containing one or more MCP clients. An
  IDE, desktop assistant, or this repository's agent demo can act as a host.
- **Client**: maintains the relationship with one server and sends MCP methods.
- **Server**: advertises capabilities and handles requests.
- **Transport**: moves messages. It does not decide what a tool means.
- **JSON-RPC**: the envelope format used to name methods, carry parameters, and
  correlate requests with responses.

The important architectural idea is that MCP is the protocol, not the transport.
`tools/call` means the same thing over stdio and Streamable HTTP.

# Part II — Level 1: MCP Foundations

This part introduces the vocabulary and protocol structure needed to understand
the code. It is still beginner material; each concept is tied to a concrete file
or captured message.

## 4. MCP capability types `[Level 1]`

This server exposes all three common user-facing capability types.

### Tools

A tool performs an operation. It has a name, description, input schema, and
possibly an output schema. Models can select tools and create their arguments.

This project exposes:

- `add(a, b)`;
- `divide(numerator, denominator)`.

Tools should be treated as actions even when the current examples are harmless.
In a real server, tools might send email, modify a database, or start a deployment.

### Resources

A resource exposes addressable context, identified by a URI. It is closer to a
readable document or data item than an action.

This project exposes `notes://{topic}`, for example:

```
notes://mcp
notes://json-rpc
notes://tracing
```

### Prompts

A prompt is a reusable prompt template supplied by a server. It helps hosts use
domain-specific instructions consistently.

This project exposes `plan_task(goal)`, which produces instructions for breaking
a goal into safe tool-assisted steps.

## 5. JSON-RPC in one page `[Level 1]`

A JSON-RPC request contains a protocol marker, request ID, method, and optional
parameters:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": {"a": 7, "b": 8}
  }
}
```

A successful response repeats the ID and contains `result`:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "structuredContent": {
      "operation": "add",
      "expression": "7.0 + 8.0",
      "result": 15.0
    },
    "isError": false
  }
}
```

The matching `id` is how a client pairs a response with a request. A protocol
error uses `error` instead of `result`. A notification has a method but no ID and
does not receive a response.

The actual MCP messages also include `_meta`. In the current protocol, the SDK
uses it to carry information such as protocol version, client identity, client
capabilities, and server identity. Let the SDK manage this metadata unless you
are deliberately studying or extending the protocol.

## 6. Repository map `[Level 1]`

```
mcp-agentic-lab/
├── pyproject.toml              dependencies, commands, and tool settings
├── uv.lock                     reproducible dependency resolution
├── .env.example                configuration reference
├── Makefile                    common developer commands
├── docs/
│   ├── architecture.md         concise architecture summary
│   ├── exercises.md            short challenge list
│   └── learning-guide.md       this course-style guide
├── src/mcp_lab/
│   ├── agent/
│   │   ├── core.py             provider-neutral agent loop
│   │   └── demo.py             deterministic teaching model
│   ├── client/
│   │   ├── observed.py         client facade and stdio target builder
│   │   └── __main__.py         client command-line entry point
│   ├── observability/
│   │   ├── config.py           typed environment configuration
│   │   ├── logging.py          structured logging and trace correlation
│   │   └── tracing.py          OpenTelemetry provider/exporters
│   ├── server/
│   │   ├── app.py              MCP capabilities and server factory
│   │   ├── middleware.py       decoded server traffic recorder
│   │   └── __main__.py         transport selection and startup
│   └── wire/
│       ├── recorder.py         reusable JSONL recorder
│       ├── redaction.py        recursive secret masking
│       ├── stdio_proxy.py      exact stdio traffic capture
│       └── http_middleware.py  HTTP request/response body capture
├── tests/                      behavior-focused tests
└── var/                        generated, git-ignored observations
```

## 7. Layered architecture `[Level 1]`

The project deliberately records the same interaction at several layers.

```
AgentModel
    │ decision: ToolCall or FinalAnswer
    ▼
ToolCallingAgent
    │ tool gateway interface
    ▼
MCPToolGateway
    │ typed client operation
    ▼
ObservedMCPClient ───────────────► var/client-wire.jsonl
    │
    ├── stdio proxy ─────────────► var/wire.jsonl
    │       │
    │       ▼
    └── Streamable HTTP middleware► var/http-wire.jsonl
            │
            ▼
MCPServer middleware ────────────► var/server-wire.jsonl
    │
    ▼
tool/resource/prompt handler
```

No single observation is best for every question:

- raw transport capture answers, "What bytes or HTTP bodies crossed the boundary?";
- client records answer, "What operation did my host request and receive?";
- server records answer, "Which handler ran, how long did it take, and did it fail?";
- logs answer, "What noteworthy application events occurred?";
- traces answer, "How is work connected across components and how long did it take?".

# Part III — Level 1: Implementing a Working MCP System

Now follow the actual startup path from configuration to server to client. The
sections are ordered so each one depends only on concepts already introduced.

## 8. Configuration flow `[Level 1]`

Start with `src/mcp_lab/observability/config.py`.

`Settings` is a Pydantic settings model. Every field maps to an environment
variable prefixed with `MCP_LAB_`. For example:

```
server_transport  -> MCP_LAB_SERVER_TRANSPORT
server_port       -> MCP_LAB_SERVER_PORT
trace_exporter    -> MCP_LAB_TRACE_EXPORTER
wire_log_enabled  -> MCP_LAB_WIRE_LOG_ENABLED
```

Pydantic converts strings from the environment into typed values and validates
constraints. A port must be from 1 through 65535, and transport must be either
`stdio` or `streamable-http`.

`get_settings()` is cached. Code anywhere in one process receives the same
settings instance instead of reparsing `.env` repeatedly.

Configuration precedence is effectively:

```
explicit Settings constructor values
        over
environment variables
        over
.env values
        over
class defaults
```

This is why tests can construct `Settings(trace_exporter="none")` without
depending on a developer's machine configuration.

## 9. Building the MCP server `[Level 1]`

The main server definition is `src/mcp_lab/server/app.py`.

### 9.1 Why use a factory?

`create_server()` builds and returns an `MCPServer`. A factory is preferable to
one hard-coded global because tests can inject alternate settings and recorders:

```python
server = create_server(
    Settings(wire_log_enabled=False),
    recorder=JsonlWireRecorder(temp_path),
)
```

The module still creates `mcp = create_server()` at the bottom. The MCP Inspector
and other loaders need an importable server object. Thus the code supports both
dependency injection and conventional SDK tooling.

### 9.2 Server identity and middleware

The constructor supplies:

- a human-readable server name;
- a version;
- instructions for clients/models;
- `WireRecordingMiddleware` for decoded traffic observation.

The official SDK also installs its own OpenTelemetry middleware. Once this
project configures an exporter, SDK-created MCP spans become visible without
wrapping every handler manually.

### 9.3 Tool schema generation

Consider `add`:

```python
@server.tool(title="Add numbers")
def add(
    a: float = Field(description="First number"),
    b: float = Field(description="Second number"),
) -> Calculation:
    return Calculation(operation="add", expression=f"{a} + {b}", result=a + b)
```

The SDK uses the signature, type hints, Pydantic field descriptions, docstring,
and return model to derive:

- an input JSON Schema requiring numeric `a` and `b`;
- an output JSON Schema matching `Calculation`;
- a tool description from the docstring;
- a display title from the decorator.

This generated schema is returned by `tools/list`. A model does not inspect the
Python function; it receives the name, description, and JSON Schema.

Returning a Pydantic model produces two useful representations:

- `content`: MCP content blocks suitable for a model;
- `structured_content`: a dictionary suitable for application code.

The client uses `structured_content` when available because it avoids parsing a
human-readable text block back into data.

### 9.4 Error behavior

`divide` rejects a zero denominator by raising `ValueError`. The high-level
`MCPServer` tool wrapper converts ordinary tool failures into a model-visible
tool result with `is_error=True`. This lets an agent observe the error and decide
whether to retry with different arguments.

Do not confuse a tool failure with a JSON-RPC protocol error:

- a **tool failure** says the request was valid but the operation failed;
- a **protocol error** says the request itself could not be processed correctly.

Agents can usually reason about tool failures. Protocol errors are normally
handled by client/application code.

### 9.5 Resources and prompts

The resource decorator contains a URI template:

```python
@server.resource("notes://{topic}")
```

When a client reads `notes://tracing`, the SDK extracts `topic="tracing"` and
calls `read_note`.

The prompt decorator registers a callable template. Calling `plan_task` with a
goal returns text; it does not itself invoke a model or tool.

## 10. Starting the server `[Level 1]`

`src/mcp_lab/server/__main__.py` is the executable boundary.

Its startup order matters:

1. Load typed settings.
2. Configure structured logging.
3. Configure the global OpenTelemetry provider.
4. Build the MCP server.
5. Select the transport.

For stdio:

```python
server.run(transport="stdio")
```

The process waits for JSON-RPC on stdin and writes protocol responses to stdout.
All application logging must go to stderr. A stray `print()` to stdout can be
mistaken for protocol data and break the connection.

For Streamable HTTP:

```python
app = server.streamable_http_app(json_response=True, stateless_http=True)
observed_app = JsonRpcHTTPRecorderMiddleware(app, recorder, ...)
uvicorn.run(observed_app, host=..., port=...)
```

The server becomes an ASGI application, the HTTP recording middleware wraps it,
and Uvicorn binds it to a host and port. `stateless_http=True` makes each modern
request independently routable. `json_response=True` makes this lab's response
bodies convenient to inspect as JSON.

## 11. Building and using the client `[Level 1]`

The client is split between a reusable facade in
`src/mcp_lab/client/observed.py` and command-line orchestration in
`src/mcp_lab/client/__main__.py`.

### 11.1 Choosing a target

The official `Client` chooses its transport from the target:

- a URL such as `http://127.0.0.1:8000/mcp` means Streamable HTTP;
- `StdioServerParameters` means launch and communicate with a local subprocess;
- a server object means connect in process, which is ideal for tests.

The CLI applies that rule here:

```python
target = url if url else default_stdio_target(settings, wiretap=wiretap)
transport = "streamable-http" if url else "stdio"
```

The rest of the client flow is transport-neutral.

### 11.2 Why `default_stdio_target` looks unusual

Without recording, the subprocess hierarchy could be:

```
client process ──starts──► server process
```

With the wiretap enabled, it becomes:

```
client process ──starts──► stdio proxy ──starts──► server process
```

`default_stdio_target()` constructs the second command. The client believes the
proxy is the MCP server. The proxy transparently forwards stdin and stdout, so
the MCP behavior is unchanged while exact messages can be captured.

The child receives an explicit, minimal configuration. In particular,
`MCP_LAB_SERVER_TRANSPORT=stdio` prevents a developer's shell setting from
accidentally making the child start an HTTP server.

### 11.3 Async context management

`ObservedMCPClient` delegates connection lifecycle to the SDK:

```python
async with ObservedMCPClient(...) as client:
    tools = await client.list_tools()
    result = await client.call_tool("add", {"a": 7, "b": 8})
```

Entering the context opens the transport and performs discovery. Leaving it
closes streams, HTTP resources, and any child process. Avoid manually creating a
client and forgetting to close it.

### 11.4 The facade's responsibility

The facade wraps three operations:

- `list_tools()`;
- `call_tool(name, arguments)`;
- `read_resource(uri)`.

For each operation it records the semantic request, calls the real SDK client,
then records the typed result or exception. It does not attempt to reimplement
MCP. The SDK remains responsible for protocol metadata, request IDs, schema
handling, transport behavior, and response parsing.

The facade's JSON-RPC-looking records are reconstructed diagnostic events. They
are not byte-exact wire messages. Use the transport recorder when exact framing,
IDs, or metadata matter.

## 12. End-to-end stdio flow `[Level 1]`

This is the most useful first code flow to learn.

```
1. shell starts mcp-lab-client
2. client builds StdioServerParameters for stdio_proxy
3. SDK starts stdio_proxy as a child
4. stdio_proxy starts mcp-lab-server as its child
5. client sends server/discover
6. proxy records and forwards the request
7. server middleware records the decoded request
8. SDK discovery handler returns capabilities
9. server middleware records the decoded response
10. proxy records and forwards the exact response
11. client sends tools/list
12. server returns generated tool schemas
13. client sends tools/call for add
14. add returns Calculation
15. SDK serializes content and structuredContent
16. client prints the typed result
17. context exit closes stdin and both child processes shut down
```

The key topology is:

```
ObservedMCPClient
  stdin/stdout
      │
      ▼
stdio_proxy.py ──records every line──► var/wire.jsonl
  child stdin/stdout
      │
      ▼
MCPServer ──decoded middleware───────► var/server-wire.jsonl
```

### 12.1 The proxy's two concurrent pumps

`stdio_proxy.py` runs two `_forward` coroutines with `asyncio.gather`:

```
client stdin  ──► child stdin     direction=client_to_server
child stdout  ──► client stdout   direction=server_to_client
```

Each pump reads one newline-delimited protocol message, records it, writes it to
the other side, and calls `drain()` for flow control. Concurrent pumps are
necessary because requests and responses can travel independently.

The proxy inherits the child's stderr. Server logs therefore remain visible but
never enter the protocol stream.

The shutdown block terminates a lingering process group. This is defensive: a
cancelled client should not leave the server running in the background.

# Part IV — Level 2: Multiple Transports and Deep Observability

This part assumes you can already explain and modify the stdio tool flow. It
adds HTTP, multiple observation layers, middleware, structured logs, and traces.

## 13. End-to-end Streamable HTTP flow `[Level 2]`

Start the server:

```bash
MCP_LAB_SERVER_TRANSPORT=streamable-http \
MCP_LAB_TRACE_EXPORTER=none \
uv run mcp-lab-server
```

In another terminal, start the client:

```bash
MCP_LAB_TRACE_EXPORTER=none \
uv run mcp-lab-client --url http://127.0.0.1:8000/mcp
```

The flow is now:

```
ObservedMCPClient
      │ HTTP POST containing JSON-RPC
      ▼
Uvicorn
      │ ASGI messages
      ▼
JsonRpcHTTPRecorderMiddleware ───────► var/http-wire.jsonl
      │
      ▼
MCP Streamable HTTP application
      │ decoded MCP request
      ▼
WireRecordingMiddleware ─────────────► var/server-wire.jsonl
      │
      ▼
tool/resource/prompt handler
```

### 13.1 ASGI middleware mechanics

ASGI applications receive three values: `scope`, `receive`, and `send`.

- `scope` describes the request, including method and path.
- `receive()` yields request-body messages.
- `send(message)` emits response messages.

`JsonRpcHTTPRecorderMiddleware` replaces `receive` and `send` with small wrapper
functions. The wrappers collect body chunks and still pass every message to the
real application unchanged. In `finally`, the middleware joins the chunks and
records request and response bodies, byte lengths, status code, and truncation.

This is an important middleware rule: observation must not consume or modify a
message before the downstream application can process it.

### 13.2 What stays the same

The methods, schemas, arguments, results, agent loop, and decoded server
middleware do not change. Only connection setup and transport framing change.
That is the practical value of separating MCP from its transports.

## 14. Comparing the real message sequence `[Level 2]`

A successful client run captured this sequence in both transports:

| ID | Method | Purpose |
|---:|---|---|
| 1 | `server/discover` | Determine protocol support, server identity, instructions, and capabilities |
| 2 | `tools/list` | Retrieve available tools and their schemas |
| 3 | `tools/call` | Invoke `add` with `a=7` and `b=8` |

The modern discovery request includes metadata similar to:

```json
{
  "io.modelcontextprotocol/protocolVersion": "2026-07-28",
  "io.modelcontextprotocol/clientInfo": {
    "name": "mcp",
    "version": "0.1.0"
  },
  "io.modelcontextprotocol/clientCapabilities": {}
}
```

The discovery response advertises tools, resources, and prompts. The SDK's
client can also fall back to the older initialization flow when talking to an
older server. This compatibility behavior is why application code should use
`Client` rather than handcrafting setup messages.

The `tools/list` result contains the JSON Schemas generated from `add`, `divide`,
and `Calculation`. Inspect it directly:

```bash
jq 'select(.payload.result.tools != null)' var/wire.jsonl
```

The stdio and HTTP payloads are nearly identical. HTTP records additionally
contain `http_method`, `path`, and `status_code`.

## 15. Wire recording and redaction `[Level 2]`

### 15.1 JSON Lines

`JsonlWireRecorder` writes one complete JSON object per line. This format is
called JSON Lines or JSONL.

It is used instead of one large JSON array because:

- records can be appended without rewriting the file;
- `tail -f` can follow new events;
- one damaged line does not necessarily invalidate every other record;
- log shippers can process events incrementally.

Every record contains:

```
timestamp      UTC timestamp
direction      client_to_server or server_to_client
vantage_point  where the observation was made
transport      stdio or streamable-http
payload        sanitized request, response, or error
...            layer-specific fields such as duration or HTTP status
```

### 15.2 Making Python values serializable

`to_jsonable()` recursively handles:

- Pydantic models using aliases, so Python `structured_content` becomes wire-like
  `structuredContent`;
- dataclasses;
- exceptions as type/message objects;
- mappings and common collections.

This conversion belongs in the recorder rather than every caller.

### 15.3 Redaction

Before encoding, `redact()` recursively replaces values whose keys resemble
authorization, API key, password, secret, token, or cookie fields.

```json
{"api_key": "[REDACTED]"}
```

This is a safety baseline, not a complete data-loss-prevention system. Secrets
can appear in arbitrary fields or free text. Add domain-specific rules, access
controls, retention, and sampling before capturing real production traffic.

### 15.4 Truncation

Raw body recorders cap captured bytes with `wire_max_body_bytes`. The record
retains the original byte length and a `truncated` flag. Size limits prevent a
large tool result from exhausting memory or filling a disk unexpectedly.

## 16. Server middleware `[Level 2]`

`WireRecordingMiddleware` runs around every decoded inbound MCP message:

```
record request
start timer
    call next middleware/handler
record result or exception
record duration
return or re-raise
```

`call_next(ctx)` is the continuation of the middleware chain. Not calling it
would short-circuit request handling. Returning a different result would replace
the handler response. This project observes only; it does not change behavior.

The `try`/`except` is required so failed handlers are still recorded with timing
information. The exception is re-raised so normal SDK error handling continues.

This middleware sees decoded values after transport parsing. It works for both
stdio and HTTP, which makes it the best general layer for method latency and
application-level diagnostics.

## 17. Structured logging and tracing `[Level 2]`

Logging, wire recording, and tracing overlap, but they answer different questions.

### 17.1 Structured logging

`configure_logging()` configures standard logging and structlog together. Every
log gets a timestamp and level. JSON mode makes fields machine-queryable:

```bash
MCP_LAB_LOG_FORMAT=json MCP_LAB_TRACE_EXPORTER=none uv run mcp-lab-client
```

If a valid span is active, `_add_trace_context` adds its 32-character trace ID
and 16-character span ID to the event. This lets an operator move from a log
record to the corresponding distributed trace.

All logs use stderr. This is mandatory for stdio servers because stdout is the
MCP protocol channel.

### 17.2 OpenTelemetry setup

`configure_tracing()` installs one process-wide `TracerProvider`. A lock and
`_configured` flag prevent duplicate setup.

The provider has a `Resource` describing the service name and environment. It
then installs one exporter path:

- `none`: tracing setup is skipped;
- `console`: completed spans are printed for local learning;
- `otlp`: spans are sent to an OpenTelemetry collector.

`BatchSpanProcessor` exports completed spans in batches rather than blocking the
application on every span.

The SDK creates server spans automatically. The agent code adds `agent.run` and
`agent.tool_call` spans, so a trace can connect model reasoning orchestration to
the MCP request and server work.

### 17.3 A useful diagnostic hierarchy

When something fails, ask questions in this order:

1. **Application output:** did the command complete?
2. **Structured logs:** which component reported a problem?
3. **Trace:** where was time spent and where did status become an error?
4. **Semantic records:** which MCP method and typed result were involved?
5. **Raw wire:** what exact message crossed the transport?

Starting at the raw wire for every problem creates noise. Descend only as needed.

# Part V — Level 3: Agentic Systems

Only begin this part once MCP works without a model. Agentic behavior becomes
much easier to reason about when tool discovery and invocation are already clear.

## 18. The agent architecture `[Level 3]`

The agent code is intentionally independent of a specific model vendor.

### 18.1 Decisions, not magic

At each step, a model returns one of two values:

```python
ToolCall(name="add", arguments={"a": 20, "b": 22})
```

or:

```python
FinalAnswer(text="The result is 42.")
```

This turns an agent into a comprehensible state machine rather than an opaque
framework.

### 18.2 Protocol-based dependency inversion

`AgentModel` and `ToolGateway` are Python `Protocol` interfaces.

```
ToolCallingAgent
    ├── depends on AgentModel protocol
    └── depends on ToolGateway protocol
```

It does not depend directly on OpenAI, another model provider, or the MCP SDK.
That yields three benefits:

- tests can use small fake implementations;
- a model provider can be replaced without rewriting the loop;
- MCP can be replaced by another tool backend if needed.

### 18.3 Adapting MCP into the agent

`MCPToolGateway` translates SDK types into agent types:

- `list_tools()` becomes a list of `ToolDefinition` values;
- `call_tool()` becomes `invoke()`;
- `structured_content` becomes the observation returned to the model;
- content blocks are the fallback when structured output is unavailable.

This is an adapter pattern: each side keeps its natural data model.

### 18.4 The plan/act/observe loop

`ToolCallingAgent.run()` performs:

```
DISCOVER tools
    │
    ▼
ADD user prompt to messages
    │
    ▼
ASK model for a decision ◄────────────────────┐
    │                                         │
    ├── FinalAnswer ──► RETURN                │
    │                                         │
    └── ToolCall                              │
          │                                   │
          ├── verify tool was advertised      │
          ├── invoke through gateway           │
          ├── append call + observation        │
          └────────────────────────────────────┘
```

The loop has a maximum of eight steps by default. A step budget is a safety and
cost boundary: a confused model cannot call tools forever.

The advertised-tool check is another safety boundary. A model-generated name is
untrusted input. The agent rejects any tool not present in the discovered catalog.

### 18.5 Why the deterministic model matters

`DeterministicMathModel` is not pretending to be intelligent. It exists so you
can learn and test the orchestration without an API key, network call, cost, or
nondeterministic model output.

Its first decision parses two numbers and returns `ToolCall("add", ...)`. After
the tool observation is appended, its second decision returns `FinalAnswer`.
The same `ToolCallingAgent` can later use a real model adapter.

## 19. Tests as executable explanations `[Levels 1–3]`

The tests demonstrate three boundaries.

### `tests/test_server.py`

The SDK receives the server object directly:

```python
async with Client(server, raise_exceptions=True) as client:
    result = await client.call_tool(...)
```

This skips ports and subprocesses while exercising real MCP discovery, schema,
dispatch, and result handling. It is the fastest form of MCP integration test.

The tests verify both successful structured output and model-visible tool errors.

### `tests/test_agent.py`

Fake tools and a two-step fake model prove the agent loop independently of MCP.
Another test proves that an unadvertised tool is rejected.

### `tests/test_wire.py`

These tests verify recursive redaction and the invariant that every event is one
valid JSON object per line.

Together, the test pyramid is:

```
few live transport checks       stdio and HTTP commands
        ▲
MCP in-process integration      real SDK + real server
        ▲
focused unit tests              agent policy, redaction, recorder
```

# Part VI — Levels 0–4: Practice and Assessment

Use this part to turn the preceding explanation into hands-on skill. The stages
repeat the whole path as an actionable syllabus with mastery gates.

## 20. Novice-to-expert curriculum

The stages below are cumulative. Do the mastery check before advancing.

### Level 0 — Orientation

**Goal:** See the system work before reading implementation details.

1. Run `uv run pytest`.
2. Run the stdio client with tracing disabled.
3. Open `var/wire.jsonl` and find request IDs 1, 2, and 3.
4. Run the agent demo and identify the tool result.
5. Read sections 3 through 6 of this guide.

**Do not focus on yet:** ASGI internals, OpenTelemetry exporters, or model APIs.

**Mastery check:** Draw four boxes labeled host, client, transport, and server,
then explain what crosses each boundary.

### Level 1 — Novice: tools and stdio

**Goal:** Understand one complete local MCP request.

1. Read `server/app.py` and identify decorators, inputs, return types, and errors.
2. Read the first six lines of a fresh `var/wire.jsonl`.
3. Match `tools/list` schemas to the Python signatures.
4. Call a different tool:

   ```bash
   uv run mcp-lab-client \
     --tool divide \
     --arguments '{"numerator": 21, "denominator": 3}'
   ```

5. Add a `subtract(a, b)` tool returning `Calculation`.
6. Add an in-process test for its result.

**Concepts to know:** tool, JSON Schema, JSON-RPC ID, request, response, content,
structured content, stdio, stderr versus stdout.

**Mastery check:** Without running the code, predict the new `tools/list` entry
and the `tools/call` request for `subtract(10, 4)`.

### Level 2 — Intermediate: both transports and observability

**Goal:** Diagnose behavior across process and network boundaries.

1. Run the Streamable HTTP server and client.
2. Compare one `tools/call` entry in `wire.jsonl` and `http-wire.jsonl`.
3. Read `stdio_proxy.py` and explain its two concurrent data pumps.
4. Read `http_middleware.py` and explain `scope`, `receive`, and `send`.
5. Call `divide` with zero and compare:
   - terminal output;
   - `client-wire.jsonl`;
   - `server-wire.jsonl`;
   - raw transport records.
6. Use `ObservedMCPClient.read_resource("notes://tracing")` in a small example.
7. Run with JSON logs and identify structured fields.
8. Add a test proving a domain-specific secret key is redacted.

**Concepts to know:** ASGI, HTTP framing, middleware, semantic versus raw
recording, JSONL, redaction, truncation, typed settings, tool failure.

**Mastery check:** Given a failed request, explain which observation layer you
would inspect first and why.

### Level 3 — Advanced: agents, models, tracing, and policy

**Goal:** Build a controlled model-driven tool loop.

1. Read `agent/core.py` from the dataclasses down through `run()`.
2. Manually write the messages list after one tool call.
3. Extend the deterministic model to choose `divide` for division prompts.
4. Add a test for a two-tool, multi-step task.
5. Implement a real `AgentModel` adapter for your preferred provider.
6. Translate every `ToolDefinition` into that provider's tool schema format.
7. Translate provider tool calls back into this project's `ToolCall`.
8. Add a policy gateway that refuses or requests approval for selected tools.
9. Enable console tracing and correlate an agent span with MCP server spans.
10. Export traces through OTLP to a local collector.

**Concepts to know:** dependency inversion, adapter pattern, plan/act/observe,
step budgets, allowlists, approval, trace context, spans, resources, exporters.

**Mastery check:** Explain every trust boundary from model-generated arguments to
the final tool handler and name one control at each boundary.

### Level 4 — Expert: production design

**Goal:** Evolve the lab into a secure, observable, scalable service.

Design and, where useful, prototype:

1. authentication and per-tool authorization;
2. tenant-aware data isolation;
3. schema and business-rule validation;
4. rate limits, concurrency limits, deadlines, retries, and circuit breakers;
5. idempotency for tools with side effects;
6. human approval for irreversible actions;
7. prompt-injection defenses and untrusted-content labeling;
8. domain-specific data classification and redaction;
9. trace sampling, log retention, and audit trails;
10. horizontally scaled stateless HTTP deployment;
11. version compatibility and contract/conformance testing;
12. multi-server discovery, routing, and failure isolation;
13. evaluation datasets for tool selection and argument correctness;
14. cost, latency, and success-rate service-level objectives.

**Mastery check:** Produce an architecture decision record explaining transport,
identity, authorization, observability, failure handling, and deployment choices
for a real use case.

## 21. Guided implementation labs `[Levels 1–3]`

### Lab A — Add and test a new tool (novice)

Add this inside `create_server()`:

```python
@server.tool(title="Subtract numbers")
def subtract(a: float, b: float) -> Calculation:
    """Subtract the second number from the first."""
    return Calculation(
        operation="subtract",
        expression=f"{a} - {b}",
        result=a - b,
    )
```

Then add an in-process test. Verify:

- `subtract` appears in `tools/list`;
- its input schema requires `a` and `b`;
- its structured result equals the expected object;
- stdio and HTTP clients can both call it without code changes.

### Lab B — Trace an error (intermediate)

Run:

```bash
uv run mcp-lab-client \
  --tool divide \
  --arguments '{"numerator": 1, "denominator": 0}'
```

Answer:

1. Does the process fail, or does it receive a tool result?
2. Where does `isError` appear?
3. What does server middleware record?
4. Does the raw response contain `result` or top-level `error`?
5. How should an agent respond to this observation?

### Lab C — Add a model adapter (advanced)

Keep provider code outside `core.py`. The shape should resemble:

```python
class ProviderModel:
    def __init__(self, provider_client: object) -> None:
        self.provider_client = provider_client

    async def decide(
        self,
        messages: list[dict[str, object]],
        tools: list[ToolDefinition],
    ) -> ToolCall | FinalAnswer:
        provider_tools = [self._convert_tool(tool) for tool in tools]
        response = await self._request(messages, provider_tools)
        if self._contains_tool_call(response):
            return ToolCall(
                name=self._tool_name(response),
                arguments=self._tool_arguments(response),
            )
        return FinalAnswer(self._text(response))
```

The adapter owns provider-specific message formats. The core loop remains
unchanged. Validate provider-generated arguments before invocation even if the
provider claims to enforce a schema.

### Lab D — Add an approval policy (advanced)

Wrap a `ToolGateway` rather than modifying the agent loop:

```
ToolCallingAgent
      │
      ▼
ApprovalGateway
      │ if allowed/approved
      ▼
MCPToolGateway
```

The wrapper can classify tools as:

- read-only and automatically allowed;
- reversible but approval-requiring;
- irreversible and denied by default.

Test the policy with a fake gateway. Never rely on a model to approve its own
action.

# Part VII — Levels 3–4: Engineering Judgment and Production Design

The final learning part moves from making the lab work to operating, securing,
and evolving a real system.

## 22. Common failures and how to reason about them `[Level 3]`

| Symptom | Likely cause | First check |
|---|---|---|
| JSON parse/protocol errors on stdio | Something wrote non-protocol text to stdout | Move prints/logs to stderr |
| Client cannot connect over HTTP | Server not running, wrong URL/port, or bind policy | Server startup log and `/mcp` URL |
| Tool is missing | Decorator did not run or wrong server object loaded | `tools/list` record |
| Tool arguments rejected | Schema/type mismatch | Tool's `inputSchema` and request arguments |
| `is_error=True` | Tool executed but reported an operational failure | Tool content plus server record |
| Top-level JSON-RPC error | Invalid method/request or handler/protocol failure | Raw response `error` object |
| Empty `structured_content` | Tool returned only content blocks | Inspect `content` fallback |
| No trace output | Exporter disabled or process configured too late | `MCP_LAB_TRACE_EXPORTER` and startup order |
| Trace and logs do not correlate | Log occurred outside an active span | `trace_id` presence in log |
| Wire file exposes sensitive data | Key pattern did not cover the domain | Expand redaction and remove unsafe records |
| Agent loops repeatedly | Model is not using observations or task is impossible | Step transcript and `max_steps` |
| Agent calls invented tool | Untrusted model output | Advertised-tool allowlist rejection |

## 23. Important design decisions and tradeoffs `[Level 3]`

### High-level `MCPServer`

This lab favors schema derivation and decorators over manual protocol objects.
That is ideal for learning and most application servers. A low-level server is
appropriate when exact schemas or custom methods require full control.

### Facade instead of SDK subclassing

Composition keeps SDK internals replaceable and makes the observation behavior
explicit. The cost is that newly used client methods must be added to the facade.

### Separate raw and semantic records

One recorder cannot simultaneously be byte-exact, transport-neutral, and rich
with typed application context. Separate layers make each claim honest.

### Provider-neutral agent core

The adapter boundary adds a few small types, but avoids coupling orchestration,
tests, and policy to a vendor API.

### In-process tests plus live smoke checks

In-process tests are fast and deterministic. They do not prove process startup,
stdio forwarding, port binding, or HTTP behavior, so live checks still matter.

## 24. Security and production boundaries `[Level 4]`

Treat all of these as untrusted until proven otherwise:

- user prompts;
- model-selected tool names;
- model-generated arguments;
- resource contents;
- remote MCP servers;
- tool results returned to a model;
- commands or URLs supplied through configuration.

Production controls should include:

- server identity and authenticated clients;
- authorization at tool and resource level;
- input validation beyond structural JSON Schema;
- output validation and size limits;
- least-privilege credentials for tool implementations;
- explicit approval for consequential actions;
- subprocess command allowlists;
- outbound network restrictions;
- rate, concurrency, and time limits;
- idempotency and audit logging;
- secret management outside source and prompts;
- carefully governed wire capture.

The stdio target in this lab is constructed by trusted application code. Never
turn arbitrary model or user text into a subprocess command.

# Reference

The remaining sections are reference material and the expert capstone. They are
not prerequisites for earlier lessons.

## 25. Glossary

**Agent** — An orchestration loop that lets a model decide between answering and
using tools.

**ASGI** — Python interface connecting asynchronous web servers, middleware, and
applications.

**Capability discovery** — Learning what a server supports before using it.

**Content block** — MCP representation of model-consumable text, image, audio,
resource, or link content.

**Host** — User-facing application containing MCP clients.

**JSON Lines / JSONL** — One JSON value per newline.

**JSON-RPC** — Request/response envelope format used by MCP.

**MCP client** — Component that communicates with one MCP server.

**MCP server** — Component that exposes tools, resources, prompts, and related
capabilities.

**Middleware** — Code wrapping request processing to observe, reject, or alter it.

**OTLP** — OpenTelemetry Protocol used to export telemetry to a collector.

**Prompt** — Server-provided reusable prompt template.

**Resource** — URI-addressed context exposed by a server.

**Span** — Timed unit of work within a trace.

**Stdio transport** — Protocol messages carried over a child process's standard
input and output.

**Streamable HTTP** — MCP transport carried over HTTP with streaming support.

**Structured content** — Machine-oriented tool result represented as structured
data rather than only model-readable blocks.

**Tool** — Server-exposed operation with a name and argument schema.

**Trace** — Connected tree of spans representing one distributed operation.

**Transport** — Mechanism carrying protocol messages between peers.

## 26. Command reference

```bash
# Install
uv sync --all-extras

# Tests, lint, formatting, and typing
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src/mcp_lab

# Stdio client and agent
MCP_LAB_TRACE_EXPORTER=none uv run mcp-lab-client
MCP_LAB_TRACE_EXPORTER=none uv run mcp-lab-agent "Add 7 and 8"

# Streamable HTTP server
MCP_LAB_SERVER_TRANSPORT=streamable-http \
MCP_LAB_TRACE_EXPORTER=none \
uv run mcp-lab-server

# Streamable HTTP client
MCP_LAB_TRACE_EXPORTER=none \
uv run mcp-lab-client --url http://127.0.0.1:8000/mcp

# MCP Inspector
uv run mcp dev src/mcp_lab/server/app.py

# Inspect records
jq . var/wire.jsonl
jq . var/http-wire.jsonl
jq . var/client-wire.jsonl
jq . var/server-wire.jsonl

# Remove generated wire records
make clean-wire
```

## 27. Final mastery project `[Level 4]`

Choose a small real domain such as a personal reading list, local issue tracker,
or safe read-only analytics service. Build:

1. at least three tools with typed structured output;
2. one URI-template resource;
3. one reusable prompt;
4. stdio and Streamable HTTP support;
5. unit, in-process integration, and live smoke tests;
6. structured logs and correlated traces;
7. raw and semantic recording with domain-specific redaction;
8. a model adapter using the unchanged agent core;
9. a policy gateway with at least two risk levels;
10. a short threat model and architecture decision record.

You have reached expert-level understanding when you can justify not only how
each piece works, but why its boundary exists, what can fail at that boundary,
how it is observed, and which control contains the failure.

