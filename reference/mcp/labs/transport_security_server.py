"""Loopback server with explicit Host and Origin policy for Lesson 17."""

from fastmcp import FastMCP


HOST = "127.0.0.1"
PORT = 8781
mcp = FastMCP("Transport security exercise")


@mcp.tool
def health() -> str:
    """Return the service health state."""
    return "ok"


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host=HOST,
        port=PORT,
        json_response=True,
        host_origin_protection=True,
        allowed_hosts=[f"{HOST}:{PORT}"],
        allowed_origins=["https://trusted.example"],
    )
