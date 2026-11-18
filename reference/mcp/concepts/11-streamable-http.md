# Streamable HTTP

**Outcome:** Move a working MCP contract across a network and recognize modern HTTP behavior.

**Prerequisites:** [04: Protocol versions and capability discovery](04-versions-discovery.md), [08: stdio and subprocess boundaries](08-stdio-processes.md).

## An independently running server

HTTP lets the server run independently of a particular client process. The
client needs an endpoint address and the server needs to listen on a socket.

```
Client process -- HTTP POST /mcp --> Server process --> ticket service
               <-- JSON or SSE ---
```

Modern MCP sends requests to one MCP endpoint. A request can receive a JSON
response or an SSE response stream. SSE means Server-Sent Events: a framing
format for server-to-client events inside an HTTP response. It is not a
separate business operation.

## Run the same contracts

After [lab setup](../labs/README.md), start the server in terminal 1:

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

**Professional articulation:**

> “HTTP changes where the server runs and how messages travel. It preserves
> the tool contract while adding network, authentication, and routing concerns.”

## Sources and next step

- [Archive: conversations/chatgpt/5_StreamableHttp_Uvicorn.md](../../conversations/chatgpt/5_StreamableHttp_Uvicorn.md)
- [Archive: conversations/streamable/streamable-3.md](../../conversations/streamable/streamable-3.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) — checked 2026-11-15.

Next: [Progress, streaming, and final results](12-progress-streaming.md).

