"""Try several providers in order until one works."""

from __future__ import annotations

import logging

from papersift.providers.base import LLMProvider, ProviderError

logger = logging.getLogger(__name__)


class FallbackProvider(LLMProvider):
    """Calls ``providers`` in order; moves to the next one when a call fails."""

    def __init__(self, providers: list[LLMProvider]):
        if not providers:
            raise ValueError("FallbackProvider needs at least one provider")
        self.providers = providers
        self.name = "fallback(" + ",".join(p.name for p in providers) + ")"

    def chat(self, messages, *, json_mode=False, temperature=0.0):
        errors: list[str] = []
        for provider in self.providers:
            try:
                return provider.chat(messages, json_mode=json_mode, temperature=temperature)
            except ProviderError as exc:
                logger.warning("Provider %s failed (%s); trying the next one", provider.name, exc)
                errors.append(f"{provider.name}: {exc}")
        raise ProviderError("All providers failed: " + " | ".join(errors))
