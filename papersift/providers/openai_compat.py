"""Provider for any OpenAI-compatible chat API (Groq, OpenRouter, Together, ...)."""

from __future__ import annotations

import time
from collections.abc import Callable

import requests

from papersift.providers._http import post_with_retry
from papersift.providers.base import LLMProvider, ProviderError


class OpenAICompatProvider(LLMProvider):
    """Talks to ``{base_url}/chat/completions``.

    ``use_json_mode`` sends ``response_format={"type": "json_object"}``. It is
    off by default because not every provider/model supports it; papersift's
    JSON parser is tolerant either way.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        name: str = "openai_compat",
        timeout: float = 120.0,
        max_retries: int = 4,
        use_json_mode: bool = False,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.name = name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_json_mode = use_json_mode
        self.session = session or requests.Session()
        self._sleep = sleep
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def chat(self, messages, *, json_mode=False, temperature=0.0):
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode and self.use_json_mode:
            payload["response_format"] = {"type": "json_object"}
        response = post_with_retry(
            self.session,
            f"{self.base_url}/chat/completions",
            headers=self._headers,
            json=payload,
            timeout=self.timeout,
            max_retries=self.max_retries,
            sleep=self._sleep,
        )
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Unexpected response format from {self.name}") from exc
        if not isinstance(content, str):
            raise ProviderError(f"{self.name} returned an empty message")
        return content
