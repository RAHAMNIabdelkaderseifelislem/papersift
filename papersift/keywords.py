"""Turn a project description into arXiv search keywords with an LLM."""

from __future__ import annotations

import re

from papersift.providers import LLMProvider
from papersift.utils import extract_json


def parse_keywords(text: str, limit: int = 12) -> list[str]:
    """Accept a JSON list, or a comma/newline separated list, and clean it up."""
    items: list[str]
    try:
        data = extract_json(text)
        if isinstance(data, dict):
            data = next((v for v in data.values() if isinstance(v, list)), [])
        items = [str(x) for x in data] if isinstance(data, list) else []
    except ValueError:
        items = re.split(r"[,\n;]", text)
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        keyword = re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s*", "", item).strip().strip("\"'`")
        if keyword and keyword.lower() not in seen:
            seen.add(keyword.lower())
            cleaned.append(keyword)
    return cleaned[:limit]


def generate_keywords(provider: LLMProvider, project_title: str, count: int = 6) -> list[str]:
    prompt = (
        f"Generate {count} specific, technical academic search keywords or short phrases "
        f"for finding research papers related to this project: '{project_title}'.\n"
        "Return ONLY a JSON array of strings, nothing else."
    )
    keywords = parse_keywords(provider.complete(prompt, json_mode=True), limit=count * 2)
    if not keywords:
        raise ValueError("The model did not return any usable keywords")
    return keywords
