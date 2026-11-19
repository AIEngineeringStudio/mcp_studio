# Lesson 3 — Resources, URIs, and change subscriptions

## Outcome

After this lesson, you can choose between a resource and a tool, design stable
resource URIs, and explain how modern clients receive resource changes.

## Resources are addressable context

```
Tool                               Resource
----                               --------
operation                          addressable data
tools/call(name, arguments)        resources/read(uri)
often a verb                       usually a noun
may have side effects              read-oriented
```

A resource is not necessarily a file. It may represent a document, database
record, schema, configuration snapshot, or generated report. Its URI is a
stable protocol identity; it need not reveal the backend storage location.

## Discovery and retrieval

`resources/list` returns concrete resource metadata.
`resources/templates/list` returns parameterized URI families.
`resources/read` reads either kind through its resolved URI.

The repeated modern request `_meta` is omitted in these short examples.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "resources/read",
  "params": {"uri": "ticket://T-100"}
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "complete",
    "contents": [
      {
        "uri": "ticket://T-100",
        "mimeType": "application/json",
        "text": "{\"ticket_id\":\"T-100\",\"status\":\"open\"}"
      }
    ],
    "ttlMs": 0,
    "cacheScope": "private"
  }
}
```

Resource content is text or binary/blob content. It does not use a tool's
`structuredContent` field. JSON can be carried as text with an appropriate MIME
type. Modern complete results from `resources/read` and resource-list methods
must include `ttlMs` and `cacheScope` hints.

## Resource templates

```
Template: ticket://{ticket_id}
Concrete URI: ticket://T-100
```

Template parameters are encoded in the URI. They are not a tool-style
`inputSchema`. Validate decoded values, normalize carefully, and enforce
authorization after resolution.

```python
import json

from fastmcp import FastMCP

mcp = FastMCP("Ticket resources")


@mcp.resource("ticket://{ticket_id}", mime_type="application/json")
def read_ticket(ticket_id: str) -> str:
    """Read one synthetic ticket."""
    return json.dumps({"ticket_id": ticket_id, "status": "open"})
```

## Resource errors

MCP `2026-07-28` retired the legacy resource-not-found code `-32002` in favor
of `-32602` Invalid Params. Do not copy the older code into a modern-only
server.

## Modern change delivery

The modern revision removed the standalone HTTP GET stream,
`resources/subscribe`, `resources/unsubscribe`, and connection-scoped
subscription state.

```
CLIENT                                      SERVER
  |                                            |
  |-- subscriptions/listen ------------------->|
  |   resourceSubscriptions: [ticket://T-100]  |
  |<-- notifications/subscriptions/acknowledged|
  |<-- notifications/resources/updated --------|
  |<-- final complete result when stream ends --|
```

The server tags delivered notifications with
`io.modelcontextprotocol/subscriptionId`. Request-scoped progress and logging
notifications stay on the originating request's response stream.

- `notifications/resources/list_changed` invalidates resource discovery.
- `notifications/resources/updated` says a selected resource changed.

## Security rules

- Treat every URI as untrusted input.
- Reject traversal and unsafe percent-decoding outcomes.
- Authorize the resolved resource, not only the template.
- Do not use URI obscurity as access control.
- Keep list results deterministic and safe to cache by the declared scope.

## Hands-on checkpoint

```bash
cd reference/mcp/labs
uv run python -m unittest -q test_protocol
```

Read [`../concepts/09-resources.md`](../concepts/09-resources.md) for the deeper
resource-design lesson.

**Say it professionally:**

> Resources expose addressable context through stable URIs. In MCP
> `2026-07-28`, long-lived resource and catalog changes flow through a
> `subscriptions/listen` response stream rather than connection-scoped
> subscribe methods or a standalone GET stream.

## Official references

- [Resources](https://modelcontextprotocol.io/specification/2026-07-28/server/resources)
- [Subscriptions](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/subscriptions)
- [FastMCP resources](https://gofastmcp.com/servers/resources)

