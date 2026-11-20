"""Local Ollama provider (talks to the Ollama HTTP API, no extra dependency)."""

from __future__ import annotations

import requests

from papersift.providers.base import LLMProvider, ProviderError

DEFAULT_HOST = "http://localhost:11434"


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self,
        model: str,
        host: str = DEFAULT_HOST,
        timeout: float = 300.0,
        session: requests.Session | None = None,
    ):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def chat(self, messages, *, json_mode=False, temperature=0.0):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"
        url = f"{self.host}/api/chat"
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ProviderError(
                f"Could not reach Ollama at {self.host}. Is it running? ({exc})"
            ) from exc
        if response.status_code != 200:
            raise ProviderError(
                f"Ollama returned HTTP {response.status_code}: {response.text[:300]}"
            )
        try:
            return response.json()["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError("Unexpected response format from Ollama") from exc
