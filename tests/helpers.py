"""Fakes used to test the pipeline without network access."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from papersift.models import Paper


def make_paper(n: int, title: str | None = None) -> Paper:
    return Paper(
        arxiv_id=f"2601.{n:05d}",
        title=title or f"Paper number {n}",
        abstract=f"Abstract {n}",
        authors=["Ada"],
        published=datetime(2026, 1, 1, tzinfo=timezone.utc),
        url=f"http://arxiv.org/abs/2601.{n:05d}",
        pdf_url=f"http://arxiv.org/pdf/2601.{n:05d}",
    )


class FakeSource:
    def __init__(self, papers):
        self.papers = papers
        self.calls = []

    def search(self, keywords, *, since_days, max_results):
        self.calls.append((keywords, since_days, max_results))
        return list(self.papers)


def rubric_reply(topic: int, method: int, novelty: int) -> str:
    return json.dumps(
        {"topic_match": topic, "method_match": method, "novelty": novelty,
         "key_strengths": ["s"], "potential_limitations": ["l"], "reasoning": "r"}
    )


def scripted_provider_responder(scores_by_title: dict[str, tuple[int, int, int]]):
    """Answers keyword prompts and rubric prompts based on the paper title in the prompt."""

    def respond(messages):
        text = messages[-1]["content"]
        if "search keywords" in text:
            return '["alpha", "beta"]'
        for title, rubric in scores_by_title.items():
            if title in text:
                return rubric_reply(*rubric)
        return rubric_reply(0, 0, 0)

    return respond
