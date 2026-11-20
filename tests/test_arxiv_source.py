from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from papersift.sources import SourceError
from papersift.sources.arxiv import ArxivSource, build_query


def test_build_query_quotes_each_keyword_and_joins_with_or():
    query = build_query(["self improving agents", 'llm "agents"'])
    assert query == '(all:"self improving agents" OR all:"llm  agents")'


def test_build_query_adds_date_window_in_arxiv_format():
    since = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    until = datetime(2026, 5, 6, 7, 8, tzinfo=timezone.utc)
    assert build_query(["a"], since, until).endswith("AND submittedDate:[202601020304 TO 202605060708]")


def test_build_query_rejects_empty_keywords():
    with pytest.raises(ValueError):
        build_query(["", "  "])


def fake_result(short_id, published):
    return SimpleNamespace(
        get_short_id=lambda: short_id,
        title="A  Title\nwith newline",
        summary="An   abstract.",
        authors=[SimpleNamespace(name="Ada"), SimpleNamespace(name="Bob")],
        published=published,
        entry_id=f"http://arxiv.org/abs/{short_id}",
        pdf_url=f"http://arxiv.org/pdf/{short_id}",
        categories=["cs.AI"],
    )


class FakeClient:
    def __init__(self, results=(), error=None):
        self._results, self._error = results, error
        self.searches = []

    def results(self, search):
        self.searches.append(search)
        if self._error:
            raise self._error
        yield from self._results


def test_search_converts_results_strips_version_and_normalizes_text():
    recent = datetime.now(timezone.utc) - timedelta(days=5)
    client = FakeClient([fake_result("2601.00001v2", recent)])
    papers = ArxivSource(client=client).search(["agents"], since_days=30, max_results=10)
    assert len(papers) == 1
    paper = papers[0]
    assert paper.arxiv_id == "2601.00001"
    assert paper.title == "A Title with newline"
    assert paper.abstract == "An abstract."
    assert paper.authors == ["Ada", "Bob"]
    assert client.searches[0].max_results == 10


def test_search_drops_papers_older_than_window():
    old = datetime.now(timezone.utc) - timedelta(days=400)
    recent = datetime.now(timezone.utc) - timedelta(days=1)
    client = FakeClient([fake_result("1.1", old), fake_result("2.2", recent)])
    papers = ArxivSource(client=client).search(["agents"], since_days=30)
    assert [p.arxiv_id for p in papers] == ["2.2"]


def test_search_wraps_failures_in_source_error():
    with pytest.raises(SourceError, match="arXiv search failed"):
        ArxivSource(client=FakeClient(error=RuntimeError("boom"))).search(["agents"])


def test_paper_to_dict():
    recent = datetime(2026, 3, 4, tzinfo=timezone.utc)
    from papersift.sources.arxiv import _to_paper

    data = _to_paper(fake_result("2601.00001v1", recent)).to_dict()
    assert data["published_date"] == "2026-03-04" and data["year"] == 2026
