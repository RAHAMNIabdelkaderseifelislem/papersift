import pytest

from papersift.core import Scout
from papersift.providers import MockProvider
from papersift.ranking.fulltext import FulltextError
from tests.helpers import FakeSource, make_paper, rubric_reply

# (topic, method, novelty) -> score:  (3,2,0)=70  (3,3,3)=100  (0,0,0)=0  (1,0,0)=17
ABSTRACT = {"Rising paper": (3, 2, 0), "Falling paper": (3, 3, 3), "Weak paper": (1, 0, 0), "Third paper": (3, 2, 0)}
FULLTEXT = {"Rising paper": (3, 3, 3), "Falling paper": (0, 0, 0), "Third paper": (3, 3, 3)}


@pytest.fixture(autouse=True)
def fake_io(monkeypatch):
    downloads = []

    def fake_download(paper, dest, session=None, timeout=60.0):
        downloads.append(paper.arxiv_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"%PDF-fake")
        return dest

    monkeypatch.setattr("papersift.core.download_pdf", fake_download)
    monkeypatch.setattr("papersift.core.extract_text", lambda path: "1 Introduction\nbody")
    return downloads


def responder(messages):
    text = messages[-1]["content"]
    if "search keywords" in text:
        return '["alpha"]'
    table = FULLTEXT if "Excerpts from the paper" in text else ABSTRACT
    for title, rubric in table.items():
        if f"Paper title: {title}" in text:
            return rubric_reply(*rubric)
    return rubric_reply(0, 0, 0)


def make(tmp_path, titles, **kwargs):
    papers = [make_paper(i, t) for i, t in enumerate(titles, start=1)]
    scout = Scout("p", MockProvider(responder), source=FakeSource(papers), output_dir=tmp_path,
                  fulltext=True, **kwargs)
    return scout


def test_fulltext_can_promote_and_demote_papers(tmp_path):
    results = make(tmp_path, ["Rising paper", "Falling paper"]).run()
    # Rising: abstract 70 -> combined 88 (kept). Falling: abstract 100 -> combined 40 (dropped).
    assert [r.paper.title for r in results] == ["Rising paper"]
    assert results[0].score == 88
    assert results[0].fulltext_assessment.score == 100
    assert results[0].abstract_assessment.score == 70


def test_papers_below_triage_threshold_are_never_downloaded(tmp_path, fake_io):
    make(tmp_path, ["Rising paper", "Weak paper"]).run()
    assert fake_io == ["2601.00001"]


def test_top_k_limits_how_many_are_read_in_full(tmp_path, fake_io):
    make(tmp_path, ["Rising paper", "Third paper", "Falling paper"], top_k_fulltext=1).run()
    assert len(fake_io) == 1


def test_fulltext_failure_falls_back_to_abstract_score(tmp_path, monkeypatch):
    def broken(path):
        raise FulltextError("scanned pdf")

    monkeypatch.setattr("papersift.core.extract_text", broken)
    results = make(tmp_path, ["Falling paper"]).run()  # abstract score 100 >= 80
    assert [r.score for r in results] == [100] and results[0].fulltext_assessment is None


def test_fulltext_scores_are_cached(tmp_path):
    make(tmp_path, ["Rising paper"]).run()
    second = make(tmp_path, ["Rising paper"])
    second.run()
    assert len(second.provider.calls) == 1  # only the keyword call


def test_missing_pymupdf_fails_early(tmp_path, monkeypatch):
    def missing():
        raise FulltextError("install it")

    monkeypatch.setattr("papersift.core.require_pymupdf", missing)
    with pytest.raises(FulltextError):
        make(tmp_path, ["Rising paper"])
