"""Data objects shared across papersift."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Paper:
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    published: datetime
    url: str
    pdf_url: str
    categories: list[str] = field(default_factory=list)

    @property
    def year(self) -> int:
        return self.published.year

    def to_dict(self) -> dict:
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "abstract": self.abstract,
            "authors": list(self.authors),
            "published_date": self.published.strftime("%Y-%m-%d"),
            "year": self.year,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "categories": list(self.categories),
        }
