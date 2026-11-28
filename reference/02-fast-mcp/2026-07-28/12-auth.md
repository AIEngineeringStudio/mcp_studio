# Lesson 12 — Authentication and authorization

## Outcome

After this lesson, you can trace the MCP HTTP authorization flow and keep
identity, scopes, component visibility, and business authorization separate.

## Identity is not permission

```
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

```
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

```
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

## One policy for visibility and execution

The lab uses one policy function in both paths. A hidden tool is also denied
when a client calls its name directly.

```python
TOOL_SCOPES = {
    "list_calendar_events": "calendar:read",
    "create_calendar_event": "calendar:write",
}


def permits(tool_name: str, granted_scopes: set[str]) -> bool:
    required_scope = TOOL_SCOPES.get(tool_name)
    return required_scope is None or required_scope in granted_scopes
```

Production code receives `granted_scopes` only after validating issuer,
audience, expiry, signature or introspection, and token status.

## Token passthrough is forbidden

Do not forward an MCP access token unchanged to a downstream API. That creates
audience confusion and a confused-deputy risk.

```
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

**Execution boundary:**

> Streamable HTTP on loopback. Tokens and the downstream calendar are
> synthetic; no authorization server or external account is contacted.

The calendar authorization lab uses synthetic tokens and no external account:

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python verify_auth_calendar.py
```

Expected output ends with:

```
calendar auth: discovery, private tool visibility, direct-call denial, user isolation, and mock downstream delegation passed
```

The complete runnable files are
[`auth_calendar_server.py`](labs/auth_calendar_server.py) and
[`verify_auth_calendar.py`](labs/verify_auth_calendar.py).

Read the detailed sequence in
[`../concepts/20-oauth-discovery.md`](../../01-mcp-concepts/guides/20-oauth-discovery.md) and
[`../concepts/21-authorization.md`](../../01-mcp-concepts/guides/21-authorization.md).

**Say it professionally:**

> The MCP server validates a token issued for its resource, then applies
> component, tenant, object, and downstream policy. Tool visibility improves
> least privilege, but direct invocation must enforce the same authorization.

## Official references

- [Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- [Security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)
- [FastMCP authentication](https://gofastmcp.com/servers/auth/authentication)

