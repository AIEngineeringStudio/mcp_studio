Creating a new `Server()` per request means re-registering all
handlers on every request — that's unnecessary object allocation and Python
function registration overhead on every single HTTP call. At high TPS it adds
up, and it's not how you'd build this in production.

But the reason it was done that way is real: **auth context needs to be
request-scoped**. The per-request server was a blunt solution to that problem.

The correct approach is to **keep a single long-lived server instance** and pass
auth context through the call stack explicitly, not by recreating the object.

There are two standard ways to do this in Python async:

---

### Option 1: `contextvars.ContextVar` (correct for async)

Python's `contextvars` module is designed exactly for this — per-request context
in async code without thread-locals or globals. Each async task gets its own
copy.

```python
from contextvars import ContextVar

_jwt_payload: ContextVar[dict | None] = ContextVar("jwt_payload", default=None)
_oauth_token: ContextVar[str | None] = ContextVar("oauth_token", default=None)

# In the ASGI handler, before dispatching:
token1 = _jwt_payload.set(decoded_payload)
token2 = _oauth_token.set(raw_oauth)
try:
    # handle request — all downstream async calls in this task
    # see these values via _jwt_payload.get()
    await transport.handle_request(request)
finally:
    _jwt_payload.reset(token1)
    _oauth_token.reset(token2)
```

The single `Server()` instance's handlers call `_jwt_payload.get()` — they see
the value set by their specific request's async task, not any other concurrent
request's value. This is safe, zero-copy, and has negligible overhead.

---

### Option 2: Middleware + request state (Starlette-native)

```python
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    request.state.jwt_payload = decode_if_present(request)
    request.state.oauth_token = extract_oauth(request)
    return await call_next(request)
```

Then thread `request` into your handlers. Works, but MCP's `Server` handler
signatures don't receive a `request` object — you'd need to bridge it through
`ContextVar` anyway, making this just a structured way to populate the vars.

---

### What the production design looks like

```
Single Server() instance (created once at startup)
     │
     ├── list_tools()   → reads _jwt_payload.get() for role filtering
     ├── call_tool()    → reads _jwt_payload.get() / _oauth_token.get()
     └── read_resource() → reads _oauth_token.get()

ASGI handler (per request)
     │
     ├── decode JWT / validate OAuth   (fast, no I/O)
     ├── set ContextVars               (O(1))
     ├── dispatch to Server instance   (reused)
     └── reset ContextVars             (cleanup)
```

No handler re-registration, no object allocation per request. The server
instance is stateless with respect to auth — all auth state lives in the
`ContextVar` task-local store.

---

### The one real constraint

MCP's `StreamableHTTPServerTransport` creates a new transport instance per
request — that's correct and unavoidable, because a transport represents one
HTTP connection's lifetime. The *server* being shared is fine; the *transport*
being per-request is the spec.

---

Want me to rewrite `mcp_server.py` with the single-instance + `ContextVar`
design?

Yes

---

Here's exactly what changed and why each part is correct:

### What changed

**Before:** `make_server(jwt_payload, oauth_token)` was called inside the
handler — a new `Server()` constructed per request, all four `@server.*`
decorators re-executed, all handler functions re-created as closures capturing
the auth state.

**After:** `server = Server(...)` is a module-level singleton. All four handler
registrations happen once at import time. Auth state is never captured in
closures — handlers call `_jwt_payload.get()` at call-time, reading from the
current task's `ContextVar` slot.

### Why `ContextVar` is the right primitive here

`asyncio` creates a shallow copy of the current `Context` when spawning a task.
Each request runs in its own task, so `ContextVar.set()` in one task is
invisible to all others — this is guaranteed by the language, not by
application-level locking. It's the same mechanism used by `contextvars`-aware
frameworks like Starlette itself for `request.state`.

### Why the `finally` reset still matters

The task handling one HTTP request is reused from uvicorn's worker pool in some
configurations. Without the reset, a `ContextVar` set for request N could bleed
into a future request handled by the same recycled task. The `Token` objects
returned by `.set()` make the reset O(1) and exact — no scanning, no dict
lookup.

### What stays per-request and why

`StreamableHTTPServerTransport` is still instantiated per request — that's
correct. It owns the session ID and the read/write stream pair for one HTTP
connection. It is inherently stateful to that connection and must not be shared.

```python
"""
api_server.py  —  Backend API
Endpoints:
  GET /public           → open
  GET /profile          → JWT required
  GET /report           → OAuth Bearer required
  GET /admin            → JWT required, role=admin claim required

Run: uvicorn api_server:app --port 8001
"""
import os
from fastapi import FastAPI, Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt  # PyJWT

app = FastAPI()
bearer = HTTPBearer()

JWT_SECRET = os.environ["JWT_SECRET"]  # e.g. "dev-secret-do-not-use-in-prod"
JWT_ALGORITHM = "HS256"
# In production: introspect at your AS. Here we use a static set for clarity.
VALID_OAUTH_TOKENS: set[str] = set(os.environ["VALID_OAUTH_TOKENS"].split(","))


def decode_jwt(credentials: HTTPAuthorizationCredentials) -> dict:
    try:
        return jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            f"Invalid token: {exc}")


@app.get("/public")
def public_data():
    return {"data": "public info"}


@app.get("/profile")
def get_profile(creds: HTTPAuthorizationCredentials = Security(bearer)):
    payload = decode_jwt(creds)
    return {"sub": payload["sub"], "role": payload["role"],
            "email": payload["email"]}


@app.get("/report")
def get_report(creds: HTTPAuthorizationCredentials = Security(bearer)):
    if creds.credentials not in VALID_OAUTH_TOKENS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid OAuth token")
    return {"report": "Q1 2026 Financial Summary", "revenue": "$4.2M"}


@app.get("/admin")
def admin_action(creds: HTTPAuthorizationCredentials = Security(bearer)):
    payload = decode_jwt(creds)
    if payload.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin role required")
    return {"action": "Admin panel accessed", "by": payload["sub"]}
```

```python
"""
agent.py  —  Google ADK Agent

Auth flow
─────────
1. Agent mints a signed JWT (or receives one from its identity provider).
2. Agent obtained an OAuth access token via its own OAuth2 client-credentials
   or authorization-code flow (simulated here with a static token).
3. Both tokens are sent as HTTP headers on the MCP Streamable HTTP connection.
4. MCP server decodes them per-request and:
     - Returns only the tools the role permits in tools/list
     - Enforces auth on every tool call / resource read
5. ADK sees only what the server returns — admin_tool is invisible to non-admins.

Run:
  JWT_SECRET=dev-secret-do-not-use-in-prod \\
  VALID_OAUTH_TOKENS=oauth-token-admin,oauth-token-user \\
  AGENT_ROLE=admin \\  # set to "user" to test RBAC
  python agent.py
"""
import asyncio
import os
from datetime import datetime, timezone, timedelta

import jwt  # PyJWT
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset,
    StreamableHTTPServerParams
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# ── Config ────────────────────────────────────────────────────────────────────
MCP_URL = os.environ.get("MCP_URL", "http://localhost:8000/mcp")
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
AGENT_ROLE = os.environ.get("AGENT_ROLE", "user")  # "admin" or "user"

# Simulates a token obtained via OAuth2 client-credentials grant.
# In production: use httpx + your AS token endpoint, cache with expiry.
OAUTH_TOKEN = os.environ["OAUTH_TOKEN"]  # e.g. "oauth-token-admin"


def mint_agent_jwt(role: str) -> str:
    """
    In production the agent receives a JWT from its identity provider
    (Workload Identity, a service account token, etc.). We mint one here
    for demonstration using the shared secret.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "agent-001",
        "email": "agent@example.com",
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def main() -> None:
    agent_jwt = mint_agent_jwt(AGENT_ROLE)

    # ── Connect to MCP server ─────────────────────────────────────────────────
    # StreamableHTTPServerParams lets us attach custom headers.
    # The JWT goes in Authorization: Bearer <jwt>.
    # The OAuth token goes in X-OAuth-Token so the server can distinguish them.
    toolset = MCPToolset(
        connection_params=StreamableHTTPServerParams(
            url=MCP_URL,
            headers={
                "Authorization": f"Bearer {agent_jwt}",
                "X-OAuth-Token": OAUTH_TOKEN,
            },
        ),
    )

    # tools/list is issued here by ADK. The server returns only the tools
    # that the agent's role permits. admin_tool will be absent for role=user.
    tools, exit_stack = await toolset.load_tools()
    print(f"[agent] visible tools: {[t.name for t in tools]}")

    # ── Build ADK agent ───────────────────────────────────────────────────────
    agent = LlmAgent(
        name="auth_demo_agent",
        model="gemini-2.0-flash",
        instruction=(
            "You are a helpful assistant. Use your tools to answer questions. "
            "Auth is handled transparently — do not ask the user for credentials."
        ),
        tools=tools,
    )

    session_svc = InMemorySessionService()
    session = await session_svc.create_session(app_name="auth_demo",
                                               user_id="u1")
    runner = Runner(agent=agent, app_name="auth_demo",
                    session_service=session_svc)

    queries = [
        "Fetch the public data.",
        "Get my user profile.",
        "Read the protected financial report resource at protected://report.",
        "Run the admin tool.",
    ]

    for query in queries:
        print(f"\n{'─' * 60}")
        print(f"[user]  {query}")
        async for event in runner.run_async(
                user_id="u1", session_id=session.id, new_message=query
        ):
            if event.is_final_response():
                print(f"[agent] {event.content.parts[0].text}")

    await exit_stack.aclose()


if __name__ == "__main__":
    asyncio.run(main())
```

```python
"""
# mcp_server.py  —  MCP Server (Streamable HTTP, spec 2025-03-26)

Auth context is carried per-request via contextvars.ContextVar.
A single Server() instance is created at module load; its handlers
read request-scoped auth state from ContextVars set by the ASGI handler.

Concurrency safety:
  asyncio runs one task per request. ContextVar.set() affects only the
  current task's context — concurrent requests cannot observe each other's
  auth state. ContextVar.reset() in the finally block is belt-and-suspenders
  cleanup; asyncio task contexts are already isolated.

Run: uvicorn mcp_server:app --port 8000
"""

import os
from contextvars import ContextVar
from typing import Any

import httpx
import jwt  # PyJWT
from mcp.server import Server
from mcp.server.streamable_http import StreamableHTTPServerTransport
from mcp import types
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE = os.environ.get("API_BASE", "http://localhost:8001")
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
VALID_OAUTH_TOKENS: set[str] = set(os.environ["VALID_OAUTH_TOKENS"].split(","))

# ── Per-request auth context ──────────────────────────────────────────────────
# Set once by the ASGI handler before MCP dispatch; read by server handlers.
# Default None means "unauthenticated".
_jwt_payload: ContextVar[dict | None] = ContextVar("jwt_payload", default=None)
_jwt_raw: ContextVar[str | None] = ContextVar("jwt_raw", default=None)
_oauth_token: ContextVar[str | None] = ContextVar("oauth_token", default=None)


# ── Auth helpers ──────────────────────────────────────────────────────────────
class AuthError(Exception):
    def __init__(self, message: str, status: int = 401):
        self.message = message
        self.http_status = status
        super().__init__(message)


def _decode_jwt(raw: str) -> dict:
    try:
        return jwt.decode(raw, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthError("JWT expired")
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"Invalid JWT: {exc}")


def _require_jwt() -> tuple[dict, str]:
    payload = _jwt_payload.get()
    raw = _jwt_raw.get()
    if payload is None or raw is None:
        raise AuthError("JWT required")
    return payload, raw


def _require_oauth() -> str:
    token = _oauth_token.get()
    if token is None:
        raise AuthError("OAuth token required")
    if token not in VALID_OAUTH_TOKENS:
        raise AuthError("Invalid OAuth token")
    return token


# ── Tool & resource definitions ───────────────────────────────────────────────
_ALL_TOOLS: list[types.Tool] = [
    types.Tool(
        name="get_public_data",
        description="Fetch public data. No authentication required.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="get_user_profile",
        description="Fetch the authenticated user's profile. Requires JWT.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="admin_tool",
        description="Execute privileged admin action. Requires JWT with role=admin.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]

_ALL_RESOURCES: list[types.Resource] = [
    types.Resource(
        uri="public://info",  # type: ignore[arg-type]
        name="Public Info",
        description="Open resource, no auth required.",
        mimeType="application/json",
    ),
    types.Resource(
        uri="protected://report",  # type: ignore[arg-type]
        name="Financial Report",
        description="Q1 report. Requires OAuth Bearer token.",
        mimeType="application/json",
    ),
]

# ── Single shared Server instance ─────────────────────────────────────────────
server = Server("auth-demo-mcp")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    RBAC: admin_tool is omitted from the response unless the caller's JWT
    carries role=admin. The tool name is never disclosed to unauthorised callers.
    """
    payload = _jwt_payload.get()
    role = (payload or {}).get("role", "")
    return [t for t in _ALL_TOOLS if
            not (t.name == "admin_tool" and role != "admin")]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[
    types.TextContent]:
    async with httpx.AsyncClient() as client:

        if name == "get_public_data":
            resp = await client.get(f"{API_BASE}/public")
            resp.raise_for_status()
            return [types.TextContent(type="text", text=resp.text)]

        elif name == "get_user_profile":
            _, raw = _require_jwt()
            resp = await client.get(
                f"{API_BASE}/profile",
                headers={"Authorization": f"Bearer {raw}"},
            )
            if resp.status_code == 401:
                raise AuthError(f"API rejected JWT: {resp.text}")
            resp.raise_for_status()
            return [types.TextContent(type="text", text=resp.text)]

        elif name == "admin_tool":
            payload, raw = _require_jwt()
            # Defense-in-depth: re-check role even though list_tools never
            # disclosed this tool to non-admins.
            if payload.get("role") != "admin":
                raise AuthError("admin role required", status=403)
            resp = await client.get(
                f"{API_BASE}/admin",
                headers={"Authorization": f"Bearer {raw}"},
            )
            if resp.status_code in (401, 403):
                raise AuthError(f"API rejected: {resp.text}", resp.status_code)
            resp.raise_for_status()
            return [types.TextContent(type="text", text=resp.text)]

        else:
            raise ValueError(f"Unknown tool: {name}")


@server.list_resources()
async def list_resources() -> list[types.Resource]:
    return _ALL_RESOURCES


@server.read_resource()
async def read_resource(uri: str) -> str:
    async with httpx.AsyncClient() as client:

        if uri == "public://info":
            resp = await client.get(f"{API_BASE}/public")
            resp.raise_for_status()
            return resp.text

        elif uri == "protected://report":
            token = _require_oauth()
            resp = await client.get(
                f"{API_BASE}/report",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 401:
                raise AuthError(f"API rejected OAuth token: {resp.text}")
            resp.raise_for_status()
            return resp.text

        else:
            raise ValueError(f"Unknown resource: {uri}")


# ── ASGI handler ──────────────────────────────────────────────────────────────
async def handle_mcp(request: Request) -> Any:
    """
    1. Decode auth headers — fail fast before touching MCP machinery.
    2. Set ContextVars for this async task's context.
    3. Dispatch to the shared server via a per-request transport.
    4. Reset ContextVars unconditionally in finally.

    The transport is per-request because it represents one HTTP connection.
    The server is shared because it is stateless w.r.t. auth.
    """
    # ── 1. Parse and validate credentials ─────────────────────────────────────
    jwt_payload: dict | None = None
    jwt_raw: str | None = None
    oauth_token: str | None = None

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        raw = auth_header[len("Bearer "):]
        try:
            jwt_payload = _decode_jwt(raw)
            jwt_raw = raw
        except AuthError:
            # Not a valid JWT — treat as opaque OAuth token.
            oauth_token = raw

    x_oauth = request.headers.get("X-OAuth-Token")
    if x_oauth:
        oauth_token = x_oauth

    # ── 2. Bind to this task's context ────────────────────────────────────────
    t1 = _jwt_payload.set(jwt_payload)
    t2 = _jwt_raw.set(jwt_raw)
    t3 = _oauth_token.set(oauth_token)

    try:
        # ── 3. Dispatch ───────────────────────────────────────────────────────
        transport = StreamableHTTPServerTransport(
            mcp_session_id=request.headers.get("mcp-session-id"),
        )
        async with transport.connect() as streams:
            await server.run(*streams, server.create_initialization_options())
            return await transport.handle_request(request)

    except AuthError as exc:
        return JSONResponse({"error": exc.message}, status_code=exc.http_status)

    finally:
        # ── 4. Reset — belt-and-suspenders; task context isolation already
        #    ensures other tasks are unaffected, but explicit reset is correct.
        _jwt_payload.reset(t1)
        _jwt_raw.reset(t2)
        _oauth_token.reset(t3)


app = Starlette(routes=[Route("/mcp", handle_mcp, methods=["POST"])])
```

```
# ADK Agent + MCP Server — Auth & RBAC

## Install


pip install google-adk mcp fastapi uvicorn PyJWT httpx starlette


## Run

```bash
# Terminal 1 — Backend API
JWT_SECRET=dev-secret \
VALID_OAUTH_TOKENS=oauth-token-admin,oauth-token-user \
uvicorn api_server:app --port 8001

# Terminal 2 — MCP Server
JWT_SECRET=dev-secret \
VALID_OAUTH_TOKENS=oauth-token-admin,oauth-token-user \
uvicorn mcp_server:app --port 8000

# Terminal 3 — Agent (admin)
JWT_SECRET=dev-secret \
OAUTH_TOKEN=oauth-token-admin \
AGENT_ROLE=admin \
python agent.py

# Terminal 3 — Agent (user, RBAC test)
JWT_SECRET=dev-secret \
OAUTH_TOKEN=oauth-token-user \
AGENT_ROLE=user \
python agent.py
# admin_tool will NOT appear in visible tools — server never listed it.


---

## Design decisions

### Why server-side RBAC on `tools/list`?

Client-side filtering (dropping tool names after receiving the list) is
**security theater**: the tool was already disclosed. An attacker controlling
the agent process can call any listed tool directly. The only correct place
to enforce "this caller cannot know this tool exists" is inside the MCP
server's `tools/list` handler, before the response leaves the process.

### Transport: Streamable HTTP (not SSE)

The SSE-only transport (`/sse` + `/messages`) is the **2024-11-05 draft**
and is being removed. The current spec (2025-03-26) uses **Streamable HTTP**:
a single `POST /mcp` endpoint. ADK's `StreamableHTTPServerParams` speaks this
protocol. `SseServerParams` speaks the old draft — don't use it for new code.

### Per-request server instances

A new `Server()` is created for every HTTP request. This is intentional:
it scopes the decoded JWT payload and OAuth token to exactly one request,
eliminating any risk of credential bleed between concurrent requests.
There is no shared mutable auth state.

### Two auth schemes, one connection

| Header                          | Carries            | Used for                      |
|---------------------------------|--------------------|-------------------------------|
| `Authorization: Bearer <token>` | JWT                | identity + role               |
| `X-OAuth-Token: <token>`        | OAuth access token | resource `protected://report` |

The server tries to decode the `Authorization` bearer as a JWT first. If
decoding fails it treats it as an opaque OAuth token. `X-OAuth-Token`
explicitly disambiguates when both are needed simultaneously.

### Double enforcement on `admin_tool`

The tool is excluded from `tools/list` for non-admins **and** the `call_tool`
handler re-checks the role. Defense in depth: the second check catches any
future code path that bypasses list filtering.

### JWT forwarding — no storage

The MCP server never stores the JWT. It decodes it to extract the role for
`tools/list`, then forwards the original raw token string to the backend API
for all protected calls. The backend is the authoritative validator; the MCP
server is just a secure proxy.

```
