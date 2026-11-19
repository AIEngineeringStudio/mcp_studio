# Lesson 5 — Roots: deprecated compatibility feature

## Outcome

After this lesson, you can explain what roots represented in legacy MCP, why
they are deprecated in `2026-07-28`, and which explicit alternatives to use.

## Status in this protocol revision

**Deprecated:**

> Roots remain in the 2026 schema for compatibility, but new implementations
> should not design around them. The recommended replacements are ordinary tool
> parameters, resource URIs, or server configuration.

The direct server-initiated `roots/list` flow belonged to the handshake era:

```
LEGACY MCP
server -- roots/list --> client
server <-- roots ------- client
```

MCP `2026-07-28` removed the server-to-client request channel and
`notifications/roots/list_changed`. FastMCP 4 therefore does not expose the old
`ctx.list_roots()` pattern for modern connections.

## What a root meant

A root described a client-selected filesystem boundary, usually as a `file://`
URI. It did not provide file contents, grant operating-system permissions, or
authorize every path below it.

```
root URI               file content              authorization
--------               ------------              -------------
declared scope         read by application       enforced by application
```

Even in legacy deployments, servers had to canonicalize paths, prevent
traversal, and enforce authorization separately.

## Preferred modern designs

### Tool parameter

Use a tool argument when the caller chooses the target for one operation:

```python
from fastmcp import FastMCP

mcp = FastMCP("Workspace service")


@mcp.tool
def list_project_files(project_id: str) -> list[str]:
    """List files in a server-known project after authorization."""
    return [f"{project_id}/README.md"]
```

Prefer a server-minted `project_id` over an unrestricted local path for remote
services.

### Resource URI

Use a resource URI when the target is addressable context:

```
project://P-100/file/README.md
```

### Server configuration

Use validated startup configuration when the server operator owns the scope.
Do not expose configuration secrets or raw host paths unless the application
requires them.

## MRTR compatibility form

The modern Multi Round-Trip Request (MRTR) schema can embed a `roots/list`
request inside an `InputRequiredResult`. This exists for compatibility and does
not reverse the deprecation guidance.

```json
{
  "resultType": "input_required",
  "inputRequests": {
    "workspace_roots": {
      "method": "roots/list",
      "params": {}
    }
  },
  "requestState": "opaque-integrity-protected-state"
}
```

The client retries the original `tools/call`, `resources/read`, or
`prompts/get` with `inputResponses`. It does not resume an open server handler.

## Security checklist

- Treat all returned URIs and retry state as untrusted input.
- Resolve and canonicalize before checking containment.
- Bind any continuation state to the authenticated principal and expiry.
- Keep authorization independent from filesystem scope.
- Avoid path strings as durable public identifiers when a server-minted ID is
  safer.

## Hands-on checkpoint

Design a modern replacement for this legacy signature:

```
search_code(query) + hidden roots/list dependency
```

A better public contract is:

```
search_project(project_id, query)
```

The `project_id` is explicit, auditable, and resolvable through server-owned
authorization policy.

**Say it professionally:**

> Roots are a deprecated client capability. For modern MCP, I make scope
> explicit with tool arguments, resource URIs, or validated server
> configuration, then enforce path safety and authorization in application
> code.

## Official references

- [Key changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [MRTR](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [Schema reference](https://modelcontextprotocol.io/specification/2026-07-28/schema)

