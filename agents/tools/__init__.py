"""Tool registry: register tools and look them up by name at dispatch time."""
from .base import Tool

_registry: dict[str, Tool] = {}


def register(tool: Tool) -> None:
    """Add a tool to the global registry."""
    _registry[tool.name] = tool


def get(name: str) -> Tool | None:
    """Look up a registered tool by name."""
    return _registry.get(name)


def all_tools() -> list[Tool]:
    return list(_registry.values())


def schemas() -> list[dict]:
    """Return OpenAI function-calling schemas for all registered tools."""
    return [t.to_schema() for t in _registry.values()]


__all__ = ["Tool", "register", "get", "all_tools", "schemas"]