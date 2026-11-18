# Lesson 12 — Authentication + Authorization

This lesson introduces the first real **security boundary** in the MCP stack.

Keep these two concepts separate:

```
AUTHENTICATION
"Who is calling?"

            ↓

AUTHORIZATION
"What is this caller allowed to do?"
```

For HTTP MCP, the protocol authorization model is based on OAuth 2.1 concepts. The MCP server acts as an OAuth **resource server**, the MCP client acts as an OAuth **client**, and a separate authorization server issues access tokens. For stdio, the MCP specification recommends obtaining credentials through the local environment rather than applying the HTTP OAuth flow. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

---

## 1. First principle: identity is not permission

Suppose a verified token tells us:

```
user = alice
```

That only establishes identity.

It does **not** automatically imply:

```
alice can:

read customers
delete customers
send email
modify production
access another tenant
```

A useful model is:

```
                 ACCESS DECISION

incoming request
      │
      ▼
authenticate
      │
      ▼
principal = Alice
      │
      ▼
authorize
      │
      ├── scope?
      ├── role?
      ├── tenant?
      ├── ownership?
      └── business policy?
      │
      ▼
allow / deny
```

FastMCP deliberately separates these two layers: an authentication provider validates tokens, while authorization checks decide which authenticated callers may see or invoke individual components. [FastMCP](https://gofastmcp.com/servers/auth/authentication)

---

# 2. The four OAuth actors you need to know

For MCP, think:

```
                RESOURCE OWNER
                     User
                       │
                       ▼
              AUTHORIZATION SERVER
              login / consent / tokens
                       │
                  access token
                       │
                       ▼
MCP CLIENT ──────────────────────> MCP SERVER
 OAuth client                       Resource server
```

The roles are:

| Term | Meaning |
|---|---|
| **Resource owner** | Usually the human whose data/actions are being accessed |
| **MCP client** | Requests authorization and calls the server |
| **Authorization server** | Authenticates/authorizes and issues tokens |
| **MCP server** | Protected OAuth resource server |

The MCP authorization specification explicitly assigns the OAuth client role to the MCP client and the protected resource-server role to the MCP server. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

Professional phrasing:

> **“The MCP server should validate access tokens as a resource server; it does not inherently need to be the identity provider.”**

---

# 3. First unauthenticated HTTP request

Suppose the client calls:

```http
POST /mcp
```

without credentials.

A protected MCP server responds:

```http
HTTP/1.1 401 Unauthorized

WWW-Authenticate:
  Bearer
  resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"
```

It may also tell the client which scopes are currently required:

```http
WWW-Authenticate:
  Bearer
  resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource",
  scope="inventory:read"
```

The MCP authorization flow uses this `WWW-Authenticate` challenge plus **Protected Resource Metadata** so a client can discover how that MCP server is protected. [Model Context Protocol](https://modelcontextprotocol.io/docs/tutorials/security/authorization)

---

# 4. Protected Resource Metadata

The client retrieves the referenced metadata.

Conceptually:

```json
{
  "resource": "https://mcp.example.com/mcp",
  "authorization_servers": [
    "https://auth.example.com"
  ],
  "scopes_supported": [
    "inventory:read",
    "inventory:write"
  ]
}
```

This tells the client:

```
WHAT RESOURCE?

https://mcp.example.com/mcp


WHO AUTHORIZES IT?

https://auth.example.com


WHAT PERMISSIONS EXIST?

inventory:read
inventory:write
```

MCP servers implementing authorization must publish OAuth Protected Resource Metadata, and MCP clients use that metadata to discover the corresponding authorization server. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

Professional term:

> **Protected Resource Metadata (PRM)**

---

# 5. The full discovery chain

A client does not ideally contain:

```python
AUTH_URL = "..."
TOKEN_URL = "..."
```

for every MCP server.

Instead:

```
MCP server
    │
    │ 401 + resource_metadata
    ▼
Protected Resource Metadata
    │
    │ authorization_servers
    ▼
Authorization Server Metadata
    │
    ├── authorization_endpoint
    ├── token_endpoint
    ├── registration support
    └── capabilities
```

MCP requires authorization-server discovery through OAuth Authorization Server Metadata or OpenID Connect Discovery. For client identity/registration, the current specification supports Client ID Metadata Documents, pre-registration, and legacy-compatible Dynamic Client Registration. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

This property is important:

> **MCP authorization is discoverable rather than requiring every client/server pair to be manually configured.**

---

# 6. The `resource` parameter

This is one of the most important security concepts in MCP OAuth.

When the client requests authorization, it must say:

```
"I want a token for THIS MCP server."
```

Conceptually:

```
resource=https://mcp.example.com/mcp
```

The MCP specification requires that resource indicator in both authorization and token requests. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

Why?

Because:

```
token for MCP Server A
        ≠
token for MCP Server B
        ≠
token for Google API
        ≠
token for GitHub
```

This creates **audience binding**.

---

# 7. Token audience

Imagine a token says:

```json
{
  "sub": "alice",
  "aud": "inventory-api"
}
```

Someone sends it to:

```
payroll-mcp
```

If `payroll-mcp` accepts it merely because the signature is valid, there is a serious security flaw.

A valid signature proves:

```
trusted issuer created token
```

It does **not** prove:

```
this token was intended for me
```

MCP servers must validate that presented access tokens were issued specifically for that MCP server as the intended audience. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

Professional phrase:

> **“Signature validation is necessary but insufficient; the resource server must also validate issuer, expiration, and audience.”**

FastMCP's production `JWTVerifier` supports issuer and audience validation directly. [FastMCP](https://gofastmcp.com/servers/auth/token-verification)

---

# 8. Bearer token on the actual MCP request

After OAuth completes, every protected HTTP request carries:

```http
Authorization: Bearer <access-token>
```

Tokens must not be placed in the query string. The current MCP authorization specification requires the Authorization header on every HTTP request to the protected server. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

Conceptually:

```
CLIENT

tools/call
+
Bearer token

        │
        ▼

SERVER

validate token
        │
        ▼
authorize operation
        │
        ▼
execute
```

---

# 9. A bearer token does not have to be a JWT

Two common forms exist.

### JWT

```
header.payload.signature
```

The MCP server can often validate it locally using:

```
issuer public keys / JWKS
```

### Opaque token

```
A3f92Ks8x...
```

The token contains no locally readable claims, so the resource server asks the authorization server's **introspection endpoint** whether it is active and what it represents.

FastMCP supports both models: `JWTVerifier` for signed JWT validation and `IntrospectionTokenVerifier` for OAuth token introspection. [FastMCP](https://gofastmcp.com/servers/auth/token-verification)

---

# 10. Authentication pipeline

For a JWT, the server typically cares about:

```
token
 │
 ▼
signature valid?
 │
 ▼
issuer trusted?
 │
 ▼
expired?
 │
 ▼
audience = this MCP server?
 │
 ▼
extract identity + scopes
```

FastMCP's JWT verification layer handles signature verification, expiration checking, claim extraction, issuer checks, and audience validation. [FastMCP](https://gofastmcp.com/servers/auth/authentication)

Only after this should application-level authorization begin.

---

# 11. Scopes

A scope represents delegated permission.

Examples:

```
inventory:read
inventory:write
orders:read
orders:cancel
admin
```

Suppose Alice's token contains:

```
inventory:read
```

She may perform:

```
get_inventory
```

but not:

```
set_inventory
```

Scopes should follow **least privilege**: clients should initially request only permissions necessary for the operation rather than asking for every available permission. MCP's current authorization flow explicitly recommends this approach. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

---

# 12. `401` vs `403`

Memorize this distinction.

```
401 Unauthorized

"Your authentication is missing or invalid."
```

Examples:

```
no token
expired token
invalid signature
wrong audience
```

Versus:

```
403 Forbidden

"I know who you are,
but you don't have permission."
```

Example:

```
valid token
+
inventory:read

attempt:
inventory:write
```

The current MCP spec defines `401` for missing/invalid authorization and `403` for insufficient scopes or permissions. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

---

# 13. Step-up authorization

Suppose the user initially requested:

```
inventory:read
```

Later they invoke:

```
set_inventory()
```

The server can respond:

```http
HTTP/1.1 403 Forbidden

WWW-Authenticate:
  Bearer
  error="insufficient_scope",
  scope="inventory:write",
  resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"
```

The client can then acquire a token with additional permissions and retry.

```
initial token

inventory:read

        │
        ▼

attempt write
        │
        ▼

403 insufficient_scope

        │
        ▼

user grants write

        │
        ▼

new token

inventory:read
inventory:write
```

This is **step-up authorization**, and current MCP explicitly defines the insufficient-scope challenge and subsequent reauthorization flow. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

Professional phrase:

> **“Prefer incremental scope elevation over requesting broad privileges up front.”**

---

# 14. Now FastMCP: start with a testable local auth system

For learning, do **not** start by configuring Auth0, Entra, Keycloak, or another identity provider.

First isolate the authorization logic.

FastMCP provides `StaticTokenVerifier` specifically for development/testing. It accepts predefined tokens and associated claims. It stores those tokens as plaintext and is explicitly **not for production**. [FastMCP](https://gofastmcp.com/servers/auth/token-verification)

Create `auth_server.py`:

```python
from fastmcp import FastMCP

from fastmcp.server.auth import require_scopes
from fastmcp.server.auth.providers.jwt import (
    StaticTokenVerifier,
)
from fastmcp.server.dependencies import (
    get_access_token,
)


INVENTORY = {
    "ABC-1001": 27,
}


auth = StaticTokenVerifier(
    tokens={
        "dev-reader-token": {
            "client_id": "reader-client",
            "scopes": [
                "inventory:read",
            ],
        },
        "dev-writer-token": {
            "client_id": "writer-client",
            "scopes": [
                "inventory:read",
                "inventory:write",
            ],
        },
    },
    required_scopes=[
        "inventory:read",
    ],
)


mcp = FastMCP(
    "InventoryAuthDemo",
    auth=auth,
)


@mcp.tool(
    auth=require_scopes(
        "inventory:read"
    )
)
def get_inventory(
    sku: str,
) -> dict:
    return {
        "sku": sku,
        "units": INVENTORY.get(
            sku,
            0,
        ),
    }


@mcp.tool(
    auth=require_scopes(
        "inventory:write"
    )
)
def set_inventory(
    sku: str,
    units: int,
) -> dict:
    INVENTORY[sku] = units

    return {
        "sku": sku,
        "units": units,
    }


@mcp.tool
def who_am_i() -> dict:
    token = get_access_token()

    return {
        "client_id": token.client_id,
        "scopes": token.scopes,
    }


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8000,
    )
```

FastMCP's `auth=` provider establishes transport-level authentication, while component-level `auth=require_scopes(...)` adds finer authorization rules. `get_access_token()` exposes the validated request token to Tool code when you genuinely need claims or identity inside the implementation. [FastMCP](https://gofastmcp.com/servers/authorization)

---

# 15. Test with a read-only client

Create:

```python
# reader_client.py

import asyncio

from fastmcp import Client


async def main():
    async with Client(
        "http://127.0.0.1:8000/mcp",
        auth="dev-reader-token",
    ) as client:

        tools = await client.list_tools()

        print(
            "TOOLS:",
            [
                tool.name
                for tool in tools
            ],
        )

        result = await client.call_tool(
            "get_inventory",
            {
                "sku": "ABC-1001",
            },
        )

        print(result.data)


asyncio.run(main())
```

FastMCP accepts a token string through the client's `auth=` parameter and formats it as an HTTP Bearer Authorization header. This authentication mechanism applies to HTTP transports. [FastMCP](https://gofastmcp.com/clients/auth/bearer)

The read-only principal should be able to access:

```
get_inventory
who_am_i
```

but not the write-only component.

FastMCP component authorization also filters component discovery: components whose authorization checks fail are hidden from list responses, and unauthorized direct component access behaves as not-found. [FastMCP](https://gofastmcp.com/servers/authorization)

This is useful because it prevents easy **capability enumeration**.

---

# 16. Test with a writer

```python
# writer_client.py

import asyncio

from fastmcp import Client


async def main():
    async with Client(
        "http://127.0.0.1:8000/mcp",
        auth="dev-writer-token",
    ) as client:

        tools = await client.list_tools()

        print(
            "TOOLS:",
            [
                tool.name
                for tool in tools
            ],
        )

        result = await client.call_tool(
            "set_inventory",
            {
                "sku": "ABC-1001",
                "units": 40,
            },
        )

        print(result.data)


asyncio.run(main())
```

Now the token contains:

```
inventory:read
inventory:write
```

so both scope checks succeed. FastMCP's `require_scopes()` requires all scopes supplied to that check, and multiple authorization checks compose with AND semantics. [FastMCP](https://gofastmcp.com/servers/authorization)

---

# 17. FastMCP's two security layers

This is the main abstraction map:

```
                    FastMCP

HTTP request
    │
    ▼
AuthProvider
    │
    │ token valid?
    ▼
AUTHENTICATION
    │
    ▼
AccessToken
    │
    ▼
Auth checks
    │
    │ scopes / roles / claims / policy
    ▼
AUTHORIZATION
    │
    ▼
Tool / Resource / Prompt
```

An `AuthProvider` protects the endpoint itself. Once configured, requests without a valid token are rejected before component-level auth checks. Authorization checks then discriminate among authenticated callers using scopes and claims. [FastMCP](https://gofastmcp.com/servers/authorization)

---

# 18. Component authorization

You can protect each primitive separately:

```python
@mcp.tool(
    auth=require_scopes("write")
)
def update_record():
    ...
```

```python
@mcp.resource(
    "customer://{id}",
    auth=require_scopes("customers:read"),
)
def customer(id: str):
    ...
```

```python
@mcp.prompt(
    auth=require_scopes("admin")
)
def incident_response():
    ...
```

FastMCP applies component authorization to Tools, Resources, and Prompts, affecting both discovery and direct access. [FastMCP](https://gofastmcp.com/servers/authorization)

This gives us a new architectural principle:

> **Authorization belongs on the capability boundary, not merely inside business logic.**

---

# 19. Server-wide authorization

Suppose **everything** requires:

```
tenant:active
```

Repeating:

```python
auth=require_scopes("tenant:active")
```

on 100 Tools is poor design.

FastMCP exposes `AuthMiddleware` for cross-cutting server-wide authorization:

```python
from fastmcp import FastMCP
from fastmcp.server.auth import require_scopes
from fastmcp.server.middleware import (
    AuthMiddleware,
)


mcp = FastMCP(
    "ProtectedServer",
    middleware=[
        AuthMiddleware(
            auth=require_scopes(
                "api:access"
            )
        )
    ],
)
```

Server-wide middleware and component-level rules combine, with all required checks needing to pass. [FastMCP](https://gofastmcp.com/servers/authorization)

Think:

```
GLOBAL POLICY

must have api:access

        +

COMPONENT POLICY

must have inventory:write
```

Final requirement:

```
api:access
AND
inventory:write
```

---

# 20. Authorization is not limited to scopes

Scopes answer many cases, but not all.

Imagine:

```
user may update customers
```

but only:

```
customers in their own tenant
```

The token might contain:

```json
{
  "tenant_id": "acme"
}
```

FastMCP auth checks receive an `AuthContext`, so you can implement claim-based policies:

```python
from fastmcp.server.auth import (
    AuthContext,
)


def require_acme(
    ctx: AuthContext,
) -> bool:

    if ctx.token is None:
        return False

    return (
        ctx.token.claims.get(
            "tenant_id"
        )
        == "acme"
    )
```

Then:

```python
@mcp.tool(
    auth=require_acme
)
def tenant_report():
    ...
```

FastMCP permits synchronous or asynchronous callable authorization checks based on token claims, component metadata, or external state. [FastMCP](https://gofastmcp.com/servers/authorization)

---

# 21. Authentication vs business authorization

Be careful with this code:

```python
@mcp.tool(
    auth=require_scopes(
        "orders:write"
    )
)
def cancel_order(
    order_id: str,
):
    ...
```

The scope says:

```
caller may perform order-writing operations
```

It does **not** necessarily mean:

```
caller may cancel THIS order
```

You may additionally need:

```
order belongs to caller's tenant
order is cancellable
caller owns account
order isn't legally locked
```

So:

```
OAuth scope
      │
      ▼
coarse-grained authorization

        +

domain rules
      │
      ▼
fine-grained authorization
```

Professional terminology:

- **coarse-grained authorization**
- **fine-grained authorization**
- **resource-level authorization**
- **object-level authorization**

---

# 22. Never trust object IDs supplied by the caller

Suppose Alice is authorized for:

```
customer://123
```

She changes:

```
customer_id=123
```

to:

```
customer_id=456
```

If the Tool simply queries:

```python
db.get_customer(customer_id)
```

you may have an **IDOR/BOLA-style authorization bug**.

You should query in caller context:

```python
db.get_customer(
    customer_id=customer_id,
    tenant_id=authenticated_tenant,
)
```

The key principle:

```
IDENTIFIER POSSESSION
      ≠
AUTHORIZATION
```

MCP's current security guidance similarly warns that possession of a state handle must never be treated as authentication and recommends binding server-managed state to the authenticated principal. [Model Context Protocol](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)

---

# 23. Token passthrough: a critical anti-pattern

Suppose your MCP server calls GitHub.

Bad architecture:

```
MCP Client
   │
   │ sends GitHub token
   ▼
MCP Server
   │
   │ forwards same token
   ▼
GitHub
```

This is **token passthrough**.

The MCP security guidance explicitly prohibits accepting a token intended for another service and forwarding it downstream. Tokens presented to the MCP server must be intended for that MCP server. [Model Context Protocol](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)

Why?

Because you destroy the audience boundary:

```
token audience:
github

but accepted by:
my-mcp-server
```

That can produce confused-deputy problems and undermine rate limits, auditing, and service trust boundaries. [Model Context Protocol](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)

---

# 24. Correct downstream-token architecture

Better:

```
                    TOKEN A
              audience = MCP
MCP Client ────────────────────> MCP Server
                                    │
                                    │ obtains/holds
                                    │ appropriate
                                    │ downstream token
                                    ▼
                                TOKEN B
                              audience = API
                                    │
                                    ▼
                              Downstream API
```

The two trust relationships are separate.

```
Client → MCP
and
MCP → downstream API
```

Professional phrase:

> **“Do not collapse resource-server trust boundaries through bearer-token passthrough.”**

---

# 25. Production FastMCP: JWT verification

Your development server used:

```
StaticTokenVerifier
```

Do not deploy that.

A common production pattern is:

```python
import os

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import (
    JWTVerifier,
)


auth = JWTVerifier(
    jwks_uri=os.environ[
        "JWT_JWKS_URI"
    ],
    issuer=os.environ[
        "JWT_ISSUER"
    ],
    audience=os.environ[
        "JWT_AUDIENCE"
    ],
)


mcp = FastMCP(
    "ProductionServer",
    auth=auth,
)
```

With a JWKS endpoint, FastMCP can fetch the issuer's public keys and validate incoming JWT signatures while enforcing configured issuer and audience requirements. FastMCP recommends putting production auth configuration in environment variables rather than source code. [FastMCP](https://gofastmcp.com/servers/auth/token-verification)

---

# 26. But `JWTVerifier` alone is not the whole discoverable OAuth experience

This distinction matters.

A simple token verifier means:

```
"Give me a valid token and I will validate it."
```

It does not necessarily mean:

```
"I expose the entire MCP OAuth discovery
and interactive authorization lifecycle."
```

FastMCP describes `TokenVerifier` as primarily pure resource-server validation and notes that it operates somewhat outside the full formal MCP authentication flow. For interoperable client-driven OAuth discovery, FastMCP provides OAuth-aware providers and external identity-provider integrations. [FastMCP](https://gofastmcp.com/servers/auth/authentication)

Professional distinction:

```
TOKEN VALIDATION
              ≠
FULL OAUTH AUTHORIZATION FLOW
```

---

# 27. FastMCP OAuth client

For a proper remote OAuth-capable MCP server, a FastMCP client can use:

```python
from fastmcp import Client
from fastmcp.client.auth import OAuth


async with Client(
    "https://mcp.example.com/mcp",
    auth=OAuth(
        scopes=[
            "inventory:read",
        ]
    ),
) as client:

    tools = await client.list_tools()
```

FastMCP's OAuth client performs server/auth-server discovery, client registration where appropriate, browser authorization, authorization-code exchange using PKCE, token caching, Bearer attachment, and token refresh handling. [FastMCP](https://gofastmcp.com/clients/auth/oauth)

The important abstraction map is:

```
OAuth(...)
   │
   ▼
discovery
   │
   ▼
registration
   │
   ▼
user login / consent
   │
   ▼
authorization code
   │
   ▼
token exchange
   │
   ▼
access token
   │
   ▼
Authorization: Bearer ...
```

---

# 28. Token storage becomes a security asset

After login, clients may store:

```
access token
refresh token
```

If that store is compromised:

```
attacker may gain access
to several MCP servers
```

FastMCP therefore recommends encrypted persistent token storage for production rather than plaintext persistence. [FastMCP](https://gofastmcp.com/clients/auth/oauth)

This introduces a useful term:

> **credential-at-rest protection**

Authentication doesn't end after login. Token storage is part of the system's security boundary.

---

# 29. stdio is different

Do not blindly add:

```
OAuth
```

to every stdio server.

The current MCP authorization spec says HTTP implementations should use the authorization specification, whereas stdio implementations should generally obtain credentials from the environment instead. [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

Typical local topology:

```
MCP Host
   │
   │ starts process with env
   ▼
stdio server
   │
   ├── DATABASE_TOKEN
   ├── GITHUB_TOKEN
   └── other local credentials
```

That means:

```
remote HTTP identity
and
local process credentialing
```

are different security designs.

---

# 30. Auth annotations are not authorization

Recall Tool annotations:

```python
readOnlyHint=True
destructiveHint=False
```

These describe behavior.

They do **not** grant or deny access.

```
ANNOTATION

"This Tool is read-only."


AUTHORIZATION

"Caller Alice may execute this Tool."
```

Never implement security policy based on model-facing metadata.

The actual boundary must be:

```
validated identity
+
authorization policy
+
business rules
```

---

# 31. The complete request pipeline

A production Tool call should conceptually travel through:

```
HTTP request
    │
    ▼
TLS
    │
    ▼
Bearer token extraction
    │
    ▼
token validation
    │
    ├── signature
    ├── issuer
    ├── expiration
    └── audience
    │
    ▼
authenticated principal
    │
    ▼
server-wide auth policy
    │
    ▼
component auth policy
    │
    ▼
domain/object-level policy
    │
    ▼
input validation
    │
    ▼
Tool implementation
    │
    ▼
downstream authorization
```

That layering is more important than any particular library API.

---

# 32. Common weak architecture

Avoid:

```python
@mcp.tool
def delete_customer(
    customer_id: str,
):
    if os.environ[
        "API_TOKEN"
    ]:
        delete(customer_id)
```

Why is this weak?

Because:

```
server has credentials
        ≠
caller has permission
```

The server's ability to perform an action downstream does not imply the MCP caller should be allowed to trigger it.

This is the classic **confused deputy** category of problem: a privileged service can be tricked into exercising its authority on behalf of someone who shouldn't have it. MCP's security guidance explicitly calls out confused-deputy risks in proxy-style MCP architectures. [Model Context Protocol](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)

---

# 33. Capability visibility is also security-sensitive

Suppose only admins have:

```
delete_database
```

A weaker system might return it in `tools/list` to everyone but reject invocation later.

Better:

```
non-admin

tools/list
──────────
get_user
search_users


admin

tools/list
──────────
get_user
search_users
delete_database
```

FastMCP component authorization filters unauthorized components from discovery as well as blocking direct access. [FastMCP](https://gofastmcp.com/servers/authorization)

Professional term:

> **Authorization-aware discovery**

This reduces unnecessary information disclosure.

---

# 34. Auth design checklist

For each MCP capability, ask:

```
1. Who is the principal?

2. How was identity verified?

3. Is this token intended for this MCP server?

4. What OAuth scopes are present?

5. What roles/claims matter?

6. Does the principal belong to the correct tenant?

7. Are they authorized for this specific object?

8. Is the operation allowed in the object's current state?

9. Are downstream credentials separate from inbound MCP credentials?

10. What should be logged for audit?
```

If your authorization logic stops at:

```
token valid?
```

you've only solved authentication.

---

# 35. Abstraction map

| Security concept | Protocol / OAuth | FastMCP |
|---|---|---|
| Protected resource | MCP server | `FastMCP(..., auth=...)` |
| Bearer token | `Authorization` header | `Client(..., auth=...)` |
| Token validation | OAuth resource server | `JWTVerifier`, introspection verifier |
| PRM discovery | OAuth Protected Resource Metadata | OAuth-capable providers |
| Client OAuth | OAuth client | `OAuth()` |
| Scope | OAuth permission | `require_scopes()` |
| Custom policy | application authorization | `AuthContext` callable |
| Global policy | server authorization | `AuthMiddleware` |
| Component policy | per Tool/Resource/Prompt | decorator `auth=` |
| Current principal/token | token claims | `get_access_token()` |
| Step-up permission | `403 insufficient_scope` | scope-aware authorization path |

FastMCP explicitly separates token verification, component-level checks, global middleware policies, and request-token access. [FastMCP](https://gofastmcp.com/servers/auth/authentication)

---

# 36. Professional vocabulary

Know these precisely:

| Term | Meaning |
|---|---|
| **Authentication** | Establishing caller identity |
| **Authorization** | Determining permitted actions |
| **Principal** | Authenticated identity |
| **Resource owner** | User/entity granting access |
| **Resource server** | Protected API accepting tokens |
| **Authorization server** | System issuing access tokens |
| **Bearer token** | Credential usable by whoever possesses it |
| **JWT** | Signed self-contained token format |
| **Opaque token** | Token whose metadata requires server-side lookup/introspection |
| **Scope** | Delegated permission |
| **Claim** | Attribute carried by validated token data |
| **Issuer (`iss`)** | Authority that issued a token |
| **Audience (`aud`)** | Intended recipient/resource |
| **Subject (`sub`)** | Principal represented by token |
| **JWKS** | Published public keys used for JWT verification |
| **Token introspection** | Asking authorization server about opaque token state |
| **Protected Resource Metadata** | Metadata describing how a resource is authorized |
| **Least privilege** | Grant only required permissions |
| **Step-up authorization** | Acquire additional permission when needed |
| **Token passthrough** | Unsafe forwarding of inbound tokens to another resource |
| **Confused deputy** | Privileged service tricked into misusing its authority |
| **Object-level authorization** | Permission check on a specific record/resource |
| **Authorization-aware discovery** | Hiding components the caller cannot access |

A strong explanation would sound like:

> **“For remote HTTP MCP, the server acts as an OAuth resource server. Clients discover authorization through Protected Resource Metadata, obtain an access token targeted to the MCP server via the OAuth resource indicator, and send it as a Bearer token on every request. The server must validate token audience as well as token validity. FastMCP separates that authentication layer through `AuthProvider`/verifiers from authorization checks such as `require_scopes()` and custom `AuthContext` policies.”** [Model Context Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

---

# Hands-on assignment

Use the static-token example first.

1. Start the HTTP server.
2. Call it **without a token**.
3. Call it with `dev-reader-token`.
4. Inspect `list_tools()` and note that the write Tool is hidden.
5. Try directly invoking `set_inventory` as the reader.
6. Call it with `dev-writer-token`.
7. Call `who_am_i()` and inspect the validated client/scopes.
8. Add an `admin` Tool requiring `admin`.
9. Add a custom claim such as `tenant_id`.
10. Write an `AuthContext` check requiring the correct tenant.
11. Add object-level authorization so callers cannot access another tenant's records.
12. Replace `StaticTokenVerifier` with a generated test JWT + `JWTVerifier`.
13. Deliberately change the JWT audience and verify rejection.
14. Deliberately expire the JWT and verify rejection.
15. Only after those concepts are clear, connect a real OAuth provider.

The test for understanding is being able to explain why:

```
valid JWT
    ≠
correct audience
    ≠
authenticated user
    ≠
required scope
    ≠
authorization for this record
```

Each is a separate security assertion.

## Next lesson — Context, Dependency Injection, Lifespan + Request State

Next we should move from protocol features into **FastMCP server architecture**:

```
Context
dependency injection
request-scoped state
lifespan state
shared service objects
database pools
HTTP clients
current access token
concurrency
cleanup
testability
```

This is where we'll build a realistic server structure instead of putting all code directly inside decorators.