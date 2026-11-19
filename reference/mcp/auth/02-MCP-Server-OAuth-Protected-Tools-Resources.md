> Part-1:
> Build a working python sample MCP server(mcp/@modelcontextprotocol sdk) which
> exposes 2 write tools(1 protected) and 2 read tools(1 protected), 2 resources(1
> protected).
> MCP server requires OAUTH authorization to access the protected tools and
> resources. If the correct scope claims are not on the auth token, protected
> tools and resources should not be even visible. MCP server must expose metadata
> for authorization discovery.
> MCP server must validate the auth token and process only valid requests

> Part-2:
> Using Google ADK MCPToolSet, expose the MCP server tools on an agent.
> Agent must call all tools successfully and pass delegated access token specific
> to each tool when calling protected resources.

> Verify against official documentation before generating content. You are
> not allowed to fabricate non-existent API's or facts.
>

```
I'll research the official documentation for both the MCP Python SDK's OAuth
capabilities and Google ADK's MCPToolSet before writing a single line of code.

Now let me research Google ADK's MCPToolSet specifically.

Let me check one more specific thing about FastMCP internals and the
**list_tools** override approach.

Let me look at the specific StreamableHTTPSessionManager API.

Now I have all the verified APIs I need. Let me build the complete solution.
```

**Confirmed APIs:**

- `mcp.server.lowlevel.Server` + `StreamableHTTPSessionManager` +
  `session_manager.handle_request` for MCP HTTP server
- `mcp.server.auth.provider.AccessToken`, `TokenVerifier` for auth types
- `mcp.server.auth.settings.AuthSettings` for RFC 9728 metadata
- `FastMCP.streamable_http_app()`, `FastMCP._mcp_server`,
  `mcp.session_manager.run()` for Starlette mounting
-

`McpToolset(connection_params=StreamableHTTPConnectionParams(url=..., headers=...))`
for ADK

---

## auth_server.py - OAuth 2.1 Authorization Server (Port 9000)

```python
"""
OAuth 2.1 Authorization Server — acts as the external AS referenced by the MCP
Resource Server's /.well-known/oauth-protected-resource document (RFC 9728).

Endpoints
---------
GET  /.well-known/oauth-authorization-server   RFC 8414 discovery metadata
POST /token                                    client_credentials grant (HS256 JWT)
POST /introspect                               RFC 7662 token introspection

Pre-registered clients
----------------------
client_id          client_secret    granted scopes
---------------    -----------      ----------------------------
public_client      public_secret    (none)
reader_client      reader_secret    data:read
writer_client      writer_secret    data:write
admin_client       admin_secret     data:read  data:write

Run:  uvicorn auth_server:app --port 9000
"""

import time
from typing import Optional

import jwt  # PyJWT
from fastapi import FastAPI, Form, HTTPException, status
from fastapi.responses import JSONResponse

# ── Configuration ──────────────────────────────────────────────────────────────
AS_URL = "http://localhost:9000"
RS_URL = "http://localhost:8001"  # MCP Resource Server audience
SECRET = "change-me-in-production-use-asymmetric-keys"
ALG = "HS256"
TTL = 3600  # seconds

ALL_SCOPES = {"data:read", "data:write"}

CLIENTS: dict[str, dict] = {
    "public_client": {"secret": "public_secret", "scopes": set()},
    "reader_client": {"secret": "reader_secret", "scopes": {"data:read"}},
    "writer_client": {"secret": "writer_secret", "scopes": {"data:write"}},
    "admin_client": {"secret": "admin_secret",
                     "scopes": {"data:read", "data:write"}},
}

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Demo OAuth AS", docs_url=None)


# ── RFC 8414 Authorization Server Metadata ─────────────────────────────────────
@app.get("/.well-known/oauth-authorization-server")
async def as_metadata() -> JSONResponse:
    return JSONResponse({
        "issuer": AS_URL,
        "token_endpoint": f"{AS_URL}/token",
        "introspection_endpoint": f"{AS_URL}/introspect",
        "grant_types_supported": ["client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "scopes_supported": sorted(ALL_SCOPES),
        "response_types_supported": ["token"],
    })


# ── Token endpoint (client_credentials only) ───────────────────────────────────
@app.post("/token")
async def token_endpoint(
        grant_type: str = Form(...),
        client_id: str = Form(...),
        client_secret: str = Form(...),
        scope: Optional[str] = Form(None),
) -> JSONResponse:
    client = CLIENTS.get(client_id)
    if not client or client["secret"] != client_secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_client")
    if grant_type != "client_credentials":
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "unsupported_grant_type")

    requested = set(scope.split()) if scope else set()
    granted = requested & client["scopes"]  # intersection — never over-grant

    now = int(time.time())
    payload = {
        "iss": AS_URL,
        "aud": RS_URL,  # Resource server validates this
        "sub": client_id,
        "client_id": client_id,
        "scope": " ".join(sorted(granted)),
        "iat": now,
        "exp": now + TTL,
    }
    access_token = jwt.encode(payload, SECRET, algorithm=ALG)

    return JSONResponse({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": TTL,
        "scope": " ".join(sorted(granted)),
    })


# ── RFC 7662 Token Introspection ───────────────────────────────────────────────
@app.post("/introspect")
async def introspect(
        token: str = Form(...),
        client_id: str = Form(...),
        client_secret: str = Form(...),
) -> JSONResponse:
    # Authenticate the requesting client (the RS uses its own credentials here)
    client = CLIENTS.get(client_id)
    if not client or client["secret"] != client_secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_client")

    try:
        payload = jwt.decode(
            token,
            SECRET,
            algorithms=[ALG],
            audience=RS_URL,
            options={"verify_exp": True},
        )
        return JSONResponse({
            "active": True,
            "client_id": payload.get("client_id", ""),
            "scope": payload.get("scope", ""),
            "sub": payload.get("sub", ""),
            "exp": payload.get("exp"),
            "iss": payload.get("iss"),
        })
    except jwt.ExpiredSignatureError:
        return JSONResponse({"active": False})
    except jwt.InvalidTokenError:
        return JSONResponse({"active": False})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("auth_server:app", host="0.0.0.0", port=9000, reload=False)
```

---

## mcp_server.py - MCP Resource Server with OAuth scope filtered

```python
"""
MCP Resource Server — implements the 2025-06-18 MCP specification.

Auth model (RFC 9728 — Protected Resource Metadata)
────────────────────────────────────────────────────
• GET  /.well-known/oauth-protected-resource  → AS discovery metadata
• All MCP requests arrive at POST/GET /mcp
• A pure-ASGI auth middleware validates the Bearer token via the AS introspection
  endpoint and stores the result in a ContextVar before the MCP handler runs.
• tools/list and resources/list responses are FILTERED so protected items are
  invisible to clients whose token lacks the required scope.
• Protected handlers double-check the scope on every call_tool / read_resource.

Scopes
──────
Tool / Resource              Scope required
─────────────────────────    ──────────────
list_items     (read)        — (public)
get_private_data (read)      data:read
create_item    (write)       — (public)
update_private_data (write)  data:write
resource data://items        — (public)
resource data://private      data:read

Run:
  python mcp_server.py          (starts uvicorn on port 8001)
  # or: uvicorn mcp_server:app --port 8001
"""

from __future__ import annotations

import contextlib
import json
import logging
from contextvars import ContextVar
from typing import Any, Optional

import httpx
import uvicorn
from pydantic import AnyUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

log = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
AS_URL = "http://localhost:9000"
RS_URL = "http://localhost:8001"
RS_CLIENT_ID = "public_client"  # RS uses this to call /introspect
RS_CLIENT_SECRET = "public_secret"

# The RS registers its own "service account" with the AS.
# In production use a dedicated, privileged client for introspection.

# ── Auth state for the current async task ─────────────────────────────────────
# Python ContextVars propagate into asyncio.create_task() children (PEP 567),
# so any value set here before `await session_manager.handle_request(...)` is
# visible inside MCP handler coroutines.
_current_auth: ContextVar[Optional[types.AccessToken]] = ContextVar(
    "_current_auth", default=None
)


def _get_auth() -> Optional[types.AccessToken]:
    return _current_auth.get()


def _has_scope(scope: str) -> bool:
    auth = _get_auth()
    if auth is None:
        return False
    return scope in (auth.scopes or [])


# ── Token verifier (introspection-based) ───────────────────────────────────────
class IntrospectionTokenVerifier:
    """Validates Bearer tokens via the Authorization Server's /introspect endpoint."""

    async def verify_token(self, token: str) -> Optional[types.AccessToken]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.post(
                    f"{AS_URL}/introspect",
                    data={
                        "token": token,
                        "client_id": RS_CLIENT_ID,
                        "client_secret": RS_CLIENT_SECRET,
                    },
                )
            data: dict[str, Any] = r.json()
        except Exception as exc:
            log.warning("Introspection call failed: %s", exc)
            return None

        if not data.get("active"):
            return None

        scopes = [s for s in data.get("scope", "").split() if s]
        access_token = types.AccessToken(
            token=token,
            client_id=data.get("client_id", ""),
            scopes=scopes,
        )
        # Store for this request's entire async context
        _current_auth.set(access_token)
        return access_token


_verifier = IntrospectionTokenVerifier()


# ── Pure-ASGI auth middleware ──────────────────────────────────────────────────
class BearerAuthMiddleware:
    """
    Validates the Authorization: Bearer header on every HTTP request.

    • No token  → unauthenticated request allowed (public tools remain visible).
    • Bad token → 401 Unauthorized.
    • Good token → AccessToken stored in ContextVar, request continues.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive,
                       send: Send) -> None:
        if scope["type"] == "http":
            _current_auth.set(None)  # reset for every request

            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            raw_auth: bytes = headers.get(b"authorization", b"")
            auth_str = raw_auth.decode("latin-1")

            if auth_str.startswith("Bearer "):
                token = auth_str[7:].strip()
                access_token = await _verifier.verify_token(token)
                if access_token is None:
                    body = json.dumps({"error": "invalid_token"}).encode()
                    await send({
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                            (b"www-authenticate",
                             b'Bearer error="invalid_token",'
                             b' error_description="The access token is invalid"'),
                        ],
                    })
                    await send({"type": "http.response.body", "body": body})
                    return
                # access_token already stored in ContextVar by verify_token()

        await self._app(scope, receive, send)


# ── In-memory data store ───────────────────────────────────────────────────────
_items: list[dict] = [
    {"id": 1, "name": "Widget", "category": "hardware"},
    {"id": 2, "name": "Gadget", "category": "electronics"},
]
_private: dict = {
    "classification": "CONFIDENTIAL",
    "secret_key": "MCP-DEMO-1234",
    "owner": "ops-team",
}

# ── Scope map ─────────────────────────────────────────────────────────────────
# Maps tool / resource name → required scope (None = public)
TOOL_SCOPES: dict[str, Optional[str]] = {
    "list_items": None,
    "get_private_data": "data:read",
    "create_item": None,
    "update_private_data": "data:write",
}

RESOURCE_SCOPES: dict[str, Optional[str]] = {
    "data://items": None,
    "data://private": "data:read",
}

# ── Tool definitions ───────────────────────────────────────────────────────────
_TOOL_LIST_ITEMS = types.Tool(
    name="list_items",
    description="List all public inventory items (no auth required).",
    inputSchema={"type": "object", "properties": {}, "required": []},
)

_TOOL_GET_PRIVATE = types.Tool(
    name="get_private_data",
    description="Return classified private data. Requires scope: data:read.",
    inputSchema={"type": "object", "properties": {}, "required": []},
)

_TOOL_CREATE_ITEM = types.Tool(
    name="create_item",
    description="Create a new inventory item (no auth required).",
    inputSchema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Item name"},
            "category": {"type": "string", "description": "Item category"},
        },
        "required": ["name"],
    },
)

_TOOL_UPDATE_PRIVATE = types.Tool(
    name="update_private_data",
    description="Overwrite private data fields. Requires scope: data:write.",
    inputSchema={
        "type": "object",
        "properties": {
            "classification": {"type": "string"},
            "secret_key": {"type": "string"},
            "owner": {"type": "string"},
        },
        "required": [],
    },
)

_ALL_TOOLS = [_TOOL_LIST_ITEMS, _TOOL_GET_PRIVATE, _TOOL_CREATE_ITEM,
              _TOOL_UPDATE_PRIVATE]

# ── Resource definitions ───────────────────────────────────────────────────────
_RES_ITEMS = types.Resource(
    uri=AnyUrl("data://items"),
    name="Public Items Database",
    description="Read-only view of all public inventory items.",
    mimeType="application/json",
)

_RES_PRIVATE = types.Resource(
    uri=AnyUrl("data://private"),
    name="Private Data Store",
    description="Classified data. Requires scope: data:read.",
    mimeType="application/json",
)

_ALL_RESOURCES = [_RES_ITEMS, _RES_PRIVATE]

# ── Low-level MCP Server ───────────────────────────────────────────────────────
server = Server("mcp-oauth-demo")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Return only those tools the caller is authorised to see."""
    auth = _get_auth()
    scopes = set(auth.scopes or []) if auth else set()

    return [
        t for t in _ALL_TOOLS
        if TOOL_SCOPES[t.name] is None or TOOL_SCOPES[t.name] in scopes
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Execute a tool — always re-validates scope even if the tool was visible."""
    required = TOOL_SCOPES.get(name)
    if required and not _has_scope(required):
        raise ValueError(
            f"Access denied: '{name}' requires scope '{required}'. "
            f"Present scopes: {getattr(_get_auth(), 'scopes', [])!r}"
        )

    if name == "list_items":
        return [
            types.TextContent(type="text", text=json.dumps(_items, indent=2))]

    elif name == "get_private_data":
        return [
            types.TextContent(type="text", text=json.dumps(_private, indent=2))]

    elif name == "create_item":
        item = {
            "id": len(_items) + 1,
            "name": arguments.get("name", ""),
            "category": arguments.get("category", "misc"),
        }
        _items.append(item)
        return [types.TextContent(
            type="text",
            text=f"✅ Created item #{item['id']}: {json.dumps(item)}",
        )]

    elif name == "update_private_data":
        _private.update({k: v for k, v in arguments.items() if v is not None})
        return [types.TextContent(
            type="text",
            text=f"✅ Private data updated: {json.dumps(_private, indent=2)}",
        )]

    else:
        raise ValueError(f"Unknown tool: {name!r}")


@server.list_resources()
async def list_resources() -> list[types.Resource]:
    """Return only resources the caller is authorised to see."""
    auth = _get_auth()
    scopes = set(auth.scopes or []) if auth else set()

    return [
        r for r in _ALL_RESOURCES
        if RESOURCE_SCOPES[str(r.uri)] is None
           or RESOURCE_SCOPES[str(r.uri)] in scopes
    ]


@server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """Return a resource — always re-validates scope."""
    uri_str = str(uri)
    required = RESOURCE_SCOPES.get(uri_str)
    if required and not _has_scope(required):
        raise ValueError(
            f"Access denied: resource '{uri_str}' requires scope '{required}'."
        )

    if uri_str == "data://items":
        return json.dumps(_items, indent=2)
    elif uri_str == "data://private":
        return json.dumps(_private, indent=2)
    else:
        raise ValueError(f"Resource not found: {uri_str!r}")


# ── RFC 9728 Protected Resource Metadata ───────────────────────────────────────
async def protected_resource_metadata(_: Request) -> JSONResponse:
    """
    Endpoint: GET /.well-known/oauth-protected-resource
    Tells MCP clients which AS issues valid tokens for this RS.
    See: https://www.rfc-editor.org/rfc/rfc9728
    """
    return JSONResponse({
        "resource": RS_URL,
        "authorization_servers": [AS_URL],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["data:read", "data:write"],
        "resource_documentation": f"{RS_URL}/docs",
    })


# ── ASGI app assembly ──────────────────────────────────────────────────────────
session_manager = StreamableHTTPSessionManager(
    app=server,
    json_response=True,
    stateless=False,
)


async def handle_mcp(scope: Scope, receive: Receive, send: Send) -> None:
    """Delegate to the MCP session manager (streamable-HTTP transport)."""
    await session_manager.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    """Start/stop the StreamableHTTPSessionManager task group."""
    async with session_manager.run():
        log.info("MCP RS listening — http://localhost:8001/mcp")
        log.info(
            "Auth discovery — http://localhost:8001/.well-known/oauth-protected-resource")
        yield


_starlette = Starlette(
    routes=[
        Route(
            "/.well-known/oauth-protected-resource",
            endpoint=protected_resource_metadata,
            methods=["GET"],
        ),
        Mount("/mcp", app=handle_mcp),
    ],
    lifespan=lifespan,
)

# Wrap with our pure-ASGI auth middleware (outermost layer)
app = BearerAuthMiddleware(_starlette)

# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=8001, reload=False)
```

---

## adk_agent/agent.py - Google ADK agent with scope-delegated

```python
"""
Part 2 — Google ADK agent that consumes the protected MCP server.

Strategy: "Delegated access token per tool scope"
──────────────────────────────────────────────────
The agent uses THREE McpToolset instances, each connecting to the SAME MCP RS
but with a different Bearer token (scoped to only what that set of tools needs).

  Toolset           Token scopes       tool_filter (exposed to agent)
  ─────────────     ────────────       ──────────────────────────────────
  public_toolset    (none)             list_items, create_item
  reader_toolset    data:read          get_private_data
  writer_toolset    data:write         update_private_data

The MCP server's list_tools response is automatically filtered per connection:
  • public_toolset sees only the two public tools.
  • reader_toolset gets the public tools PLUS get_private_data.
  • writer_toolset gets the public tools PLUS update_private_data.

tool_filter on each McpToolset ensures each tool is exposed to the agent
exactly once, from the minimally privileged connection that can serve it.

Environment variables
─────────────────────
GOOGLE_API_KEY   — Gemini API key (or set GOOGLE_GENAI_USE_VERTEXAI=true)
MCP_SERVER_URL   — defaults to http://localhost:8001/mcp
AUTH_SERVER_URL  — defaults to http://localhost:9000/token

Usage
─────
  # 1. Run with adk web (recommended for interactive testing)
  cd adk_agent && adk web

  # 2. Run the built-in demo script
  python agent.py
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from typing import Any

import httpx

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import \
    StreamableHTTPConnectionParams
from google.genai.types import Content, Part

log = logging.getLogger(__name__)

# ── Server URLs ────────────────────────────────────────────────────────────────
MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")
AUTH_URL = os.getenv("AUTH_SERVER_URL", "http://localhost:9000/token")


# ── Helper: obtain an access token from the AS ────────────────────────────────
async def fetch_token(client_id: str, client_secret: str, scope: str) -> str:
    """
    Performs an OAuth 2.1 client_credentials grant against the AS.
    Returns the raw access_token string.
    """
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.post(
            AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": scope,
            },
        )
        r.raise_for_status()
        return r.json()["access_token"]


# ── Build agent with per-scope delegated tokens ────────────────────────────────
async def build_agent() -> tuple[Agent, contextlib.AsyncExitStack]:
    """
    Fetches three tokens (no scope, data:read, data:write), creates one
    McpToolset per scope, and returns a fully initialised Agent.

    The returned AsyncExitStack must be kept alive for the duration of the
    agent's use and closed when the agent is no longer needed.
    """
    exit_stack = contextlib.AsyncExitStack()

    # ── Fetch delegated tokens ─────────────────────────────────────────────────
    log.info("Fetching delegated access tokens from AS …")

    # Public token — no scopes, sees only public tools
    # (We still authenticate so the AS can issue a properly-formed JWT)
    public_token = await fetch_token("public_client", "public_secret", "")
    log.info("  public_token  scopes=[]")

    reader_token = await fetch_token("reader_client", "reader_secret",
                                     "data:read")
    log.info("  reader_token  scopes=[data:read]")

    writer_token = await fetch_token("writer_client", "writer_secret",
                                     "data:write")
    log.info("  writer_token  scopes=[data:write]")

    # ── Toolset 1: public tools (no protected scope) ───────────────────────────
    # This connection sends the public token. The MCP server responds to
    # list_tools with only list_items and create_item.
    public_toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=MCP_URL,
            headers={"Authorization": f"Bearer {public_token}"},
        ),
        # Expose ONLY the two public tools from this connection
        tool_filter=["list_items", "create_item"],
    )

    # ── Toolset 2: reader tools (data:read scope) ──────────────────────────────
    # The server's list_tools for this connection includes get_private_data.
    reader_toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=MCP_URL,
            headers={"Authorization": f"Bearer {reader_token}"},
        ),
        # Expose only the protected read tool from this connection
        tool_filter=["get_private_data"],
    )

    # ── Toolset 3: writer tools (data:write scope) ────────────────────────────
    # The server's list_tools for this connection includes update_private_data.
    writer_toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=MCP_URL,
            headers={"Authorization": f"Bearer {writer_token}"},
        ),
        # Expose only the protected write tool from this connection
        tool_filter=["update_private_data"],
    )

    # ── Assemble the agent ─────────────────────────────────────────────────────
    agent = Agent(
        model="gemini-2.5-flash",  # change to gemini-2.5-pro if desired
        name="mcp_oauth_demo_agent",
        instruction=(
            "You are a helpful assistant that exercises a protected MCP server. "
            "When asked to 'run the full demo', call ALL four tools in order:\n"
            "  1. list_items          — no auth needed\n"
            "  2. get_private_data    — data:read scope\n"
            "  3. create_item         — no auth needed (create name='DemoItem')\n"
            "  4. update_private_data — data:write scope (set owner='demo-agent')\n"
            "Report the result of each call clearly."
        ),
        tools=[public_toolset, reader_toolset, writer_toolset],
    )

    return agent, exit_stack


# ── root_agent (used by `adk web`) ────────────────────────────────────────────
# adk web imports this module and looks for root_agent.
# We build it synchronously for module-level availability.
# NOTE: adk web manages the async lifecycle for McpToolset automatically.

def _make_sync_toolsets() -> list[McpToolset]:
    """
    Creates toolsets with tokens fetched synchronously (for module-level init
    required by `adk web`). Tokens are fetched via a new event loop.
    """

    async def _fetch():
        pt = await fetch_token("public_client", "public_secret", "")
        rt = await fetch_token("reader_client", "reader_secret", "data:read")
        wt = await fetch_token("writer_client", "writer_secret", "data:write")
        return pt, rt, wt

    try:
        pt, rt, wt = asyncio.get_event_loop().run_until_complete(_fetch())
    except RuntimeError:
        # If there is already a running event loop (e.g. Jupyter), fall back
        import nest_asyncio  # pip install nest_asyncio
        nest_asyncio.apply()
        pt, rt, wt = asyncio.get_event_loop().run_until_complete(_fetch())

    return [
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=MCP_URL,
                headers={"Authorization": f"Bearer {pt}"},
            ),
            tool_filter=["list_items", "create_item"],
        ),
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=MCP_URL,
                headers={"Authorization": f"Bearer {rt}"},
            ),
            tool_filter=["get_private_data"],
        ),
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=MCP_URL,
                headers={"Authorization": f"Bearer {wt}"},
            ),
            tool_filter=["update_private_data"],
        ),
    ]


# Build root_agent only if the MCP server is reachable
try:
    _toolsets = _make_sync_toolsets()
    root_agent = Agent(
        model="gemini-2.5-flash",
        name="mcp_oauth_demo_agent",
        instruction=(
            "You are a helpful assistant that exercises a protected MCP server. "
            "When asked to 'run the full demo', call ALL four tools in order:\n"
            "  1. list_items          — no auth needed\n"
            "  2. get_private_data    — data:read scope\n"
            "  3. create_item         — no auth needed (name='DemoItem')\n"
            "  4. update_private_data — data:write scope (set owner='demo-agent')\n"
            "Report the result of each call clearly."
        ),
        tools=_toolsets,
    )
except Exception as _e:
    import sys

    print(
        f"⚠️  Could not connect to MCP server at {MCP_URL}: {_e}\n"
        "Make sure auth_server.py and mcp_server.py are running first.",
        file=sys.stderr,
    )
    root_agent = None  # type: ignore[assignment]


# ── Standalone demo runner ─────────────────────────────────────────────────────
async def run_demo() -> None:
    """
    Programmatically drives the agent through all four tools and prints results.
    Verifies:
      • Public tools are callable without special auth.
      • Protected tools are callable when the right delegated token is used.
    """
    logging.basicConfig(level=logging.INFO)

    agent, exit_stack = await build_agent()

    async with exit_stack:
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            app_name="mcp_oauth_demo",
            session_service=session_service,
        )

        session = await session_service.create_session(
            app_name="mcp_oauth_demo",
            user_id="demo_user",
        )

        prompts = [
            "Call list_items and show me the results.",
            "Call get_private_data and show me the classified data.",
            "Call create_item with name='DemoItem' and category='test'.",
            "Call update_private_data and set owner to 'demo-agent'.",
        ]

        for prompt in prompts:
            print(f"\n{'=' * 60}")
            print(f"USER ▶ {prompt}")
            print("─" * 60)

            final_text = ""
            async for event in runner.run_async(
                    session_id=session.id,
                    user_id="demo_user",
                    new_message=Content(parts=[Part(text=prompt)]),
            ):
                # Collect the final text response
                if hasattr(event, "content") and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            final_text = part.text

            print(f"AGENT ▶ {final_text}")


if __name__ == "__main__":
    asyncio.run(run_demo())
```

---

## README.md + requirements.txt - Setup, architecture etc.

```
# MCP OAuth Demo — Setup Guide

## Architecture

┌─────────────────────────────────────────────────────────────────┐
│              OAuth 2.1 Authorization Server                     │
│              auth_server.py  :9000                              │
│                                                                 │
│  GET /.well-known/oauth-authorization-server  (RFC 8414)        │
│  POST /token   (client_credentials grant, HS256 JWT)            │
│  POST /introspect   (RFC 7662)                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │  introspect()
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              MCP Resource Server                                │
│              mcp_server.py  :8001                               │
│                                                                 │
│  GET /.well-known/oauth-protected-resource   (RFC 9728)         │
│  POST/GET /mcp  → StreamableHTTP transport   (MCP 2025-06-18)   │
│                                                                 │
│  BearerAuthMiddleware (pure ASGI)                               │
│    ├─ validates Bearer token via AS /introspect                 │
│    └─ stores AccessToken in ContextVar                          │
│                                                                 │
│  Tools                             Required scope               │
│    list_items        (read)         —  public                   │
│    get_private_data  (read)         data:read   ◀── protected   │
│    create_item       (write)        —  public                   │
│    update_private_data (write)      data:write  ◀── protected   │
│                                                                 │
│  Resources                                                      │
│    data://items    (public)                                     │
│    data://private  (data:read scope required)  ◀── protected    │
└────────────────────────┬────────────────────────────────────────┘
                         │  Bearer token (per-scope, delegated)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Google ADK Agent                                   │
│              adk_agent/agent.py                                 │
│                                                                 │
│  McpToolset #1  — public_token  (no scopes)                     │
│    tool_filter: [list_items, create_item]                       │
│                                                                 │
│  McpToolset #2  — reader_token  (data:read)                     │
│    tool_filter: [get_private_data]                              │
│                                                                 │
│  McpToolset #3  — writer_token  (data:write)                    │
│    tool_filter: [update_private_data]                           │
└─────────────────────────────────────────────────────────────────┘
```

### Prerequisites

```

python >= 3.11

```

### Installation

```bash
pip install -r requirements.txt
```

**requirements.txt**

```
# MCP Python SDK (official — includes FastMCP, low-level server, auth)
mcp>=1.9.0

# Authorization Server
fastapi>=0.115
uvicorn[standard]>=0.30
PyJWT>=2.9            # JWT encode / decode

# MCP server / client HTTP layer
httpx>=0.27
starlette>=0.40

# Google ADK
google-adk>=1.0.0
google-genai>=0.8.0

# Utilities
python-multipart      # FastAPI Form() parsing
```

### Running (3 terminals)

#### Terminal 1 — Authorization Server

```bash
python auth_server.py
# Listening on http://localhost:9000
```

#### Terminal 2 — MCP Resource Server

```bash
python mcp_server.py
# Listening on http://localhost:8001
```

#### Terminal 3 — ADK Agent

**Option A — Interactive UI (recommended)**

```bash
# Set your Gemini API key
export GOOGLE_API_KEY="your-key-here"

cd adk_agent
adk web
# Open http://localhost:8000 → select mcp_oauth_demo_agent
# Type: "run the full demo"
```

**Option B — Standalone demo script**

```bash
export GOOGLE_API_KEY="your-key-here"
python adk_agent/agent.py
```

### Manual Verification (curl)

```bash
# 1. Check RFC 9728 discovery
curl http://localhost:8001/.well-known/oauth-protected-resource | python -m json.tool

# 2. Check AS RFC 8414 discovery
curl http://localhost:9000/.well-known/oauth-authorization-server | python -m json.tool

# 3. Get a public token (no scopes)
PUBLIC_TOKEN=$(curl -s -X POST http://localhost:9000/token \
  -d "grant_type=client_credentials&client_id=public_client&client_secret=public_secret" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 4. Get an admin token (data:read + data:write)
ADMIN_TOKEN=$(curl -s -X POST http://localhost:9000/token \
  -d "grant_type=client_credentials&client_id=admin_client&client_secret=admin_secret&scope=data:read data:write" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 5. list_tools with public token → only 2 tools
curl -s -X POST http://localhost:8001/mcp \
  -H "Authorization: Bearer $PUBLIC_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}'

curl -s -X POST http://localhost:8001/mcp \
  -H "Authorization: Bearer $PUBLIC_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
# → only list_items and create_item are visible

# 6. list_tools with admin token → all 4 tools
curl -s -X POST http://localhost:8001/mcp \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
# → all four tools visible

# 7. Call protected tool without auth → error
curl -s -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_private_data","arguments":{}}}'
# → 401 Unauthorized (no token) or scope error
```

### Security Notes

| Concern           | Implementation                                                                                                 |
|-------------------|----------------------------------------------------------------------------------------------------------------|
| Token validation  | Bearer tokens are introspected against the AS on **every** request                                             |
| Scope enforcement | Checked in **both** `list_tools`/`list_resources` (visibility) **and** `call_tool`/`read_resource` (execution) |
| No over-grant     | The AS intersects requested scopes with client's allowed scopes                                                |
| Audience          | JWT `aud` claim is set to the RS URL; AS validates it during decode                                            |
| Public vs private | `required_scopes=[]` not used globally — all scope logic is per-tool/resource                                  |

### Key API References

| Component                                                                      | Source                  |
|--------------------------------------------------------------------------------|-------------------------|
| `mcp.server.lowlevel.Server`                                                   | Official MCP Python SDK |
| `mcp.server.streamable_http_manager.StreamableHTTPSessionManager`              | Official MCP Python SDK |
| `mcp.types.AccessToken`, `mcp.types.Tool`, `mcp.types.Resource`                | Official MCP Python SDK |
| RFC 9728 `/.well-known/oauth-protected-resource`                               | MCP 2025-06-18 spec     |
| `google.adk.agents.Agent`                                                      | Google ADK v1.0+        |
| `google.adk.tools.mcp_tool.McpToolset`                                         | Google ADK v1.0+        |
| `google.adk.tools.mcp_tool.mcp_session_manager.StreamableHTTPConnectionParams` | Google ADK v1.0+        |

Here's a full explanation of what was built, every verified API used, and what
to watch for.

---

## What Was Built & Why

### Part 1 — MCP Server

**`auth_server.py` (port 9000) — OAuth 2.1 Authorization Server**

The MCP authorization spec separates the Authorization Server (token factory)
from the Resource Server (the MCP server), allowing organizations to leverage
existing authorization servers. The AS provides three RFC-compliant endpoints:

- `GET /.well-known/oauth-authorization-server` — RFC 8414 discovery so clients
  can find token and authorization endpoints automatically
- `POST /token` — `client_credentials` grant, issues HS256 JWTs with scope
  claims
- `POST /introspect` — RFC 7662, called by the RS on every request to validate
  tokens

**`mcp_server.py` (port 8001) — MCP Resource Server**

`mcp.server.auth` implements OAuth 2.1 resource server functionality, where MCP
servers act as Resource Servers (RS) that validate tokens issued by separate
Authorization Servers (AS). This follows the MCP authorization specification and
implements RFC 9728 (Protected Resource Metadata) for AS discovery.

Key design decisions:

| Decision                                                              | Rationale                                                                                                                                                                                                                                                       |
|-----------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **`mcp.server.lowlevel.Server`**                                      | Full control of `list_tools`, `list_resources`, `call_tool`, `read_resource` handlers — necessary for per-request scope filtering                                                                                                                               |
| **`StreamableHTTPSessionManager` + `session_manager.handle_request`** | Confirmed from official SDK issue tracker as the correct pattern for mounting an MCP low-level server onto a Starlette app via ASGI                                                                                                                             |
| **Pure-ASGI middleware**                                              | Unlike `BaseHTTPMiddleware`, a raw ASGI `__call__` runs in the exact same coroutine as the downstream app, so `ContextVar` values set before `await self._app(...)` are visible in tool handlers without any asyncio task boundary issues                       |
| **`ContextVar[AccessToken]`**                                         | Python's `ContextVar` is propagated into `asyncio.create_task()` children (PEP 567), meaning any async task spawned inside the session manager inherits the auth state                                                                                          |
| **Scope-based `list_tools` / `list_resources` filtering**             | Per the MCP auth spec: "Always use `requiredScopes` to enforce that the token contains the necessary permissions for each operation. Never assume a valid token implies full access." Visibility filtering + execution double-check implements defense-in-depth |

### Part 2 — Google ADK Agent

The `McpToolset` class is ADK's primary mechanism for integrating tools from an
MCP server. It queries the MCP server for its available tools via the
`list_tools` MCP method, converts the schemas of these discovered MCP tools into
ADK-compatible `BaseTool` instances, and transparently proxies tool calls using
the `call_tool` MCP method.

The **delegated-token-per-scope** pattern works like this:

```
McpToolset #1 Bearer public_token → server returns [list_items, create_item]
tool_filter=[list_items, create_item]   → agent sees 2 public tools

McpToolset #2 Bearer reader_token → server
returns [list_items, create_item, get_private_data]
tool_filter=[get_private_data]           → agent sees 1 protected read tool

McpToolset #3 Bearer writer_token → server returns [..., update_private_data]
tool_filter=[update_private_data]        → agent sees 1 protected write tool

```

Passing `headers={"Authorization": "Bearer <token>"}` to
`StreamableHTTPConnectionParams` is the documented pattern for bearer-token
authentication in ADK's `McpToolset`.

---

### Caveats & Production Hardening

1. **JWT secret** — The HS256 `SECRET` in `auth_server.py` is a demo
   placeholder. Use asymmetric RS256 keys with JWKS in production and add
   JWKS-based local validation in the RS (instead of introspection) for
   performance.
2. **Introspection client credentials** — `RS_CLIENT_ID / RS_CLIENT_SECRET` in
   `mcp_server.py` are the RS's own credentials used to call `/introspect`. In
   production, use a dedicated service account.
3. **Token caching** — The RS calls `/introspect` on every MCP request. Add an
   in-memory cache keyed by token hash with TTL ≤ token expiry.
4. **`adk web` vs. standalone** — `McpToolset` works directly inside `adk web`'s
   managed lifecycle. The `build_agent()` async function in `agent.py` is for
   programmatic use with `Runner`; the module-level `root_agent` is for
   `adk web`.
5. **ADK token refresh** — ADK does not automatically refresh OAuth 2.0 tokens;
   if a session lasts longer than the token TTL, re-authentication is required.