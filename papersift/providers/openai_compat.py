"""OpenAI-compatible LLM provider."""

import requests
from typing import Optional

from .base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """Provider for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1"
    ):
        super().__init__(model_name)

        if not api_key:
            raise ValueError("API key is required.")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None
    ) -> str:

        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=120
            )

            response.raise_for_status()

            data = response.json()

            choices = data.get("choices", [])

            if not choices:
                raise RuntimeError(
                    "API returned no response choices."
                )

            content = choices[0].get(
                "message", {}
            ).get("content")

            if not isinstance(content, str) or not content.strip():
                raise RuntimeError(
                    "API returned an empty or unsupported response."
                )

            return content.strip()

        except requests.exceptions.RequestException as error:
            raise RuntimeError(
                f"OpenAI-compatible API request failed: {error}"
            ) from error