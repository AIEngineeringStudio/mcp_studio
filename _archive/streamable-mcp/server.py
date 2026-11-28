import secrets

from mcp.server import Server, ServerRequestContext

from mcp.server.request_state import (
    RequestStateBoundary,
    RequestStateSecurity,
)

from mcp.types import (
    Tool,
    TextContent,
    ListToolsResult,
    CallToolResult,
    InputRequiredResult,
    CallToolRequestParams,
    PaginatedRequestParams,
)

from tools.stream_numbers import stream_numbers

TOOLS = [
    Tool(
        name="stream_numbers",
        description="Stream numbered progress events.",
        input_schema={
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                }
            },
            "required": ["count"],
        },
    ),
]


async def list_tools(
        ctx: ServerRequestContext,
        params: PaginatedRequestParams | None,
) -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)


async def call_tool(
        ctx: ServerRequestContext,
        params: CallToolRequestParams,
) -> CallToolResult | InputRequiredResult:
    args = params.arguments or {}

    if ctx.protocol_version != "2026-07-28":
        return error("MCP 2026-07-28 is required.")

    if params.name == "stream_numbers":

        count = args.get("count")

        if type(count) is not int or not 1 <= count <= 20:
            return error("count must be an integer from 1–20.")

        return await stream_numbers(count, ctx)

    return error(f"Unknown tool: {params.name}")


def error(message: str) -> CallToolResult:
    return CallToolResult(
        is_error=True,
        content=[
            TextContent(type="text", text=message)
        ],
    )


server = Server(
    "streamable-demo",
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)

# Protect continuation state from client modification.

server.middleware.append(
    RequestStateBoundary(
        RequestStateSecurity(
            keys=[secrets.token_bytes(32)]
        ),
        default_audience=server.name,
    )
)

# Create the Streamable HTTP ASGI application.

app = server.streamable_http_app()