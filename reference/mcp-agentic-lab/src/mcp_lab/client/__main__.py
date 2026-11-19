"""Exercise the example MCP server over stdio or Streamable HTTP."""

import argparse
import asyncio
import json

from mcp_lab.client.observed import ObservedMCPClient, default_stdio_target
from mcp_lab.observability import configure_logging, configure_tracing, get_settings
from mcp_lab.wire import JsonlWireRecorder
from mcp_lab.wire.recorder import to_jsonable


async def run(url: str | None, wiretap: bool, tool: str, arguments: dict[str, object]) -> None:
    settings = get_settings()
    configure_logging(settings)
    configure_tracing(settings)
    target = url if url else default_stdio_target(settings, wiretap=wiretap)
    transport = "streamable-http" if url else "stdio"
    recorder = JsonlWireRecorder("var/client-wire.jsonl", enabled=settings.wire_log_enabled)

    async with ObservedMCPClient(target, transport_name=transport, recorder=recorder) as client:
        tools = await client.list_tools()
        print("Available tools:", ", ".join(item.name for item in tools.tools))
        result = await client.call_tool(tool, arguments)
        print(json.dumps(to_jsonable(result), indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Streamable HTTP MCP URL; omit for stdio")
    parser.add_argument("--no-wiretap", action="store_true", help="Disable raw stdio proxy")
    parser.add_argument("--tool", default="add")
    parser.add_argument("--arguments", default='{"a": 7, "b": 8}')
    args = parser.parse_args()
    try:
        arguments = json.loads(args.arguments)
    except json.JSONDecodeError as exc:
        parser.error(f"--arguments must be JSON: {exc}")
    if not isinstance(arguments, dict):
        parser.error("--arguments must decode to an object")
    asyncio.run(run(args.url, not args.no_wiretap, args.tool, arguments))


if __name__ == "__main__":
    main()
