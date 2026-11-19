# Authorization, tool visibility, and calendar isolation

**Outcome:** Use one server-side policy to control which calendar tools a caller
can discover, which calls it may execute, and which user's events it may access.

**Prerequisites:** [16: Service layers and persistence](16-service-persistence.md),
[20: OAuth discovery and delegated calendar access](20-oauth-discovery.md).

## Authentication starts the decision

Authentication establishes a verified caller. Authorization decides whether
that caller may perform one operation on one resource.

```
verified subject
    + client or agent identity
    + granted scopes
    + requested tool
    + target calendar and event
    + current server-side policy
    = allow or deny
```

A valid token does not mean “allow every tool.” A `calendar:read` scope does not
mean “read every calendar.”

## Separate three authorization layers

### Layer 1: token validity

Before MCP dispatch, validate:

- Signature or active introspection state.
- Issuer.
- Audience or resource binding.
- Expiration and not-before time.
- Subject and client identity.
- Required baseline scopes.

Missing, invalid, expired, or wrong-audience tokens receive HTTP `401` with a
`WWW-Authenticate` challenge pointing to Protected Resource Metadata.

### Layer 2: operation permission

Map each MCP operation to its minimum permission:

```
list_calendar_events    -> calendar:read
get_calendar_event      -> calendar:read
create_calendar_event   -> calendar:write
delete_calendar_event   -> calendar:write + high-impact policy
admin_export_calendars  -> calendar:admin + administrator entitlement
```

An authenticated token with insufficient scopes should receive HTTP `403` and
an `insufficient_scope` challenge when the client can use scope step-up:

```http
HTTP/1.1 403 Forbidden
WWW-Authenticate: Bearer
  error="insufficient_scope",
  scope="calendar:write",
  resource_metadata="https://calendar.example.com/.well-known/oauth-protected-resource/mcp"
```

The client combines the challenged scope with scopes it already needs,
reauthorizes, and retries only a bounded number of times.

### Layer 3: calendar and event ownership

The server derives the user and tenant from validated identity and server-side
policy. It never trusts these model-generated arguments as authority:

```json
{
  "user_id": "ceo@example.com",
  "tenant_id": "another-company"
}
```

For an ordinary personal-calendar tool, the server should query the calendar
belonging to the validated subject. Shared calendars require a provider-side
access-control list or an equivalent business policy check.

## Treat visibility as usability, not security

Filtering `tools/list` reduces model confusion and can avoid disclosing features
the caller can never use. It does not enforce authorization.

An attacker can:

- Guess a hidden tool name.
- Reuse a stale cached catalog.
- Construct `tools/call` directly.
- Bypass a client-side filter.

Therefore, `tools/call` must evaluate the same policy again.

```
                         +------------------------+
tools/list  ------------>| shared policy registry|----> filtered catalog
                         +------------------------+
                                    ^
                                    |
tools/call  ------------------------+----> allow or deny, then dispatch
```

The policy registry is the single source of truth. Visibility and execution do
not maintain separate scope maps.

## Preserve scope step-up usability

Hiding every tool whose optional scope is absent can prevent the host from ever
learning that it may request more permission.

Use this practical distinction:

**Permanent ineligibility:**

> Hide tools the subject, tenant, or agent is never allowed to use. Examples are
> administrator-only export or a tool unavailable in the caller's organization.

**Consent that can be added:**

> Consider listing an eligible tool even when its optional scope has not yet
> been granted. A call can then return `403 insufficient_scope`, allowing the
> host to run the standard step-up flow.

If the existence of a feature is itself confidential, hide it—but still deny a
direct call using the same policy.

Authorization-dependent catalog responses must use private caching. For MCP
`2026-07-28`, keep `cacheScope` as `private`; use a low or zero `ttlMs` until the
entitlement and revocation behavior is intentionally designed.

## Keep MCP and calendar tokens separate

The inbound token is intended for the MCP server:

```
audience = https://calendar.example.com/mcp
```

The downstream token is intended for the provider:

```
audience = https://graph.microsoft.com
```

or an equivalent Google Calendar resource.

The MCP server must not relay the inbound access token to the calendar provider.
Choose one explicit downstream pattern.

### Pattern A: Microsoft Entra OBO

Use the incoming user token as the assertion in an Entra On-Behalf-Of exchange.
The middle-tier MCP application authenticates itself and requests Microsoft
Graph delegated scopes such as `Calendars.Read` or `Calendars.ReadWrite`.

The result is a new Graph token. OBO does not turn an app-only token into a user
token; app-only workloads use Client Credentials.

### Pattern B: Google user consent and stored refresh token

Run Google's Authorization Code flow for the Calendar scopes. Request offline
access if the server must operate after the browser session ends. Encrypt and
store the refresh token per user and OAuth client. Refresh a short-lived Google
access token when calling Calendar.

This is delegated user access, but it is not the Microsoft OBO protocol. Do not
assume a generic MCP token can be exchanged by Google.

### Pattern C: Google Workspace domain-wide delegation

A Workspace administrator grants selected scopes to a service account. The
service account requests a token while impersonating a specific domain user.
This is powerful organization-wide authority. Restrict scopes, protect the
service identity, audit impersonation, and never take the impersonated user from
an untrusted model argument.

### Pattern D: workload-only calendar

A scheduler or integration may act as itself through Client Credentials or a
service account. Its tools should describe workload-owned calendars explicitly.
Do not claim that a human user performed the action.

## Walk the runnable policy example

The calendar lab has three fake MCP tokens:

```
mcp-alice-read  -> calendar:read
mcp-alice-write -> calendar:read + calendar:write
mcp-bob-read    -> calendar:read for Bob's identity
```

The read tokens see only `list_calendar_events`. Alice's write token sees both
`list_calendar_events` and `create_calendar_event`.

The direct-call test deliberately invokes the hidden write tool with the read
token. The server rejects it because dispatch consults the same policy as
discovery. The mock credential broker then proves that the successful tool call
uses a newly created calendar credential, not the inbound MCP bearer token.
The Bob call returns only Bob's synthetic event, proving that the subject comes
from validated identity rather than a model-supplied user argument.

The lab treats the hidden write tool as confidential, so a guessed direct call
receives a generic “unknown tool” result. A production service that wants
incremental scope consent should expose an eligible write tool and enforce its
scope at the HTTP boundary, returning the `403 insufficient_scope` challenge
shown earlier.

Run it from the workspace root:

```bash
cd reference/mcp/labs
export UV_CACHE_DIR="$PWD/.uv-cache"
export UV_PYTHON_INSTALL_DIR="$PWD/.python"
uv sync --locked --python 3.14.3
uv run python verify_auth_calendar.py
```

See [the server](../labs/auth_calendar_server.py) and
[the verification flow](../labs/verify_auth_calendar.py).

## Evolve the concept lab into production

The fake token table and mock credential broker make the mechanism visible. A
production extension replaces one boundary at a time.

### Replace token lookup with verification

Use an MCP SDK `TokenVerifier` backed by one of:

- Local JWT validation against a trusted and cached JSON Web Key Set (JWKS).
- RFC 7662 token introspection using a confidential Resource Server identity.

Validate issuer, audience/resource, lifetime, token type, and required claims.
Refresh keys when an unknown `kid` appears, and bound cache lifetimes.

### Replace the mock broker with a provider adapter

Create an interface such as:

```python
class CalendarCredentialBroker:
    async def for_user(
        self,
        *,
        subject: str,
        provider: str,
        required_scopes: set[str],
    ) -> CalendarCredential: ...
```

The Microsoft implementation uses a supported OBO library. The Google
implementation uses securely stored consent and refresh credentials, or an
explicitly approved Workspace delegation design. Keep provider tokens out of
tool results, model context, logs, and exception messages.

### Externalize configuration

Use environment variables loaded through a typed `pydantic-settings` model.
Require issuer URLs, MCP resource URL, allowed algorithms, provider client IDs,
secret references, and tenant policy at process startup. Commit an
`.env.example`, never a real `.env` or provider secret.

### Make business state durable

Store calendar-account links, consent status, encrypted credential references,
policy versions, idempotency keys, and audit records in durable storage. Avoid
using request context or MCP transport state as a credential database.

### Protect side effects

For event creation, update, response, and deletion:

- Validate time zones and attendee domains.
- Use stable idempotency keys where the provider supports them.
- Distinguish timeout, rejection, and unknown outcome.
- Require confirmation for high-impact or unusually broad changes.
- Re-check authorization immediately before the side effect.

Human confirmation does not create missing permission. Both confirmation and
backend authorization must pass.

### Add operational evidence

Audit allowed and denied decisions without recording tokens or full sensitive
event bodies. Record a correlation ID, subject identifier, client identifier,
tool, required policy, outcome, provider, and latency.

Test at least these cases:

```
missing token
invalid signature or inactive token
expired token
wrong issuer
wrong MCP audience
missing read scope
missing write scope
direct call to hidden tool
wrong tenant or calendar owner
revoked downstream consent
downstream token for the wrong audience
provider timeout before and after a possible write
```

## Recognize common design errors

**Client-side tool filtering:**

> It improves presentation but provides no server-side protection.

**Agent-minted identity:**

> An agent must not choose its own role or sign a token that the server accepts
> as user authority.

**JWT versus OAuth as two headers:**

> OAuth is the authorization framework; JSON Web Token (JWT) is one token
> representation. Use the standard `Authorization: Bearer` header for the MCP
> resource token.

**Global current-user state:**

> Shared mutable identity can leak between concurrent requests. Use the SDK's
> request-scoped validated access-token context.

**Token passthrough:**

> A token issued for the MCP resource is not a calendar API token. Exchange it
> or obtain a separate provider credential.

**Scopes without record checks:**

> `calendar:read` allows an operation class. It does not identify which calendar
> or event the caller owns.

**Professional articulation:**

> “Tool visibility is a usability decision; execution-time authorization is the
> security boundary. The server combines validated identity, scopes, tenant and
> record policy, then obtains a separate downstream calendar credential.”

## Sources and next step

- [MCP authorization and scope challenges](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- [MCP authorization security considerations](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations)
- [MCP Python SDK authorization](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/authorization.md)
- [MCP Python SDK caching hints](https://py.sdk.modelcontextprotocol.io/client/caching/)
- [Microsoft Entra On-Behalf-Of flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow)
- [Google OAuth for web-server applications](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google Calendar MCP server configuration](https://developers.google.com/workspace/calendar/api/guides/configure-mcp-server)
- [Google service accounts and domain-wide delegation](https://developers.google.com/identity/protocols/oauth2/service-account)
- [Archive: secure gateway transcript](../auth/01-Secure-MCP-gateway.md)
- [Archive: request-context authentication transcript](../auth/04B-MCP_server-AuthN.md)

Next: [Reverse proxies and TLS](22-proxy-tls.md).
