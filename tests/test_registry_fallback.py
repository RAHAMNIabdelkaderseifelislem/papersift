import pytest

from papersift.providers import (
    FallbackProvider,
    GeminiProvider,
    MockProvider,
    OllamaProvider,
    OpenAICompatProvider,
    ProviderError,
    available_providers,
    create_provider,
)


class Failing(MockProvider):
    name = "failing"

    def chat(self, messages, **kwargs):
        raise ProviderError("down")


def test_available_providers_lists_presets():
    names = available_providers()
    assert {"ollama", "gemini", "groq", "openrouter", "openai_compat"} <= set(names)


def test_create_ollama_needs_no_key():
    assert isinstance(create_provider("ollama", "llama3"), OllamaProvider)


def test_create_preset_reads_key_from_environment(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    provider = create_provider("groq", "some-model")
    assert isinstance(provider, OpenAICompatProvider)
    assert provider.base_url == "https://api.groq.com/openai/v1"
    assert provider.name == "groq"


def test_missing_key_gives_helpful_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="GEMINI_API_KEY"):
        create_provider("gemini", "m")


def test_create_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert isinstance(create_provider("gemini", "m"), GeminiProvider)


def test_generic_provider_requires_base_url(monkeypatch):
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "k")
    with pytest.raises(ProviderError, match="base URL"):
        create_provider("openai_compat", "m")
    assert create_provider("openai_compat", "m", base_url="http://x/v1").base_url == "http://x/v1"


def test_unknown_provider():
    with pytest.raises(ProviderError, match="Unknown provider"):
        create_provider("nope", "m")


def test_fallback_uses_next_provider_after_failure():
    chain = FallbackProvider([Failing(), MockProvider(["from second"])])
    assert chain.complete("hi") == "from second"
    assert chain.name == "fallback(failing,mock)"


def test_fallback_raises_when_all_fail():
    with pytest.raises(ProviderError, match="All providers failed"):
        FallbackProvider([Failing(), Failing()]).complete("hi")


def test_fallback_needs_providers():
    with pytest.raises(ValueError):
        FallbackProvider([])
