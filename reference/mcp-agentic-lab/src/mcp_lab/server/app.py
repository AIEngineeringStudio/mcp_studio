"""A compact MCP server exposing tools, a resource, and a prompt."""

from pathlib import Path

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from mcp_lab.observability.config import Settings, get_settings
from mcp_lab.server.middleware import WireRecordingMiddleware
from mcp_lab.wire.recorder import JsonlWireRecorder


class Calculation(BaseModel):
    operation: str
    expression: str
    result: float


class Note(BaseModel):
    topic: str
    content: str


def create_server(
    settings: Settings | None = None,
    *,
    recorder: JsonlWireRecorder | None = None,
) -> MCPServer:
    settings = settings or get_settings()
    server_recorder = recorder or JsonlWireRecorder(
        Path("var/server-wire.jsonl"), enabled=settings.wire_log_enabled
    )
    server = MCPServer(
        "MCP Agentic Lab",
        version="0.1.0",
        instructions="Use the tools for arithmetic and note lookup practice.",
        middleware=[WireRecordingMiddleware(server_recorder, settings.server_transport)],
    )

    @server.tool(title="Add numbers")
    def add(
        a: float = Field(description="First number"),
        b: float = Field(description="Second number"),
    ) -> Calculation:
        """Add two numbers and return structured output."""

        return Calculation(operation="add", expression=f"{a} + {b}", result=a + b)

    @server.tool(title="Divide numbers")
    def divide(
        numerator: float,
        denominator: float,
    ) -> Calculation:
        """Divide two numbers. A zero denominator becomes a model-visible tool error."""

        if denominator == 0:
            raise ValueError("denominator must not be zero")
        return Calculation(
            operation="divide",
            expression=f"{numerator} / {denominator}",
            result=numerator / denominator,
        )

    @server.resource("notes://{topic}")
    def read_note(topic: str) -> Note:
        """Return a small learning note by topic."""

        notes = {
            "mcp": "MCP standardizes how hosts discover and invoke tools and context.",
            "json-rpc": "JSON-RPC uses request IDs to correlate requests and responses.",
            "tracing": "A trace connects work across client, transport, and server spans.",
        }
        return Note(topic=topic, content=notes.get(topic, "No note exists for this topic."))

    @server.prompt(title="Plan a tool-assisted task")
    def plan_task(goal: str) -> str:
        """Create a simple planning prompt for an agent."""

        return (
            f"Goal: {goal}\n"
            "List the smallest safe steps. Identify which MCP tool, if any, each step needs. "
            "Stop and ask before any irreversible action."
        )

    return server


# Importable entry point used by `mcp dev src/mcp_lab/server/app.py`.
mcp = create_server()
