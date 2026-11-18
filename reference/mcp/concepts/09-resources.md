# Resources, URIs, and templates

**Outcome:** Represent readable context with a URI and distinguish resource reads from tool actions.

**Prerequisites:** [05: Tools and their contracts](05-tool-contracts.md), [07: The first client and in-memory testing](07-in-memory-client.md).

## Give context an address

A resource exposes readable information through a URI, a uniform resource
identifier. In our example, `ticket://T-100` names the ticket representation.

The custom URI does not imply a public web URL. The MCP client sends a
resource-read operation to the server, which resolves the URI.

```
resource URI --> resources/read --> template match --> record --> content
ticket://T-100                      ticket://{ticket_id}
```

A static resource names one representation. A resource template describes a
family of URIs. Listing static resources is not the same as listing templates,
and a server need not enumerate every ticket as a static resource.

## Compare with the lookup tool

The same business data can appear through a tool or a resource. A tool fits an
operation with structured arguments such as search or lookup. A resource fits
addressable context that the host can read and manage.

Do not use “tools write, resources read” as an absolute classification.
Read-only tools are valid. The distinction is the interface and interaction
model, not whether the implementation happens to use a database SELECT.

## Observe the lab

The [server](../labs/server.py) registers
`@mcp.resource("ticket://{ticket_id}")`. Its handler reads the same fixture as
the lookup tool and serializes it as JSON text. The client's
`read_resource("ticket://T-100")` check confirms that expected content arrives.

The resource handler does not change ticket status. Keeping reads free of
business mutations makes caching and repeated retrieval easier to reason about.

## Identity, freshness, and bounds

A resource URI identifies data; it does not grant access. A guessed ticket URI
must still be checked against the authenticated caller's permissions.
Design content size limits and avoid exposing confidential fields merely
because a record is available in memory.

The host decides how fetched context enters the model's input. Reading a
resource does not guarantee the model sees it, and a template does not imply
that the entire dataset should be fetched.

Freshness matters when the underlying ticket changes. A resource read may
carry caching hints in the modern protocol; change notification support is
optional. A later guide explains pagination, caching, and subscriptions.
For a beginner example, explicitly refetch after a change rather than
assuming automatic synchronization.

## Failure path

If T-100 is removed, a previously valid URI can stop resolving. The caller
should show a meaningful unavailable/not-found state and avoid retaining old
content as if it were current. A cache needs an invalidation and authorization
policy, not just a dictionary.

**Professional articulation:**

> “A resource exposes addressable context. The URI names the representation;
> authorization determines who may read it.”

## Sources and next step

- [Archive: conversations/chatgpt/3_Resources_Prompts.md](../../conversations/chatgpt/3_Resources_Prompts.md)
- [Archive: docs/mcp-learning-guide2.md](../../docs/%5BDONE%5Dmcp-learning-guide2.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/server/resources) — checked 2026-11-15.

Next: [Reusable MCP prompts](10-prompts.md).

