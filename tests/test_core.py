import json

import pytest

from papersift.core import Scout
from papersift.download import DownloadError
from papersift.providers import MockProvider, ProviderError
from tests.helpers import FakeSource, make_paper, scripted_provider_responder

HIGH, LOW = (3, 3, 3), (1, 0, 0)


@pytest.fixture(autouse=True)
def fake_download(monkeypatch):
    calls = []

    def fake(paper, dest, session=None, timeout=60.0):
        calls.append(paper.arxiv_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"%PDF-fake")
        return dest

    monkeypatch.setattr("papersift.core.download_pdf", fake)
    return calls


def make_scout(tmp_path, papers, scores, **kwargs):
    provider = MockProvider(scripted_provider_responder(scores))
    return Scout("my project", provider, source=FakeSource(papers), output_dir=tmp_path, **kwargs), provider


def test_run_keeps_only_papers_above_threshold(tmp_path, fake_download):
    papers = [make_paper(1, "Great paper"), make_paper(2, "Weak paper")]
    scout, _ = make_scout(tmp_path, papers, {"Great paper": HIGH, "Weak paper": LOW})
    results = scout.run()
    assert [r.paper.title for r in results] == ["Great paper"]
    assert results[0].score == 100
    assert results[0].pdf_path.exists() and results[0].metadata_path.exists()
    assert fake_download == ["2601.00001"]  # the weak paper is never downloaded
    metadata = json.loads(results[0].metadata_path.read_text(encoding="utf-8"))
    assert metadata["assessments"]["abstract"]["score"] == 100


def test_results_sorted_by_score(tmp_path):
    papers = [make_paper(1, "Good paper"), make_paper(2, "Best paper")]
    scout, _ = make_scout(tmp_path, papers, {"Good paper": (3, 3, 0), "Best paper": HIGH}, relevance_threshold=50)
    assert [r.paper.title for r in scout.run()] == ["Best paper", "Good paper"]


def test_second_run_uses_the_cache_and_skips_llm_scoring(tmp_path):
    papers = [make_paper(1, "Great paper")]
    scout, provider = make_scout(tmp_path, papers, {"Great paper": HIGH})
    scout.run()
    calls_after_first = len(provider.calls)
    scout2, provider2 = make_scout(tmp_path, papers, {"Great paper": HIGH})
    scout2.run()
    # second run only needs the keyword call, not another scoring call
    assert calls_after_first == 2 and len(provider2.calls) == 1


def test_no_cache_option_rescored(tmp_path):
    papers = [make_paper(1, "Great paper")]
    make_scout(tmp_path, papers, {"Great paper": HIGH})[0].run()
    scout2, provider2 = make_scout(tmp_path, papers, {"Great paper": HIGH}, use_cache=False)
    scout2.run()
    assert len(provider2.calls) == 2


def test_unparseable_paper_is_skipped_not_fatal(tmp_path):
    def respond(messages):
        text = messages[-1]["content"]
        if "search keywords" in text:
            return '["alpha"]'
        return "garbage" if "Bad paper" in text else '{"topic_match":3,"method_match":3,"novelty":3}'

    papers = [make_paper(1, "Bad paper"), make_paper(2, "Fine paper")]
    scout = Scout("p", MockProvider(respond), source=FakeSource(papers), output_dir=tmp_path)
    assert [r.paper.title for r in scout.run()] == ["Fine paper"]


def test_stops_after_repeated_provider_errors(tmp_path):
    def respond(messages):
        if "search keywords" in messages[-1]["content"]:
            return '["alpha"]'
        raise ProviderError("quota exceeded")

    papers = [make_paper(i) for i in range(1, 10)]
    provider = MockProvider(respond)
    scout = Scout("p", provider, source=FakeSource(papers), output_dir=tmp_path)
    with pytest.raises(ProviderError, match="in a row"):
        scout.run()
    assert len(provider.calls) == 6  # 1 keyword call + 5 failures


def test_missing_pdf_does_not_lose_the_result(tmp_path, monkeypatch):
    def failing(paper, dest, session=None, timeout=60.0):
        raise DownloadError("offline")

    monkeypatch.setattr("papersift.core.download_pdf", failing)
    scout, _ = make_scout(tmp_path, [make_paper(1, "Great paper")], {"Great paper": HIGH})
    result = scout.run()[0]
    assert result.pdf_path is None and result.metadata_path.exists()


def test_search_parameters_are_passed_to_source(tmp_path):
    source = FakeSource([])
    scout = Scout("p", MockProvider(scripted_provider_responder({})), source=source,
                  output_dir=tmp_path, since_days=30, max_results=7)
    assert scout.run() == []
    assert source.calls == [(["alpha", "beta"], 30, 7)]
