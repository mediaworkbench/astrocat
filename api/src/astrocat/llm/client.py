"""Minimal Ollama chat client."""

import os
from typing import Any, Protocol

import httpx


class LLMUnavailable(RuntimeError):
    """Ollama is unreachable or returned an error."""


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
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        # e4b instead of e2b: clearly better Spanish and German at ~8 s per reading (M2 review, v4).
        self.model = model or os.environ.get("OLLAMA_MODEL", "gemma4:e4b")
        self.timeout = timeout or float(os.environ.get("OLLAMA_TIMEOUT", "120"))

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
            raise LLMUnavailable(f"Ollama request failed: {exc}") from exc
