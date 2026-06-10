"""Single source of truth for timeouts, limits, and loop bounds."""

# Tool execution
TOOL_TIMEOUT_SECONDS: float = 60.0
TOOL_OUTPUT_MAX_CHARS: int = 10_000

# Agent loop
MAX_AGENT_ROUNDS: int = 50

# LLM HTTP
DEFAULT_TIMEOUT: int = 30
STREAM_TIMEOUT: int = 300
MAX_RETRIES: int = 3
RETRY_DELAY_SECONDS: float = 0.5

# Dead-host cooldown: mark a host unreachable after this many consecutive
# connect failures, then refuse calls to it for COOLDOWN seconds so one
# offline upstream doesn't stall the whole loop.
DEAD_HOST_COOLDOWN_SECONDS: float = 20.0
DEAD_HOST_FAIL_THRESHOLD: int = 2

# Response cache (in-process LRU-style eviction)
RESPONSE_CACHE_MAX_SIZE: int = 128
RESPONSE_CACHE_EVICT_COUNT: int = 64