# JSON-RPC requests, responses, and notifications

**Outcome:** Read a message envelope and distinguish request identity from business identity.

**Prerequisites:** [02: Host, client, model, and server](02-host-client-server.md).

## The message inside the transport

JSON is a data representation. JSON-RPC adds a convention for requesting a
method and matching its response. MCP assigns meanings to methods such as
`tools/call`.

The following is an envelope illustration, not a complete modern MCP request:
required version/capability metadata is added in guide 04.

```json
{
  "jsonrpc": "2.0",
  "id": 17,
  "method": "tools/call",
  "params": {
    "name": "get_ticket",
    "arguments": {"ticket_id": "T-100"}
  }
}
```

The outer method is `tools/call`. The application tool's name lives inside
`params.name`. There is no requirement for an HTTP route named
`/get_ticket`.

## Correlation

If request 17 finishes after request 18, the client still knows which result
belongs to which call because each response carries its matching ID.
Correlation means connecting related events; it does not imply ordering.

```text
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

A notification deliberately has no request ID and expects no JSON-RPC
response. Progress is one example of notification-style information. Do not
send a response to a notification merely because it arrived over a stream.

An RPC error indicates that the requested protocol operation could not be
handled normally. A tool can also run and report an application-level failure.
Transport failure is a third possibility: the client may receive no usable
RPC response at all.

For example, an unknown RPC method, a known tool rejecting a nonexistent
ticket, and a disconnected socket require different investigations. Later
guides address retry policy; retrying every error conceals incorrect inputs
and can repeat side effects.

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
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/index) — checked 2026-11-15.

Next: [Protocol versions and capability discovery](04-versions-discovery.md).

