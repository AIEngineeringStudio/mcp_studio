# Pagination, caching, and subscriptions

**Outcome:** Keep large catalogs and resources bounded, fresh, and isolated by caller.

**Prerequisites:** [09: Resources, URIs, and templates](09-resources.md), [11: Streamable HTTP](11-streamable-http.md), [21: Authorization, scopes, and tenant isolation](21-authorization.md).

## A list can outgrow one response

A small server returns a few tools. A large server might expose hundreds.
A ticket search might return thousands of records. Pagination divides a list
into bounded pieces and supplies a continuation cursor.

```
first request --> page A + cursor
next(cursor) --> page B + cursor
next(cursor) --> page C + no next cursor
```

Treat protocol cursors as opaque. Do not assume they are offsets or decode
them in a client. Application search pagination is a separate contract from
MCP catalog pagination, even if both use cursors.

## Stable ordering

If records are inserted while pages are read, offset pagination can skip or
repeat records. A stable ordering and an appropriate cursor/snapshot design
reduce ambiguity. Include a unique tie-breaker when timestamps can be equal.

In the archive's batch-processing example, the final batch must respect both
the configured batch size and remaining result limit. “Return up to 25” should
not become 30 just because batches contain 10.

## Cache the right representation

A cache reuses previously obtained data. Its key must include inputs that
change the result. If user permissions affect visibility, a shared cache keyed
only by method can expose one user's catalog or records to another user.

Modern MCP provides freshness and cache-scope information for certain results.
Honor those contracts and keep authorization-aware partitioning. Freshness
does not override access revocation.

## Change notification

Modern `subscriptions/listen` requests selected change notifications and
receives an acknowledgment indicating supported filters. A resource update
notification tells a client that something changed; the client may need to
refetch the resource to obtain current content.

Request progress travels on the originating request's response path, not the
catalog/resource subscription stream. This distinction matters when several
operations are active simultaneously.

## Reconnect deliberately

A subscription can end because the connection closes or the server restarts.
Reestablish it and reconcile current state. Do not assume every intervening
change is replayed. A notification channel is not automatically a durable
event log.

## Worked failure

Alice's cached ticket list contains A's records. Bob calls the same search.
A cache keyed only by `status=open` is unsafe. Include trusted identity/tenant
scope in the cache design, or avoid shared caching until isolation is proven.

**Professional articulation:**

> “Pagination bounds each response; caching reduces repeated work;
> subscriptions signal change. Each needs its own consistency and access
> rules.”

## Sources and next step

- [Archive: _learning_resources/walkthrough_doc.md](../../_learning_resources/walkthrough_doc.md)
- [Archive: _learning_resources/diagrams/diagrams_index.md](../../_learning_resources/diagrams/diagrams_index.md)
- [Archive: conversations/streamable/streamable-6.md](../../conversations/streamable/streamable-6.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/subscriptions) — checked 2026-11-15.

Next: [Testing and debugging MCP by layer](27-testing.md).

