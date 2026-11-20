"""Stage 1: cheap triage from the title and abstract."""

from __future__ import annotations

from papersift.models import Paper
from papersift.providers import LLMProvider
from papersift.ranking.rubric import RUBRIC_INSTRUCTIONS, Assessment, run_rubric_assessment

SYSTEM = (
    "You are a careful research assistant helping with a literature review. "
    "Judge only from the text you are given and do not invent details.\n\n" + RUBRIC_INSTRUCTIONS
)


def assess_abstract(provider: LLMProvider, project_title: str, paper: Paper) -> Assessment:
    prompt = (
        f"Research project: {project_title}\n\n"
        f"Paper title: {paper.title}\n"
        f"Abstract: {paper.abstract}"
    )
    return run_rubric_assessment(provider, SYSTEM, prompt, stage="abstract")
