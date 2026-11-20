"""Paper sources (where candidate papers come from)."""

from __future__ import annotations

from typing import Protocol

from papersift.models import Paper


class SourceError(Exception):
    """Raised when a paper source cannot be queried."""


class PaperSource(Protocol):
    def search(self, keywords: list[str], *, since_days: int, max_results: int) -> list[Paper]:
        """Return candidate papers matching any keyword, newest window first."""


__all__ = ["PaperSource", "SourceError"]
