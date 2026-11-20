"""Small helpers shared across modules."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any


def extract_json(text: str) -> Any:
    """Parse the first JSON object/array found in an LLM reply.

    Handles replies wrapped in markdown code fences or surrounded by prose.
    Raises ``ValueError`` when no valid JSON is found.
    """
    if not text or not text.strip():
        raise ValueError("Empty reply, no JSON found")
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(cleaned)
    except ValueError:
        pass
    decoder = json.JSONDecoder()
    for match in re.finditer(r"[{\[]", cleaned):
        try:
            value, _ = decoder.raw_decode(cleaned[match.start():])
        except ValueError:
            continue
        return value
    raise ValueError("No valid JSON found in the reply")


def sanitize_filename(title: str, max_length: int = 80) -> str:
    """Turn a title into a safe, lowercase, underscore-separated file name part."""
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_title).strip("_").lower()
    return slug[:max_length].strip("_") or "untitled"
