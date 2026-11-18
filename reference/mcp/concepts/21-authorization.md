# Authorization, scopes, and tenant isolation

**Outcome:** Enforce who can do what to which record, independently of tool visibility.

**Prerequisites:** [16: Service layers and persistence](16-service-persistence.md), [20: OAuth discovery and delegated access](20-oauth-discovery.md).

## Identity is the beginning of a decision

Authentication establishes a verified caller identity. Authorization decides
whether that caller may perform a particular action on a particular resource.

A token with `tickets:read` may allow a kind of operation. It does not
necessarily permit every ticket in every tenant. A tenant is a customer or
organizational boundary whose records must remain isolated.

```
verified caller + operation + target record + current policy
                              |
                              v
                         allow / deny
```

Do not trust a model-supplied `tenant_id` as the caller's authority. Derive
permitted tenant context from verified identity and server-side policy.

## A concrete decision

Alice belongs to tenant A and has `tickets:read`. Ticket T-100 belongs to
tenant A, so a lookup may succeed. T-900 belongs to tenant B, so the same tool
must reject that lookup even though the argument is a valid string and the
tool appears in Alice's catalog.

Write access adds another decision. Alice can have read permission without
permission to close the ticket. A confirmation form does not manufacture
that missing permission.

## Visibility is usability

Filtering tools can prevent confusion and reduce model context. It is not
enforcement. A client can guess a hidden tool name or use a stale cached
catalog. Check access again when invoking tools and reading resources.

Modern catalog results may vary according to request authorization. That
does not justify keeping one mutable “current user” on a shared server object.

## Downstream credentials

An MCP server calling a backend API may need a separate credential or a
proper delegation mechanism. Do not forward the incoming access token to a
different audience by default. A valid token is intended for a resource, not
for every service in the request chain.

If a gateway performs broad checks, the business service should still enforce
record-level access at the source of truth. Otherwise bypass routes or confused
identity propagation can defeat the intended policy.

## Meaningful verification

Test the same valid request under permitted, missing-scope, wrong-tenant,
expired-token, and changed-permission conditions. Also invoke a filtered tool
directly. Verify both denial and absence of a side effect.

Use dummy identities and fixture records in tests. Never print access tokens
to understand a failure; record safe validation outcomes and a correlation ID.

**Professional articulation:**

> “Scopes constrain operation classes. The service also enforces resource
> ownership and tenant isolation at execution time.”

## Sources and next step

- [Archive: conversations/auth/01-Secure-MCP-gateway.md](../../conversations/auth/01-Secure-MCP-gateway.md)
- [Archive: conversations/auth/04B-MCP_server-AuthN.md](../../conversations/auth/04B-MCP_server-AuthN.md)
- [Archive: conversations/chatgpt/10_TLS_AuthN_AuthZ_Observability.md](../../conversations/chatgpt/10_TLS_AuthN_AuthZ_Observability.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) — checked 2026-11-15.

Next: [Reverse proxies and TLS](22-proxy-tls.md).

