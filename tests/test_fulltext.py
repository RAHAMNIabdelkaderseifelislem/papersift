import pytest

from papersift.providers import MockProvider
from papersift.ranking.fulltext import (
    FulltextError,
    assess_fulltext,
    combine_scores,
    extract_text,
    select_sections,
)
from tests.helpers import make_paper, rubric_reply

PAPER_TEXT = """Title
Abstract
Short abstract.
1 Introduction
INTRO BODY text about the problem.
2 Related Work
Some related work.
3 Methodology
METHOD BODY text describing the approach.
4 Experiments
Many numbers.
5 Conclusion
CONCLUSION BODY wrap up.
References
[1] A ref.
"""


def test_select_sections_picks_intro_method_conclusion():
    excerpts = select_sections(PAPER_TEXT, max_chars=900)
    assert "INTRO BODY" in excerpts and "METHOD BODY" in excerpts and "CONCLUSION BODY" in excerpts
    assert "[INTRODUCTION]" in excerpts and "[CONCLUSION]" in excerpts


def test_select_sections_respects_budget():
    text = "1 Introduction\n" + "x" * 5000 + "\n3 Method\n" + "y" * 5000 + "\n5 Conclusion\n" + "z" * 5000
    assert len(select_sections(text, max_chars=600)) < 700


def test_conclusion_uses_last_heading_to_skip_table_of_contents():
    text = "Contents\nConclusion\n\n1 Introduction\nbody\n5 Conclusion\nREAL CONCLUSION"
    assert "REAL CONCLUSION" in select_sections(text, max_chars=500)


def test_fallback_to_head_and_tail_without_headings():
    text = "A" * 5000 + "B" * 5000
    excerpts = select_sections(text, max_chars=1000)
    assert excerpts.startswith("A") and excerpts.endswith("B") and "[...]" in excerpts


def test_short_text_without_headings_is_returned_whole():
    assert select_sections("just a little text", max_chars=1000) == "just a little text"


def test_combine_scores_weights_fulltext_more():
    assert combine_scores(70, 100) == 88
    assert combine_scores(100, 0) == 40
    assert combine_scores(80, 60, fulltext_weight=0.5) == 70


def test_assess_fulltext_includes_excerpts_and_marks_stage():
    provider = MockProvider([rubric_reply(3, 3, 3)])
    assessment = assess_fulltext(provider, "project", make_paper(1), "EXCERPT TEXT")
    assert assessment.stage == "fulltext" and assessment.score == 100
    assert "EXCERPT TEXT" in provider.calls[0][-1]["content"]


def test_extract_text_reads_a_real_pdf(tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Introduction\n" + "\n".join("Hello papersift, this is line %d." % i for i in range(20)))
    path = tmp_path / "paper.pdf"
    doc.save(str(path))
    doc.close()
    assert "Hello papersift" in extract_text(path)


def test_extract_text_rejects_garbage(tmp_path):
    pytest.importorskip("pymupdf")
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(FulltextError):
        extract_text(bad)
