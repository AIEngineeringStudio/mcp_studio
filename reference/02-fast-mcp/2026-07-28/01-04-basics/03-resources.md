# Lesson 3 — Resources, URIs, and change subscriptions

## Outcome

After this lesson, you can choose between a resource and a tool, design stable
resource URIs, and explain how modern clients receive resource changes.


## **Say it professionally:**

> Resources expose addressable context through stable URIs. In MCP
> `2026-07-28`, long-lived resource and catalog changes flow through a
> `subscriptions/listen` response stream rather than connection-scoped
> subscribe methods or a standalone GET stream.

TODO: subscriptions/listen

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
  "params": {
    "uri": "ticket://T-100"
  }
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

## Resources vs Resource Templates

In MCP, the difference is between **concrete resources** and **parameterized
resource definitions**.

| Feature             | `client.list_resources()`               | `client.list_resource_templates()`        |
|---------------------|-----------------------------------------|-------------------------------------------|
| Returns             | Concrete resources                      | Resource templates                        |
| URI                 | Complete URI                            | URI with placeholders                     |
| Parameters required | No                                      | Usually yes                               |
| Example             | `tickets://closed`                      | `ticket://{ticket_id}`                    |
| Purpose             | Discover directly addressable resources | Discover how to address dynamic resources |

### `list_resources()`

Discovers resources that already have a complete URI.

The local server exposes this complete URI:

```
tickets://closed
```

The client discovers them using:

```python
resources = await client.list_resources()
```

The client can directly read any of these URIs:

```python
contents = await client.read_resource("tickets://closed")
```

### `list_resource_templates()`

Discovers URI patterns that the client can use to access specific resources.

For many tickets, the server can expose one template instead of listing every
ticket URI. The local server exposes:

```
ticket://{ticket_id}
```

The client discovers it using:

```python
templates = await client.list_resource_templates()
```

The client supplies the required parameter and reads the resource:

```python
ticket_id = "T-100"
contents = await client.read_resource(f"ticket://{ticket_id}")
```

### How retrieval works

Both discovery methods ultimately use the same `read_resource()` method to
retrieve actual data.

### Important distinction

- A regular resource can also return dynamic data. Its URI is simply fixed.
- A resource template does not return individual ticket IDs. The client must
  obtain them separately.
- Both listing methods return metadata, not the actual resource contents.
- A resource generated from a template can also appear in `list_resources()` if
  the server supports enumerating its instances.

**Mental model:** Think of regular resources as fixed REST endpoint paths and
resource templates as parameterized REST endpoint paths.

```
GET /tickets/closed
GET /tickets/{ticket_id}
```

This is an analogy, not the actual MCP transport mechanism. The ticket URIs
above are illustrative examples.

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

```python
import json

from fastmcp import FastMCP

mcp = FastMCP("Ticket resources")


@mcp.resource("ticket://{ticket_id}", mime_type="application/json")
def read_ticket(ticket_id: str) -> str:
    """Read one synthetic ticket."""
    return json.dumps({"ticket_id": ticket_id, "status": "open"})
```

### Follow the local ticket example

The [server](labs/server.py) registers both forms. The fixed
`@mcp.resource("tickets://closed")` returns a list containing synthetic ticket
`T-101`. The parameterized `@mcp.resource("ticket://{ticket_id}")` calls the
same `lookup_ticket` domain function as the tool and returns JSON text for the
requested ticket. The fixed URI is not a snapshot: its function runs when the
client reads it.

The [client check](labs/verify_primitives.py) first calls
`client.list_resource_templates()` and finds `ticket://{ticket_id}`. It then
calls `client.list_resources()` and finds the complete URI
`tickets://closed`. Neither listing contains the ticket content. Two
`client.read_resource(...)` calls retrieve the content: the fixed URI yields
`T-101` with status `closed`; `ticket://T-100` yields `T-100` with status
`open`. The script decodes the returned text with `json.loads` before printing
the ticket fields.

These records are synthetic and have no authorization logic. A production
handler must validate the decoded ID and check access to the resolved ticket.

### How to run

From the repository root, run the example files beside this guide. The pinned
environment is supplied by `../labs/pyproject.toml` and its lockfile:

```bash
cd reference/mcp/fast-mcp-2026-07-28
UV_CACHE_DIR=../labs/.uv-cache uv run --project ../labs --locked python verify_primitives.py --transport in-memory --focus resources
```

The script prints both discovery lists and both decoded records. Among its
output, expect:

```
Reading resource: tickets://closed
 id: T-101
 status: closed
Reading resource template: ticket://T-100
 id: T-100
 status: open
```

These lines are excerpts; the script prints titles and separators between the
two reads. `--transport stdio` runs the adjacent server in a subprocess;
`--transport http` requires a separately running server at
`http://127.0.0.1:8000/mcp`.

Read [`../concepts/09-resources.md`](../../../01-mcp-concepts/guides/09-resources.md) for the
deeper resource-design lesson.

## Official references

- [Resources](https://modelcontextprotocol.io/specification/2026-07-28/server/resources)
- [Subscriptions](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/subscriptions)
- [FastMCP resources](https://gofastmcp.com/servers/resources)

