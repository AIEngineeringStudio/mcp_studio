"""Central registry of runnable lesson servers."""

from importlib import import_module

from mcp.server.mcpserver import MCPServer


LESSONS = {
    "hello": "mcp_apps_learning.lessons.register_tool_resource.server",
    "customer": "mcp_apps_learning.lessons.structured_data.server",
}


def load_server(lesson: str) -> MCPServer:
    """Import and return the server registered for a lesson name."""
    module = import_module(LESSONS[lesson])
    return module.mcp
