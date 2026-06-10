"""
Example usage of the AI-Agents framework.

Run with a real provider key:
    ANTHROPIC_API_KEY=sk-ant-... python examples/basic_usage.py

Or run offline using the built-in MockProvider.
"""

import asyncio

from agents import Agent, AgentConfig, AnthropicProvider, MockProvider, OpenAICompatibleProvider
from agents.tools.base import Tool


# ── Example tool ──────────────────────────────────────────────────────────


class CalculatorTool(Tool):
    name = "calculator"
    description = "Evaluate a simple arithmetic expression and return the result."

    async def execute(self, input_text: str) -> str:
        try:
            # Restrict to safe arithmetic only.
            allowed = set("0123456789+-*/()., ")
            if not all(c in allowed for c in input_text):
                return "Error: only arithmetic expressions are allowed."
            result = eval(input_text, {"__builtins__": {}})  # noqa: S307
            return str(result)
        except Exception as e:
            return f"Error: {e}"


# ── Examples ──────────────────────────────────────────────────────────────


def basic_sync_example():
    """Synchronous usage with MockProvider."""
    print("=== Basic sync example ===")
    provider = MockProvider(response="The capital of France is Paris.")
    agent = Agent(name="Assistant", provider=provider)
    result = agent.execute("What is the capital of France?")
    print(f"Response: {result}\n")


async def streaming_example():
    """Async streaming with MockProvider."""
    print("=== Streaming example ===")
    provider = MockProvider(response="Roses are red, violets are blue, AI is cool and so are you.")
    agent = Agent(name="Poet", provider=provider)
    print("Streaming: ", end="")
    async for chunk in agent.stream("Write a short poem."):
        print(chunk, end="", flush=True)
    print("\n")


async def tool_use_example():
    """Agent with a calculator tool."""
    print("=== Tool use example ===")

    # MockProvider that emits a tool call on the first turn.
    class ToolCallingMock(MockProvider):
        _first = True

        async def stream(self, messages, **kwargs):
            if self._first:
                self._first = False
                yield "Let me calculate that:\n```calculator\n(12 * 8) + 4\n```"
            else:
                yield "The result is 100."

    agent = Agent(
        name="MathAgent",
        provider=ToolCallingMock(),
        tools=[CalculatorTool()],
    )
    result = await agent.aexecute("What is 12 times 8 plus 4?")
    print(f"Result: {result}\n")


async def anthropic_example():
    """Real Anthropic call — requires ANTHROPIC_API_KEY in environment."""
    config = AgentConfig()
    if not config.anthropic_api_key:
        print("=== Anthropic example (skipped — no ANTHROPIC_API_KEY) ===\n")
        return

    print("=== Anthropic example ===")
    provider = AnthropicProvider(api_key=config.anthropic_api_key, model=config.anthropic_model)
    agent = Agent(
        name="ClaudeAgent",
        provider=provider,
        system_prompt="You are a concise assistant. Reply in one sentence.",
    )
    result = await agent.aexecute("What is the Zen of Python about?")
    print(f"Response: {result}\n")


async def ollama_example():
    """Local Ollama call — requires Ollama running on localhost:11434."""
    print("=== Ollama example (skipped if Ollama not running) ===")
    config = AgentConfig()
    if not config.openai_compatible_url:
        print("Set OPENAI_COMPATIBLE_URL=http://localhost:11434 and OPENAI_COMPATIBLE_MODEL=llama3.2\n")
        return

    provider = OpenAICompatibleProvider(
        base_url=config.openai_compatible_url,
        model=config.openai_compatible_model or "llama3.2",
        api_key=config.openai_compatible_api_key,
    )
    agent = Agent(name="OllamaAgent", provider=provider)
    result = await agent.aexecute("Say hello in three words.")
    print(f"Response: {result}\n")


async def state_management_example():
    """Agent with persistent state."""
    print("=== State management example ===")
    provider = MockProvider(response="Task complete.")
    agent = Agent(name="StatefulAgent", provider=provider)

    agent.update_state("tasks_completed", 0)
    await agent.aexecute("Do task 1")
    agent.update_state("tasks_completed", 1)

    state = agent.get_state()
    print(f"Agent: {state['name']}")
    print(f"Tasks completed: {state['state']['tasks_completed']}\n")


# ── Entry point ───────────────────────────────────────────────────────────


async def main():
    await streaming_example()
    await tool_use_example()
    await anthropic_example()
    await ollama_example()
    await state_management_example()
    print("All examples complete.")


if __name__ == "__main__":
    # Sync example must run outside asyncio.run() since agent.execute() creates its own loop.
    basic_sync_example()
    asyncio.run(main())
