# FastMCP 4.2 — STDIO + Streamable HTTP protocol tracing

This project extends the previous STDIO tracing lesson with **both-side HTTP
JSON-RPC tracing** without changing ticket tools, resources, or prompts.

## Key files

| File                                | Role                                                                                                                                 |
|-------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `http_protocol_trace.py`            | HTTPX client request/response hooks and ASGI server middleware. Handles JSON bodies, SSE messages, HTTP status, and bounded buffers. |
| `protocol_trace.py`                 | Retains the previous STDIO `SessionMessage` tracing example.                                                                         |
| `server.py`                         | Ticket service with the STDIO or HTTP observer attached, based on `--transport`.                                                     |
| `verify_primitives.py`              | Same tools/resources/prompts tests, selecting instrumented HTTP or STDIO transport.                                                  |
| `tests/test_http_protocol_trace.py` | Local contract tests with HTTPX and a fake ASGI server.                                                                              |

## Run with FastMCP 4.2

Use a Python environment with `fastmcp==4.2.0` installed. FastMCP 4.2's client
implementation uses `httpx2`, so the client instrumentation explicitly imports
`httpx2`. No additional external tracing service is required.

**Terminal 1 — start HTTP server:**

```bash
python server.py --transport http 2>http-server.log
```

**Terminal 2 — run client:**

```bash
python verify_primitives.py --transport http --focus tools 2>http-client.log
python verify_primitives.py --transport http --focus resources 2>http-resources.log
python verify_primitives.py --transport http --focus prompts 2>http-prompts.log
```

Trace messages are one JSON object per line written to **stderr** (mixed with
server framework logs, if any). They have `side`, `direction`, `kind`, `method`,
`path`, `status` where available, and `payload` for parsed JSON-RPC bodies.
Filter JSON trace lines if the server log contains other messages. You should
see client-side `CLIENT OUT` request and `CLIENT IN` response; and server-side
`SERVER IN` request and `SERVER OUT` response, connected by each JSON-RPC `id`.

Response `Content-Type: application/json` is traced as `kind: jsonrpc`;
`Content-Type: text/event-stream` is parsed incrementally, logging each complete
SSE `data:` JSON-RPC envelope as `kind: sse_jsonrpc`. Keepalives (SSE comments)
are ignored. HTTP start/status records use `kind: http_request` and
`http_response`. Client `OUT` is an attempted send, not confirmed delivery.

## Merge only the HTTP changes into your existing local project

You may have additional semantic tracing in your local versions of `server.py`
and `verify_primitives.py` that is not in the example copies. **Do not overwrite
your local files** if so. Copy `http_protocol_trace.py` into the same directory
as your scripts, and make these two minimal changes:

In `server.py`:

```python
from starlette.middleware import Middleware
from http_protocol_trace import HTTPProtocolTraceMiddleware

# In the existing HTTP branch:
mcp.run(
    transport="http", host="127.0.0.1", port=8000, path="/mcp",
    middleware=[Middleware(HTTPProtocolTraceMiddleware)],
)
```

In `verify_primitives.py`:

```python
from http_protocol_trace import tracing_httpx_client_factory

# In client_source("http"):
return StreamableHttpTransport(
    url="http://127.0.0.1:8000/mcp",
    httpx_client_factory=tracing_httpx_client_factory,
)
```

Keep the existing STDIO tracing and semantic logging. This HTTP observer does
not affect those paths.

## Validate without FastMCP

Run the standalone adapter tests after installing normal `httpx` (already
present in many environments):

```bash
python tests/test_http_protocol_trace.py
```

The test suite exercises:

1. Client JSON request and response body capture without changing original body
   bytes.
2. Client SSE JSON-RPC events split across arbitrary chunks, including CRLF.
3. ASGI server JSON request and response bodies split across ASGI frames.
4. ASGI SSE bodies split across frames.
5. Capture size limits for JSON and SSE.
6. Client and server observers together, verifying the same JSON-RPC `id` at all
   four boundaries.
7. FastMCP-compatible HTTP client factory signature and hook wiring.

The local adapter tests use ordinary `httpx` as a substitute for the absent
`httpx2`; **they are not an end-to-end FastMCP 4.2 integration test**. Run the
real two-terminal example above in your FastMCP environment to verify the
installed SDK.

## Scope and limitations

- **HTTP protocol tracing, not raw TCP/TLS bytes.** Content is observed after
  HTTP parsing/serialization and before application consumption.
- **SSE streams remain streaming.** The observer reads each chunk while passing
  exactly the same bytes downstream. It does not pre-read or buffer entire
  streams.
- **Bounded capture:** JSON bodies/events over 128 KiB are marked
  `json_truncated` / `sse_truncated` and are still delivered unchanged. The body
  cap is for tracing only.
- **Privacy:** Traces include full JSON-RPC arguments and responses. Use only
  with synthetic data until redaction and restricted log access are added.
  Request authorization headers are not logged.
- **Local lab path:** The ASGI observer only handles `/mcp` (also matches
  `/mcp/`). Update the path filter if you change your route.
- **Version sensitivity:** The code targets FastMCP 4.2 (`httpx2` factory
  signature checked against the v4.2.0 source). Re-test if upgrading FastMCP.
- **Infrastructure:** The tracing observer writes synchronously to stderr; use
  bounded, asynchronous logging for production under heavy traffic.

## Official references

- [FastMCP v4.2.0 client HTTP transport](https://github.com/PrefectHQ/fastmcp/blob/v4.2.0/fastmcp_slim/fastmcp/client/transports/http.py)
- [FastMCP v4.2.0 HTTP server
  `middleware` parameter](https://github.com/PrefectHQ/fastmcp/blob/v4.2.0/fastmcp_slim/fastmcp/server/mixins/transport.py)
- [HTTPX transport and streaming extension points](https://www.python-httpx.org/advanced/transports/)
