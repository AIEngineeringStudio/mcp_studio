# Reading and migrating legacy MCP examples

**Outcome:** Identify an archived example's protocol and framework before adapting it.

**Prerequisites:** [04: Protocol versions and capability discovery](04-versions-discovery.md), [11: Streamable HTTP](11-streamable-http.md), [13: Elicitation and additional user input](13-elicitation.md), [30: Optional extensions and deprecated features](30-extensions.md).

## Start with evidence

The archive accumulated over time. A newer-looking filename does not prove
a newer protocol. Some individual documents mix eras.

Record the import path, package constraints, protocol version, endpoint
arrangement, initialization flow, and advanced features used by the example.
Then compare them with official documentation for that version.

| Evidence in a source | Likely interpretation |
|---|---|
| initialize then initialized | Legacy lifecycle |
| Mcp-Session-Id | Legacy HTTP session mechanism |
| input_required and inputResponses | Modern MRTR pattern |
| mcp.server.fastmcp import | Official SDK v1 API |
| standalone fastmcp import | Separate FastMCP distribution |

These are clues. Confirm the actual installed implementation before changing
code.

## Migrate a minimal slice

Choose one read-only operation. Rebuild its server and scripted client using
one explicit dependency set. Verify discovery, valid inputs, and controlled
failure before adding resources, authorization, or elicitation.

Do not modernize a source by replacing only an import line while keeping
incompatible transport constructors and callback types. A library migration
can change Python attributes without changing their wire spelling.

## Compare flow, not only syntax

Legacy initialization establishes connection-level agreement. Modern requests
carry their own version and capabilities. Legacy server requests for input
become input-required round trips in modern operation.

This affects state ownership and side effects. A handler that previously
waited can now be reentered. Moving code into the new API without revisiting
when a write occurs can create repeated actions.

Subscriptions, task methods, cancellation, and caching also require
version-specific review. “Both examples use HTTP” is not enough compatibility
evidence.

## Preserve useful historical explanations

The old handshake remains worth understanding when maintaining legacy hosts.
Label the trace and keep it in the compatibility guide. Do not rewrite the
archive silently, because that erases the context behind earlier decisions.

The maintained concept guide should have one current explanation plus a short
legacy distinction. Use links for deeper historical behavior.

## Correct the nonstandard parts

The archive's `[DONE]` sentinel and `stream/chunk` messages are not made
standard merely by being old. Distinguish a superseded standard from a custom
or incorrect example. The catalog records concrete locations for these issues.

## Migration completion

A successful import is only the beginning. Verify the client/server pair,
required host features, authentication, failure behavior, and any business
side-effect protections. Record what was tested and which deployment remains
a proposal.

## Recognize implementation families in code

These imports are evidence of different implementation surfaces:

```python
# Standalone FastMCP used by this course
from fastmcp import FastMCP

# Older official Python SDK v1 examples may use this instead
from mcp.server.fastmcp import FastMCP as SDKv1FastMCP
```

Do not keep both in one migrated application. The side-by-side form is shown
only for recognition. Select one pinned stack, rebuild one minimal server and
client, and verify its actual protocol behavior before migrating advanced
features.

**Professional articulation:**

> “We migrate the interaction model and state assumptions as well as the SDK
> calls, and retain explicit compatibility coverage for older clients.”

## Sources and next step

- [Archived MCP walkthrough](../../02-fast-mcp/walk-through-docs/walk-through.md)
- [Archived legacy elicitation example](../fastMcp-fastApi-uvicorn-ngnix-docker/81_MCP_Elicitation.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/changelog) — checked 2026-11-15.

Next: [A ticket service grown one requirement at a time](32-capstone.md).

