"""Scout: the pipeline that ties providers, sources, ranking and storage together."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from papersift.download import DownloadError, download_pdf, pdf_filename, safe_id, write_metadata
from papersift.keywords import generate_keywords
from papersift.models import Paper
from papersift.providers import LLMProvider, ProviderError
from papersift.ranking import Assessment, AssessmentError, assess_abstract
from papersift.ranking.fulltext import (
    FulltextError,
    assess_fulltext,
    combine_scores,
    extract_text,
    require_pymupdf,
    select_sections,
)
from papersift.sources import PaperSource
from papersift.sources.arxiv import ArxivSource
from papersift.store import Store

logger = logging.getLogger("papersift")

MAX_CONSECUTIVE_PROVIDER_ERRORS = 5


@dataclass
class ScoutResult:
    paper: Paper
    score: int
    abstract_assessment: Assessment
    fulltext_assessment: Assessment | None = None
    pdf_path: Path | None = None
    metadata_path: Path | None = None
    from_cache: bool = False


class Scout:
    """Find, score and download the papers most relevant to a project.

    Typical use::

        scout = Scout("my project", provider)
        results = scout.run()
    """

    def __init__(
        self,
        project_title: str,
        provider: LLMProvider,
        *,
        relevance_threshold: int = 80,
        since_days: int = 365,
        max_results: int = 100,
        n_keywords: int = 6,
        output_dir: str | Path = "papersift_output",
        source: PaperSource | None = None,
        use_cache: bool = True,
        fulltext: bool = False,
        triage_threshold: int = 60,
        top_k_fulltext: int = 10,
        fulltext_weight: float = 0.6,
        max_fulltext_chars: int = 12000,
    ):
        self.project_title = project_title
        self.provider = provider
        self.relevance_threshold = relevance_threshold
        self.since_days = since_days
        self.max_results = max_results
        self.n_keywords = n_keywords
        self.output_dir = Path(output_dir)
        self.source = source or ArxivSource()
        self.use_cache = use_cache
        self.fulltext = fulltext
        self.triage_threshold = triage_threshold
        self.top_k_fulltext = top_k_fulltext
        self.fulltext_weight = fulltext_weight
        self.max_fulltext_chars = max_fulltext_chars
        if fulltext:
            require_pymupdf()  # fail early, before spending any LLM calls
        self.pdfs_dir = self.output_dir / "pdfs"
        self.metadata_dir = self.output_dir / "metadata"
        self.cache_dir = self.output_dir / ".cache"

    # ------------------------------------------------------------------ run
    def run(self) -> list[ScoutResult]:
        with Store(self.cache_dir / "papersift.sqlite3", self.project_title) as store:
            keywords = generate_keywords(self.provider, self.project_title, self.n_keywords)
            logger.info("Search keywords: %s", ", ".join(keywords))
            papers = self.source.search(keywords, since_days=self.since_days, max_results=self.max_results)
            logger.info("Found %d candidate papers", len(papers))

            scored = self._stage_one(papers, store)
            selected = self._select(scored, store)

            results = [self._finalize(paper, score, assessments, store) for paper, score, assessments in selected]
        results.sort(key=lambda r: r.score, reverse=True)
        logger.info("Kept %d papers (threshold %d)", len(results), self.relevance_threshold)
        return results

    # -------------------------------------------------------------- stage 1
    def _stage_one(self, papers: list[Paper], store: Store) -> list[tuple[Paper, Assessment, bool]]:
        scored: list[tuple[Paper, Assessment, bool]] = []
        consecutive_errors = 0
        for index, paper in enumerate(papers, start=1):
            cached = store.get(paper.arxiv_id) if self.use_cache else None
            if cached and cached["abstract_assessment"]:
                scored.append((paper, Assessment.from_dict(cached["abstract_assessment"]), True))
                continue
            try:
                assessment = assess_abstract(self.provider, self.project_title, paper)
                consecutive_errors = 0
            except AssessmentError as exc:
                logger.warning("Skipping '%s': %s", paper.title, exc)
                continue
            except ProviderError as exc:
                consecutive_errors += 1
                logger.warning("Provider error on '%s': %s", paper.title, exc)
                if consecutive_errors >= MAX_CONSECUTIVE_PROVIDER_ERRORS:
                    raise ProviderError(
                        f"Stopping: {consecutive_errors} provider errors in a row. Last error: {exc}"
                    ) from exc
                continue
            store.upsert(
                paper.arxiv_id,
                title=paper.title,
                published=paper.published.isoformat(),
                abstract_assessment=assessment.to_dict(),
            )
            logger.info("[%d/%d] %d  %s", index, len(papers), assessment.score, paper.title)
            scored.append((paper, assessment, False))
        return scored

    # ------------------------------------------------------------ selection
    def _select(self, scored, store: Store) -> list[tuple[Paper, int, dict]]:
        """Decide which papers to keep. Returns (paper, final_score, assessments)."""
        if not self.fulltext:
            return [
                (paper, assessment.score, {"abstract": assessment.to_dict()})
                for paper, assessment, _ in scored
                if assessment.score >= self.relevance_threshold
            ]
        # Stage 2: only the best abstract scores are read in full.
        candidates = sorted(
            (item for item in scored if item[1].score >= self.triage_threshold),
            key=lambda item: item[1].score,
            reverse=True,
        )[: self.top_k_fulltext]
        logger.info("Reading the full text of %d paper(s)", len(candidates))
        selected = []
        for paper, abstract, _ in candidates:
            assessments = {"abstract": abstract.to_dict()}
            final = abstract.score
            fulltext = self._stage_two(paper, store)
            if fulltext is not None:
                assessments["fulltext"] = fulltext.to_dict()
                final = combine_scores(abstract.score, fulltext.score, self.fulltext_weight)
                logger.info("Full text %d, combined %d: %s", fulltext.score, final, paper.title)
            if final >= self.relevance_threshold:
                selected.append((paper, final, assessments))
        return selected

    # -------------------------------------------------------------- stage 2
    def _stage_two(self, paper: Paper, store: Store) -> Assessment | None:
        """Score the paper from its full text; None if that is not possible."""
        cached = store.get(paper.arxiv_id) if self.use_cache else None
        if cached and cached["fulltext_assessment"]:
            return Assessment.from_dict(cached["fulltext_assessment"])
        pdf = self.cache_dir / "pdfs" / f"{safe_id(paper.arxiv_id)}.pdf"
        try:
            if not pdf.exists():
                download_pdf(paper, pdf)
            excerpts = select_sections(extract_text(pdf), self.max_fulltext_chars)
            assessment = assess_fulltext(self.provider, self.project_title, paper, excerpts)
        except (DownloadError, FulltextError, AssessmentError, ProviderError) as exc:
            logger.warning("Full-text scoring failed for '%s' (%s); using the abstract score", paper.title, exc)
            return None
        store.upsert(paper.arxiv_id, fulltext_assessment=assessment.to_dict())
        return assessment

    # ------------------------------------------------------------- finalize
    def _finalize(self, paper: Paper, score: int, assessments: dict, store: Store) -> ScoutResult:
        pdf_path = self._place_pdf(paper, score)
        metadata_path = write_metadata(paper, assessments, pdf_path, self.metadata_dir, score)
        store.upsert(paper.arxiv_id, final_score=score, pdf_path=str(pdf_path) if pdf_path else None)
        logger.info("Kept (%d): %s", score, paper.title)
        return ScoutResult(
            paper=paper,
            score=score,
            abstract_assessment=Assessment.from_dict(assessments["abstract"]),
            fulltext_assessment=(
                Assessment.from_dict(assessments["fulltext"]) if "fulltext" in assessments else None
            ),
            pdf_path=pdf_path,
            metadata_path=metadata_path,
        )

    def _place_pdf(self, paper: Paper, score: int) -> Path | None:
        """Put the PDF at its final path, reusing a cached download when there is one."""
        final = self.pdfs_dir / pdf_filename(paper, score)
        cached = self.cache_dir / "pdfs" / f"{safe_id(paper.arxiv_id)}.pdf"
        try:
            if cached.exists():
                final.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(cached), str(final))
            elif not final.exists():
                download_pdf(paper, final)
        except (DownloadError, OSError) as exc:
            logger.warning("PDF not saved for '%s': %s", paper.title, exc)
            return None
        return final
