# FastMCP Transport Security: `allowed_hosts`, `allowed_origins`, CORS, and Browser-Only Access

> Verified against the current official Model Context Protocol Python SDK source and documentation on 2026-11-15.

## 1. What `TransportSecuritySettings` does

`TransportSecuritySettings` controls HTTP request checks used by the MCP Python SDK to reduce DNS-rebinding risk.

The relevant settings are:

```python
TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[...],
    allowed_origins=[...],
)
```

When DNS-rebinding protection is enabled, an incoming request is checked roughly like this:

```text
HTTP request
    |
    v
POST? ---- yes ----> Content-Type must be application/json
    |
    v
Check Host
    |
    +---- invalid --> 421 Invalid Host header
    |
    v
Check Origin
    |
    +---- invalid --> 403 Invalid Origin header
    |
    v
MCP application
```

`Host` is checked before `Origin`.

---

## 2. `allowed_hosts`

`allowed_hosts` validates the HTTP `Host` header.

Example request:

```http
Host: mcp.example.com
```

Example configuration:

```python
allowed_hosts=[
    "mcp.example.com",
    "mcp.example.com:*",
]
```

Meaning:

- `"mcp.example.com"` matches the exact bare host.
- `"mcp.example.com:*"` matches that host with an explicit port, such as `mcp.example.com:8000`.
- `:*` is a wildcard for the **port only**.
- It is not a wildcard for arbitrary domains or subdomains.

Examples:

| Host header | Allowed by configuration above? |
|---|---:|
| `mcp.example.com` | Yes |
| `mcp.example.com:8000` | Yes |
| `mcp.example.com:443` | Yes |
| `api.mcp.example.com` | No |
| `evil.example.com` | No |

A missing `Host` header also fails validation.

### Empty host list

```python
allowed_hosts=[]
```

With DNS-rebinding protection enabled, this rejects every normal HTTP request at the Host check because no `Host` value can match the empty allowlist.

Result:

```text
421 Misdirected Request
Invalid Host header
```

---

## 3. `allowed_origins`

`allowed_origins` validates the HTTP `Origin` header.

Browsers commonly send an `Origin` header for cross-origin requests.

Example:

```http
Origin: https://app.example.com
```

Example configuration:

```python
allowed_origins=[
    "https://app.example.com",
]
```

Meaning:

```text
Origin: https://app.example.com
    -> allowed

Origin: https://evil.example.com
    -> rejected with 403
```

Origins include the scheme (`http://` or `https://`).

### Port wildcard

The Python SDK also supports a wildcard port pattern:

```python
allowed_origins=[
    "http://localhost:*",
]
```

This permits origins such as:

```text
http://localhost:3000
http://localhost:5173
```

---

## 4. Critical behavior: a missing `Origin` is allowed

The Python SDK explicitly treats a missing `Origin` as valid.

Conceptually:

```python
if not origin:
    return True
```

Therefore:

```python
allowed_origins=[]
```

does **not** mean:

```text
Reject every request.
```

It means:

```text
No Origin header          -> allowed by Origin validation
Any Origin header present -> rejected
```

Example:

| Request | Origin result |
|---|---:|
| No `Origin` header | Allowed |
| `Origin: https://app.example.com` | Rejected |
| `Origin: https://evil.example.com` | Rejected |

This is why `allowed_origins=[]` is often suitable for server-to-server clients that do not send `Origin`.

---

## 5. What happens when both lists are empty

Configuration:

```python
enable_dns_rebinding_protection=True
allowed_hosts=[]
allowed_origins=[]
```

No normal HTTP request reaches the MCP application.

Reason:

```text
Request
   |
   v
Host check against []
   |
   +---- no possible match
   |
   v
421 Invalid Host header
```

The request fails at `allowed_hosts` before `allowed_origins` matters.

So the important distinction is:

```text
allowed_hosts=[]
    -> blocks requests because Host is required and nothing matches

allowed_origins=[]
    -> blocks requests that contain Origin
       but still accepts requests without Origin
```

---

## 6. `Host` and `Origin` solve different problems

### `Host`

Answers:

> Which server hostname was this HTTP request addressed to?

Example:

```http
Host: mcp.example.com
```

Used here primarily as part of DNS-rebinding protection.

### `Origin`

Answers:

> Which browser origin initiated this request?

Example:

```http
Origin: https://app.example.com
```

The origin is approximately:

```text
scheme + hostname + port
```

Examples:

```text
https://app.example.com
http://localhost:3000
```

`Host` and `Origin` are not interchangeable.

A browser request can contain both:

```http
Host: mcp.example.com
Origin: https://app.example.com
```

Meaning:

```text
Browser page: https://app.example.com
                    |
                    | sends request
                    v
MCP server:  https://mcp.example.com
```

---

## 7. Request example

Suppose the browser UI runs at:

```text
https://app.example.com
```

and the MCP server runs at:

```text
https://mcp.example.com
```

The request could contain:

```http
POST /mcp HTTP/1.1
Host: mcp.example.com
Origin: https://app.example.com
Content-Type: application/json
```

A matching security configuration would allow:

```python
TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "mcp.example.com",
        "mcp.example.com:*",
    ],
    allowed_origins=[
        "https://app.example.com",
    ],
)
```

The request must satisfy both checks:

```text
Host == allowed Host?
        |
       yes
        |
        v
Origin absent OR allowed Origin?
        |
       yes
        |
        v
Request continues
```

---

## 8. Browser-to-server only: the built-in settings are insufficient

Suppose the requirement is:

```text
Allow browser -> MCP server
Reject server -> MCP server
```

It is tempting to configure:

```python
allowed_hosts=["mcp.example.com"]
allowed_origins=["https://app.example.com"]
```

This does **not** enforce browser-only access.

Why:

```text
Browser request
Origin: https://app.example.com
    -> allowed

Normal server request
No Origin header
    -> also allowed
```

The SDK intentionally accepts a missing `Origin`.

---

## 9. Requiring an `Origin` header

If the operational requirement is:

> Reject ordinary clients that do not send `Origin`.

Add middleware before the MCP application that requires an approved `Origin`.

Conceptually:

```text
HTTP request
    |
    v
Custom Origin-required middleware
    |
    +---- missing Origin --> 403
    |
    +---- wrong Origin ---> 403
    |
    v
FastMCP transport security
    |
    v
MCP application
```

Pseudo-code:

```python
origin = request.headers.get("origin")

if origin not in ALLOWED_BROWSER_ORIGINS:
    reject(403)
```

This blocks ordinary server clients that omit `Origin`.

---

## 10. Important security limitation: `Origin` does not prove the caller is a browser

A non-browser client can manually send:

```http
Origin: https://app.example.com
```

Therefore this rule:

```text
Origin == https://app.example.com
```

proves only that the request contains that header value.

It does **not** cryptographically prove:

```text
"This request came from my browser application."
```

A malicious server-side client can imitate browser headers.

Therefore:

```text
Require Origin
    -> useful request filtering
    -> useful CSRF / browser-origin boundary
    -> NOT caller authentication
```

For real access control, use authentication and authorization.

---

## 11. CORS is separate from `allowed_origins`

This is a common source of confusion.

`allowed_origins` in `TransportSecuritySettings` performs a server-side security check.

It does **not** by itself configure browser CORS behavior.

Think of the two layers separately:

```text
Browser
   |
   | CORS preflight / browser policy
   v
CORS middleware
   |
   | request reaches application
   v
TransportSecuritySettings
   |
   | Host + Origin validation
   v
MCP server
```

For browser clients you commonly need both:

```text
1. CORS middleware
2. TransportSecuritySettings.allowed_origins
```

CORS answers:

> Will the browser allow JavaScript to make/read this cross-origin request?

Transport security answers:

> Will the MCP server accept this Host/Origin combination?

They are related, but they are not the same mechanism.

---

## 12. Recommended browser setup

Example architecture:

```text
+----------------------------+
| Browser                    |
| https://app.example.com    |
+-------------+--------------+
              |
              | HTTPS
              | Origin: https://app.example.com
              v
+----------------------------+
| Reverse proxy / gateway    |
| mcp.example.com            |
+-------------+--------------+
              |
              v
+----------------------------+
| CORS middleware            |
| allow app.example.com      |
+-------------+--------------+
              |
              v
+----------------------------+
| Require Origin middleware  |
| optional policy layer      |
+-------------+--------------+
              |
              v
+----------------------------+
| FastMCP transport security |
| Host allowlist             |
| Origin allowlist           |
+-------------+--------------+
              |
              v
+----------------------------+
| Authentication             |
| Authorization              |
+-------------+--------------+
              |
              v
+----------------------------+
| MCP tools/resources        |
+----------------------------+
```

The strongest boundary should be authentication/authorization, not `Origin` alone.

---

## 13. Reverse proxies and `allowed_hosts`

If FastMCP runs behind nginx or another reverse proxy, understand which `Host` value reaches FastMCP.

Example external request:

```text
Browser -> https://mcp.example.com
```

nginx may forward:

```http
Host: mcp.example.com
```

or it may replace it with an internal host, depending on proxy configuration.

`allowed_hosts` must match the `Host` header FastMCP actually receives.

Example Docker topology:

```text
Browser
   |
   v
mcp.example.com
   |
   v
nginx
   |
   v
fastmcp:8000
```

Possible FastMCP-visible Host values include:

```text
mcp.example.com
nginx
fastmcp:8000
```

The exact value depends on proxy configuration. Do not guess it; inspect the forwarded request or nginx configuration.

---

## 14. Example with nginx / localhost values

Given:

```python
allowed_hosts=[
    "nginx",
    "localhost:*",
    "127.0.0.1:*",
]
```

These match:

```text
Host: nginx
Host: localhost:3000
Host: localhost:8000
Host: 127.0.0.1:8000
```

But these do not necessarily match:

```text
Host: nginx:8000
Host: mcp.example.com
Host: fastmcp:8000
```

To accept nginx with any explicit port:

```python
"nginx:*"
```

If both bare host and host-with-port are possible, list both:

```python
allowed_hosts=[
    "nginx",
    "nginx:*",
]
```

---

## 15. DNS rebinding: why these checks exist

A simplified DNS-rebinding attack looks like this:

```text
Victim browser
    |
    | visits attacker.example
    v
Attacker-controlled page
    |
    | attacker changes DNS resolution
    v
127.0.0.1 / internal MCP server
```

Without appropriate Host/Origin validation, a malicious web page could try to reach a local or internal service through the victim's browser.

The transport-security checks narrow which hostnames and browser origins are accepted.

They are defense-in-depth controls, not a substitute for authentication.

---

## 16. `enable_dns_rebinding_protection=False`

If protection is disabled:

```python
TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)
```

Host and Origin allowlist validation is skipped.

For POST requests, the SDK's transport middleware still performs the relevant content-type validation independently of the DNS-rebinding setting.

Do not disable the protection merely to fix a `421` unless another trusted layer already owns the Host validation boundary and the deployment design intentionally relies on that.

The official Python SDK deployment documentation specifically notes that disabling this check can be appropriate behind a reverse proxy that already controls the `Host` header.

---

## 17. Status codes worth recognizing

| Failure | Result |
|---|---|
| Invalid/missing `Host` | `421 Misdirected Request` / `Invalid Host header` |
| Present but invalid `Origin` | `403 Forbidden` / `Invalid Origin header` |
| Invalid POST `Content-Type` | `400` / `Invalid Content-Type header` |

A `421 Invalid Host header` occurs before MCP protocol handling. It is an HTTP transport rejection, not an MCP JSON-RPC error.

---

## 18. Decision table

| Requirement | `allowed_hosts` | `allowed_origins` | Extra layer needed? |
|---|---|---|---|
| Allow specific server hostname | Populate | Any appropriate value | No |
| Reject all requests | `[]` with protection enabled | Irrelevant | No |
| Allow server-to-server only, no browser Origin | Populate | `[]` | Usually no |
| Allow only approved browser origins but also tolerate clients without Origin | Populate | Populate | No |
| Reject clients with missing Origin | Populate | Populate | **Yes: require Origin middleware** |
| Prove caller is really an authorized browser/user | Populate | Populate | **Yes: authentication + authorization** |
| Make cross-origin browser JavaScript work | Populate | Populate | **Yes: CORS configuration** |

---

## 19. Practical configuration patterns

### Pattern A: server-to-server clients

```python
TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "mcp.example.com",
        "mcp.example.com:*",
    ],
    allowed_origins=[],
)
```

Effect:

```text
No Origin header -> allowed after Host check
Origin present   -> rejected
```

This is useful when legitimate clients are non-browser clients that do not send `Origin`.

### Pattern B: browser + server clients

```python
TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "mcp.example.com",
        "mcp.example.com:*",
    ],
    allowed_origins=[
        "https://app.example.com",
    ],
)
```

Effect:

```text
Approved browser Origin -> allowed
Missing Origin          -> allowed
Other Origin            -> rejected
```

### Pattern C: operationally browser-only

Use:

```text
CORS
+
Require approved Origin middleware
+
FastMCP Host/Origin allowlists
+
Authentication/authorization
```

Effect:

```text
Browser with approved Origin + valid credentials -> allowed
Ordinary server client without Origin            -> rejected
Wrong Origin                                      -> rejected
Spoofed Origin without valid credentials          -> rejected
```

This is the recommended structure when the actual requirement is access control rather than only header filtering.

---

## 20. One realistic failure and recovery path

### Failure

The application is deployed behind nginx and every MCP client receives:

```text
421 Misdirected Request
Invalid Host header
```

Possible cause:

```text
FastMCP receives:
Host: mcp.example.com

but configuration allows only:
allowed_hosts=["nginx"]
```

### Recovery

First determine the actual `Host` header FastMCP receives.

Then either:

1. Preserve the intended public Host in the proxy and allowlist it, or
2. Intentionally forward a controlled internal Host and allowlist that value.

Do not solve it by adding broad values without first understanding which layer owns Host validation.

---

## 21. Security rule of thumb

Treat these mechanisms as different layers:

```text
Host validation
    -> protects which server name is accepted

Origin validation
    -> constrains browser-origin requests

CORS
    -> controls browser cross-origin behavior

Require-Origin middleware
    -> rejects requests that omit Origin

Authentication
    -> establishes caller identity

Authorization
    -> decides what that identity may do
```

Do not use `Host`, `Origin`, or CORS as a replacement for authentication or authorization.

---

## 22. Version note

The exact place where `transport_security` is supplied can vary across MCP Python SDK versions.

Current SDK documentation shows transport settings being passed when building/running the HTTP transport, such as `streamable_http_app()` / `run()`. If your installed version accepts it in a different location, keep the semantics in this guide but verify the API shape against the version you actually have installed.

Useful local check:

```bash
python -c "import mcp; print(getattr(mcp, '__version__', 'version not exposed'))"
```

Also inspect your installed callable signatures rather than copying examples from a different SDK version.

---

## 23. Official references

1. MCP Python SDK — transport security implementation  
   https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/server/transport_security.py

2. MCP Python SDK — deployment guidance  
   https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/deploy.md

3. MCP Python SDK — troubleshooting  
   https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/troubleshooting.md

4. MCP Python SDK — current server implementation/default transport-security behavior  
   https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/server/lowlevel/server.py

5. MCP security/authorization documentation  
   https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/docs/2026-07-28/tutorials/security/authorization.mdx

---

## Short summary

```text
allowed_hosts
    checks Host
    empty [] => nothing can match => requests fail at Host validation

allowed_origins
    checks Origin only when Origin exists
    empty [] => every present Origin fails
    missing Origin => still accepted

Browser-only requirement
    cannot be guaranteed by allowed_origins alone
    require Origin if desired
    use authentication + authorization for real security

CORS
    separate from FastMCP Origin validation
    browser deployments commonly need both
```
