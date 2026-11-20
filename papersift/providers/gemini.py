"""Google Gemini provider (REST API, no extra dependency)."""

from __future__ import annotations

import time
from collections.abc import Callable

import requests

from papersift.providers._http import post_with_retry
from papersift.providers.base import LLMProvider, ProviderError

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 120.0,
        max_retries: int = 4,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self._sleep = sleep
        # The key travels in a header, not in the URL, so it never shows up in logs.
        self._headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    @staticmethod
    def _to_payload(messages, json_mode: bool, temperature: float) -> dict:
        system_parts = []
        contents = []
        for message in messages:
            role, text = message["role"], message["content"]
            if role == "system":
                system_parts.append({"text": text})
            else:
                contents.append(
                    {"role": "model" if role == "assistant" else "user", "parts": [{"text": text}]}
                )
        generation_config: dict = {"temperature": temperature}
        if json_mode:
            generation_config["responseMimeType"] = "application/json"
        payload: dict = {"contents": contents, "generationConfig": generation_config}
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}
        return payload

    def chat(self, messages, *, json_mode=False, temperature=0.0):
        response = post_with_retry(
            self.session,
            f"{self.base_url}/models/{self.model}:generateContent",
            headers=self._headers,
            json=self._to_payload(messages, json_mode, temperature),
            timeout=self.timeout,
            max_retries=self.max_retries,
            sleep=self._sleep,
        )
        try:
            data = response.json()
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            feedback = ""
            try:
                feedback = f" ({response.json().get('promptFeedback')})"
            except Exception:  # noqa: BLE001 - best-effort detail only
                pass
            raise ProviderError(f"Unexpected response format from Gemini{feedback}") from exc
