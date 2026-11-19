"""Minimal plan/act/observe loop with explicit model and tool boundaries."""

from dataclasses import dataclass
from typing import Any, Protocol

from opentelemetry import trace

tracer = trace.get_tracer(__name__)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str | None
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class FinalAnswer:
    text: str


AgentDecision = ToolCall | FinalAnswer


class AgentModel(Protocol):
    async def decide(
        self, messages: list[dict[str, Any]], tools: list[ToolDefinition]
    ) -> AgentDecision: ...


class ToolGateway(Protocol):
    async def list_tool_definitions(self) -> list[ToolDefinition]: ...

    async def invoke(self, name: str, arguments: dict[str, Any]) -> Any: ...


class MCPToolGateway:
    """Adapt ObservedMCPClient to the narrow interface used by the agent."""

    def __init__(self, client: Any) -> None:
        self.client = client

    async def list_tool_definitions(self) -> list[ToolDefinition]:
        page = await self.client.list_tools()
        return [
            ToolDefinition(
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_schema,
            )
            for tool in page.tools
        ]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> Any:
        result = await self.client.call_tool(name, arguments)
        return result.structured_content or [
            block.model_dump(mode="json", by_alias=True) for block in result.content
        ]


class ToolCallingAgent:
    def __init__(self, model: AgentModel, tools: ToolGateway, *, max_steps: int = 8) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        self.model = model
        self.tools = tools
        self.max_steps = max_steps

    async def run(self, prompt: str) -> FinalAnswer:
        definitions = await self.tools.list_tool_definitions()
        allowed = {tool.name for tool in definitions}
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

        with tracer.start_as_current_span("agent.run") as span:
            span.set_attribute("agent.max_steps", self.max_steps)
            for step in range(self.max_steps):
                decision = await self.model.decide(messages, definitions)
                if isinstance(decision, FinalAnswer):
                    span.set_attribute("agent.steps", step + 1)
                    return decision
                if decision.name not in allowed:
                    raise ValueError(f"Model selected an unavailable tool: {decision.name}")
                with tracer.start_as_current_span("agent.tool_call") as tool_span:
                    tool_span.set_attribute("gen_ai.tool.name", decision.name)
                    observation = await self.tools.invoke(decision.name, decision.arguments)
                messages.extend(
                    [
                        {
                            "role": "assistant",
                            "tool_call": {
                                "name": decision.name,
                                "arguments": decision.arguments,
                            },
                        },
                        {
                            "role": "tool",
                            "name": decision.name,
                            "content": observation,
                        },
                    ]
                )
        raise RuntimeError(f"Agent exceeded its {self.max_steps}-step budget")
