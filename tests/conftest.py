"""Shared pytest fixtures."""

import pytest
from agents.llm import MockProvider
from agents.tools.base import Tool


@pytest.fixture
def mock_provider():
    return MockProvider(response="Hello from mock.")


@pytest.fixture
def echo_provider():
    """Provider that echoes the last user message back."""

    class _EchoProvider(MockProvider):
        async def generate(self, messages, **kwargs):
            last = next(
                (m["content"] for m in reversed(messages) if m.get("role") == "user"),
                "no message",
            )
            return f"Echo: {last}"

        async def stream(self, messages, **kwargs):
            text = await self.generate(messages, **kwargs)
            for word in text.split():
                yield word + " "

    return _EchoProvider()


@pytest.fixture
def noop_tool():
    """A tool that always returns 'noop' — useful for testing tool dispatch."""

    class _NoopTool(Tool):
        name = "noop"
        description = "Does nothing and returns a fixed string."

        async def execute(self, input_text: str) -> str:
            return "noop"

    return _NoopTool()
