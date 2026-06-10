"""
AI-Agents Framework
A scalable framework for building autonomous AI agents.
"""

__version__ = "0.2.0"
__author__ = "AI-Agents Contributors"
__license__ = "MIT"

from agents.agent import Agent
from agents.agent_loop import run_agent_loop
from agents.config import AgentConfig
from agents.exceptions import AgentError, LLMError, ProviderUnavailableError, ToolError, ToolTimeoutError
from agents.llm import AnthropicProvider, LLMProvider, MockProvider, OpenAICompatibleProvider, OpenAIProvider
from agents.tools import Tool

__all__ = [
    "Agent",
    "AgentConfig",
    "AgentError",
    "AnthropicProvider",
    "LLMError",
    "LLMProvider",
    "MockProvider",
    "OpenAICompatibleProvider",
    "OpenAIProvider",
    "ProviderUnavailableError",
    "Tool",
    "ToolError",
    "ToolTimeoutError",
    "run_agent_loop",
]