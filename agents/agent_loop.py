"""
Multi-round agentic execution loop.

The loop streams the LLM response, parses fenced code block tool calls, executes
them (in parallel), injects results back into the conversation, then repeats until
the model produces no more tool calls or MAX_AGENT_ROUNDS is reached.

Pattern adapted from odysseus/src/agent_loop.py.
"""

import asyncio
import logging
import re
from typing import AsyncGenerator, Dict, List, Optional

from .constants import MAX_AGENT_ROUNDS, TOOL_OUTPUT_MAX_CHARS, TOOL_TIMEOUT_SECONDS
from .exceptions import ToolError

logger = logging.getLogger(__name__)

# Matches ```tool_name\n...\n``` — the convention for tool invocations in chat.
_TOOL_BLOCK_RE = re.compile(r"```(\w[\w.-]*)\n(.*?)\n?```", re.DOTALL)


def parse_tool_calls(text: str) -> list[dict]:
    """Extract fenced-block tool calls from an LLM response.

    Returns a list of {"name": str, "input": str} dicts in order of appearance.
    """
    return [
        {"name": m.group(1), "input": m.group(2).strip()}
        for m in _TOOL_BLOCK_RE.finditer(text)
    ]


async def _execute_one(tool, input_text: str, timeout: float) -> str:
    """Run a single tool with timeout and output cap. Never raises — errors become result strings."""
    try:
        result = await asyncio.wait_for(tool.execute(input_text), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("Tool '%s' timed out after %.0fs", tool.name, timeout)
        return f"[Error: tool '{tool.name}' timed out after {timeout:.0f}s]"
    except Exception as e:
        logger.warning("Tool '%s' raised: %s", tool.name, e)
        return f"[Error: tool '{tool.name}' failed: {e}]"

    if len(result) > TOOL_OUTPUT_MAX_CHARS:
        result = result[:TOOL_OUTPUT_MAX_CHARS] + f"\n[...output truncated at {TOOL_OUTPUT_MAX_CHARS} chars]"
    return result


async def run_agent_loop(
    provider,
    messages: List[Dict],
    tools: Optional[Dict] = None,
    max_rounds: int = MAX_AGENT_ROUNDS,
    tool_timeout: float = TOOL_TIMEOUT_SECONDS,
    **llm_kwargs,
) -> AsyncGenerator[str, None]:
    """Stream the agent loop, yielding text chunks as they arrive.

    Each round:
      1. Stream the LLM response (yields chunks as they arrive).
      2. Parse fenced-block tool calls from the accumulated response.
      3. Execute all tool calls in parallel (with timeout + output cap).
      4. Inject results back as a user message.
      5. Repeat until no tool calls or max_rounds reached.

    Args:
        provider: Any LLMProvider instance.
        messages: Initial conversation (system + user messages).
        tools: Mapping of tool name → Tool instance.
        max_rounds: Hard cap on loop iterations.
        tool_timeout: Per-tool execution timeout in seconds.
        **llm_kwargs: Forwarded to provider.stream() (temperature, max_tokens, etc.).
    """
    tools = tools or {}
    conversation = list(messages)

    for round_num in range(max_rounds):
        response_text = ""

        async for chunk in provider.stream(conversation, **llm_kwargs):
            yield chunk
            response_text += chunk

        tool_calls = parse_tool_calls(response_text)

        if not tool_calls:
            logger.debug("Agent loop: no tool calls in round %d — done", round_num + 1)
            break

        conversation.append({"role": "assistant", "content": response_text})

        # Execute all tool calls concurrently.
        async def _exec(call: dict) -> str:
            name = call["name"]
            tool = tools.get(name)
            if tool is None:
                logger.warning("Agent called unknown tool '%s'", name)
                return f"[Error: unknown tool '{name}']"
            return await _execute_one(tool, call["input"], tool_timeout)

        results = await asyncio.gather(*[_exec(c) for c in tool_calls])

        result_parts = [
            f"[{call['name']} result]\n{result}"
            for call, result in zip(tool_calls, results)
        ]
        conversation.append({"role": "user", "content": "\n\n".join(result_parts)})

        logger.debug(
            "Agent loop: round %d/%d — executed %d tool(s)",
            round_num + 1,
            max_rounds,
            len(tool_calls),
        )
    else:
        logger.warning("Agent loop: reached max_rounds=%d without finishing", max_rounds)