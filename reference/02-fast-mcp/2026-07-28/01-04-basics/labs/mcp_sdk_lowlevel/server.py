"""Ticket service using MCP SDK 2.3.0's low-level, handler-based Server API."""

import argparse
import asyncio
import json
from typing import Any

import uvicorn
from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    GetPromptRequestParams,
    GetPromptResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    ReadResourceRequestParams,
    ReadResourceResult,
    Resource,
    ResourceTemplate,
    TextResourceContents,
    TextContent,
    Tool,
)

TICKETS = {
    "T-100": {"id": "T-100", "title": "Cannot sign in", "status": "open"},
    "T-101": {
        "id": "T-101",
        "title": "Update contact address",
        "status": "closed",
    },
}


def lookup_ticket(ticket_id: str) -> dict[str, str]:
    """Domain function; deliberately independent of the protocol."""
    if ticket_id not in TICKETS:
        raise ValueError("Unknown ticket")
    return dict(TICKETS[ticket_id])


TOOLS = [
    Tool(
        name="get_ticket",
        description="Read a synthetic support ticket by ID. Does not change the ticket.",
        input_schema={
            "type": "object",
            "properties": {"ticket_id": {"type": "string"}},
            "required": ["ticket_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "title": {"type": "string"},
                "status": {"type": "string"},
            },
            "required": ["id", "title", "status"],
        },
    )
]

RESOURCES = [
    Resource(
        uri="tickets://closed",
        name="Closed tickets",
        description="The closed support tickets.",
        mime_type="application/json",
    )
]

RESOURCE_TEMPLATES = [
    ResourceTemplate(
        uri_template="ticket://{ticket_id}",
        name="Ticket by ID",
        description="Read a synthetic support ticket by ID.",
        mime_type="application/json",
    )
]

PROMPTS = [
    Prompt(
        name="summarize_ticket",
        description="Prepare instructions to summarize a support ticket.",
        arguments=[PromptArgument(name="ticket_id", required=True)],
    )
]


async def list_tools(
    ctx: ServerRequestContext[Any], params: Any
) -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)


async def call_tool(
    ctx: ServerRequestContext[Any], params: CallToolRequestParams
) -> CallToolResult:
    if params.name != "get_ticket":
        raise ValueError(f"Unknown tool: {params.name}")
    ticket_id = params.arguments.get("ticket_id")
    if not isinstance(ticket_id, str):
        raise ValueError("ticket_id must be a string")
    ticket = lookup_ticket(ticket_id)
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(ticket))],
        structured_content=ticket,
    )


async def list_resources(
    ctx: ServerRequestContext[Any], params: Any
) -> ListResourcesResult:
    return ListResourcesResult(resources=RESOURCES)


async def list_resource_templates(
    ctx: ServerRequestContext[Any], params: Any
) -> ListResourceTemplatesResult:
    return ListResourceTemplatesResult(resource_templates=RESOURCE_TEMPLATES)


async def read_resource(
    ctx: ServerRequestContext[Any], params: ReadResourceRequestParams
) -> ReadResourceResult:
    if str(params.uri) == "tickets://closed":
        value = [TICKETS["T-101"]]
    elif str(params.uri).startswith("ticket://"):
        value = lookup_ticket(str(params.uri).removeprefix("ticket://"))
    else:
        raise ValueError(f"Unknown resource: {params.uri}")
    return ReadResourceResult(
        contents=[
            TextResourceContents(
                uri=params.uri,
                mime_type="application/json",
                text=json.dumps(value),
            )
        ]
    )


async def list_prompts(
    ctx: ServerRequestContext[Any], params: Any
) -> ListPromptsResult:
    return ListPromptsResult(prompts=PROMPTS)


async def get_prompt(
    ctx: ServerRequestContext[Any], params: GetPromptRequestParams
) -> GetPromptResult:
    if params.name != "summarize_ticket":
        raise ValueError(f"Unknown prompt: {params.name}")
    ticket_id = (params.arguments or {}).get("ticket_id")
    if not ticket_id:
        raise ValueError("ticket_id is required")
    prompt_text = (
        f"Summarize ticket {ticket_id} using the provided ticket data. "
        "State its status and distinguish facts from missing information."
    )
    return GetPromptResult(
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=prompt_text),
            )
        ]
    )


server = Server(
    "Ticket learning service",
    version="2.3.0",
    on_list_tools=list_tools,
    on_call_tool=call_tool,
    on_list_resources=list_resources,
    on_list_resource_templates=list_resource_templates,
    on_read_resource=read_resource,
    on_list_prompts=list_prompts,
    on_get_prompt=get_prompt,
)


async def run_stdio() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run_http() -> None:
    app = server.streamable_http_app(streamable_http_path="/mcp")
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "http"], required=True)
    transport = parser.parse_args().transport
    if transport == "stdio":
        asyncio.run(run_stdio())
    else:
        run_http()
