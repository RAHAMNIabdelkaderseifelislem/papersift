"""Helpers for discovering locally installed Ollama models."""

from __future__ import annotations

import requests


class OllamaDiscoveryError(RuntimeError):
    """Raised when the Ollama model list cannot be retrieved or parsed."""


def list_ollama_models(host: str = "http://localhost:11434", timeout: float = 3.0) -> list[str]:
    """Return every model name reported by an Ollama server's /api/tags endpoint."""
    url = f"{host.rstrip('/')}/api/tags"
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise OllamaDiscoveryError(f"Could not connect to Ollama at {host}: {exc}") from exc
    except ValueError as exc:
        raise OllamaDiscoveryError("Ollama returned invalid JSON while listing installed models.") from exc

    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise OllamaDiscoveryError("Ollama's /api/tags response did not contain a models list.")

    names = sorted(
        {
            model["name"].strip()
            for model in models
            if isinstance(model, dict) and isinstance(model.get("name"), str) and model["name"].strip()
        },
        key=str.casefold,
    )
    return names
