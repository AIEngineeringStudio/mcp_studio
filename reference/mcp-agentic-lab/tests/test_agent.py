from typing import Any

from mcp_lab.agent.core import FinalAnswer, ToolCall, ToolCallingAgent, ToolDefinition


class FakeTools:
    async def list_tool_definitions(self) -> list[ToolDefinition]:
        return [ToolDefinition("add", "Add", {"type": "object"})]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> Any:
        assert name == "add"
        return {"result": arguments["a"] + arguments["b"]}


class TwoStepModel:
    async def decide(self, messages, tools):
        if messages[-1]["role"] == "tool":
            return FinalAnswer(f"answer={messages[-1]['content']['result']}")
        return ToolCall("add", {"a": 2, "b": 3})


async def test_agent_plan_act_observe_loop():
    answer = await ToolCallingAgent(TwoStepModel(), FakeTools()).run("add two and three")
    assert answer.text == "answer=5"


class BadModel:
    async def decide(self, messages, tools):
        return ToolCall("delete_everything", {})


async def test_agent_rejects_unadvertised_tool():
    agent = ToolCallingAgent(BadModel(), FakeTools())
    try:
        await agent.run("do something")
    except ValueError as exc:
        assert "unavailable tool" in str(exc)
    else:
        raise AssertionError("agent accepted an unavailable tool")
