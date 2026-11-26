import argparse

from fastmcp import FastMCP
from tools import process_records

mcp = FastMCP("Progress-exercise")

# Register tools
mcp.tool(process_records)

if __name__ == "__main__":
    choices = ["stdio", "http"]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport",
        choices=choices,
        required=True,
        # default="stdio",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(
            transport="http",
            host="127.0.0.1",
            port=8000,
            path="/mcp",
        )
