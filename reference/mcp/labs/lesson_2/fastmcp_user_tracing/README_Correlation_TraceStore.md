# MCP protocol tracing — correlation + structured JSONL storage

Targets your **FastMCP 4.2 ticket service**. This lab builds on the earlier
STDIO/HTTP protocol observers, and adds persistent JSONL files and identifiers
that let client and server messages be joined without guessing.

## Why no MCP session ID?

MCP revision **2026-07-28** removed protocol sessions and the `Mcp-Session-Id`
HTTP header. We add a separate **application-controlled `trace_session_id`** to
group operations during a client run. It is *not* an MCP session and is never
used for security or authorization.

HTTP also carries a fresh **`http_exchange_id`** on each request; a JSON-RPC
`rpc_id` only identifies a request/response within its proper scope.

```text
Client                                    Server
  |                                         |
  +-- X-Debug-Trace-Session: S ------------>|
  +-- X-Debug-HTTP-Exchange: E ------------>|
  |                                         |
  | CLIENT OUT  S,E,rpc_id=7  ------------> | SERVER IN  S,E,rpc_id=7
  | CLIENT IN   S,E,rpc_id=7  <------------ | SERVER OUT S,E,rpc_id=7
```

STDIO does not have HTTP headers. Its `TracedStdioTransport` creates a UUID per
subprocess and passes it in `MCP_TRACE_SESSION_ID` in the child environment.
The client and child server log the same ID.

## Files

- `trace_store.py`: the single JSONL schema, file appends, UUID validation,
  basic key-name redaction, 0600 file creation and best-effort log failure
  handling.
- `http_protocol_trace.py`: HTTPX hooks + ASGI middleware, preserving JSON/SSE
  streaming, forwarding `X-Debug-*` IDs, parsing bounded JSON-RPC messages.
- `protocol_trace.py`: prior STDIO `SessionMessage` observers, now sharing an
  environment-propagated trace session ID.
- `server.py`: demo ticket service with HTTP/STDIO tracer insertion points.
- `verify_primitives.py`: demo client for tools/resources/prompts.
- `query_traces.py`: filter and display correlated records across processes.
- `tests/test_trace.py`: local contract tests, including fragmented SSE,
  reused RPC IDs and STDIO environment propagation.

## Run HTTP

From this folder, with `fastmcp==4.2.0` installed in your environment:

**Terminal 1:**

```bash
python server.py --transport http
```

**Terminal 2:**

```bash
python verify_primitives.py --transport http --focus tools
```

## Run STDIO

No separately started server is needed:

```bash
python verify_primitives.py --transport stdio --focus tools
```

Both modes write JSONL files in `trace-logs/` (by default). Files are named
`client-<pid>.jsonl` and `server-<pid>.jsonl`. You can set `MCP_TRACE_DIR` to
an absolute directory for a different location; the STDIO child inherits it.

## Query logs

Inspect all collected messages:

```bash
python query_traces.py
```

Filter on JSON-RPC request ID (IDs can repeat across connections):

```bash
python query_traces.py --rpc-id 7
```

Narrow to a specific logical tracing session (use an ID seen in the logs):

```bash
python query_traces.py --session <32-hex-id> --rpc-id 7
```

Narrow to one HTTP exchange:

```bash
python query_traces.py --exchange <32-hex-id>
```

To print the full JSONL records instead of a human-readable view:

```bash
python query_traces.py --json
```

Each record has:

```json
{
  "schema_version": 1,
  "timestamp": "2026-11-23T22:41:00.000+00:00",
  "pid": 5555,
  "side": "CLIENT",
  "direction": "OUT",
  "transport": "http",
  "event": "jsonrpc",
  "trace_session_id": "4a8c3da0cae047cc821c802db96e59af",
  "http_exchange_id": "06106225d035433abc6b2d0cbb5c71a7",
  "http_method": "POST",
  "path": "/mcp",
  "http_status": null,
  "detail": null,
  "rpc_id": 7,
  "rpc_kind": "request",
  "rpc_method": "tools/call",
  "tool_name": "get_ticket",
  "rpc_error_code": null
}
```

*Example above is synthetic.* Responses have the same `rpc_id`, but don't have
an RPC `method`; `query_traces.py` associates it with the earlier request.

## Full JSON-RPC payloads (optional)

By default, JSONL stores metadata only. For your synthetic ticket service,
explicitly set `MCP_TRACE_PAYLOAD=1` on both the client and server before
running. This adds a `payload` object containing the JSON-RPC envelope. Known
secret-named keys are replaced with `[REDACTED]`.

The key-name redactor cannot detect arbitrary PII or sensitive free-form text.
Never use full-payload tracing on real user data without stronger controls.

## Integrating into your existing files

The demo copies do not contain every semantic trace hook you may have added
locally. Do not overwrite your updated project. Copy the tracing modules,
and keep the same integration points from the prior HTTP/STDIO lesson:

**Server** — before `mcp.run(transport='stdio')` call
`install_server_stdio_trace()`. In `mcp.run(transport='http', ...)`, set
`middleware=[Middleware(HTTPProtocolTraceMiddleware)]`.

**Client** — for STDIO return `TracedStdioTransport(command, args)`. For HTTP
pass `httpx_client_factory=tracing_httpx_client_factory` to
`StreamableHttpTransport`.

## Validation and known limits

Run isolated adapter tests:

```bash
python tests/test_trace.py
```

These tests use a mock ASGI app and SDK stubs. They validate correlation,
JSONL persistence, unchanged HTTP bodies, split SSE frames, request-ID reuse,
and STDIO child environment propagation. They **do not** prove a complete
FastMCP 4.2 runtime integration because FastMCP is not available in the build
environment. Run the real HTTP and STDIO examples above in your own environment.

Caveats:

- HTTP `X-Debug-*` headers are **untrusted** and **non-standard**. Gate or strip
  them at an appropriate boundary in production; a client can forge them.
- Requests rejected before ASGI middleware have no `SERVER IN` event.
- No log rotation, queueing, durability guarantee, or secure centralized
  collection: this is a local instructional JSONL store, not production logging.
- Disk I/O is synchronous. Log failures are reported to stderr and deliberately
  do not interrupt MCP traffic.
- JSON/SSE observation is capped to 128 KiB per JSON body/event, but that is
  not a complete memory/traffic quota or universal data-loss-prevention system.
- In-memory modern FastMCP bypasses JSON-RPC serialization; the example leaves
  in-memory protocol tracing disabled.

## Official sources

- [MCP Python SDK v2: no handshake or protocol session](https://py.sdk.modelcontextprotocol.io/whats-new/)
- [FastMCP v4.2.0 StreamableHttpTransport](https://github.com/PrefectHQ/fastmcp/blob/v4.2.0/fastmcp_slim/fastmcp/client/transports/http.py)
- [FastMCP v4.2.0 server transport middleware](https://github.com/PrefectHQ/fastmcp/blob/v4.2.0/fastmcp_slim/fastmcp/server/mixins/transport.py)

---

# Your FastMCP tracing files — updated for correlation + JSONL storage

Based on your six uploaded Python files. Your original `get_ticket`,
`ticket_resource`, and `summarize_ticket` definitions, test assertions, semantic
middleware class names, and CLI transport choices are retained.

Two uploaded files had `(2)` suffixes, but the client imports `server` and the
STDIO transport launches `server.py`. These copies are named `server.py` and
`verify_primitives.py` so the project runs from a single directory. The uploaded
HTTP tracer `http_protocol_trace(1).py` is named `http_protocol_trace.py` to
match your existing import.

## Changes

| File                               | What changed                                                                                                                                                                                                                                             |
|------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `semantic_trace_client.py`         | Existing `trace_client()` still forwards the exact operation/result/error. Adds JSONL `semantic_call` / `semantic_result` / `semantic_error`, grouping one call using `semantic_operation_id`.                                                           |
| `semantic_trace_server.py`         | Existing `SemanticTrace.on_message()` still calls `call_next` unchanged. Adds JSONL events with current correlation context where available.                                                                                                             |
| `stdio_protocol_trace.py`          | Existing read/send stream wrappers and server runner hook remain. The client passes `MCP_TRACE_SESSION_ID` and a fresh `MCP_TRACE_STDIO_CONNECTION_ID` to its child. Both sides record matching IDs.                                                     |
| `http_protocol_trace.py`           | Existing HTTPX hooks, ASGI middleware, fragmented JSON/SSE handling, and 128 KiB capture limit remain. Adds trace-only `x-debug-trace-session` and `x-debug-http-exchange` headers and ASGI context propagation. Each HTTP exchange gets a different ID. |
| `server.py`                        | Retains semantic middleware registration, STDIO hook, and HTTP ASGI middleware. No extra server configuration is required; the imported tracer modules now write JSONL.                                                                                  |
| `verify_primitives.py`             | Generates one logical trace ID for a test run, passes it to STDIO/HTTP transports, and shares it with the semantic client wrapper. Also traces `list_prompts()`.                                                                                         |
| `trace_store.py`                   | **New.** Shared JSONL storage, schema, optional payload capture, basic key redaction, permissions, contextvars.                                                                                                                                          |
| `query_traces.py`                  | **New.** Print records filtered by session, HTTP exchange, STDIO connection, or JSON-RPC ID.                                                                                                                                                             |
| `tests/test_correlated_tracing.py` | **New.** Standalone HTTPX-ASGI tests and STDIO SDK-stub tests; not a substitute for a FastMCP integration run.                                                                                                                                           |

## Setup

Use a Python environment where your own `fastmcp==4.2.0` installation works. The
HTTP tracer imports `httpx2` as used by that FastMCP release. Save every `.py`
file from this folder together.

**By default** the logger writes *metadata only*. Files are created in
`./trace-logs` (relative to each process working directory). To choose a
directory in both terminals:

```bash
export MCP_TRACE_DIR="$(pwd)/trace-logs"
```

### Run HTTP

Terminal 1:

```bash
python server.py --transport http
```

Terminal 2:

```bash
python verify_primitives.py --transport http --focus tools
```

### Run STDIO

Only one terminal is needed; the client launches the server subprocess:

```bash
python verify_primitives.py --transport stdio --focus tools
```

The same `--focus resources` and `--focus prompts` values remain supported.
In-memory retains **semantic** tracing but is not guaranteed to create JSON-RPC
wire messages.

### Inspect correlated log records

The client prints a `Trace session ID: ...` line. Use the printed value:

```bash
python query_traces.py --session THE_ID
python query_traces.py --session THE_ID --rpc-id 7
python query_traces.py --exchange HTTP_EXCHANGE_ID
python query_traces.py --connection STDIO_CONNECTION_ID
python query_traces.py --session THE_ID --json
```

A log record has fields like:

```json
{
  "schema_version": 1,
  "timestamp": "2026-11-23T15:41:00.123+00:00",
  "pid": 1234,
  "side": "CLIENT",
  "direction": "OUT",
  "transport": "http",
  "event": "jsonrpc",
  "trace_session_id": "0123456789abcdef0123456789abcdef",
  "http_exchange_id": "11111111111111111111111111111111",
  "stdio_connection_id": null,
  "http_method": "POST",
  "path": "/mcp",
  "http_status": null,
  "detail": null,
  "semantic_operation_id": null,
  "rpc_id": 7,
  "rpc_kind": "request",
  "rpc_method": "tools/call",
  "tool_name": "get_ticket",
  "rpc_error_code": null
}
```

This record is illustrative. Actual IDs, times and messages will differ. A
single request is grouped by `(trace_session_id, http_exchange_id, rpc_id)` for
HTTP or `(trace_session_id, stdio_connection_id, rpc_id)` for STDIO. JSON-RPC
IDs by themselves are not globally unique. The semantic client wrapper has its
own `semantic_operation_id`; it **cannot reliably attach an actual JSON-RPC ID**
without deeper session instrumentation.

### Optional debug settings

```bash
# Only for your synthetic local ticket data, where payload logging is safe:
export MCP_TRACE_PAYLOAD=1

# Restore your earlier human-readable semantic stderr prints:
export MCP_TRACE_CONSOLE=1
```

Both options are **off by default**, because full payloads/console
representation can leak sensitive values. `trace_store.redact()` only masks a
few common secret keys; it does not detect arbitrary PII or secrets embedded in
strings. The HTTP trace headers are untrusted *diagnostic metadata*, never
authorization or an MCP protocol session. They must not be used for access
control. HTTP middleware only observes `/mcp` and `/mcp/`.

JSONL files are stored as separate `client-PID.jsonl` and `server-PID.jsonl`,
opened in append mode with 0600 permissions. Writing is best effort: a failure
to open/write the file is reported to stderr but does not interrupt MCP message
delivery. This local-lab implementation does **not** handle retention, log
rotation, concurrent replicas sharing a single filesystem, or security-grade
redaction. Times in different processes may have clock skew.

### Verification

Run the local contract suite:

```bash
python tests/test_correlated_tracing.py
```

The suite checks HTTP four-way correlation, duplicate RPC IDs across different
HTTP requests, SSE chunks, JSONL storage and permissions, semantic wrapper
behavior, STDIO message identity, and child environment propagation using stubs.
It does **not** execute FastMCP 4.2 end-to-end because the SDK was not installed
in the build environment. Please verify both `stdio` and `http` CLI commands in
your FastMCP environment.

### Version-specific sources

- [FastMCP v4.2.0 HTTP client transport](https://github.com/PrefectHQ/fastmcp/blob/v4.2.0/fastmcp_slim/fastmcp/client/transports/http.py)
- [FastMCP v4.2.0 server transport mixin](https://github.com/PrefectHQ/fastmcp/blob/v4.2.0/fastmcp_slim/fastmcp/server/mixins/transport.py)
- [MCP 2026-07-28 transport overview](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)
