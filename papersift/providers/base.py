"""Common interface that every LLM provider implements."""

from __future__ import annotations

from abc import ABC, abstractmethod

Message = dict[str, str]  # {"role": "system" | "user" | "assistant", "content": "..."}


class ProviderError(Exception):
    """Raised when an LLM provider fails (network, auth, bad response...)."""


class RateLimitError(ProviderError):
    """Raised when a provider keeps answering 'too many requests'."""


class LLMProvider(ABC):
    """Minimal chat interface used by the rest of papersift.

    Implementations only have to provide ``chat``; ``complete`` is a
    convenience wrapper for the common "one system prompt + one user prompt"
    case.
    """

    name: str = "provider"

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        *,
        json_mode: bool = False,
        temperature: float = 0.0,
    ) -> str:
        """Send a conversation and return the assistant's text reply."""

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_mode: bool = False,
        temperature: float = 0.0,
    ) -> str:
        messages: list[Message] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, json_mode=json_mode, temperature=temperature)
