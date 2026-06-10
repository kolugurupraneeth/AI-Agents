"""
Tests for the AI-Agents framework.
"""

import pytest
from agents.agent import Agent
from agents.llm import MockProvider, OpenAIProvider


class TestAgent:
    """Test cases for the Agent class."""

    def test_agent_creation(self):
        """Test basic agent creation."""
        agent = Agent(name="TestAgent")
        assert agent.name == "TestAgent"
        assert agent.model == "gpt-4"

    def test_agent_custom_model(self):
        """Test agent creation with custom model."""
        agent = Agent(name="TestAgent", model="gpt-3.5-turbo")
        assert agent.model == "gpt-3.5-turbo"

    def test_agent_execute(self):
        """Test agent task execution."""
        agent = Agent(name="TestAgent")
        result = agent.execute("test task")
        assert "TestAgent" in result
        assert "test task" in result

    def test_agent_state_management(self):
        """Test agent state management."""
        agent = Agent(name="TestAgent")
        agent.update_state("test_key", "test_value")
        state = agent.get_state()
        assert state["state"]["test_key"] == "test_value"

    def test_agent_get_state(self):
        """Test getting agent state."""
        agent = Agent(name="TestAgent")
        state = agent.get_state()
        assert state["name"] == "TestAgent"
        assert state["model"] == "gpt-4"
        assert "created_at" in state


class TestLLMProviders:
    """Test cases for LLM providers."""

    def test_mock_provider(self):
        """Test Mock provider."""
        provider = MockProvider()
        response = provider.generate("test prompt")
        assert "Mock response" in response

    def test_openai_provider_initialization(self):
        """Test OpenAI provider initialization."""
        provider = OpenAIProvider(api_key="test_key", model="gpt-4")
        assert provider.model == "gpt-4"

    def test_openai_provider_generate(self):
        """Test OpenAI provider generate method."""
        provider = OpenAIProvider()
        response = provider.generate("test prompt")
        assert "gpt-4" in response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

