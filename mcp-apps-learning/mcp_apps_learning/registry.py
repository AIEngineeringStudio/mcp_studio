"""Central registry of runnable lesson servers."""

from importlib import import_module, util
from pathlib import Path

from mcp.server.mcpserver import MCPServer


LESSONS = {
    "hello": "mcp_apps_learning.lessons.register_tool_resource.server",
    "customer": "mcp_apps_learning.lessons.structured_data.server",
}


def load_server(lesson: str) -> MCPServer:
    """Import and return the server registered for a lesson name."""
    module = import_module(LESSONS[lesson])
    return module.mcp


def server_file(lesson: str) -> Path:
    """Return the source file for a registered lesson server."""
    module_name = LESSONS[lesson]
    spec = util.find_spec(module_name)
    if spec is None or spec.origin is None:
        raise RuntimeError(f"Cannot find the server file for lesson: {lesson}")
    return Path(spec.origin)


def project_root(lesson: str) -> Path:
    """Return the project directory containing a lesson server."""
    for directory in server_file(lesson).parents:
        if (directory / "pyproject.toml").is_file():
            return directory
    raise RuntimeError(f"Cannot find pyproject.toml for lesson: {lesson}")
