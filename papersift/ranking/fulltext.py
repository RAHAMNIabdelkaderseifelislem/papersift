"""Stage 2: deeper scoring from the paper's full text.

Full papers are too long for most free-tier context windows, so we extract
the text, keep the most informative sections (introduction, method,
conclusion) within a character budget, and score those excerpts.
"""

from __future__ import annotations

import re
from pathlib import Path

from papersift.models import Paper
from papersift.providers import LLMProvider
from papersift.ranking.rubric import RUBRIC_INSTRUCTIONS, Assessment, run_rubric_assessment

DEFAULT_MAX_CHARS = 12000

SYSTEM = (
    "You are a careful research assistant helping with a literature review. "
    "You are given the title, abstract and selected excerpts of a paper. "
    "Judge only from the text you are given and do not invent details.\n\n" + RUBRIC_INSTRUCTIONS
)

_HEADING = re.compile(
    r"^[ \t]*(?:\d+(?:\.\d+)*\.?[ \t]+|[IVX]+\.[ \t]+)?"
    r"(?P<name>introduction|methods?|methodology|proposed method|approach|conclusions?"
    r"|conclusions? and future work)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
_GROUPS = {
    "introduction": "introduction",
    "method": "method",
    "methods": "method",
    "methodology": "method",
    "proposed method": "method",
    "approach": "method",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "conclusion and future work": "conclusion",
    "conclusions and future work": "conclusion",
}


class FulltextError(Exception):
    """Full-text ranking is unavailable or the PDF could not be read."""


def _pymupdf():
    try:
        import pymupdf  # PyMuPDF >= 1.24.3

        return pymupdf
    except ImportError:
        try:
            import fitz  # older PyMuPDF versions

            return fitz
        except ImportError as exc:
            raise FulltextError(
                'Full-text ranking needs PyMuPDF. Install it with: pip install "papersift[fulltext]"'
            ) from exc


def require_pymupdf() -> None:
    _pymupdf()


def extract_text(pdf_path: str | Path, max_pages: int | None = 40) -> str:
    """Return the text of a PDF (first ``max_pages`` pages)."""
    lib = _pymupdf()
    try:
        with lib.open(str(pdf_path)) as doc:
            pages = [page.get_text() for index, page in enumerate(doc) if max_pages is None or index < max_pages]
    except Exception as exc:  # noqa: BLE001 - corrupted/encrypted files raise various errors
        raise FulltextError(f"Could not read PDF {pdf_path}: {exc}") from exc
    text = "\n".join(pages).strip()
    if len(text) < 200:
        raise FulltextError(f"No usable text in {pdf_path} (scanned PDF?)")
    return text


def select_sections(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Pick introduction, method and conclusion excerpts that fit ``max_chars``.

    Falls back to the beginning and the end of the paper when no section
    headings can be recognised.
    """
    found: dict[str, int] = {}
    for match in _HEADING.finditer(text):
        group = _GROUPS.get(" ".join(match.group("name").lower().split()))
        if group is None:
            continue
        if group == "conclusion":
            found[group] = match.end()  # keep the LAST one: skips a table of contents
        else:
            found.setdefault(group, match.end())  # keep the FIRST one
    if not found:
        head = int(max_chars * 0.6)
        tail = max_chars - head
        if len(text) <= max_chars:
            return text
        return f"{text[:head]}\n[...]\n{text[-tail:]}"
    per_section = max_chars // len(found)
    parts = []
    for group in ("introduction", "method", "conclusion"):
        if group in found:
            start = found[group]
            parts.append(f"[{group.upper()}]\n{text[start:start + per_section].strip()}")
    return "\n\n".join(parts)


def assess_fulltext(
    provider: LLMProvider, project_title: str, paper: Paper, excerpts: str
) -> Assessment:
    prompt = (
        f"Research project: {project_title}\n\n"
        f"Paper title: {paper.title}\n"
        f"Abstract: {paper.abstract}\n\n"
        f"Excerpts from the paper:\n{excerpts}"
    )
    return run_rubric_assessment(provider, SYSTEM, prompt, stage="fulltext")


def combine_scores(abstract_score: int, fulltext_score: int, fulltext_weight: float = 0.6) -> int:
    """Blend the two stages; the full text counts more because it is better evidence."""
    return round((1 - fulltext_weight) * abstract_score + fulltext_weight * fulltext_score)
