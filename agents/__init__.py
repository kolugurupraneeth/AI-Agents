"""
AI-Agents Framework
A proof of concept framework for building and managing AI agents.
"""

__version__ = "0.1.0"
__author__ = "AI-Agents Contributors"
__license__ = "MIT"

from agents.agent import Agent
from agents.llm import LLMProvider

__all__ = ["Agent", "LLMProvider"]

