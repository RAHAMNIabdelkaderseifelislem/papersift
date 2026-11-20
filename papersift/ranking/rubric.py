"""Rubric-based scoring shared by both ranking stages.

The LLM only fills in a small rubric (0-3 per criterion). The final 0-100
score and the recommendation are computed here, in code, so they are
reproducible and comparable across models.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError, field_validator

from papersift.providers import LLMProvider
from papersift.utils import extract_json

WEIGHTS = {"topic_match": 0.5, "method_match": 0.3, "novelty": 0.2}
RUBRIC_MAX = 3

RUBRIC_INSTRUCTIONS = """Score the paper against the research project with this rubric (integers 0-3):
- topic_match: 0 = unrelated, 1 = loosely related, 2 = related, 3 = directly about the project's topic.
- method_match: 0 = unrelated methods, 1 = loosely related, 2 = useful methods, 3 = methods the project could build on.
- novelty: 0 = nothing new, 1 = incremental, 2 = solid contribution, 3 = significant or influential contribution.
Reply with ONLY a JSON object with exactly these keys:
{"topic_match": int, "method_match": int, "novelty": int,
 "key_strengths": [short strings], "potential_limitations": [short strings],
 "reasoning": "one or two sentences"}"""


class AssessmentError(Exception):
    """The model never produced a usable assessment."""


class RubricScores(BaseModel):
    topic_match: int = Field(ge=0, le=RUBRIC_MAX)
    method_match: int = Field(ge=0, le=RUBRIC_MAX)
    novelty: int = Field(ge=0, le=RUBRIC_MAX)
    key_strengths: list[str] = Field(default_factory=list)
    potential_limitations: list[str] = Field(default_factory=list)
    reasoning: str = ""

    @field_validator("topic_match", "method_match", "novelty", mode="before")
    @classmethod
    def _coerce_score(cls, value):
        # Models sometimes answer "2", 2.0 or 4: round and clamp instead of failing.
        try:
            return max(0, min(RUBRIC_MAX, int(round(float(value)))))
        except (TypeError, ValueError):
            return value  # let pydantic raise a clear error

    @field_validator("key_strengths", "potential_limitations", mode="before")
    @classmethod
    def _coerce_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return value


def score_from_rubric(rubric: RubricScores) -> int:
    total = sum(WEIGHTS[name] * getattr(rubric, name) / RUBRIC_MAX for name in WEIGHTS)
    return round(100 * total)


def recommendation_for(score: int) -> str:
    if score >= 85:
        return "HIGH PRIORITY"
    if score >= 70:
        return "CONSIDER"
    if score >= 50:
        return "LOW PRIORITY"
    return "SKIP"


@dataclass
class Assessment:
    stage: str  # "abstract" or "fulltext"
    score: int
    recommendation: str
    rubric: RubricScores

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "score": self.score,
            "recommendation": self.recommendation,
            **self.rubric.model_dump(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Assessment":
        rubric = RubricScores(**{k: v for k, v in data.items() if k in RubricScores.model_fields})
        return cls(
            stage=data.get("stage", "abstract"),
            score=int(data["score"]),
            recommendation=data.get("recommendation", recommendation_for(int(data["score"]))),
            rubric=rubric,
        )


def run_rubric_assessment(
    provider: LLMProvider, system: str, prompt: str, stage: str, max_attempts: int = 2
) -> Assessment:
    """Ask the model, validate the JSON, and retry once with a reminder if needed."""
    last_problem = ""
    for attempt in range(max_attempts):
        full_prompt = prompt
        if attempt:
            full_prompt += (
                f"\n\nYour previous reply was not valid ({last_problem}). "
                "Reply with ONLY the JSON object described above."
            )
        reply = provider.complete(full_prompt, system=system, json_mode=True)
        try:
            rubric = RubricScores(**extract_json(reply))
        except (ValueError, TypeError, ValidationError) as exc:
            last_problem = str(exc).splitlines()[0][:150]
            continue
        score = score_from_rubric(rubric)
        return Assessment(stage, score, recommendation_for(score), rubric)
    raise AssessmentError(f"No valid assessment after {max_attempts} attempts ({last_problem})")
