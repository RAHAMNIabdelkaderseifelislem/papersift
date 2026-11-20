import pytest

from papersift.providers import OpenAICompatProvider, ProviderError
from tests.conftest import FakeResponse, FakeSession

OK = FakeResponse(200, {"choices": [{"message": {"content": "answer"}}]})


def make(session, **kwargs):
    return OpenAICompatProvider(
        "model-x", "secret", "https://api.example.com/v1/", session=session, sleep=lambda s: None, **kwargs
    )


def test_chat_returns_content_and_sends_auth_header():
    session = FakeSession([OK])
    assert make(session).complete("hi", system="sys") == "answer"
    call = session.calls[0]
    assert call["url"] == "https://api.example.com/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer secret"
    assert call["json"]["model"] == "model-x"
    assert "response_format" not in call["json"]


def test_json_mode_only_sent_when_enabled():
    session = FakeSession([OK])
    make(session, use_json_mode=True).complete("hi", json_mode=True)
    assert session.calls[0]["json"]["response_format"] == {"type": "json_object"}


def test_retries_rate_limit_then_succeeds():
    session = FakeSession([FakeResponse(429), OK])
    assert make(session).complete("hi") == "answer"
    assert len(session.calls) == 2


def test_malformed_response_raises():
    session = FakeSession([FakeResponse(200, {"nope": 1})])
    with pytest.raises(ProviderError, match="Unexpected"):
        make(session).complete("hi")


def test_api_key_is_never_in_error_messages():
    session = FakeSession([FakeResponse(401, text="invalid key")])
    with pytest.raises(ProviderError) as info:
        make(session).complete("hi")
    assert "secret" not in str(info.value)
