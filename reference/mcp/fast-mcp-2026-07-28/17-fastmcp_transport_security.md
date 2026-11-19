# Lesson 17 — FastMCP transport security

## Outcome

After this lesson, you can distinguish Host validation, Origin validation,
CORS, authentication, and proxy trust.

## The controls answer different questions

```text
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

## CORS is separate

Origin allowlisting in transport security rejects untrusted origins. CORS
middleware controls browser preflight and response headers. Configure both when
browser JavaScript directly calls the server.

Never use `Access-Control-Allow-Origin: *` with credentials. Enumerate trusted
origins and minimize allowed methods and headers.

## Reverse proxy trust

```text
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

Run the loopback-only HTTP verification:

```bash
cd reference/mcp/labs
uv run python verify_http.py
```

Read
[`../concepts/19-origin-cors.md`](../concepts/19-origin-cors.md) and
[`../concepts/22-proxy-tls.md`](../concepts/22-proxy-tls.md).

**Say it professionally:**

> Host and Origin validation reduce DNS-rebinding and browser-origin risk; CORS
> governs browser access; OAuth establishes identity; application policy
> authorizes operations. I configure and test each layer independently across
> the reverse-proxy boundary.

## Official references

- [Streamable HTTP security](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [Security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)
- [FastMCP HTTP deployment](https://gofastmcp.com/deployment/http)

