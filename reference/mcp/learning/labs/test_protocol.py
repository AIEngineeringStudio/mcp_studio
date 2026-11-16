"""Negative contract checks through a real in-memory MCP client."""
import unittest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from server import mcp


class ContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_required_argument(self):
        async with Client(mcp) as client:
            with self.assertRaises(ToolError):
                await client.call_tool("get_ticket", {})

    async def test_unknown_record(self):
        async with Client(mcp) as client:
            with self.assertRaises(ToolError):
                await client.call_tool("get_ticket", {"ticket_id": "missing"})


if __name__ == "__main__":
    unittest.main()
