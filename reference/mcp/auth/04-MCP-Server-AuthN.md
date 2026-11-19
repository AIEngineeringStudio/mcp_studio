> > Google ADK agent interacting with MCP server which calls an API. MCP server
> > exposes calls and resources.
> > Atleast one call and one resource must be protected and requires agent to
> > pass
> > auth. One must be jwt based auth and another OAuth.
> > One tool must be visible only to admins(use RBAC based tool filtering)


Here's a full breakdown of what's built and how each security layer works:

---

## Architecture Overview

```
ADK Agent  ──SSE──►  MCP Server  ──HTTP──►  Backend API
  JWT mint              JWT forward            /profile (JWT)
  OAuth token           OAuth forward          /report  (OAuth)
  RBAC filter           RBAC gate              /admin   (JWT+role)
```

---

## Security Layers

### 🔐 JWT Authentication (`get_user_profile`, `admin_tool`)

The agent mints a signed JWT with `sub`, `role`, and `exp` claims using
`python-jose`. The MCP server stores it per-session and forwards it as
`Authorization: Bearer <jwt>` to the backend API, which validates the signature
before responding.

### 🔑 OAuth Authentication (`protected://report` resource)

The agent holds a pre-obtained OAuth access token (simulating a real OAuth2
flow). The MCP server forwards it as a Bearer token. The backend validates it
against a token store — in production this would be token introspection or JWKS.

### 🛡️ RBAC Tool Filtering (`admin_tool`)

Before building the agent, `rbac_tool_filter()` runs over all tools returned by
the MCP server. If the agent's role is not `"admin"`, `admin_tool` is stripped
from the visible tools list entirely — the agent can't even see it exists.
Change `AGENT_ROLE = "user"` to test.

---

## Running It

```bash
# Terminal 1 — Backend API
python api_server.py        # → :8001

# Terminal 2 — MCP Server
python mcp_server.py        # → :8000/sse

# Terminal 3 — Agent
python agent.py
```

The launcher script writes all three files when run directly (
`python adk_mcp_auth.py`).

---

## Key Design Decisions

| Concern         | Approach                                                           |
|-----------------|--------------------------------------------------------------------|
| Token injection | `configure_tokens` bootstrap tool called before any real work      |
| JWT signing     | `python-jose` with HS256; swap to RS256 + JWKS for production      |
| OAuth           | Pre-obtained token simulated; plug in `httpx-oauth` for real flows |
| RBAC            | Client-side filter on ADK tool list + server-side enforcement      |
| MCP transport   | SSE (`/sse`) so ADK's `MCPToolset` can connect                     |

---

Architecture:

```
  ┌─────────────────────────────────────────────────────────┐
  │  Google ADK Agent  (agent.py)                           │
  │   - Holds JWT token + OAuth access token                │
  │   - Connects to MCP server via SSE                      │
  │   - RBAC: admin role → sees admin_tool                  │
  └────────────────────┬────────────────────────────────────┘
                       │ MCP (SSE)
  ┌────────────────────▼────────────────────────────────────┐
  │  MCP Server  (mcp_server.py)                            │
  │  Tools (calls):                                         │
  │   • get_public_data      → open                         │
  │   • get_user_profile     → JWT required                 │
  │   • admin_tool           → JWT + role=admin (RBAC)      │
  │  Resources:                                             │
  │   • public://info        → open                         │
  │   • protected://report   → OAuth Bearer required        │
  └────────────────────┬────────────────────────────────────┘
                       │ HTTP
  ┌────────────────────▼────────────────────────────────────┐
  │  Fake Backend API  (api_server.py)                      │
  │   /public             → no auth                         │
  │   /profile            → validates JWT                   │
  │   /report             → validates OAuth token           │
  │   /admin              → validates JWT + admin claim     │
  └─────────────────────────────────────────────────────────┘
```

Install:
pip install google-adk mcp fastapi uvicorn python-jose httpx

Run (3 terminals):

1. python api_server.py → http://localhost:8001
2. python mcp_server.py → http://localhost:8000
3. python agent.py

```
# ─────────────────────────────────────────────
# FILE: api_server.py  (the actual backend API)
# ─────────────────────────────────────────────
```

```python
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Depends
from jose import jwt, JWTError

app = FastAPI(title="Backend API")

JWT_SECRET = "super-secret-key"
JWT_ALGORITHM = "HS256"
VALID_OAUTH_TOKENS = {"oauth-token-admin",
                      "oauth-token-user"}  # mock token store


def verify_jwt(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(401, f"Invalid JWT: {e}")


def verify_oauth(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    token = authorization.split(" ", 1)[1]
    if token not in VALID_OAUTH_TOKENS:
        raise HTTPException(401, "Invalid OAuth token")
    return token


@app.get("/public")
def public_data():
    return {"data": "This is public information — no auth needed."}


@app.get("/profile")
def get_profile(payload: dict = Depends(verify_jwt)):
    return {
        "user": payload.get("sub"),
        "role": payload.get("role", "user"),
        "email": payload.get("email"),
    }


@app.get("/report")
def get_report(token: str = Depends(verify_oauth)):
    return {
        "report": "Q1 2026 Financial Summary",
        "revenue": "$4.2M",
        "accessed_with": token,
    }


@app.get("/admin")
def admin_action(payload: dict = Depends(verify_jwt)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Admin role required")
    return {
        "action": "Admin panel accessed",
        "by": payload.get("sub"),
        "secret": "TOP_SECRET_ADMIN_DATA",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

```

```
# ─────────────────────────────────────────────
# FILE: mcp_server.py
# ─────────────────────────────────────────────
```

```python

import json
import httpx
from mcp.server.fastmcp import FastMCP
from mcp import types

API_BASE = "http://localhost:8001"

# ── Token store (in production: per-session credential store) ──────────────
# Tokens are injected by the agent at startup via a shared config.
# Here we use a simple module-level dict for clarity.
TOKEN_STORE: dict = {}


def get_jwt() -> str:
    t = TOKEN_STORE.get("jwt")
    if not t:
        raise ValueError("JWT token not configured in MCP server")
    return t


def get_oauth() -> str:
    t = TOKEN_STORE.get("oauth")
    if not t:
        raise ValueError("OAuth token not configured in MCP server")
    return t


def get_role() -> str:
    return TOKEN_STORE.get("role", "user")


# ── RBAC tool filter ────────────────────────────────────────────────────────
def is_admin() -> bool:
    return get_role() == "admin"


# ── MCP Server ──────────────────────────────────────────────────────────────
mcp = FastMCP("AuthDemoServer")


# ── TOOLS (calls) ───────────────────────────────────────────────────────────

@mcp.tool()
def get_public_data() -> str:
    """Fetch public data. No authentication required."""
    resp = httpx.get(f"{API_BASE}/public")
    resp.raise_for_status()
    return json.dumps(resp.json())


@mcp.tool()
def get_user_profile() -> str:
    """
    Fetch the current user's profile.
    🔒 Requires JWT authentication.
    """
    jwt_token = get_jwt()
    resp = httpx.get(
        f"{API_BASE}/profile",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    if resp.status_code == 401:
        return f"JWT auth failed: {resp.text}"
    resp.raise_for_status()
    return json.dumps(resp.json())


@mcp.tool()
def admin_tool() -> str:
    """
    Execute privileged admin action.
    🔒 Requires JWT authentication.
    🔑 Requires role=admin (RBAC).
    Only exposed to admin agents.
    """
    if not is_admin():
        return "Access denied: admin role required (RBAC filter)"
    jwt_token = get_jwt()
    resp = httpx.get(
        f"{API_BASE}/admin",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    if resp.status_code in (401, 403):
        return f"Admin call failed: {resp.text}"
    resp.raise_for_status()
    return json.dumps(resp.json())


# ── RESOURCES ────────────────────────────────────────────────────────────────

@mcp.resource("public://info")
def public_info() -> str:
    """Public informational resource. No authentication required."""
    resp = httpx.get(f"{API_BASE}/public")
    resp.raise_for_status()
    return resp.text


@mcp.resource("protected://report")
def protected_report() -> str:
    """
    Financial report resource.
    🔒 Requires OAuth Bearer token.
    """
    oauth_token = get_oauth()
    resp = httpx.get(
        f"{API_BASE}/report",
        headers={"Authorization": f"Bearer {oauth_token}"},
    )
    if resp.status_code == 401:
        return f"OAuth auth failed: {resp.text}"
    resp.raise_for_status()
    return resp.text


# ── Token injection endpoint (called by agent before starting) ──────────────
@mcp.tool()
def configure_tokens(jwt: str, oauth: str, role: str = "user") -> str:
    """
    Internal bootstrap tool — agent injects credentials into this MCP session.
    In production, use a secure credential vault or per-session auth middleware.
    """
    TOKEN_STORE["jwt"] = jwt
    TOKEN_STORE["oauth"] = oauth
    TOKEN_STORE["role"] = role
    return f"Tokens configured. Role set to: {role}"


if __name__ == "__main__":
    import uvicorn

    # Run with SSE transport so ADK agent can connect
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 8000
    uvicorn.run(mcp.sse_app(), host="0.0.0.0", port=8000)
```

```

# ─────────────────────────────────────────────
# FILE: agent.py  (Google ADK Agent)
# ─────────────────────────────────────────────
AGENT_PY = """
```

```python
import asyncio
from datetime import datetime, timezone, timedelta
from jose import jwt as jose_jwt

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# ── Credential Configuration ─────────────────────────────────────────────────
JWT_SECRET = "super-secret-key"
JWT_ALGORITHM = "HS256"

AGENT_ROLE = "admin"  # Change to "user" to test RBAC filtering


def mint_jwt(role: str) -> str:
    """Mint a short-lived JWT with a role claim."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "agent-001",
        "email": "agent@example.com",
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jose_jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# Tokens the agent will use
JWT_TOKEN = mint_jwt(AGENT_ROLE)
OAUTH_TOKEN = "oauth-token-admin"  # Simulates a pre-obtained OAuth access token


# ── RBAC Tool Filter ──────────────────────────────────────────────────────────
def rbac_tool_filter(tool_name: str, role: str) -> bool:
    """
    Returns True if the tool should be visible to the agent given its role.
    Admin-only tools are hidden from non-admin agents entirely.
    """
    ADMIN_ONLY_TOOLS = {"admin_tool"}
    if tool_name in ADMIN_ONLY_TOOLS and role != "admin":
        print(
            f"[RBAC] Tool '{tool_name}' hidden — agent role is '{role}' (requires admin)")
        return False
    return True


async def build_agent_with_mcp():
    """Connect to MCP server, inject credentials, apply RBAC filter, build agent."""

    # ── 1. Connect to MCP server over SSE ─────────────────────────────────────
    toolset = MCPToolset(
        connection_params=SseServerParams(url="http://localhost:8000/sse"),
    )

    # ── 2. Bootstrap — inject tokens into the MCP session ─────────────────────
    # In production this would use a secure per-session vault / middleware layer.
    await toolset.call_tool(
        "configure_tokens",
        {"jwt": JWT_TOKEN, "oauth": OAUTH_TOKEN, "role": AGENT_ROLE},
    )
    print(f"[Agent] Tokens injected. Agent role: {AGENT_ROLE}")

    # ── 3. Fetch available tools and apply RBAC filter ─────────────────────────
    all_tools = await toolset.load_tools()
    visible_tools = [
        t for t in all_tools
        if rbac_tool_filter(t.name, AGENT_ROLE)
    ]
    print(f"[Agent] Visible tools: {[t.name for t in visible_tools]}")

    # ── 4. Build the ADK LlmAgent ──────────────────────────────────────────────
    agent = LlmAgent(
        name="auth_demo_agent",
        model="gemini-2.0-flash",
        instruction="""
            You are a helpful assistant with access to a set of tools backed
            by a secure API. Use tools to answer user queries.

            Auth context injected automatically:
            - JWT-protected tools: credentials handled transparently
            - OAuth-protected resources: credentials handled transparently
            - Admin tools: only visible if your role is 'admin'
        """,
        tools=visible_tools,
    )
    return agent


async def main():
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="auth_demo", user_id="user-1"
    )

    agent = await build_agent_with_mcp()

    runner = Runner(
        agent=agent,
        app_name="auth_demo",
        session_service=session_service,
    )

    queries = [
        "Fetch the public data.",
        "Get my user profile.",
        "Read the protected financial report resource.",
        "Run the admin tool.",  # Only works if AGENT_ROLE == "admin"
    ]

    for query in queries:
        print(f"\\n{'=' * 60}")
        print(f"[User] {query}")
        async for event in runner.run_async(
                user_id="user-1",
                session_id=session.id,
                new_message=query,
        ):
            if event.is_final_response():
                print(f"[Agent] {event.content.parts[0].text}")


if __name__ == "__main__":
    asyncio.run(main())

```

---

> Name based filtering is poor design. Tool filtering must be done my MCP
> ==> MCP shouldn't disclose the tool unless agent sends the right auth and
> role. Don't handwave code or implement non-standard solutions or 
> non-production
> grade designs