"""A fake provider for tests and offline demos (no network, no API key)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from papersift.providers.base import LLMProvider, Message, ProviderError

Responder = Callable[[list[Message]], str]


class MockProvider(LLMProvider):
    """Returns scripted answers.

    ``responses`` is either a list of strings (returned in order, the last one
    repeats forever) or a function ``messages -> str``. Every call is recorded
    in ``self.calls``.
    """

    name = "mock"

    def __init__(self, responses: Sequence[str] | Responder = ("{}",)):
        self._responses = responses
        self._index = 0
        self.calls: list[list[Message]] = []

    def chat(self, messages, *, json_mode=False, temperature=0.0):
        self.calls.append(list(messages))
        if callable(self._responses):
            return self._responses(messages)
        if not self._responses:
            raise ProviderError("MockProvider has no responses configured")
        answer = self._responses[min(self._index, len(self._responses) - 1)]
        self._index += 1
        return answer
