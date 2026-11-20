"""arXiv search."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import arxiv

from papersift.models import Paper
from papersift.sources import SourceError


def build_query(
    keywords: list[str],
    since: datetime | None = None,
    until: datetime | None = None,
) -> str:
    """Build an arXiv query: each keyword as an exact phrase, joined with OR.

    The date filter uses arXiv's ``submittedDate:[YYYYMMDDHHMM TO YYYYMMDDHHMM]``
    syntax (GMT).
    """
    terms = []
    for keyword in keywords:
        cleaned = keyword.replace('"', " ").strip()
        if cleaned:
            terms.append(f'all:"{cleaned}"')
    if not terms:
        raise ValueError("At least one non-empty keyword is required")
    query = "(" + " OR ".join(terms) + ")"
    if since is not None:
        until = until or datetime.now(timezone.utc)
        query += f" AND submittedDate:[{since:%Y%m%d%H%M} TO {until:%Y%m%d%H%M}]"
    return query


def _to_paper(result) -> Paper:
    arxiv_id = re.sub(r"v\d+$", "", result.get_short_id())
    return Paper(
        arxiv_id=arxiv_id,
        title=" ".join(result.title.split()),
        abstract=" ".join(result.summary.split()),
        authors=[author.name for author in result.authors],
        published=result.published,
        url=result.entry_id,
        pdf_url=result.pdf_url,
        categories=list(result.categories),
    )


class ArxivSource:
    """Searches arXiv through the official ``arxiv`` package."""

    def __init__(self, client=None, page_size: int = 100, delay_seconds: float = 3.0, num_retries: int = 3):
        self.client = client or arxiv.Client(
            page_size=page_size, delay_seconds=delay_seconds, num_retries=num_retries
        )

    def search(self, keywords: list[str], *, since_days: int = 365, max_results: int = 100) -> list[Paper]:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=since_days)
        query = build_query(keywords, since=since, until=now)
        search = arxiv.Search(
            query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance
        )
        papers: list[Paper] = []
        try:
            for result in self.client.results(search):
                paper = _to_paper(result)
                published = paper.published
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
                if published >= since:  # safety net in case the API filter is loose
                    papers.append(paper)
        except Exception as exc:  # noqa: BLE001 - wrap any library/network failure
            raise SourceError(f"arXiv search failed: {exc}") from exc
        return papers
