import pytest
import requests

from papersift.providers import OllamaProvider, ProviderError
from tests.conftest import FakeResponse, FakeSession


def test_chat_returns_message_content_and_sends_json_format():
    session = FakeSession([FakeResponse(200, {"message": {"content": "hi"}})])
    provider = OllamaProvider("llama3", session=session)
    assert provider.complete("hello", json_mode=True) == "hi"
    call = session.calls[0]
    assert call["url"] == "http://localhost:11434/api/chat"
    assert call["json"]["model"] == "llama3"
    assert call["json"]["format"] == "json"
    assert call["json"]["stream"] is False


def test_connection_error_becomes_provider_error():
    session = FakeSession([requests.ConnectionError("refused")])
    with pytest.raises(ProviderError, match="Is it running"):
        OllamaProvider("llama3", session=session).complete("hello")


def test_http_error_becomes_provider_error():
    session = FakeSession([FakeResponse(500, text="boom")])
    with pytest.raises(ProviderError, match="500"):
        OllamaProvider("llama3", session=session).complete("hello")


def test_malformed_body_becomes_provider_error():
    session = FakeSession([FakeResponse(200, {"unexpected": True})])
    with pytest.raises(ProviderError):
        OllamaProvider("llama3", session=session).complete("hello")
