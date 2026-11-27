# Streamable HTTP

**Outcome:** Explain why Streamable HTTP exists, move a working MCP contract
across a network, and recognize modern HTTP behavior.

**Prerequisites:**
[04: Protocol versions and capability discovery](04-versions-discovery.md) and
[08: stdio and subprocess boundaries](08-stdio-processes.md).

You need only a beginner understanding of HTTP requests, JSON, and client/server
roles. REST design, HTTP chunked transfer encoding, asynchronous Python,
FastAPI, Docker, and Uvicorn are not prerequisites for this chapter.

## Why Streamable HTTP exists

An independently running MCP server needs a network transport. Some operations
also need to report related activity before their final result, such as progress
for a long-running report.

An ordinary JSON HTTP response can be processed asynchronously, so it does not
inherently freeze a user interface. Its limitation here is simpler: one JSON
response carries one response object. It does not provide a standard stream for
request-related MCP notifications before that final response.

Modern Streamable HTTP solves that transport problem.

**Streamable HTTP MCP** allows:

- Server to push partial results as they are ready.
- Client to reply mid-stream (bidirectional).
- Long-running tasks to report progress live.

```
MCP client                  /mcp                     MCP server
    |--- POST: one self-contained JSON-RPC request ----->|
    |<-- application/json: one final response -----------|

or

    |--- POST: one self-contained JSON-RPC request ----->|
    |<== text/event-stream: related notifications =======|
    |<== then the final JSON-RPC response ===============|
```

### Where It Is Used in Industry

- **AI agent pipelines** — LLM tools calling APIs to stream results to agents.
- **Data processing systems** — Batch jobs that report row-by-row progress.
- **Enterprise dashboards** — Live ETL status feeds.
- **DevOps tooling** — CI/CD pipelines streaming logs.
- **Financial systems** — streaming trade confirmations.

### Concrete Use Cases

```
┌──────────────────────┬─────────────────────┬──────────────────────────┐
│ Use Case             │ Industry            │ Problem It Solves        │
├──────────────────────┼─────────────────────┼──────────────────────────┤
│ AI agent calls DB    │ Enterprise SaaS     │ Agent waits 30s for full │
│ tool, streams rows   │                     │ result — now streams row │
│ as they arrive       │                     │ by row, stays responsive │
├──────────────────────┼─────────────────────┼──────────────────────────┤
│ Data migration tool  │ FinTech / HealthTech│ No visibility into batch │
│ reports progress,    │                     │ progress; user can now   │
│ asks user to pause   │                     │ pause/resize mid-run     │
│ or resize batch      │                     │                          │
├──────────────────────┼─────────────────────┼──────────────────────────┤
│ LLM document         │ Legal / Research    │ Full doc summary blocks  │
│ summariser streams   │                     │ UI for 60s; streaming    │
│ paragraph by para.   │                     │ shows output instantly   │
└──────────────────────┴─────────────────────┴──────────────────────────┘
```

**Endpoint:**

> The network address that accepts MCP HTTP requests, such as
> `http://127.0.0.1:8765/mcp`.

**HTTP POST:**

> The HTTP request method a modern MCP client uses to send one self-contained
> JSON-RPC message to the endpoint.

**Server-Sent Events (SSE):**

> A text framing format that lets the server send multiple events in an HTTP
> response stream. Each meaningful MCP event carries a complete JSON-RPC
> message, not an arbitrary text fragment or model token.

**Request-scoped stream:**

> An SSE response associated with one originating request. It can carry
> notifications related to that request and then its final response. It is not
> a connection-wide protocol session.

**Important limitation:**

> SSE transports MCP messages. It does not automatically turn a tool result
> into row-by-row output, model-token streaming, or a sequence of partial tool
> results.

## An independently running server

HTTP lets the server run independently of a particular client process. The
client needs an endpoint address and the server needs to listen on a socket.

```
Client process -- HTTP POST /mcp --> Server process --> ticket service
               <-- JSON or SSE ---
```

Modern MCP sends requests to one endpoint. A request can receive one JSON
response or one request-scoped SSE response. The transport changes how messages
travel; it does not change the ticket tool's contract or business behavior.

## Run the same contracts

After [lab setup](../fast-mcp-2026-07-28/labs/README.md), start the server in terminal 1:

```bash
uv run python server.py --http
```

In terminal 2, from the same lab directory:

```bash
uv run python client.py http
```

Expected final line:

```
http: tool, resource, and prompt checks passed
```

Stop the server with Ctrl-C. The client now uses a URL instead of a Python
object or subprocess configuration. The tool and fixture remain the same.

The passing check proves that discovery and the component contracts work over
HTTP with the pinned client and server. It does not prove authentication, TLS,
proxy routing, progress delivery, or every optional host feature.

## Understand the address

`127.0.0.1` refers to this machine's loopback interface. Port `8765`
identifies the listening service. `/mcp` is the application path.
`0.0.0.0` is a bind choice for all interfaces, not the destination URL a
remote user should normally enter.

The example is a local, unauthenticated concept exercise. Remote deployment
introduces a trust boundary and needs the security guides.

## Modern versus legacy HTTP

Modern 2026-07-28 removes the protocol session header and the old GET stream.
Requests carry metadata, including protocol version and capabilities; HTTP
request headers also identify protocol method and, where applicable, component
name. The SDK should construct these consistently.

Legacy Streamable HTTP can use initialization, optional sessions, and GET
streams. The still older HTTP+SSE transport uses another connection arrangement.
Recognize those traces before diagnosing a missing endpoint as a generic
network failure.

## Debug by boundary

“Connection refused” usually means no listener at the address. HTTP 404 points
toward the wrong route or proxy mapping. A protocol error means some component
received the request but rejected its meaning. A tool error means the request
reached application execution.

A browser GET to `/mcp` is not a complete tool test. Use a compatible client
to exercise the actual method, metadata, and response handling.

**Important distinctions:**

- Streamable HTTP is MCP JSON-RPC over HTTP; it is not a REST resource design.
- SSE is server-to-client on one HTTP response; it is not a full-duplex socket.
- A request-scoped stream is not chat memory or durable business state.
- A network connection succeeding does not prove that a tool operation
  succeeded.

**Professional articulation:**

> “HTTP changes where the server runs and how messages travel. It preserves
> the tool contract while adding network, authentication, and routing concerns.”

## Sources and next step

- [Archived Streamable HTTP and Uvicorn example](../fastMcp-fastApi-uvicorn-ngnix-docker/5_StreamableHttp_Uvicorn.md)
- [Archived streamable transport notes](../streamable/streamable-3.md)
- [Legacy definitions and prerequisites](../elicitation/chunk-1.md)
- [Legacy problem-first transport explanation](../elicitation/chunk-2.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) —
  checked 2026-11-15.

Next: [Progress, streaming, and final results](12-progress-streaming.md).

