import pytest

from papersift.providers import GeminiProvider, ProviderError
from tests.conftest import FakeResponse, FakeSession


def make(session):
    return GeminiProvider("gemini-test", "secret-key", session=session, sleep=lambda s: None)


def reply(text):
    return FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": text}]}}]})


def test_payload_maps_roles_and_system_instruction():
    session = FakeSession([reply("ok")])
    make(session).chat(
        [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
        ],
        json_mode=True,
        temperature=0.2,
    )
    call = session.calls[0]
    body = call["json"]
    assert call["url"].endswith("/models/gemini-test:generateContent")
    assert "secret-key" not in call["url"]
    assert call["headers"]["x-goog-api-key"] == "secret-key"
    assert body["systemInstruction"] == {"parts": [{"text": "rules"}]}
    assert [c["role"] for c in body["contents"]] == ["user", "model", "user"]
    assert body["generationConfig"] == {"temperature": 0.2, "responseMimeType": "application/json"}


def test_chat_joins_text_parts():
    response = FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": "a"}, {"text": "b"}]}}]})
    assert make(FakeSession([response])).complete("hi") == "ab"


def test_blocked_prompt_raises_provider_error():
    response = FakeResponse(200, {"promptFeedback": {"blockReason": "SAFETY"}})
    with pytest.raises(ProviderError, match="SAFETY"):
        make(FakeSession([response])).complete("hi")
