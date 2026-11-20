import pytest

from papersift import cli
from papersift.providers import FallbackProvider, OllamaProvider, ProviderError


def test_providers_command_lists_names(capsys):
    assert cli.main(["providers"]) == 0
    assert "ollama" in capsys.readouterr().out


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as info:
        cli.main(["--version"])
    assert info.value.code == 0 and "papersift" in capsys.readouterr().out


def test_run_requires_model():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["run", "my project"])


def test_build_provider_with_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    args = cli.build_parser().parse_args(
        ["run", "p", "--provider", "ollama", "--model", "llama3", "--fallback", "gemini=gemini-x"]
    )
    provider = cli.build_provider(args)
    assert isinstance(provider, FallbackProvider)
    assert isinstance(provider.providers[0], OllamaProvider)


def test_invalid_fallback_spec():
    args = cli.build_parser().parse_args(["run", "p", "--model", "m", "--fallback", "gemini"])
    with pytest.raises(ProviderError, match="PROVIDER=MODEL"):
        cli.build_provider(args)


def test_run_prints_friendly_error_on_missing_key(monkeypatch, capsys):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    code = cli.main(["run", "p", "--provider", "groq", "--model", "m"])
    assert code == 1 and "GROQ_API_KEY" in capsys.readouterr().err
