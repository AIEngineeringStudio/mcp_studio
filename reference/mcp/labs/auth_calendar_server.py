"""Calendar authorization lab with synthetic data and fake tokens.

This is a concept exercise, not an authorization server and not a real Google
or Microsoft calendar integration. It demonstrates four boundaries:

1. The MCP server publishes OAuth Protected Resource Metadata.
2. The MCP SDK validates a bearer token on every HTTP request.
3. The visible tool catalog depends on the validated token's scopes.
4. A separate credential broker creates a downstream calendar credential.

Run with:
    uv run python auth_calendar_server.py
"""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, InputRequiredResult


HOST = "127.0.0.1"
PORT = 8780
MCP_RESOURCE = f"http://{HOST}:{PORT}/mcp"
AUTHORIZATION_SERVER = "https://login.example.test"


# These are deliberately fake access tokens. A production verifier would
# validate a JWT against trusted keys or call an RFC 7662 introspection endpoint.
TOKEN_RECORDS = {
    "mcp-alice-read": {
        "client_id": "calendar-host",
        "subject": "alice@example.test",
        "scopes": ["calendar:read"],
    },
    "mcp-alice-write": {
        "client_id": "calendar-host",
        "subject": "alice@example.test",
        "scopes": ["calendar:read", "calendar:write"],
    },
    "mcp-bob-read": {
        "client_id": "calendar-host",
        "subject": "bob@example.test",
        "scopes": ["calendar:read"],
    },
}

TOOL_SCOPES = {
    "list_calendar_events": "calendar:read",
    "create_calendar_event": "calendar:write",
}


class StaticTokenVerifier:
    """Translate a fake bearer string into validated request identity."""

    async def verify_token(self, token: str) -> AccessToken | None:
        record = TOKEN_RECORDS.get(token)
        if record is None:
            return None
        return AccessToken(
            token=token,
            client_id=record["client_id"],
            subject=record["subject"],
            scopes=list(record["scopes"]),
            resource=MCP_RESOURCE,
        )


def current_token() -> AccessToken:
    """Return the SDK-validated token for the current HTTP request."""

    token = get_access_token()
    if token is None:
        raise ToolError("Authentication context is missing")
    return token


def permits(tool_name: str, token: AccessToken | None) -> bool:
    """Use one policy function for both visibility and execution."""

    required_scope = TOOL_SCOPES.get(tool_name)
    if required_scope is None:
        return True
    return token is not None and required_scope in set(token.scopes)


class AuthorizedCalendarServer(MCPServer):
    """Filter discovery and re-check the same policy during dispatch."""

    async def list_tools(self) -> list[Any]:
        token = get_access_token()
        tools = await super().list_tools()
        return [tool for tool in tools if permits(tool.name, token)]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: Context[Any, Any] | None = None,
    ) -> CallToolResult | InputRequiredResult:
        if not permits(name, get_access_token()):
            # Do not confirm that a hidden tool exists. The HTTP authorization
            # layer already authenticated the request; this is the authoritative
            # per-tool authorization check.
            raise ToolError(f"Unknown tool: {name}")
        return await super().call_tool(name, arguments, context)


class MockCalendarCredentialBroker:
    """Model an OBO or stored-consent exchange without contacting a provider."""

    def for_user(self, mcp_token: AccessToken, downstream_scope: str) -> str:
        if not mcp_token.subject:
            raise ToolError("A user identity is required for this calendar")
        if downstream_scope not in set(mcp_token.scopes):
            raise ToolError(f"Missing scope: {downstream_scope}")

        # Crucial boundary: this is a newly issued downstream credential. It is
        # not mcp_token.token and must have the Calendar API as its audience.
        return f"calendar-token-for:{mcp_token.subject}:{downstream_scope}"


class MockCalendarService:
    """Synthetic Calendar API that accepts only broker-issued credentials."""

    def __init__(self) -> None:
        self.events: dict[str, list[dict[str, str]]] = {
            "alice@example.test": [
                {
                    "id": "E-100",
                    "title": "Architecture review",
                    "start": "2026-11-20T10:00:00-07:00",
                }
            ],
            "bob@example.test": [
                {
                    "id": "E-200",
                    "title": "Customer call",
                    "start": "2026-11-20T13:00:00-07:00",
                }
            ],
        }

    @staticmethod
    def _assert_downstream_token(token: str, subject: str) -> None:
        expected_prefix = f"calendar-token-for:{subject}:"
        if not token.startswith(expected_prefix):
            raise ToolError("Calendar credential has the wrong audience")

    def list_events(self, subject: str, downstream_token: str) -> list[dict[str, str]]:
        self._assert_downstream_token(downstream_token, subject)
        return [dict(event) for event in self.events.get(subject, [])]

    def create_event(
        self,
        subject: str,
        downstream_token: str,
        title: str,
        start: str,
    ) -> dict[str, str]:
        self._assert_downstream_token(downstream_token, subject)
        event = {
            "id": f"E-{100 + len(self.events.setdefault(subject, []))}",
            "title": title,
            "start": start,
        }
        self.events[subject].append(event)
        return dict(event)


broker = MockCalendarCredentialBroker()
calendar = MockCalendarService()

mcp = AuthorizedCalendarServer(
    name="Calendar authorization lab",
    description="Synthetic calendar tools protected by per-request OAuth scopes",
    token_verifier=StaticTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AUTHORIZATION_SERVER,
        resource_server_url=MCP_RESOURCE,
        required_scopes=["calendar:read"],
        validate_token_resource=True,
    ),
)


@mcp.tool()
def list_calendar_events() -> list[dict[str, str]]:
    """List the signed-in user's events. Requires calendar:read."""

    mcp_token = current_token()
    downstream_token = broker.for_user(mcp_token, "calendar:read")
    assert downstream_token != mcp_token.token
    return calendar.list_events(mcp_token.subject or "", downstream_token)


@mcp.tool()
def create_calendar_event(title: str, start: str) -> dict[str, str]:
    """Create an event for the signed-in user. Requires calendar:write."""

    mcp_token = current_token()
    downstream_token = broker.for_user(mcp_token, "calendar:write")
    assert downstream_token != mcp_token.token
    return calendar.create_event(
        mcp_token.subject or "",
        downstream_token,
        title,
        start,
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=HOST, port=PORT)
