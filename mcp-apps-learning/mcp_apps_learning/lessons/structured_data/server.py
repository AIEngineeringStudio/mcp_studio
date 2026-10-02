from mcp.server.apps import Apps
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel


VIEW_URI = "ui://customer/app.html"

VIEW_HTML = """\
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Customer</title>
</head>
<body>
    <h1>Customer MCP App</h1>
</body>
</html>
"""


class Customer(BaseModel):
    name: str
    company: str
    email: str


apps = Apps()


@apps.tool(
    resource_uri=VIEW_URI,
    description="Return a greeting and display its MCP App UI.",
)
def get_customer() -> Customer:
    return Customer(
        name="Alice",
        company="Acme",
        email="alice@acme.com",
    )


apps.add_html_resource(
    VIEW_URI,
    VIEW_HTML,
    title="Customer MCP App",
)


mcp = MCPServer("customer-mcp-app", extensions=[apps])


def main() -> None:
    """Run this lesson server over Streamable HTTP."""
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
