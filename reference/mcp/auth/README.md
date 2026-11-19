# MCP authorization source map

This folder contains historical prompts, generated answers, an interactive
simulation, and earlier implementation attempts. It is useful as provenance,
but it is not a single consistent course.

For the maintained learning path, use:

1. [OAuth discovery and delegated calendar access](../concepts/20-oauth-discovery.md).
2. [Authorization, tool visibility, and calendar isolation](../concepts/21-authorization.md).
3. [The runnable calendar authorization lab](../labs/auth_calendar_server.py).
4. [The automated verification flow](../labs/verify_auth_calendar.py).

The maintained material targets MCP `2026-07-28`. Check
[the version baseline](../VERSIONS.md) before adapting code.

## How to read the historical files

**Gateway design source:**

> [01-Secure-MCP-gateway.md](01-Secure-MCP-gateway.md) contains useful policy,
> audit, rate-limit, and credential-isolation ideas. Its
> `/.well-known/mcp-gateway` discovery endpoint is not a standard MCP endpoint.

**Protected tools and resources source:**

> [02-MCP-Server-OAuth-Protected-Tools-Resources.md](02-MCP-Server-OAuth-Protected-Tools-Resources.md)
> contains a substantial MCP `2025-06-18` example. Treat its initialization,
> package APIs, unpinned dependencies, and per-scope Client Credentials tokens
> as legacy demonstration material rather than current delegated-user design.

**Discovery and delegation transcript:**

> [03-OAuth_Protected_Resource_Discovery.md](03-OAuth_Protected_Resource_Discovery.md)
> records several successive implementations: simulated UI, Node, Python,
> legacy SSE, Client Credentials, RFC 8693 Token Exchange, row filtering, and
> tool filtering. Read individual sections for provenance; do not run the file
> as one tutorial.

**Unsafe initial authentication attempt:**

> [04-MCP-Server-AuthN.md](04-MCP-Server-AuthN.md) injects credentials through a
> tool, uses global token state, and relies partly on client-side filtering.
> Preserve it as an anti-pattern record. Do not use it as a starting design.

**Improved but legacy request-context attempt:**

> [04B-MCP_server-AuthN.md](04B-MCP_server-AuthN.md) improves request isolation
> and server-side filtering. It still uses legacy transport assumptions,
> nonstandard dual-token headers, and inbound-token forwarding. The maintained
> guide replaces those parts with SDK auth context and a separate calendar
> credential broker.

**Prompt workflow, not course content:**

> [Chunking_Prompts_Drift_Prevention.md](Chunking_Prompts_Drift_Prevention.md)
> is a historical prompt-generation workflow. It is not an MCP authorization
> lesson and its forced quizzes and interview sections are not part of the
> maintained teaching method.

**Legacy transport explanation:**

> [How_it_works.md](How_it_works.md) describes session-based Streamable HTTP,
> persistent GET/SSE behavior, and custom chunk streaming. It is not current
> authorization guidance and does not describe MCP `2026-07-28`.

**Legacy interactive simulation:**

> [mcp-oauth-discovery.html](mcp-oauth-discovery.html) is a self-contained,
> local simulation of OAuth discovery and PKCE. It explicitly simulates tokens
> and uses the MCP `2025-03-26` initialization flow. Use it only to visualize
> the OAuth discovery sequence.

## Canonical design rules

- The MCP server is an OAuth Resource Server; the Authorization Server issues
  tokens.
- The MCP client follows Protected Resource Metadata and authorization-server
  metadata. The MCP server does not redirect the browser itself.
- OAuth is a framework; JWT is one possible token format.
- Validate issuer, resource or audience, lifetime, and scopes on every HTTP
  request.
- Tool visibility is not authorization. Re-check policy during tool execution.
- Derive subject and tenant from validated identity, never model arguments.
- Do not forward an MCP access token to a calendar or other downstream API.
- Use OBO or another explicit credential broker to obtain a new downstream
  token when the provider supports that flow.
- Keep authorization-dependent tool catalogs private in client and gateway
  caches.

## Provider-specific calendar guidance

Microsoft Entra supports an OAuth On-Behalf-Of exchange for a middle-tier API
calling Microsoft Graph with delegated user permissions. Google Calendar more
commonly uses user Authorization Code consent plus a securely stored refresh
token. Google Workspace domain-wide delegation is a separate administrator
grant for a service account.

Do not label every one of these designs “OBO.” They all provide delegated access,
but their protocols, consent models, and operational risk differ.
