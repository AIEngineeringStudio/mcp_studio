# OAuth discovery and delegated access

**Outcome:** Trace how a client finds the authorization server for a protected MCP resource.

**Prerequisites:** [11: Streamable HTTP](11-streamable-http.md), [19: Host validation, Origin, and CORS](19-origin-cors.md).

## A token must come from the right authority

A remote MCP server may require permission delegated by the user. The client
needs to discover which authorization server can issue an acceptable token.

The MCP server is the protected resource server. The authorization server
interacts with the user as needed and issues tokens. The client obtains a
token and presents it to the resource server.

```text
Client --> MCP endpoint
       <-- authentication challenge / metadata location
Client --> protected-resource metadata
       <-- authorization server information
Client --> authorization-server metadata
       <-- authorization and token endpoints
Client --> authorization flow --> access token
Client --> MCP operation with token
```

Metadata discovery describes where to continue. It is not itself a permission
grant.

## Walk one ticket lookup

A user connects the support host to the ticket MCP service. The client learns
the protected resource and its authorization server. It then uses an appropriate
OAuth flow, including the required protections for the client type. Once a
token is available, the server validates it before allowing protected work.

A token intended for another service should not become valid simply because
its signature verifies. Audience or resource binding matters.

For browser/public-client authorization-code flows, PKCE binds code redemption
to the initiating client instance. Redirect validation and state handling
protect other parts of the flow. Use a maintained implementation; a miniature
authorization server in a transcript is an educational simulator.

## Metadata has security implications

Do not blindly fetch arbitrary URLs supplied by an untrusted service with
privileged network access. Validate issuer identity, HTTPS expectations, and
permitted destinations according to the chosen implementation.

Persisted client credentials must stay associated with the authorization
server that issued them. Changing issuer is not just changing a URL string.

## Registration is a separate concern

Client identification/registration describes the client to the authorization
server. It is separate from asking the user for permission and separate from
the token's scopes. Current MCP guidance includes Client ID Metadata Documents;
older dynamic registration examples require compatibility labeling.

The original HTML discovery simulator can illustrate the sequence, but its
final legacy initialization step should not be read as the modern protocol's
universal starting behavior.

## JWT versus OAuth

JWT is a possible token representation. OAuth is an authorization framework.
OAuth access tokens can be JWTs or opaque values. Decoding a JWT's payload is
not validation; signature, issuer, audience, lifetime, and relevant policy need
verification.

**Professional articulation:**

> “Protected-resource metadata tells the client where to obtain an appropriate
> token. The resource server still validates that token and authorizes each
> requested operation.”

## Sources and next step

- [Archive: conversations/auth/03-OAuth_Protected_Resource_Discovery.md](../../conversations/auth/03-OAuth_Protected_Resource_Discovery.md)
- [Archive: conversations/auth/02-MCP-Server-OAuth-Protected-Tools-Resources.md](../../conversations/auth/02-MCP-Server-OAuth-Protected-Tools-Resources.md)
- [Official reference](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/authorization-server-discovery) — checked 2026-11-15.

Next: [Authorization, scopes, and tenant isolation](21-authorization.md).

