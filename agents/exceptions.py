"""Typed exception hierarchy for the agents framework."""


class AgentError(Exception):
    """Base exception for all agent framework errors."""


class LLMError(AgentError):
    """Raised when an LLM call fails (HTTP error, bad response schema, etc.)."""

    def __init__(self, message: str, endpoint: str | None = None):
        self.endpoint = endpoint
        super().__init__(message)


class ProviderUnavailableError(LLMError):
    """Raised when a provider host is unreachable or in cooldown."""


class ToolError(AgentError):
    """Raised when a tool fails to execute."""

    def __init__(self, message: str, tool_name: str | None = None):
        self.tool_name = tool_name
        super().__init__(message)


class ToolTimeoutError(ToolError):
    """Raised when a tool execution exceeds its timeout."""


class ConfigurationError(AgentError):
    """Raised when required configuration is missing or invalid."""