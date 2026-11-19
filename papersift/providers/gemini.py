"""Google Gemini LLM provider."""

import requests
from typing import Optional

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    """LLM provider implementation for Google Gemini."""

    API_URL = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
    )

    def __init__(self, model_name: str, api_key: str):
        super().__init__(model_name)

        if not api_key:
            raise ValueError("Gemini API key is required.")

        self.api_key = api_key

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None
    ) -> str:

        url = (
            f"{self.API_URL}{self.model_name}:generateContent"
        )

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        contents = [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature
            }
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        if max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=120
            )

            response.raise_for_status()

            data = response.json()

            candidates = data.get("candidates", [])

            if not candidates:
                raise RuntimeError(
                    "Gemini returned no response candidates."
                )

            parts = candidates[0].get(
                "content", {}
            ).get("parts", [])

            result = "\n".join(
                part["text"]
                for part in parts
                if "text" in part
            )

            if not result:
                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            return result

        except requests.exceptions.RequestException as error:
            raise RuntimeError(
                f"Gemini API request failed: {error}"
            ) from error