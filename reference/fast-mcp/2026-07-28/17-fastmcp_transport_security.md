# Lesson 17 — FastMCP transport security

## Outcome

After this lesson, you can distinguish Host validation, Origin validation,
CORS, authentication, and proxy trust.

## The controls answer different questions

```
Host validation    -> which server name was addressed?
Origin validation  -> which browser origin initiated the request?
CORS                -> may browser JavaScript read/send this cross-origin call?
Authentication      -> who is the caller?
Authorization       -> what may that caller do?
```

None of these replaces the others.

## Required MCP HTTP behavior

For Streamable HTTP, servers must validate the `Origin` header when it is
present and return HTTP 403 for an invalid origin. Local servers should bind to
`127.0.0.1`, and remote endpoints should authenticate callers.

An absent `Origin` is common for server-to-server clients. Therefore, Origin
validation alone cannot prove that a request came from an approved browser.

## FastMCP transport settings

FastMCP and the MCP Python stack expose transport security settings for DNS
rebinding protection, including allowed hosts and origins. Treat allowlists as
exact deployment configuration:

- include the actual public host and any intended port form;
- include only approved browser origins, with scheme and port;
- do not use broad wildcards to make an error disappear;
- verify the API shape against the pinned FastMCP version before deployment.

`allowed_hosts` validates the HTTP `Host` header. An empty host allowlist with
protection enabled rejects normal requests because every request has a Host.

`allowed_origins` validates a present `Origin` header. An empty origin allowlist
rejects requests that carry an Origin but can still allow non-browser requests
without one.

Use explicit values that match the deployment:

```python
mcp.run(
    transport="http",
    host="127.0.0.1",
    port=8781,
    host_origin_protection=True,
    allowed_hosts=["127.0.0.1:8781"],
    allowed_origins=["https://trusted.example"],
)
```

This is transport filtering, not authentication. A non-browser client can omit
`Origin`, so remote endpoints still need authenticated identity and
authorization.

## CORS is separate

Origin allowlisting in transport security rejects untrusted origins. CORS
middleware controls browser preflight and response headers. Configure both when
browser JavaScript directly calls the server.

Never use `Access-Control-Allow-Origin: *` with credentials. Enumerate trusted
origins and minimize allowed methods and headers.

## Reverse proxy trust

```
browser/client -> reverse proxy -> FastMCP application
```

Decide which layer terminates TLS, validates Host and Origin, authenticates the
caller, and rewrites forwarding headers. Trust forwarded headers only from
known proxies. Ensure the application sees the intended public host and scheme;
otherwise valid requests may be rejected or attacker-controlled values may be
trusted.

Modern routing headers such as `Mcp-Method`, `Mcp-Name`, and `Mcp-Param-*` are
useful for gateways, but they are untrusted request input. Validate their
consistency with the body and never treat them as identity.

## Browser-only access is an operational policy

Requiring an Origin header can filter many non-browser clients, but Origin is a
caller-controlled HTTP header outside a trusted browser environment. “Browser
only” requires layered controls such as authentication, short-lived tokens,
network policy, and gateway enforcement. It is not established by Origin alone.

## Secure local and remote defaults

**Local development:**

> Bind to `127.0.0.1`, validate expected Host and Origin values, avoid real
> secrets, and keep the endpoint off public interfaces.

**Remote production:**

> Use TLS, MCP OAuth, explicit host/origin allowlists, trusted proxy settings,
> request size and timeout limits, rate limits, and authorization at discovery
> and execution.

## Hands-on checkpoint

**Execution boundary:**

> Streamable HTTP on loopback. The verifier sends trusted and untrusted Host
> and Origin combinations to `127.0.0.1:8781`.

Run the loopback-only Host and Origin verification from the repository root:

```bash
cd reference/mcp/labs
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python verify_transport_security.py
```

Expected output:

```
allowed Host + trusted Origin -> 200
untrusted Host -> 421
untrusted Origin -> 403
allowed Host + absent Origin -> 200 (not authentication)
```

The complete runnable files are
[`transport_security_server.py`](labs/transport_security_server.py) and
[`verify_transport_security.py`](labs/verify_transport_security.py). The
verifier refuses to run if port `8781` is occupied and terminates only the
process it starts.

Read
[`../concepts/19-origin-cors.md`](../../mcp/concepts/19-origin-cors.md) and
[`../concepts/22-proxy-tls.md`](../../mcp/concepts/22-proxy-tls.md).

**Say it professionally:**

> Host and Origin validation reduce DNS-rebinding and browser-origin risk; CORS
> governs browser access; OAuth establishes identity; application policy
> authorizes operations. I configure and test each layer independently across
> the reverse-proxy boundary.

## Official references

- [Streamable HTTP security](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [Security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)
- [FastMCP HTTP deployment](https://gofastmcp.com/deployment/http)

