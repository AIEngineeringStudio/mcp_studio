> Design a secure MCP gateway for multiple MCP servers. How do you handle auth
> discovery, token validation, scopes, and per-tool policy?

Here's a comprehensive design for a secure MCP gateway that sits in front of
multiple MCP servers and handles auth, token validation, scopes, and per-tool
policy enforcement.

## Architecture Overview

```
Client → [MCP Gateway] → [Auth Layer] → [Policy Engine] → [MCP Server Pool]
```

The gateway acts as a **reverse proxy + policy enforcement point (PEP)**,
decoupling auth concerns from individual MCP servers.

---

## 1. Auth Discovery

### Well-Known Endpoint

The gateway exposes a standard discovery document so clients can auto-configure:

```http
GET /.well-known/mcp-gateway
```

```json
{
  "issuer": "https://gateway.example.com",
  "authorization_endpoint": "https://gateway.example.com/oauth/authorize",
  "token_endpoint": "https://gateway.example.com/oauth/token",
  "introspection_endpoint": "https://gateway.example.com/oauth/introspect",
  "jwks_uri": "https://gateway.example.com/.well-known/jwks.json",
  "scopes_supported": [
    "mcp:read",
    "mcp:write",
    "mcp:admin",
    "tool:*"
  ],
  "grant_types_supported": [
    "authorization_code",
    "client_credentials"
  ],
  "token_endpoint_auth_methods": [
    "client_secret_jwt",
    "private_key_jwt"
  ]
}
```

### Per-Server Auth Mapping

Each upstream MCP server has its own auth profile registered in the gateway:

```yaml
# gateway-config.yaml
servers:
  - id: github-mcp
    url: https://github-mcp.internal:8080
    auth_profile: oauth2_bearer
    required_scopes: [ "github:read", "github:write" ]
    credential_source: vault://secret/github-mcp/token

  - id: filesystem-mcp
    url: https://fs-mcp.internal:8081
    auth_profile: mtls
    required_scopes: [ "fs:read" ]
    cert_source: vault://pki/issue/fs-mcp

  - id: db-mcp
    url: https://db-mcp.internal:8082
    auth_profile: api_key
    required_scopes: [ "db:read", "db:write", "db:admin" ]
    credential_source: vault://secret/db-mcp/apikey
```

---

## 2. Token Validation Pipeline

The gateway runs every inbound token through a multi-stage validation chain:

```
┌─────────────────────────────────────────────────────────┐
│                  Token Validation Chain                 │
│                                                         │
│  [1. Extract] → [2. Decode] → [3. Verify Sig]           │
│       ↓               ↓              ↓                  │
│  [4. Check Exp] → [5. Check Iss] → [6. Check Aud]       │
│       ↓               ↓              ↓                  │
│  [7. Introspect?] → [8. Check Revocation] → [9. PASS]   │
└─────────────────────────────────────────────────────────┘
```

### Implementation

```typescript
interface TokenValidationContext {
    rawToken: string;
    claims?: JWTClaims;
    server: MCPServer;
    requestedTool: string;
}

class TokenValidationPipeline {
    private stages: ValidationStage[] = [
        new ExtractTokenStage(),
        new JWTDecodeStage(),
        new SignatureVerificationStage(this.jwksClient),
        new ExpirationCheckStage(),
        new IssuerCheckStage(this.trustedIssuers),
        new AudienceCheckStage(),
        new RevocationCheckStage(this.revocationCache),
        new IntrospectionStage(this.introspectionEndpoint), // for opaque tokens
    ];

    async validate(ctx: TokenValidationContext): Promise<ValidationResult> {
        for (const stage of this.stages) {
            const result = await stage.run(ctx);
            if (!result.ok) {
                this.audit.log("token_validation_failed", {
                    stage: stage.name,
                    reason: result.reason,
                    tool: ctx.requestedTool,
                });
                return result;
            }
            // Enrich context as we go (e.g., decoded claims from stage 2)
            Object.assign(ctx, result.enrichments);
        }
        return {ok: true};
    }
}
```

### JWKS Caching with Rotation Awareness

```typescript
class JWKSClient {
    private cache = new Map<string, CachedJWKS>();
    private readonly TTL = 3600_000; // 1 hour
    private readonly CLOCK_SKEW = 30; // seconds

    async getKey(kid: string, issuer: string): Promise<CryptoKey> {
        const cached = this.cache.get(issuer);

        // Trigger refresh if kid not found — handles key rotation
        if (!cached || !cached.keys[kid] || Date.now() > cached.expiresAt) {
            await this.refresh(issuer);
        }

        const key = this.cache.get(issuer)?.keys[kid];
        if (!key) throw new UnknownKeyError(`Unknown kid: ${kid}`);
        return key;
    }
}
```

---

## 3. Scope Enforcement

Scopes operate at two levels: **server-level** (coarse) and **tool-level** (
fine-grained).

### Scope Hierarchy

```
mcp:*                          ← super-admin
  mcp:read                     ← list tools, read responses
  mcp:write                    ← call write tools
  mcp:admin                    ← manage gateway config

github-mcp:*
  github-mcp:repos:read
  github-mcp:repos:write
  github-mcp:issues:read
  github-mcp:issues:write

db-mcp:*
  db-mcp:query                 ← SELECT only
  db-mcp:mutate                ← INSERT/UPDATE/DELETE
  db-mcp:admin                 ← DDL, drop, truncate
```

### Scope Validation Logic

```typescript
class ScopeEnforcer {
    check(
        tokenScopes: string[],
        requiredScopes: string[],
        tool: ToolDefinition
    ): ScopeCheckResult {
        const toolScopes = this.policyStore.getRequiredScopes(tool.serverId, tool.name);
        const allRequired = [...requiredScopes, ...toolScopes];

        const granted = allRequired.every(required =>
            tokenScopes.some(granted =>
                granted === required ||           // exact match
                granted.endsWith(":*") &&         // wildcard match
                required.startsWith(granted.slice(0, -1))
            )
        );

        if (!granted) {
            return {
                ok: false,
                missing: allRequired.filter(r => !tokenScopes.includes(r)),
                wwwAuthenticate: this.buildWWWAuthenticate(allRequired),
            };
        }
        return {ok: true};
    }
}
```

### WWW-Authenticate on Failure

Return a proper challenge rather than a bare 401:

```http
HTTP/1.1 403 Forbidden
WWW-Authenticate: Bearer realm="mcp-gateway",
  error="insufficient_scope",
  error_description="Tool 'db_drop_table' requires scope 'db-mcp:admin'",
  scope="db-mcp:admin"
```

---

## 4. Per-Tool Policy Engine

This is where the gateway gets powerful. Each tool call passes through a *
*policy engine** (OPA or custom) before being proxied upstream.

### Policy Model

```typescript
interface ToolPolicy {
    toolId: string;          // "db-mcp/execute_sql"
    serverId: string;
    rules: PolicyRule[];
}

interface PolicyRule {
    name: string;
    condition: PolicyCondition;
    action: "allow" | "deny" | "redact" | "audit" | "ratelimit";
    priority: number;
}

// Example policy rules
const policies: ToolPolicy[] = [
    {
        toolId: "db-mcp/execute_sql",
        serverId: "db-mcp",
        rules: [
            {
                name: "block_ddl_for_non_admins",
                condition: {
                    tokenScopes: {notContains: "db-mcp:admin"},
                    inputMatches: {sql: /DROP|TRUNCATE|ALTER|CREATE/i}
                },
                action: "deny",
                priority: 10,
            },
            {
                name: "audit_all_writes",
                condition: {
                    inputMatches: {sql: /INSERT|UPDATE|DELETE/i}
                },
                action: "audit",
                priority: 20,
            },
            {
                name: "rate_limit_expensive_queries",
                condition: {
                    inputMatches: {sql: /SELECT.*JOIN.*JOIN/i}  // multi-join
                },
                action: "ratelimit",
                config: {rpm: 10, burst: 2},
                priority: 30,
            }
        ]
    }
];
```

### OPA Integration

```rego
# policy.rego
package mcp.gateway

default allow = false

allow {
  has_required_scopes
  not is_blocked_tool
  not rate_limited
  not input_violates_policy
}

has_required_scopes {
  required := data.tool_policies[input.tool_id].required_scopes[_]
  input.token.scopes[_] == required
}

is_blocked_tool {
  data.tool_policies[input.tool_id].blocked == true
}

# Prevent prompt injection patterns in tool inputs
input_violates_policy {
  input.tool_id == "db-mcp/execute_sql"
  regex.match(`(?i)(drop|truncate|alter)\s+table`, input.args.sql)
  not "db-mcp:admin" in input.token.scopes
}

# Dynamic rate limit check (counter managed externally in Redis)
rate_limited {
  count := data.rate_counts[input.client_id][input.tool_id]
  limit := data.tool_policies[input.tool_id].rate_limit.rpm
  count > limit
}
```

### Gateway Request Flow

```typescript
class MCPGateway {
    async handleToolCall(req: MCPRequest): Promise<MCPResponse> {
        // 1. Extract and validate token
        const token = this.extractBearer(req);
        const claims = await this.tokenPipeline.validate({rawToken: token, ...});

        // 2. Resolve target server
        const server = this.registry.resolve(req.serverId);

        // 3. Scope check
        const scopeResult = this.scopeEnforcer.check(
            claims.scopes, server.requiredScopes, req.tool
        );
        if (!scopeResult.ok) return this.denyWithChallenge(scopeResult);

        // 4. Policy evaluation
        const policyResult = await this.policyEngine.evaluate({
            tool_id: `${req.serverId}/${req.toolName}`,
            args: req.args,
            token: claims,
            client_id: claims.sub,
        });
        if (!policyResult.allow) return this.denyWithReason(policyResult);

        // 5. Apply redactions/transforms
        const sanitizedArgs = await this.transformer.apply(req.args, policyResult.transforms);

        // 6. Proxy to upstream with server credential injection
        const upstreamCred = await this.credStore.get(server.credentialSource);
        return this.proxy.forward(server, req.toolName, sanitizedArgs, upstreamCred);
    }
}
```

---

## 5. Supporting Systems

### Revocation & Short-Lived Tokens

```
┌──────────────────────────────────────────────────────┐
│  Token Lifetime Strategy                             │
│                                                      │
│  Access Token:  15 min  (JWT, sig-verified locally)  │
│  Refresh Token: 24 hrs  (opaque, server-side store)  │
│  API Key:       ∞       (HMAC, revocation via Redis) │
└──────────────────────────────────────────────────────┘
```

### Audit Log Schema

Every tool call — allowed or denied — writes a structured log:

```json
{
  "ts": "2026-05-02T14:32:01Z",
  "event": "tool_call",
  "outcome": "deny",
  "client_id": "agent-42",
  "subject": "user:alice@example.com",
  "server": "db-mcp",
  "tool": "execute_sql",
  "policy_rule": "block_ddl_for_non_admins",
  "scopes_presented": [
    "db-mcp:query"
  ],
  "scopes_required": [
    "db-mcp:admin"
  ],
  "args_fingerprint": "sha256:a3f...",
  // hash, not plaintext
  "latency_ms": 4
}
```

### Rate Limiting Per Tool Per Client

```typescript
class ToolRateLimiter {
    // Sliding window counter in Redis
    async check(clientId: string, toolId: string): Promise<RateResult> {
        const key = `ratelimit:${clientId}:${toolId}`;
        const now = Date.now();
        const window = 60_000; // 1 minute

        const [count] = await this.redis
            .multi()
            .zremrangebyscore(key, 0, now - window)
            .zadd(key, now, `${now}-${Math.random()}`)
            .zcard(key)
            .expire(key, 60)
            .exec();

        const limit = this.policyStore.getRateLimit(toolId);
        return {allowed: count <= limit, count, limit};
    }
}
```

---

## Key Design Principles

| Concern                  | Approach                                                                      |
|--------------------------|-------------------------------------------------------------------------------|
| **Zero trust**           | Every request re-validated; no implicit trust between gateway and upstream    |
| **Credential isolation** | Upstream credentials never leave the gateway; clients only see gateway tokens |
| **Least privilege**      | Scopes are additive; tools default-deny without explicit policy allow         |
| **Auditability**         | Every call logged with non-repudiable fingerprints, no raw args stored        |
| **Hot reload**           | Policy and scope config reload without gateway restart via config watch       |
| **Fail closed**          | Policy engine errors → deny, not allow                                        |

This architecture gives you a single enforcement plane regardless of how many
MCP servers you add — new servers register their auth profile and tool policies,
and the gateway handles the rest.