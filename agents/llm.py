"""
LLM provider integrations.

All providers are implemented via httpx so connection pooling, dead-host
cooldown, response caching, and retry logic are uniform across Anthropic,
OpenAI, and any OpenAI-compatible endpoint (Ollama, vLLM, LM Studio, etc.).

Pattern adapted from odysseus/src/llm_core.py.
"""

import asyncio
import hashlib
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from .constants import (
    DEFAULT_TIMEOUT,
    DEAD_HOST_COOLDOWN_SECONDS,
    DEAD_HOST_FAIL_THRESHOLD,
    MAX_RETRIES,
    RESPONSE_CACHE_EVICT_COUNT,
    RESPONSE_CACHE_MAX_SIZE,
    RETRY_DELAY_SECONDS,
    STREAM_TIMEOUT,
)
from .exceptions import LLMError, ProviderUnavailableError

logger = logging.getLogger(__name__)


# ── Response cache ─────────────────────────────────────────────────────────


def _cache_key(url: str, model: str, messages: List[Dict], temperature: float, max_tokens: int) -> str:
    content = json.dumps(
        {
            "url": url,
            "model": model,
            "messages": [tuple(sorted(m.items())) for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(content.encode()).hexdigest()


_response_cache: Dict[str, str] = {}


def _get_cached(key: str) -> Optional[str]:
    return _response_cache.get(key)


def _set_cached(key: str, value: str) -> None:
    if len(_response_cache) >= RESPONSE_CACHE_MAX_SIZE:
        to_evict = list(_response_cache.keys())[:RESPONSE_CACHE_EVICT_COUNT]
        for k in to_evict:
            _response_cache.pop(k, None)
    _response_cache[key] = value


# ── Dead-host cooldown ─────────────────────────────────────────────────────
# After DEAD_HOST_FAIL_THRESHOLD consecutive connect failures we refuse calls
# to that host for DEAD_HOST_COOLDOWN_SECONDS, making instant-fail instead of
# waiting on a connect timeout each time.

_dead_hosts: Dict[str, float] = {}  # host_key → expiry timestamp
_host_fails: Dict[str, int] = {}  # host_key → consecutive failure count
_host_health_lock = threading.Lock()  # guards both maps (accessed from threads + event loop)


def _host_key(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else url


def _is_host_dead(url: str) -> bool:
    key = _host_key(url)
    with _host_health_lock:
        expiry = _dead_hosts.get(key)
        if expiry is None:
            return False
        if time.time() >= expiry:
            _dead_hosts.pop(key, None)
            return False
        return True


def _mark_host_failure(url: str) -> bool:
    """Record a connect failure. Returns True once the host enters cooldown."""
    key = _host_key(url)
    with _host_health_lock:
        n = _host_fails.get(key, 0) + 1
        _host_fails[key] = n
        if n >= DEAD_HOST_FAIL_THRESHOLD:
            _dead_hosts[key] = time.time() + DEAD_HOST_COOLDOWN_SECONDS
            return True
        return False


def _clear_host_failure(url: str) -> None:
    key = _host_key(url)
    with _host_health_lock:
        _dead_hosts.pop(key, None)
        _host_fails.pop(key, None)


# ── Shared async HTTP client ───────────────────────────────────────────────
# Reusing one client keeps TCP/TLS connections warm across repeated calls to
# the same host (skips 100-500ms handshake on every message).

_http_client: Optional[httpx.AsyncClient] = None
_http_limits = httpx.Limits(max_connections=100, max_keepalive_connections=30, keepalive_expiry=30.0)


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(limits=_http_limits, http2=False)
    return _http_client


# ── Anthropic payload helpers ──────────────────────────────────────────────


def _build_anthropic_payload(
    model: str,
    messages: List[Dict],
    temperature: float,
    max_tokens: int,
    stream: bool = False,
) -> dict:
    system_parts = []
    chat_messages = []
    for m in messages:
        if m.get("role") == "system":
            system_parts.append(m.get("content") or "")
        else:
            chat_messages.append({"role": m["role"], "content": m.get("content", "")})

    # Anthropic only accepts temperature in [0.0, 1.0]; clamp so OpenAI-style
    # presets with values above 1.0 don't hard-break Claude requests.
    temp = max(0.0, min(float(temperature or 1.0), 1.0))

    payload: dict = {
        "model": model,
        "messages": chat_messages,
        "max_tokens": max_tokens if max_tokens and max_tokens > 0 else 4096,
        "temperature": temp,
    }
    if system_parts:
        # Send as a structured block so prompt caching can be applied later.
        payload["system"] = [{"type": "text", "text": "\n\n".join(system_parts)}]
    if stream:
        payload["stream"] = True
    return payload


def _parse_anthropic_response(data: dict) -> str:
    return "".join(
        block.get("text", "")
        for block in data.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    )


# ── Provider ABC and base httpx implementation ─────────────────────────────


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, messages: List[Dict], **kwargs) -> str:
        """Return a complete response string (non-streaming)."""
        ...

    @abstractmethod
    async def stream(self, messages: List[Dict], **kwargs) -> AsyncGenerator[str, None]:
        """Yield response text chunks as they arrive."""
        ...


class _HttpxProvider(LLMProvider):
    """httpx-based provider with dead-host cooldown, caching, and retry.

    Subclasses implement `_chat_url()`, `_headers()`, `_build_payload()`,
    `_parse_response()`, and `_parse_stream_delta()`.
    """

    def __init__(
        self,
        api_key: Optional[str],
        model: str,
        base_url: str,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _chat_url(self) -> str:
        raise NotImplementedError

    def _headers(self) -> Dict[str, str]:
        raise NotImplementedError

    def _build_payload(self, messages: List[Dict], temperature: float, max_tokens: int, stream: bool = False) -> dict:
        raise NotImplementedError

    def _parse_response(self, data: dict) -> str:
        raise NotImplementedError

    def _parse_stream_delta(self, line: str) -> Optional[str]:
        raise NotImplementedError

    async def generate(
        self,
        messages: List[Dict],
        temperature: float = 1.0,
        max_tokens: int = 0,
        **kwargs,
    ) -> str:
        url = self._chat_url()
        key = _cache_key(url, self.model, messages, temperature, max_tokens)
        cached = _get_cached(key)
        if cached:
            logger.debug("LLM cache hit for %s/%s", _host_key(url), self.model)
            return cached

        if _is_host_dead(url):
            raise ProviderUnavailableError(
                f"Host {_host_key(url)} is in cooldown ({DEAD_HOST_COOLDOWN_SECONDS:.0f}s)",
                endpoint=url,
            )

        payload = self._build_payload(messages, temperature, max_tokens)
        call_timeout = httpx.Timeout(connect=3.0, read=float(self.timeout), write=10.0, pool=5.0)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                client = _get_http_client()
                r = await client.post(url, headers=self._headers(), json=payload, timeout=call_timeout)
                _clear_host_failure(url)
                if not r.is_success:
                    if r.status_code in (429, 502, 503, 504) and attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
                        continue
                    raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}", endpoint=url)
                result = self._parse_response(r.json())
                _set_cached(key, result)
                logger.debug("LLM call to %s succeeded (attempt %d)", url, attempt)
                return result
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                cooled = _mark_host_failure(url)
                tail = f" — host cooled for {DEAD_HOST_COOLDOWN_SECONDS:.0f}s" if cooled else " — will retry"
                logger.warning("LLM connect to %s failed: %s%s", url, e, tail)
                if cooled or attempt >= MAX_RETRIES:
                    raise ProviderUnavailableError(f"Cannot reach {_host_key(url)}: {e}", endpoint=url)
                await asyncio.sleep(RETRY_DELAY_SECONDS)
            except (LLMError, ProviderUnavailableError):
                raise
            except Exception as e:
                if attempt >= MAX_RETRIES:
                    raise LLMError(f"Request failed after {MAX_RETRIES} attempts: {e}", endpoint=url)
                await asyncio.sleep(RETRY_DELAY_SECONDS)

        raise LLMError(f"All {MAX_RETRIES} attempts exhausted", endpoint=url)

    async def stream(
        self,
        messages: List[Dict],
        temperature: float = 1.0,
        max_tokens: int = 0,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        url = self._chat_url()
        if _is_host_dead(url):
            raise ProviderUnavailableError(
                f"Host {_host_key(url)} is in cooldown ({DEAD_HOST_COOLDOWN_SECONDS:.0f}s)",
                endpoint=url,
            )

        payload = self._build_payload(messages, temperature, max_tokens, stream=True)
        stream_timeout = httpx.Timeout(connect=3.0, read=float(STREAM_TIMEOUT), write=30.0, pool=5.0)

        try:
            client = _get_http_client()
            async with client.stream(
                "POST", url, headers=self._headers(), json=payload, timeout=stream_timeout
            ) as r:
                _clear_host_failure(url)
                if r.status_code != 200:
                    body = (await r.aread()).decode(errors="replace")
                    raise LLMError(f"HTTP {r.status_code}: {body[:300]}", endpoint=url)
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    delta = self._parse_stream_delta(line)
                    if delta:
                        yield delta
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            _mark_host_failure(url)
            raise ProviderUnavailableError(f"Cannot reach {_host_key(url)}: {e}", endpoint=url)
        except (LLMError, ProviderUnavailableError):
            raise
        except Exception as e:
            raise LLMError(f"Streaming failed: {e}", endpoint=url)


# ── Concrete providers ─────────────────────────────────────────────────────


class AnthropicProvider(_HttpxProvider):
    """Anthropic Claude provider (api.anthropic.com).

    Example::

        provider = AnthropicProvider(api_key="sk-ant-...", model="claude-sonnet-4-6")
        response = await provider.generate([{"role": "user", "content": "Hello"}])
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", **kwargs):
        super().__init__(api_key=api_key, model=model, base_url="https://api.anthropic.com", **kwargs)
        logger.info("AnthropicProvider initialized with model '%s'", model)

    def _chat_url(self) -> str:
        return f"{self.base_url}/v1/messages"

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
        }

    def _build_payload(
        self, messages: List[Dict], temperature: float, max_tokens: int, stream: bool = False
    ) -> dict:
        return _build_anthropic_payload(self.model, messages, temperature, max_tokens, stream=stream)

    def _parse_response(self, data: dict) -> str:
        return _parse_anthropic_response(data)

    def _parse_stream_delta(self, line: str) -> Optional[str]:
        if not line.startswith("data:"):
            return None
        raw = line[5:].strip()
        if not raw or raw == "[DONE]":
            return None
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            return None
        # Anthropic SSE delivers text via content_block_delta events.
        if event.get("type") == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                return delta.get("text") or None
        return None


class OpenAIProvider(_HttpxProvider):
    """OpenAI provider (api.openai.com/v1/chat/completions).

    Example::

        provider = OpenAIProvider(api_key="sk-...", model="gpt-4o")
        response = await provider.generate([{"role": "user", "content": "Hello"}])
    """

    def __init__(self, api_key: str, model: str = "gpt-4o", **kwargs):
        super().__init__(api_key=api_key, model=model, base_url="https://api.openai.com", **kwargs)
        logger.info("OpenAIProvider initialized with model '%s'", model)

    def _chat_url(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key or ''}",
        }

    def _build_payload(
        self, messages: List[Dict], temperature: float, max_tokens: int, stream: bool = False
    ) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens and max_tokens > 0:
            payload["max_tokens"] = max_tokens
        return payload

    def _parse_response(self, data: dict) -> str:
        return ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""

    def _parse_stream_delta(self, line: str) -> Optional[str]:
        if not line.startswith("data:"):
            return None
        raw = line[5:].strip()
        if not raw or raw == "[DONE]":
            return None
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return ((event.get("choices") or [{}])[0].get("delta") or {}).get("content") or None


class OpenAICompatibleProvider(OpenAIProvider):
    """Generic OpenAI-compatible endpoint: Ollama, vLLM, LM Studio, Together, etc.

    Example::

        provider = OpenAICompatibleProvider(
            base_url="http://localhost:11434",
            model="llama3.2",
        )
    """

    def __init__(self, base_url: str, model: str, api_key: Optional[str] = None, **kwargs):
        # Bypass OpenAIProvider.__init__ defaults — base_url is caller-supplied.
        _HttpxProvider.__init__(self, api_key=api_key, model=model, base_url=base_url, **kwargs)
        logger.info("OpenAICompatibleProvider initialized: %s / %s", base_url, model)

    def _chat_url(self) -> str:
        base = self.base_url.rstrip("/")
        # Append /v1/chat/completions only if the base doesn't already end in /v1
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"


class MockProvider(LLMProvider):
    """Configurable mock provider for tests and offline development."""

    def __init__(self, response: str = "Mock response."):
        self._response = response

    async def generate(self, messages: List[Dict], **kwargs) -> str:
        return self._response

    async def stream(self, messages: List[Dict], **kwargs) -> AsyncGenerator[str, None]:
        for word in self._response.split():
            yield word + " "