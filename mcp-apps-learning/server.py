from mcp.server.apps import Apps
from mcp.server.mcpserver import MCPServer


VIEW_URI = "ui://hello/app.html"

VIEW_HTML = """\
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Hello MCP App</title>
</head>
<body>
    <h1>Hello from an MCP App</h1>
    <p>This HTML came from an MCP resource.</p>
</body>
</html>
"""


apps = Apps()


@apps.tool(
    resource_uri=VIEW_URI,
    description="Return a greeting and display its MCP App UI.",
)
def say_hello() -> str:
    return "Hello from the MCP tool."


apps.add_html_resource(
    VIEW_URI,
    VIEW_HTML,
    title="Hello MCP App",
)


mcp = MCPServer(
    "hello-mcp-app",
    extensions=[apps],
)