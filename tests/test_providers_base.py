import pytest

from papersift.providers import MockProvider, ProviderError


def test_complete_builds_system_and_user_messages():
    provider = MockProvider(["hello"])
    assert provider.complete("question", system="be brief") == "hello"
    assert provider.calls[0] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "question"},
    ]


def test_complete_without_system_prompt():
    provider = MockProvider(["x"])
    provider.complete("question")
    assert provider.calls[0] == [{"role": "user", "content": "question"}]


def test_mock_returns_responses_in_order_then_repeats_last():
    provider = MockProvider(["a", "b"])
    assert [provider.complete("1"), provider.complete("2"), provider.complete("3")] == ["a", "b", "b"]


def test_mock_accepts_a_function():
    provider = MockProvider(lambda messages: messages[-1]["content"].upper())
    assert provider.complete("abc") == "ABC"


def test_mock_without_responses_raises():
    with pytest.raises(ProviderError):
        MockProvider([]).complete("x")
