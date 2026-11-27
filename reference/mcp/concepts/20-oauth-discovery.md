# OAuth discovery and delegated calendar access

**Outcome:** Trace how an MCP client discovers an authorization server, obtains
an access token for the MCP resource, and keeps that token separate from a
downstream calendar credential.

**Prerequisites:** [11: Streamable HTTP](11-streamable-http.md),
[19: Host validation, Origin, and CORS](19-origin-cors.md).

**Version boundary:** This guide targets MCP `2026-07-28`. It does not use the
legacy `initialize` handshake, `Mcp-Session-Id`, or a persistent `GET /mcp`
stream. Read [the version baseline](../VERSIONS.md) before adapting older
examples.

## Start with the user need

Alice asks an agent to list her calendar events. The agent's MCP host connects
to a protected Calendar MCP server. The host does not yet know which
authorization server the MCP server trusts.

The system must establish two different permissions:

1. May this host call the Calendar MCP server for Alice?
2. May the Calendar MCP server read Alice's calendar at the downstream provider?

Those questions may use the same identity platform, but they are separate
resource boundaries.

```
+-------------+    token A: audience = Calendar MCP    +--------------+
| MCP host    | --------------------------------------> | Calendar MCP |
| and client  |                                         | server       |
+-------------+                                         +--------------+
                                                               |
                                      token B: audience = Calendar API
                                                               |
                                                               v
                                                        +--------------+
                                                        | Calendar API |
                                                        +--------------+
```

Token A must not be passed through as token B.

## Assign one responsibility to each actor

**MCP host and client:**

> Discover authorization metadata, register or identify the OAuth client,
> obtain a token, store it securely, and attach it to every MCP HTTP request.

**Authorization server:**

> Authenticate the user when needed, collect consent, and issue tokens for a
> specific resource and set of scopes.

**MCP server:**

> Act as an OAuth Resource Server. Publish Protected Resource Metadata,
> validate MCP access tokens, and authorize each operation.

**Calendar provider:**

> Validate a separate calendar-audience credential and enforce the user's or
> workload's calendar permissions.

An MCP server normally does not implement the login page or mint access tokens.
Those are authorization-server responsibilities.

## Follow the discovery and authorization sequence

```
+------------+        +--------------+        +----------------------+
| MCP client |        | MCP server   |        | Authorization server |
+------------+        +--------------+        +----------------------+
      |                      |                           |
      | protected request    |                           |
      |--------------------->|                           |
      | 401 + metadata URL   |                           |
      |<---------------------|                           |
      |                      |                           |
      | GET protected-resource metadata                 |
      |--------------------->|                           |
      | resource + authorization_servers                |
      |<---------------------|                           |
      |                                                  |
      | GET OAuth or OIDC metadata                       |
      |------------------------------------------------->|
      | issuer + authorize/token endpoints + features   |
      |<-------------------------------------------------|
      |                                                  |
      | Authorization Code + PKCE + resource             |
      |------------------------------------------------->|
      | access token for the MCP resource                |
      |<-------------------------------------------------|
      |                      |                           |
      | MCP request + token  |                           |
      |--------------------->|                           |
      | authorized result    |                           |
      |<---------------------|                           |
```

### Step 1: receive or construct the metadata location

When a protected request has no usable token, the MCP server returns an HTTP
challenge similar to:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer
  resource_metadata="https://calendar.example.com/.well-known/oauth-protected-resource/mcp",
  scope="calendar:read"
```

The client should use the `resource_metadata` URL from the challenge when it is
present. Otherwise, it tries the standard well-known locations derived from the
MCP endpoint.

### Step 2: read Protected Resource Metadata

```json
{
  "resource": "https://calendar.example.com/mcp",
  "authorization_servers": [
    "https://login.example.com/tenant-a"
  ],
  "scopes_supported": [
    "calendar:read"
  ],
  "bearer_methods_supported": [
    "header"
  ]
}
```

This document tells the client which authorization servers can issue tokens for
the MCP resource. It does not grant permission.

When multiple authorization servers are listed, the client chooses one and
keeps its registration, credentials, and tokens isolated by the selected
issuer.

### Step 3: discover and validate authorization-server metadata

The client tries the OAuth Authorization Server Metadata and OpenID Connect
Discovery locations required by the MCP specification. Issuers with path
components require path-aware well-known URLs.

The returned `issuer` must exactly equal the issuer used for discovery. A client
must reject metadata that was fetched from one location but names another
issuer.

### Step 4: establish a client identity

Use the following order:

1. Existing pre-registered client information.
2. Client ID Metadata Documents when the authorization server supports them.
3. Dynamic Client Registration only as a compatibility fallback.
4. User-supplied client registration when no automatic option is available.

Persisted client credentials belong to the issuer that created them. Do not
reuse them after Protected Resource Metadata changes to a different issuer.

### Step 5: obtain an MCP-resource token

For user-delegated access, use Authorization Code with Proof Key for Code
Exchange (PKCE). Include the MCP resource identifier in both the authorization
and token requests:

```
resource=https://calendar.example.com/mcp
scope=calendar:read
```

The client also validates `state`, the exact redirect URI, and the authorization
response issuer when the authorization server supplies `iss`.

For a machine acting as itself, Client Credentials may be appropriate. That
token represents the workload, not Alice. It must not be described as user
delegation.

## Add the downstream calendar boundary

After the Calendar MCP server accepts token A, it may still need token B for
Microsoft Graph, Google Calendar, or another provider.

### Microsoft Graph pattern

Microsoft Entra can use the On-Behalf-Of (OBO) flow when the incoming access
token is for the middle-tier MCP API and represents a signed-in user:

```
MCP token for Calendar MCP
        |
        v
Entra OBO exchange
        |
        v
Graph token with Calendars.Read or Calendars.ReadWrite
```

The exchange validates the incoming assertion and issues a new token whose
audience is Microsoft Graph. App-only workloads use Client Credentials instead;
OBO is for user principals.

### Google Calendar patterns

For a normal user-consent integration, the Calendar MCP service commonly runs a
Google Authorization Code flow, requests the needed Calendar scopes, and stores
the user's refresh token securely for offline access. It then refreshes
short-lived Google access tokens as needed.

Google Workspace domain-wide delegation is a separate administrator-controlled
service-account pattern. It is not ordinary end-user OBO and should not be the
default for a consumer calendar integration.

If the host connects directly to a provider-operated Calendar MCP server, that
provider may combine the MCP and calendar boundaries internally. A custom MCP
proxy must still keep its inbound token separate from the calendar API token.

## Trace one failure

Alice presents a correctly signed token, but its audience is
`https://inventory.example.com/mcp`.

```
valid signature
    + wrong audience
    = reject with HTTP 401
```

Signature verification alone is not enough. Accepting a token issued for a
different resource creates a confused-deputy and token-passthrough risk.

## Run the concept lab

The runnable lab uses fake tokens and synthetic events. It demonstrates
Protected Resource Metadata, request authentication, scope-filtered tool
visibility, direct-call denial, and a mock downstream credential broker.

From the workspace root:

```bash
cd reference/mcp/labs
export UV_CACHE_DIR="$PWD/.uv-cache"
export UV_PYTHON_INSTALL_DIR="$PWD/.python"
uv sync --locked --python 3.14.3
uv run python verify_auth_calendar.py
```

Expected result:

```
calendar auth: discovery, private tool visibility, direct-call denial, user isolation, and mock downstream delegation passed
```

The same commands apply to Intel and Apple Silicon Macs. The current validation
record covers Intel macOS; compatible native wheels must still be confirmed on
Apple Silicon.

The files are [auth_calendar_server.py](../fast-mcp-2026-07-28/labs/auth_calendar_server.py) and
[verify_auth_calendar.py](../fast-mcp-2026-07-28/labs/verify_auth_calendar.py). The credential
broker is explicitly a simulation. It never contacts Google, Microsoft, or a
real authorization server.

**Professional articulation:**

> “Protected Resource Metadata tells the MCP client which authorization server
> can issue a token for the MCP resource. If the MCP server calls a calendar API,
> it obtains a separate calendar-audience credential instead of forwarding the
> inbound token.”

## Sources and next step

- [MCP authorization specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- [MCP authorization-server discovery](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/authorization-server-discovery)
- [MCP authorization security considerations](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations)
- [Microsoft Entra On-Behalf-Of flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow)
- [Google OAuth for web-server applications](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google Calendar MCP server configuration](https://developers.google.com/workspace/calendar/api/guides/configure-mcp-server)
- [Google service accounts and domain-wide delegation](https://developers.google.com/identity/protocols/oauth2/service-account)
- [Archive: OAuth protected-resource discovery transcript](../auth/03-OAuth_Protected_Resource_Discovery.md)
- [Archive: protected tools and resources transcript](../auth/02-MCP-Server-OAuth-Protected-Tools-Resources.md)

Next: [Authorization, tool visibility, and calendar isolation](21-authorization.md).
