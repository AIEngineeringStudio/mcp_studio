# Protocol versions and capability discovery

**Outcome:** Explain modern request metadata and recognize a legacy
initialization trace.

**Prerequisites:
** [03: JSON-RPC requests, responses, and notifications](03-json-rpc.md).

## Why the archive appears contradictory

A protocol revision is a dated agreement about message behavior. A package
version identifies an implementation release. A newer package can support
several protocol revisions. Updating Python does not select an MCP revision.

Read [the version baseline](../VERSIONS.md) before comparing examples.
This course uses modern 2026-07-28 mechanics and labels older behavior.

## A self-contained modern request

A request identifies its protocol version and relevant client capabilities
under `params._meta`. This example includes the required metadata for a
minimal tools-list request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

An empty client capability object means the request does not promise optional
client features. It does not mean the server has no tools. The SDK normally
supplies these details; a beginner should understand their purpose before
hand-writing them.

`server/discover` lets a client inspect supported versions, capabilities,
and server identity. Discovery and tool listing answer different questions:
“Which protocol features can you handle?” versus “Which tools are available
to this caller?”

## Compare the eras

| Concern              | Legacy through 2025-11-25    | Modern 2026-07-28          |
|----------------------|------------------------------|----------------------------|
| Starting interaction | Initialize handshake         | Self-contained requests    |
| Client capabilities  | Negotiated in initialization | Declared per request       |
| HTTP session ID      | Optional protocol session    | Removed                    |
| Additional input     | Server requests              | Input-required round trips |

The complete migration details are in the
[official changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog).
A framework context manager may still “connect” or “initialize” its internal
objects. That API name alone does not prove an `initialize` RPC occurred.

## Capabilities are promises

A server must not assume a client can render an elicitation form merely because
the client can call tools. Design a fallback or report the unsupported
capability. Similarly, an extension such as MCP Apps requires specific client
support.

Capability discovery is not authentication. A caller can advertise support for
a feature without having permission to read a private ticket.

## Diagnose compatibility deliberately

Record the client package, server package, protocol era, transport, and feature
being exercised. Compare a basic lookup before investigating advanced
interactions. A client that successfully lists tools may still lack the
elicitation behavior required by one tool.

**Professional articulation:**

> “We verify compatibility at the protocol and feature level. Package versions
> alone do not establish which interaction pattern both endpoints support.”

## Sources and next step

- [Archive: conversations/chatgpt/81_MCP_Elicitation.md](../../conversations/chatgpt/81_MCP_Elicitation.md)
- [Archive: docs/mcp-learning-guide.md](../../docs/%5BDONE%5Dmcp-learning-guide.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/index) —
  checked 2026-11-15.

Next: [Tools and their contracts](05-tool-contracts.md).

