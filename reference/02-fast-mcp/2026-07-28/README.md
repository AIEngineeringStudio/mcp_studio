# FastMCP with MCP 2026-07-28

This study path teaches the **modern MCP protocol era** introduced by revision
`2026-07-28`, using standalone **FastMCP 4.2.0** for Python examples.

**Checked:** 2026-11-19

**Protocol source of truth:**

> Use the versioned
> [MCP 2026-07-28 specification](https://modelcontextprotocol.io/specification/2026-07-28)
> for wire behavior. Use FastMCP documentation for framework APIs. If the two
> appear to conflict, first separate the protocol revision from the framework
> version.

## What changed in this revision

Keep this model visible while reading every lesson:

```
2025-11-25 and earlier              2026-07-28
----------------------              ----------
initialize handshake                no handshake
connection/session capabilities     capabilities on every request
optional Mcp-Session-Id             no protocol session
server -> client requests           MRTR input_required result
HTTP GET notification stream        subscriptions/listen POST stream
resource subscribe/unsubscribe      subscriptions/listen filters
```

Modern requests are self-contained. They carry the protocol version and client
capabilities in `params._meta`. `server/discover` is available for up-front
discovery, but it is not an initialization handshake.

Roots, sampling, and protocol logging are **deprecated** in this revision.
`ping`, `logging/setLevel`, and `notifications/roots/list_changed` are removed.
New applications should use the replacements described in lessons 5, 6, and 9.
Dynamic Client Registration is also deprecated; lesson 12 uses the current
authorization guidance.

## Course order

1. [MCP mental model and modern lifecycle](01-04-basics/01-what-mcp-is.md)
2. [Tools](01-04-basics/02-tools.md)
3. [Resources and change subscriptions](01-04-basics/03-resources.md)
4. [Prompts](01-04-basics/04-prompts.md)
5. [Roots: compatibility and replacement patterns](05-06-deprecated/05-roots.md)
6. [Sampling: compatibility and replacement patterns](05-06-deprecated/06-sampling.md)
7. [Elicitation and multi-round requests](07-elicitation/07-elicitation.md)
8. [Progress and cancellation](08-progress-cancel/08-progress-cancel.md)
9. [Observability and deprecated protocol logging](11-observability.md)
10. [Pagination, caching, and completion](10-pagination-completion/10-pagination-completion.md)
11. [stdio and Streamable HTTP](01-04-basics/01B-transport.md)
12. [Authentication and authorization](12-auth.md)
13. [Context, dependency injection, lifespan, and state](13-context-di-lifespan-state.md)
14. [FastMCP middleware](14-fastmcp-middleware-req_pipeline.md)
15. [Server composition](15-server-composition.md)
16. [Versioning and capabilities](16-versioning-capability_negotiation.md)
17. [Transport security](17-fastmcp_transport_security.md)

For the more granular maintained curriculum, use
[Learn MCP progressively](../../01-mcp-concepts/README.md). The original handshake-era material
is preserved in `../fast-mcp-2025-11-25/` for compatibility study.

## Hands-on environment

The runnable lab in [`../labs/`](labs/README.md) pins:

- `fastmcp==4.2.0`
- `mcp==2.3.0`

Run the verified baseline from the repository root:

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python -m unittest -q
```

Every numbered lesson now links to a focused runnable checkpoint. The complete
command list is in the [lab README](labs/README.md); use the command in the
current lesson when studying one concept rather than running unrelated tests.

The workspace-local cache keeps this exercise inside the project directory.
The commands are the same on Intel and Apple Silicon Macs. The current
validation record identifies which platform was actually executed; a lockfile
alone is not cross-platform proof.

## Reading rule for wire examples

The specification sometimes omits repeated metadata to keep an example short.
This course labels such omissions. Unless a section is explicitly marked
**legacy**, every request should be understood to include:

```json
"_meta": {
  "io.modelcontextprotocol/protocolVersion": "2026-07-28",
  "io.modelcontextprotocol/clientInfo": {
    "name": "study-client",
    "version": "1.0.0"
  },
  "io.modelcontextprotocol/clientCapabilities": {}
}
```

Every successful modern result uses `resultType: "complete"`, except a
multi-round response, which uses `resultType: "input_required"`.

See the official [deprecated-feature registry](https://modelcontextprotocol.io/specification/2026-07-28/deprecated)
for migration paths and earliest-removal dates.

