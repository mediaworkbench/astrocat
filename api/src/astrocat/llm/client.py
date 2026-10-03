"""Minimal Ollama chat client."""

import os
from typing import Any, Protocol

import httpx

DEFAULT_PORT = 11434
# Marker in the stored rejection reasons; the scheduler retries readings that fell back because of it.
UNAVAILABLE_PREFIX = "Ollama request failed"


class LLMUnavailable(RuntimeError):
    """Ollama is unreachable or returned an error."""


def normalize_base_url(value: str) -> str:
    """Accept "host", "host:port" or a full URL; a bare host gets http:// and Ollama's default port."""
    url = value.strip().rstrip("/")
    if "://" not in url:
        host, _, port = url.partition(":")
        url = f"http://{host}:{port or DEFAULT_PORT}"
    return url


class ChatClient(Protocol):
    model: str

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any], temperature: float = 0.7) -> str: ...


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        # `or` instead of a get() default: an empty value in .env means "use the default" too.
        self.base_url = normalize_base_url(base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434")
        # e4b instead of e2b: clearly better Spanish and German at ~8 s per reading (M2 review, v4).
        self.model = model or os.environ.get("OLLAMA_MODEL") or "gemma4:e4b"
        self.timeout = timeout or float(os.environ.get("OLLAMA_TIMEOUT") or "120")

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any], temperature: float = 0.7) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            "format": schema,
            "stream": False,
            "think": False,  # thinking costs ~3x the tokens without better readings (M2 probe)
            "options": {"temperature": temperature},
        }
        try:
            response = httpx.post(f"{self.base_url}/api/chat", json=body, timeout=self.timeout)
            response.raise_for_status()
            return response.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMUnavailable(f"{UNAVAILABLE_PREFIX} ({self.base_url}): {exc}") from exc
