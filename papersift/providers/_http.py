"""Shared HTTP helper: POST with retry and exponential backoff."""

from __future__ import annotations

import time
from collections.abc import Callable

import requests

from papersift.providers.base import ProviderError, RateLimitError

MAX_BACKOFF_SECONDS = 60.0


def _retry_after(response, default: float) -> float:
    """Use the server's Retry-After header (seconds) when it is a number."""
    header = response.headers.get("Retry-After") if response.headers else None
    try:
        return min(float(header), MAX_BACKOFF_SECONDS)
    except (TypeError, ValueError):
        return default


def post_with_retry(
    session,
    url: str,
    *,
    headers: dict[str, str],
    json: dict,
    timeout: float,
    max_retries: int = 4,
    backoff: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
):
    """POST ``json`` to ``url`` and return the successful response.

    Retries on network errors, HTTP 429 and HTTP 5xx, waiting
    ``backoff * 2**attempt`` seconds (or the server's Retry-After).
    Other HTTP errors (400, 401, 403, 404...) fail immediately because
    retrying will not fix them.
    """
    last_error: str = "unknown error"
    rate_limited = False
    for attempt in range(max_retries + 1):
        delay = min(backoff * (2**attempt), MAX_BACKOFF_SECONDS)
        try:
            response = session.post(url, headers=headers, json=json, timeout=timeout)
        except requests.RequestException as exc:
            last_error = f"network error: {exc}"
            rate_limited = False
        else:
            status = response.status_code
            if status == 200:
                return response
            if status == 429 or status >= 500:
                last_error = f"HTTP {status}: {response.text[:200]}"
                rate_limited = status == 429
                delay = _retry_after(response, delay)
            else:
                raise ProviderError(f"HTTP {status}: {response.text[:300]}")
        if attempt < max_retries:
            sleep(delay)
    message = f"Giving up after {max_retries + 1} attempts ({last_error})"
    raise (RateLimitError if rate_limited else ProviderError)(message)
