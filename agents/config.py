"""Pydantic-based configuration with environment variable loading."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentConfig(BaseSettings):
    """Framework configuration.

    All fields can be set via environment variables (case-insensitive) or a
    `.env` file in the working directory.

    Example::

        # .env
        ANTHROPIC_API_KEY=sk-ant-...
        ANTHROPIC_MODEL=claude-sonnet-4-6
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Anthropic
    anthropic_api_key: Optional[str] = Field(None)
    anthropic_model: str = Field("claude-sonnet-4-6")

    # OpenAI
    openai_api_key: Optional[str] = Field(None)
    openai_model: str = Field("gpt-4o")

    # Generic OpenAI-compatible endpoint (Ollama, vLLM, LM Studio, etc.)
    openai_compatible_url: Optional[str] = Field(None)
    openai_compatible_model: Optional[str] = Field(None)
    openai_compatible_api_key: Optional[str] = Field(None)

    # Agent behaviour
    max_iterations: int = Field(50)
    agent_timeout: int = Field(300)

    # General
    environment: str = Field("development")
    debug: bool = Field(False)
    log_level: str = Field("INFO")

    def validate_provider(self) -> bool:
        """Return True if at least one provider is configured."""
        return bool(
            self.anthropic_api_key
            or self.openai_api_key
            or (self.openai_compatible_url and self.openai_compatible_model)
        )

    def summary(self) -> dict:
        """Config dict safe for logging (API keys masked)."""
        return {
            "anthropic_api_key": "***" if self.anthropic_api_key else None,
            "anthropic_model": self.anthropic_model,
            "openai_api_key": "***" if self.openai_api_key else None,
            "openai_model": self.openai_model,
            "openai_compatible_url": self.openai_compatible_url,
            "openai_compatible_model": self.openai_compatible_model,
            "max_iterations": self.max_iterations,
            "environment": self.environment,
            "debug": self.debug,
        }