"""Replace a hidden roots dependency with an explicit project identifier."""

import asyncio

from fastmcp import Client, FastMCP


mcp = FastMCP("Explicit project scope")
PROJECT_FILES = {
    "P-100": ["README.md", "src/server.py"],
    "P-200": ["README.md", "src/client.py"],
}


@mcp.tool
def search_project(project_id: str, query: str) -> list[str]:
    """Search files in one server-known, authorized project."""
    files = PROJECT_FILES.get(project_id)
    if files is None:
        raise ValueError("Unknown or unauthorized project")
    return [path for path in files if query.casefold() in path.casefold()]


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        search = next(tool for tool in tools if tool.name == "search_project")
        properties = search.input_schema["properties"]
        assert set(properties) == {"project_id", "query"}
        result = await client.call_tool(
            "search_project",
            {"project_id": "P-100", "query": "server"},
        )
        assert result.data == ["src/server.py"]
        print("roots replacement: project_id and query are explicit tool inputs")
        print("result: ['src/server.py']")


if __name__ == "__main__":
    asyncio.run(main())
