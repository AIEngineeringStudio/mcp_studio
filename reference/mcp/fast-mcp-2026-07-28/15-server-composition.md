# Lesson 15 — FastMCP server composition

## Outcome

After this lesson, you can distinguish providers, mounts, proxies, transforms,
and tool search from MCP protocol primitives.

## Composition is behind the protocol boundary

Clients still see ordinary tools, resources, and prompts:

```
local provider ----+
mounted server ----+--> transforms --> MCP catalog --> client
remote proxy ------+
generated source --+
```

MCP does not define `Provider`, `Mount`, `ProxyProvider`, `Transform`, or Tool
Search. Those are FastMCP architecture features.

## Providers source components

A provider supplies tools, resources, and prompts to a FastMCP server.
Decorators register components through a local provider. Other providers can
source components from another FastMCP object, a remote MCP server, generated
metadata, or a custom catalog.

## Mounting and proxying

**Mount:**

> Compose another FastMCP server object in the same application. Namespace its
> components to prevent collisions and preserve ownership clarity.

**Proxy:**

> Source components through an MCP client connection to another server. The
> proxy adds network latency, authentication boundaries, and upstream failure
> modes.

```
mount:  one process/application boundary
proxy:  an additional MCP and network boundary
```

Do not assume that proxying makes an upstream tool safe. Re-apply authorization,
visibility policy, argument validation, timeout, and result-size controls at
the gateway boundary.

## Transforms adapt exposed contracts

A transform may rename, namespace, filter, or reshape components. It needs a
reverse mapping so a client-facing name can be dispatched to the correct source
component.

Changing a tool schema can break compatibility. A transform must not claim a
constraint that the upstream implementation does not enforce.

## Tool search is discovery, not security

For a large catalog, Tool Search can replace a huge advertised list with a
small set of search and call tools.

```
model -> search_tools("email") -> matching tool descriptions
model -> call_tool(found_name)  -> normal dispatch pipeline
```

Hidden tools can remain callable. Enforce authorization during search and again
during direct execution. Never rely on absence from `tools/list` as the only
control.

## Composition failure model

Every remote provider adds:

- latency and timeout behavior;
- version and capability negotiation;
- authentication and token handling;
- name collisions and schema evolution;
- partial failure and circuit-breaker decisions;
- observability correlation.

Prefer a small focused server until aggregation solves a measured problem.

## Hands-on checkpoint

Start with two small in-memory FastMCP servers, mount or proxy one under a
namespace, and verify that the client still uses only `tools/list` and
`tools/call`. Do not add Tool Search until the catalog size creates a real
context or usability problem.

**Say it professionally:**

> Providers source MCP components, transforms adapt their exposed contracts,
> and mounts or proxies compose sources across different topology boundaries.
> These are FastMCP features; the client still speaks standard MCP methods.

## Official references

- [FastMCP providers](https://gofastmcp.com/servers/providers/overview)
- [FastMCP composition](https://gofastmcp.com/servers/composition)
- [FastMCP tool search](https://gofastmcp.com/servers/transforms/tool-search)

