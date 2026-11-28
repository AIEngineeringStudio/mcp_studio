# JSON-RPC requests, responses, and notifications

**Outcome:** Read a JSON-RPC message, match a response to its request, and
distinguish an MCP method from an application tool name.

**Prerequisites:** [02: Host, model, client, and server](02-host-client-server.md).

## Build the idea in three steps

MCP messages are easier to understand when you separate three ideas:

1. **JSON** represents structured data as text.
2. **JSON-RPC** wraps a remote operation in a request or response envelope.
3. **MCP** defines the operations and data carried inside that envelope.

**RPC:**

> Remote Procedure Call. One program asks another program to perform a named
> operation. “Remote” means across a communication boundary; the programs may
> still run on the same computer.

**Envelope:**

> The outer message structure used for routing and matching. The application
> data is carried inside it, like a letter inside an addressed envelope.

The envelope analogy stops at security: a JSON-RPC envelope is not encrypted
or trustworthy merely because its fields are correctly shaped.

## First read a normal JSON object

```json
{
  "ticket_id": "T-100",
  "include_history": false
}
```

JSON has objects, arrays, strings, numbers, booleans, and `null`. JSON field
names and strings use double quotes. JSON does not allow comments.

In Python, the equivalent in-memory value is a dictionary:

```python
arguments = {
    "ticket_id": "T-100",
    "include_history": False,
}
```

Notice Python's `False` versus JSON's `false`. A library serializes the Python
value into JSON when it sends a message.

## Add the JSON-RPC request envelope

This simplified message asks for an MCP tool call:

```json
{
  "jsonrpc": "2.0",
  "id": 17,
  "method": "tools/call",
  "params": {
    "name": "get_ticket",
    "arguments": {
      "ticket_id": "T-100"
    }
  }
}
```

The fields have separate jobs:

**`jsonrpc`:**

> Selects the JSON-RPC version. MCP uses JSON-RPC `2.0`.

**`id`:**

> Identifies this request so the client can match the later response.

**`method`:**

> Names the protocol operation. Here, `tools/call` means “invoke one tool.”

**`params`:**

> Holds the input for that protocol operation. The application tool name is
> `params.name`; its input is `params.arguments`.

This is an envelope illustration. A complete modern MCP request also carries
protocol version and client-capability metadata, introduced in concept 04.

## MCP method and tool name are not the same

For the message above:

```
MCP method:       tools/call
Tool name:        get_ticket
Business input:   ticket_id = T-100
```

`tools/call` is a protocol operation shared by every tool call. `get_ticket` is
the application component selected for this specific call. There does not need
to be an HTTP route named `/get_ticket`.

Other important MCP methods include:

- `tools/list`: discover tools available to the caller;
- `resources/list`: discover readable resources;
- `resources/read`: read one resource;
- `prompts/list`: discover prompt templates;
- `prompts/get`: retrieve one prompt.

Learn the pattern first: *list* discovers components, while *call*, *read*, or
*get* uses one selected component.

## Match the response by request ID

A successful response repeats the request's `id`:

```json
{
  "jsonrpc": "2.0",
  "id": 17,
  "result": {
    "structuredContent": {
      "id": "T-100",
      "status": "open"
    },
    "isError": false
  }
}
```

The client may have several requests in progress. Responses can finish in a
different order:

```
Client                         Server
  | ---- request id=17 --------> |
  | ---- request id=18 --------> |
  | <--- response id=18 -------- |
  | <--- response id=17 -------- |
```

**Correlation:**

> Connecting related events by a shared identifier. The JSON-RPC `id` connects
> one response to one request; it does not require responses to arrive in order.

Do not confuse these identifiers:

- JSON-RPC request ID `17` identifies one message exchange.
- Ticket ID `T-100` identifies one business record.
- An idempotency key identifies one business operation across retries.

Each solves a different problem.

## Notifications are one-way messages

A JSON-RPC notification has a method but no `id`:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progressToken": "report-7",
    "progress": 40,
    "total": 100
  }
}
```

Because no `id` is present, the receiver does not send a JSON-RPC response.
Notifications are useful for information such as progress or change events.
The exact notification must be supported by the selected MCP revision and both
endpoints.

## Keep four failure layers separate

An unsuccessful interaction can fail at different layers:

**Tool or application failure:**

> The protocol call reached the tool, but the business operation failed. For
> example, ticket `T-999` does not exist.

**JSON-RPC or MCP failure:**

> The receiver cannot handle the protocol request, perhaps because the method
> is unknown or required parameters are missing.

**HTTP failure:**

> An HTTP transport request uses the wrong route, media type, or credentials.

**Process or network failure:**

> The server did not start, the connection broke, or no usable response
> arrived.

A JSON-RPC error response contains `error` instead of `result`:

```json
{
  "jsonrpc": "2.0",
  "id": 17,
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  }
}
```

An HTTP `200 OK` says the HTTP exchange succeeded. It does not by itself prove
the tool's business operation succeeded. Inspect the JSON-RPC and tool result.

## Transport carries the message

The same logical `tools/call` can travel through either course transport:

```
                         +--> stdio: local process pipes
JSON-RPC MCP message ----|
                         +--> Streamable HTTP: network request/response
```

**`stdio`:**

> Standard input and standard output. A client launches a child process and
> exchanges protocol data through pipes. Server logs must use standard error,
> because ordinary output is reserved for protocol messages.

**Streamable HTTP:**

> The HTTP transport for network-accessible MCP communication. In the modern
> `2026-07-28` revision used by this course, responses are request-scoped; do
> not copy older session or standalone GET-stream behavior into new examples.

Transport changes how bytes move. It does not change the ticket lookup's
business meaning.

## A tiny Python message experiment

This code needs only Python's standard library:

```python
import json

request = {
    "jsonrpc": "2.0",
    "id": 17,
    "method": "tools/call",
    "params": {
        "name": "get_ticket",
        "arguments": {"ticket_id": "T-100"},
    },
}

wire_text = json.dumps(request)
decoded = json.loads(wire_text)

print(decoded["method"])
print(decoded["params"]["name"])
print(decoded["params"]["arguments"]["ticket_id"])
```

Expected output:

```
tools/call
get_ticket
T-100
```

This proves JSON serialization only. It does not send an MCP request or start a
server. Concept 07 uses the actual client and framework.

**Say it professionally:**

> “JSON-RPC supplies the request envelope and correlation ID. MCP defines the
> operations and component contracts carried in that envelope, while the
> transport carries the serialized message.”

## Sources and next step

- [Archived MCP walkthrough](../../fast-mcp/walk-through-docs/walk-through.md)
- [Archived MCP introduction](../../fast-mcp/01-what-mcp-is.md)
- [Official MCP protocol reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/index)

Next: [Protocol versions and capability discovery](04-versions-discovery.md).
