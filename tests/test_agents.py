"""Tests for the AI-Agents framework."""

import asyncio

import pytest

from agents.agent import Agent
from agents.agent_loop import parse_tool_calls, run_agent_loop
from agents.config import AgentConfig
from agents.exceptions import LLMError, ToolTimeoutError
from agents.llm import (
    AnthropicProvider,
    MockProvider,
    OpenAICompatibleProvider,
    OpenAIProvider,
)
from agents.tools.base import Tool


# ── Agent ──────────────────────────────────────────────────────────────────


class TestAgent:
    def test_agent_creation(self, mock_provider):
        agent = Agent(name="TestAgent", provider=mock_provider)
        assert agent.name == "TestAgent"
        assert agent.max_rounds == 50

    def test_agent_execute_returns_string(self, mock_provider):
        agent = Agent(name="TestAgent", provider=mock_provider)
        result = agent.execute("hello")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_agent_state_management(self, mock_provider):
        agent = Agent(name="TestAgent", provider=mock_provider)
        agent.update_state("key", "value")
        assert agent.get_state()["state"]["key"] == "value"

    def test_agent_get_state_shape(self, mock_provider):
        agent = Agent(name="TestAgent", provider=mock_provider)
        state = agent.get_state()
        assert state["name"] == "TestAgent"
        assert "created_at" in state
        assert "tools" in state

    def test_agent_with_custom_system_prompt(self, mock_provider):
        agent = Agent(name="Bot", provider=mock_provider, system_prompt="You are a bot.")
        assert agent.system_prompt == "You are a bot."

    def test_agent_with_tools(self, mock_provider, noop_tool):
        agent = Agent(name="ToolAgent", provider=mock_provider, tools=[noop_tool])
        assert "noop" in agent.tools


# ── LLM Providers ─────────────────────────────────────────────────────────


class TestMockProvider:
    def test_generate(self):
        provider = MockProvider(response="Hello world.")
        result = asyncio.run(provider.generate([{"role": "user", "content": "hi"}]))
        assert result == "Hello world."

    def test_stream_yields_chunks(self):
        provider = MockProvider(response="Hello world.")

        async def collect():
            chunks = []
            async for chunk in provider.stream([{"role": "user", "content": "hi"}]):
                chunks.append(chunk)
            return chunks

        chunks = asyncio.run(collect())
        assert len(chunks) > 0
        assert "".join(chunks).strip() == "Hello world."

    def test_default_response(self):
        provider = MockProvider()
        result = asyncio.run(provider.generate([]))
        assert isinstance(result, str)


class TestProviderInit:
    def test_anthropic_provider_init(self):
        p = AnthropicProvider(api_key="test-key", model="claude-haiku-4-5-20251001")
        assert p.model == "claude-haiku-4-5-20251001"
        assert p.api_key == "test-key"

    def test_openai_provider_init(self):
        p = OpenAIProvider(api_key="sk-test", model="gpt-4o")
        assert p.model == "gpt-4o"

    def test_openai_compatible_provider_url(self):
        p = OpenAICompatibleProvider(base_url="http://localhost:11434", model="llama3.2")
        assert "chat/completions" in p._chat_url()
        assert "localhost" in p._chat_url()

    def test_openai_compatible_with_v1_base(self):
        p = OpenAICompatibleProvider(base_url="http://localhost:11434/v1", model="llama3.2")
        assert p._chat_url() == "http://localhost:11434/v1/chat/completions"


# ── Agent loop ─────────────────────────────────────────────────────────────


class TestParseToolCalls:
    def test_no_tool_calls(self):
        assert parse_tool_calls("Just some text.") == []

    def test_single_tool_call(self):
        text = "Let me search:\n```web_search\nPython 3.12 features\n```"
        calls = parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0]["name"] == "web_search"
        assert calls[0]["input"] == "Python 3.12 features"

    def test_multiple_tool_calls(self):
        text = "```bash\nls -la\n```\n\n```python\nprint('hi')\n```"
        calls = parse_tool_calls(text)
        assert len(calls) == 2
        assert calls[0]["name"] == "bash"
        assert calls[1]["name"] == "python"

    def test_tool_call_with_multiline_input(self):
        text = "```python\nx = 1\ny = 2\nprint(x + y)\n```"
        calls = parse_tool_calls(text)
        assert calls[0]["input"] == "x = 1\ny = 2\nprint(x + y)"


class TestRunAgentLoop:
    def test_no_tools_single_round(self, mock_provider):
        async def run():
            chunks = []
            async for chunk in run_agent_loop(
                mock_provider,
                [{"role": "user", "content": "hi"}],
            ):
                chunks.append(chunk)
            return "".join(chunks)

        result = asyncio.run(run())
        assert isinstance(result, str)

    def test_unknown_tool_returns_error_string(self, echo_provider):
        """Unknown tool calls don't crash the loop — they yield an error string."""

        class _ToolCallingProvider(MockProvider):
            _called = False

            async def stream(self, messages, **kwargs):
                # First call emits a tool call; second call emits plain text.
                last = messages[-1]
                if not self._called and last.get("role") == "user" and "hi" in last.get("content", ""):
                    self._called = True
                    yield "```nonexistent_tool\nsome input\n```"
                else:
                    yield "Done."

        provider = _ToolCallingProvider()

        async def run():
            chunks = []
            async for chunk in run_agent_loop(
                provider,
                [{"role": "user", "content": "hi"}],
                tools={},
            ):
                chunks.append(chunk)
            return "".join(chunks)

        result = asyncio.run(run())
        assert "Done." in result


# ── Config ─────────────────────────────────────────────────────────────────


class TestConfig:
    def test_defaults(self):
        config = AgentConfig()
        assert config.environment == "development"
        assert config.max_iterations == 50

    def test_validate_provider_no_keys(self):
        config = AgentConfig()
        # No API keys set — provider not configured
        assert config.validate_provider() is False

    def test_summary_masks_keys(self):
        config = AgentConfig(anthropic_api_key="secret")
        summary = config.summary()
        assert summary["anthropic_api_key"] == "***"


# ── Tools ──────────────────────────────────────────────────────────────────


class TestTool:
    def test_tool_schema(self, noop_tool):
        schema = noop_tool.to_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "noop"

    def test_tool_execute(self, noop_tool):
        result = asyncio.run(noop_tool.execute("anything"))
        assert result == "noop"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
