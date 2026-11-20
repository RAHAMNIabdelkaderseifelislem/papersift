import pytest

from papersift.keywords import generate_keywords, parse_keywords
from papersift.providers import MockProvider
from papersift.utils import extract_json, sanitize_filename


def test_extract_json_plain_fenced_and_surrounded():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! Here you go: {"a": [1, 2]} Hope it helps.') == {"a": [1, 2]}
    assert extract_json('noise ["x", "y"] trailing') == ["x", "y"]


def test_extract_json_failures():
    with pytest.raises(ValueError):
        extract_json("no json here")
    with pytest.raises(ValueError):
        extract_json("")


def test_sanitize_filename():
    assert sanitize_filename("Héllo, Wörld: A Test!") == "hello_world_a_test"
    assert sanitize_filename("???") == "untitled"
    assert len(sanitize_filename("x" * 300)) == 80


def test_parse_keywords_json_and_plain_text():
    assert parse_keywords('["self-improving agents", "LLM agents"]') == ["self-improving agents", "LLM agents"]
    assert parse_keywords('{"keywords": ["a", "b"]}') == ["a", "b"]
    assert parse_keywords("1. alpha\n2) beta\n- gamma, delta") == ["alpha", "beta", "gamma", "delta"]
    assert parse_keywords('["A", "a", " "]') == ["A"]


def test_generate_keywords_uses_provider_and_limits():
    provider = MockProvider(['["k1", "k2", "k3"]'])
    assert generate_keywords(provider, "my project", count=2) == ["k1", "k2", "k3"]
    assert "my project" in provider.calls[0][-1]["content"]


def test_generate_keywords_fails_when_empty():
    with pytest.raises(ValueError):
        generate_keywords(MockProvider(["[]"]), "x")
