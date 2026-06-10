"""
Configuration management for AI-Agents framework.
"""

import os
from typing import Optional
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Configuration class for AI-Agents."""

    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4")

    # Agent Configuration
    AGENT_LOG_LEVEL: str = os.getenv("AGENT_LOG_LEVEL", "INFO")
    AGENT_MAX_ITERATIONS: int = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))
    AGENT_TIMEOUT: int = int(os.getenv("AGENT_TIMEOUT", "300"))

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Logging
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/agents.log")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "standard")

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration."""
        if not cls.OPENAI_API_KEY and cls.ENVIRONMENT == "production":
            logger.warning("OPENAI_API_KEY not set in production environment")
            return False
        return True

    @classmethod
    def get_all(cls) -> dict:
        """Get all configuration as dictionary."""
        return {
            "openai_api_key": "***" if cls.OPENAI_API_KEY else None,
            "llm_model": cls.LLM_MODEL,
            "agent_log_level": cls.AGENT_LOG_LEVEL,
            "agent_max_iterations": cls.AGENT_MAX_ITERATIONS,
            "environment": cls.ENVIRONMENT,
            "debug": cls.DEBUG,
        }

