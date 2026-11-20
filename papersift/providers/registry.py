"""Create providers by name, reading API keys from environment variables."""

from __future__ import annotations

import os

from papersift.providers.base import LLMProvider, ProviderError
from papersift.providers.gemini import GeminiProvider
from papersift.providers.ollama import OllamaProvider
from papersift.providers.openai_compat import OpenAICompatProvider

# name -> (base_url, environment variable holding the API key)
OPENAI_COMPAT_PRESETS: dict[str, tuple[str, str]] = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "together": ("https://api.together.xyz/v1", "TOGETHER_API_KEY"),
    "cerebras": ("https://api.cerebras.ai/v1", "CEREBRAS_API_KEY"),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
}
GENERIC_KEY_ENV = "OPENAI_COMPAT_API_KEY"


def available_providers() -> list[str]:
    return sorted(["ollama", "gemini", "openai_compat", *OPENAI_COMPAT_PRESETS])


def _require_key(api_key: str | None, env_var: str, provider: str) -> str:
    key = api_key or os.environ.get(env_var)
    if not key:
        raise ProviderError(f"Missing API key for '{provider}'. Set the {env_var} environment variable.")
    return key


def create_provider(
    name: str,
    model: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs,
) -> LLMProvider:
    """Build a provider from its short name (see ``available_providers()``)."""
    name = name.lower().strip()
    if name == "ollama":
        return OllamaProvider(model, **({"host": base_url} if base_url else {}), **kwargs)
    if name == "gemini":
        key = _require_key(api_key, "GEMINI_API_KEY", name)
        return GeminiProvider(model, key, **({"base_url": base_url} if base_url else {}), **kwargs)
    if name == "openai_compat":
        if not base_url:
            raise ProviderError("The 'openai_compat' provider needs a base URL (--base-url).")
        key = _require_key(api_key, GENERIC_KEY_ENV, name)
        return OpenAICompatProvider(model, key, base_url, name=name, **kwargs)
    if name in OPENAI_COMPAT_PRESETS:
        default_url, env_var = OPENAI_COMPAT_PRESETS[name]
        key = _require_key(api_key, env_var, name)
        return OpenAICompatProvider(model, key, base_url or default_url, name=name, **kwargs)
    raise ProviderError(f"Unknown provider '{name}'. Available: {', '.join(available_providers())}")
