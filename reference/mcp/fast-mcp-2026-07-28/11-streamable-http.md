# Lesson 11 — stdio and modern Streamable HTTP

## Outcome

After this lesson, you can choose a transport and identify the modern HTTP
rules that differ from the handshake era.

## Protocol is not transport

`tools/call` has the same meaning over both standard transports:

```
stdio                       Streamable HTTP
-----                       ---------------
client starts subprocess    independently deployed server
stdin/stdout                POST /mcp
newline-delimited JSON      JSON or request-scoped SSE response
local process boundary      network and HTTP security boundary
```

## stdio

The client launches the server and exchanges newline-delimited JSON-RPC.
Protocol messages use stdin and stdout; diagnostics go to stderr.

Modern request metadata remains inside `params._meta`. A client can probe with
`server/discover`; it must not use the legacy `initialize` flow after selecting
the modern era.

Cancellation uses `notifications/cancelled`. Ending the subprocess or closing
streams is transport shutdown, not an application result.

## Streamable HTTP request

Every JSON-RPC request or notification uses a new POST to one MCP endpoint.
For a request, the server returns either one JSON object or a request-scoped
SSE stream. Clients must support both.

```http
POST /mcp HTTP/1.1
Host: example.com
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: get_ticket
```

The body is one JSON-RPC request. Modern HTTP does not accept a client-sent
JSON-RPC response body and does not batch several messages into one POST.

Required routing headers include:

- `MCP-Protocol-Version`;
- `Mcp-Method`;
- `Mcp-Name` for `tools/call`, `resources/read`, and `prompts/get`.

The body still contains the authoritative method, name, and required `_meta`.
Servers validate header/body consistency.

## Request-scoped SSE

An SSE response may carry progress or permitted log notifications followed by
the final JSON-RPC response. It must not carry independent server-to-client
requests. Elicitation, roots, and sampling use MRTR results instead.

Closing this SSE response is the modern HTTP cancellation signal.

## Long-lived change notifications

Clients obtain a long-lived notification stream by POSTing
`subscriptions/listen`. This is separate from one operation's response stream.

```
request response stream       subscriptions/listen stream
-----------------------       ---------------------------
progress for one call         tools/resources/prompts list changes
final result                  selected resource updates
closes after result           remains open until listen ends
```

## Removed HTTP behavior

MCP `2026-07-28` has:

- no `Mcp-Session-Id`;
- no standalone GET stream;
- no `Last-Event-ID` resumability;
- no protocol-level sticky session requirement;
- no `resources/subscribe` or `resources/unsubscribe`.

If a response stream breaks, the client decides whether it is safe to issue a
new request with a new ID. Use idempotency and outcome lookup for side effects.

## FastMCP run modes

The same FastMCP application can serve stdio or HTTP. A client chooses a
transport without changing component names or arguments:

```python
from fastmcp import Client


async def read_ticket(mcp_target) -> dict:
    async with Client(mcp_target) as client:
        result = await client.call_tool(
            "get_ticket",
            {"ticket_id": "T-100"},
        )
        return result.data
```

The repository's server exposes both run modes:

```bash
cd reference/mcp/labs
uv run python server.py
uv run python server.py --http
```

Run the HTTP server in one terminal, then verify it in another:

```bash
cd reference/mcp/labs
uv run python client.py http
```

The example binds to `127.0.0.1`. The commands are the same on Intel and Apple
Silicon Macs.

## Hands-on checkpoint

**Execution boundary:**

> Streamable HTTP on loopback. The verifier starts a child server on
> `127.0.0.1:8765`, makes MCP calls, and stops that server.

Run the self-contained HTTP verifier from the repository root. It starts only
its own loopback server, calls the tool, resource, and prompt over HTTP, and
then terminates that process:

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python verify_http.py
```

Expected client output:

```
http: tool, resource, and prompt checks passed
```

The complete runnable code is
[`verify_http.py`](../labs/verify_http.py). It refuses to run if port `8765` is
already occupied, so it never stops an unrelated service.

## Operational rules

- Validate `Origin` when present and reject invalid values with HTTP 403.
- Bind local development servers to loopback, not `0.0.0.0`.
- Authenticate remote connections.
- Disable proxy buffering for SSE where required.
- Set timeouts that permit expected streaming without leaving unbounded work.

**Say it professionally:**

> Modern Streamable HTTP uses one POST per message and either JSON or a
> request-scoped SSE response. Protocol sessions, the GET stream, and SSE
> resumability were removed, so each request can reach any compatible replica.

## Official references

- [stdio](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
- [Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [FastMCP running a server](https://gofastmcp.com/deployment/running-server)

