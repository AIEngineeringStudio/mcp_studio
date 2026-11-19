# Protocol versions and capability discovery

**Outcome:** Explain why MCP messages identify a protocol revision and why a
successful connection does not prove that every optional feature is supported.

**Prerequisites:**
[03: JSON-RPC requests, responses, and notifications](03-json-rpc.md).

## Three kinds of version answer different questions

Examples on the internet can look contradictory because they target different
protocol and software generations.

**Protocol revision:**

> A dated agreement about MCP message fields and interaction behavior, such as
> `2026-07-28`.

**Package version:**

> A release of an implementation, such as FastMCP `4.2.0`. One package may
> support more than one protocol revision.

**Python version:**

> The language runtime used to execute the implementation. Updating Python does
> not select an MCP protocol revision.

```text
Protocol revision  -> which communication rules?
FastMCP version    -> which framework code and API?
Python version     -> which runtime executes that code?
```

Read [the version baseline](../VERSIONS.md) before combining examples. This
course targets modern MCP `2026-07-28` and labels older behavior explicitly.

## Why the protocol revision is visible

Two programs need a shared interpretation of the message. A field that changed
between revisions can otherwise appear valid while meaning something different.

In modern MCP, each request declares the protocol version and relevant client
capabilities under `params._meta`:

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

**Metadata:**

> Data that describes other data. Here, `_meta` describes the protocol context
> needed to interpret the request; it is not the ticket lookup's business input.

An empty client-capability object means this request promises no optional
client features. It does not mean the server has no tools.

The SDK normally creates these fields. You should understand why they exist,
but application code should not manually rebuild every wire message.

## Discovery asks what the server supports

`server/discover` can report supported protocol versions, server capabilities,
and server identity. `tools/list` answers a different question.

```text
server/discover -> Which protocol features can this server handle?
tools/list       -> Which tools are visible to this caller?
```

**Capability:**

> A declared promise that one endpoint supports an optional protocol feature.

For example, a server must not assume that a client can display an additional
input form merely because that client can list and call tools. The required
input feature needs its own compatible support or a clear fallback.

Capability support is not permission. A caller can support a feature and still
lack authorization to read a private ticket.

## Modern and legacy lifecycles differ

MCP through `2025-11-25` used a stateful initialization handshake. Modern
`2026-07-28` requests are self-contained at the protocol level.

**Legacy shape:**

```text
initialize -> initialize result -> initialized notification -> normal requests
```

**Modern shape:**

```text
self-contained request with version/capabilities -> result
```

The detailed comparison belongs in the supplemental
[stateful lifecycle](05A-stateful-lifecycle.md) and
[stateless-first lifecycle](05B-stateless-lifecycle.md) guides. A beginner
should first remember one rule: do not combine fields and sequences from the
two eras into a single example.

A framework may call a Python method named `connect()` or `initialize()` for
its own object setup. The method name alone does not prove that a legacy
`initialize` MCP request was sent on the wire.

## Inspect metadata with plain Python

This experiment reads a message; it does not contact a server:

```python
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {
        "_meta": {
            "io.modelcontextprotocol/protocolVersion": "2026-07-28",
            "io.modelcontextprotocol/clientCapabilities": {},
        }
    },
}

metadata = request["params"]["_meta"]
print(metadata["io.modelcontextprotocol/protocolVersion"])
print(request["method"])
```

Expected output:

```text
2026-07-28
tools/list
```

In the runnable lab, the actual client checks its negotiated protocol version
after connecting. That proves the exercised client/server path, not universal
support for every optional feature.

## Diagnose compatibility in a useful order

Record these facts before debugging an advanced interaction:

1. client package and version;
2. server package and version;
3. intended MCP protocol revision;
4. transport (`stdio` or Streamable HTTP);
5. exact feature being exercised;
6. host support for that feature.

First prove a basic discovery and tool call. Then test the optional feature.
A client that lists tools successfully may still lack the feature required by
one particular tool.

**Say it professionally:**

> “We verify compatibility at the protocol-revision and feature level. Package
> versions alone do not establish which interaction patterns both endpoints and
> the host support.”

## Sources and next step

- [Archived elicitation lesson](../fastMcp-fastApi-uvicorn-ngnix-docker/81_MCP_Elicitation.md)
- [Archived versioning and capability notes](../fast-mcp/16-versioning-capability_negotiation.md)
- [Official MCP protocol reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/index)
- [Course version baseline](../VERSIONS.md)

Next: [Tools and their contracts](05-tool-contracts.md).
