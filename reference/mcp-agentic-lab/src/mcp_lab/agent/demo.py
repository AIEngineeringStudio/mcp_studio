"""Run the agent loop with a deterministic model; replace it with a real adapter."""

import argparse
import asyncio
import re
from typing import Any

from mcp_lab.agent.core import (
    FinalAnswer,
    MCPToolGateway,
    ToolCall,
    ToolCallingAgent,
    ToolDefinition,
)
from mcp_lab.client import ObservedMCPClient, default_stdio_target
from mcp_lab.observability import configure_logging, configure_tracing, get_settings
from mcp_lab.wire import JsonlWireRecorder


class DeterministicMathModel:
    """A no-API teaching model that exercises the same agent interface as an LLM."""

    async def decide(
        self, messages: list[dict[str, Any]], tools: list[ToolDefinition]
    ) -> ToolCall | FinalAnswer:
        if messages[-1]["role"] == "tool":
            observation = messages[-1]["content"]
            result = observation.get("result") if isinstance(observation, dict) else observation
            return FinalAnswer(f"The result is {result}.")
        prompt = str(messages[0]["content"])
        numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", prompt)]
        if "add" in prompt.lower() and len(numbers) >= 2:
            return ToolCall("add", {"a": numbers[0], "b": numbers[1]})
        return FinalAnswer(
            "This demo model only understands requests like 'Add 7 and 8'. "
            "Implement AgentModel to connect your preferred LLM."
        )


async def run(prompt: str, url: str | None) -> None:
    settings = get_settings()
    configure_logging(settings)
    configure_tracing(settings)
    target = url if url else default_stdio_target(settings)
    transport = "streamable-http" if url else "stdio"
    recorder = JsonlWireRecorder("var/client-wire.jsonl", enabled=settings.wire_log_enabled)
    async with ObservedMCPClient(target, transport_name=transport, recorder=recorder) as client:
        agent = ToolCallingAgent(DeterministicMathModel(), MCPToolGateway(client))
        answer = await agent.run(prompt)
        print(answer.text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?", default="Add 7 and 8")
    parser.add_argument("--url", help="Streamable HTTP MCP URL; omit for stdio")
    args = parser.parse_args()
    asyncio.run(run(args.prompt, args.url))


if __name__ == "__main__":
    main()
