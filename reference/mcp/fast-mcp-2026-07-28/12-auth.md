# Lesson 12 — Authentication and authorization

## Outcome

After this lesson, you can trace the MCP HTTP authorization flow and keep
identity, scopes, component visibility, and business authorization separate.

## Identity is not permission

```text
authentication  -> who is the caller?
authorization   -> may this caller perform this operation on this object?
```

A valid token does not automatically permit every tool, ticket, or downstream
system.

## Transport boundary

MCP authorization is optional. When used:

- HTTP implementations should follow the MCP authorization specification;
- stdio implementations should normally obtain credentials from their
  environment instead of running an HTTP OAuth flow.

In the HTTP model, the MCP server is an OAuth resource server. The MCP client is
an OAuth client acting for a resource owner. An authorization server issues
access tokens for the MCP resource.

## Discovery flow

```text
MCP client                 MCP server              Authorization server
    |                          |                            |
    |-- unauthenticated ------>|                            |
    |<-- 401 + metadata -------|                            |
    |-- read protected resource metadata ----------------->|
    |-- discover authorization server -------------------->|
    |-- authorize with resource indicator ---------------->|
    |<-- access token --------------------------------------|
    |-- Bearer token --------->|                            |
```

The server advertises Protected Resource Metadata, and a 401 challenge can name
its location through `resource_metadata`. Clients use the `resource` parameter
so the authorization server issues a token for the intended MCP resource.

Dynamic Client Registration is deprecated in this revision. Prefer Client ID
Metadata Documents when the deployment supports them.

## Validate the token at the MCP server

The resource server validates at least:

- signature or introspection result;
- issuer and intended audience/resource;
- expiry and not-before constraints;
- granted scopes;
- token status and applicable identity claims.

A bearer token may be a JWT or an opaque reference. Do not assume format from
the word “token.”

## 401 and 403

**401 Unauthorized:**

> Authentication is missing, invalid, expired, or insufficient and the client
> may need an authorization challenge.

**403 Forbidden:**

> The caller is authenticated, but policy denies the requested operation.

Return only the information needed for safe remediation. Do not disclose
whether another tenant's object exists.

## Authorization layers

```text
request
  |
  +-- token validation
  +-- scope/role check
  +-- tool visibility policy
  +-- direct call enforcement
  +-- tenant and object ownership
  +-- downstream provider policy
```

Filtering `tools/list` is useful, but it is not enforcement. A caller can still
send `tools/call` directly; authorize both discovery and execution.

## Token passthrough is forbidden

Do not forward an MCP access token unchanged to a downstream API. That creates
audience confusion and a confused-deputy risk.

```text
MCP token -> validate at MCP server
downstream credential -> obtain separately for downstream audience
```

Keep downstream credentials in a server-side broker or token store, bound to
the correct user and provider. Never expose them to the model.

## Continuation state is not identity

Possession of `requestState`, a basket ID, or an operation handle does not prove
who the caller is. Bind state to the authenticated principal, enforce expiry
and replay policy, and re-authorize every retry.

## Hands-on checkpoint

The calendar authorization lab uses synthetic tokens and no external account:

```bash
cd reference/mcp/labs
uv run python verify_auth_calendar.py
```

Read the detailed sequence in
[`../concepts/20-oauth-discovery.md`](../concepts/20-oauth-discovery.md) and
[`../concepts/21-authorization.md`](../concepts/21-authorization.md).

**Say it professionally:**

> The MCP server validates a token issued for its resource, then applies
> component, tenant, object, and downstream policy. Tool visibility improves
> least privilege, but direct invocation must enforce the same authorization.

## Official references

- [Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- [Security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)
- [FastMCP authentication](https://gofastmcp.com/servers/auth/authentication)

