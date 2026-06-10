"""Tool abstract base class."""
from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Base class for agent tools.

    Subclass this and implement `execute()` to create a custom tool.
    The `name` and `description` class attributes are required.
    """

    name: str
    description: str

    @abstractmethod
    async def execute(self, input_text: str) -> str:
        """Execute the tool and return its output as a string."""
        ...

    def parameters_schema(self) -> dict[str, Any]:
        """JSON Schema for tool parameters (used for native function-calling APIs)."""
        return {"type": "object", "properties": {}, "required": []}

    def to_schema(self) -> dict[str, Any]:
        """Serialize to OpenAI function-calling schema format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema(),
            },
        }