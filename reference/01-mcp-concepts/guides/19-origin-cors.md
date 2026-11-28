# Host validation, Origin, and CORS

**Outcome:** Explain what browser-related transport checks protect and why they are not authentication.

**Prerequisites:** [11: Streamable HTTP](11-streamable-http.md).

## A local service is still a reachable capability

A browser visiting an unrelated website may attempt to contact services on
the user's machine. Local binding limits network exposure, but it does not
make every request arriving from that machine trustworthy.

**Host:**

> The authority the HTTP request targets, typically hostname and port.

**Origin:**

> The origin of browser-initiated activity, expressed using scheme, host,
> and port. Non-browser clients may omit this header.

**CORS:**

> Browser-enforced rules controlling cross-origin access to responses.
> CORS does not authenticate arbitrary clients.

## Compare the checks

| Check | Main question |
|---|---|
| Host allowlist | Is this an expected destination authority? |
| Origin validation | Is this presented origin allowed? |
| CORS policy | May browser code read this cross-origin response? |
| Authentication | Who is making this request? |

A command-line client can choose headers. It is not constrained by browser
CORS enforcement. An Origin allowlist therefore cannot establish that only a
specific website's genuine users can call the service.

## A concrete request path

```
Browser --> proxy --> MCP endpoint --> authentication --> tool policy
            |
        preserves intended
        external request information
```

If the proxy rewrites Host or forwards an internal authority, an application's
allowlist must match the intended trust design. Blindly accepting every Host
to fix a deployment error can remove protection against DNS rebinding.

DNS rebinding exploits changes in how a hostname resolves to reach a local
service under an attacker-controlled name. Validate destination and origin
according to the current transport and framework behavior.

## Missing Origin

A missing Origin header can be normal for a server-to-server MCP client.
Requiring it may intentionally restrict client compatibility, but even then
a non-browser program can forge it. Use actual credentials and access rules
for identity.

The archive's transport-security note is useful because it explicitly
distinguishes absent Origin from an invalid presented Origin. Recheck exact
status codes and setting names for the pinned SDK before implementing them.

## Failure experiment

Compare an allowed Origin, a denied Origin, and no Origin using a test client.
Then repeat with valid and invalid credentials. The outcomes should show that
transport guards and identity checks are independent.

For the small lab, keep the listener on loopback. For a remote service, add
HTTPS, proper authentication, request limits, and per-operation policy.

## Keep the checks independent in code

This simplified function shows the order of questions. It is not a complete
HTTP security implementation:

```python
def authorize_request(host: str, origin: str | None, bearer: str | None) -> str:
    if host not in {"127.0.0.1:8765", "mcp.example.com"}:
        raise ValueError("Unexpected Host")
    if origin is not None and origin != "https://app.example.com":
        raise ValueError("Origin not allowed")
    if bearer is None:
        raise PermissionError("Authentication required")
    return verify_bearer_token(bearer)
```

The first two guards inspect transport context. `verify_bearer_token` answers
an identity question. The later tool policy must still decide what that
identity may do. Use the pinned framework's validated middleware and proxy
configuration in production.

**Professional articulation:**

> “Host and Origin checks protect the transport boundary. CORS controls
> browser behavior; none of them replaces authentication or authorization.”

## Sources and next step

- [Archived FastMCP transport-security notes](../../02-fast-mcp/2026-07-28/17-fastmcp_transport_security.md)
- [Archived Streamable HTTP and Uvicorn example](../fastMcp-fastApi-uvicorn-ngnix-docker/5_StreamableHttp_Uvicorn.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) — checked 2026-11-15.

Next: [OAuth discovery and delegated access](20-oauth-discovery.md).

