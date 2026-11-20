import json
from datetime import datetime, timezone

import pytest

from papersift.models import Paper
from papersift.providers import MockProvider
from papersift.ranking import AssessmentError, assess_abstract
from papersift.ranking.rubric import Assessment, RubricScores, recommendation_for, score_from_rubric

PAPER = Paper("1", "T", "An abstract.", ["A"], datetime(2026, 1, 1, tzinfo=timezone.utc), "u", "p")


def reply(topic, method, novelty):
    return json.dumps(
        {"topic_match": topic, "method_match": method, "novelty": novelty,
         "key_strengths": ["s"], "potential_limitations": [], "reasoning": "r"}
    )


def test_score_is_computed_in_code_from_the_rubric():
    assert score_from_rubric(RubricScores(topic_match=3, method_match=3, novelty=3)) == 100
    assert score_from_rubric(RubricScores(topic_match=0, method_match=0, novelty=0)) == 0
    assert score_from_rubric(RubricScores(topic_match=3, method_match=0, novelty=0)) == 50


def test_recommendation_thresholds():
    assert [recommendation_for(s) for s in (90, 75, 55, 10)] == [
        "HIGH PRIORITY", "CONSIDER", "LOW PRIORITY", "SKIP"]


def test_assess_abstract_happy_path():
    assessment = assess_abstract(MockProvider([reply(3, 3, 3)]), "project", PAPER)
    assert assessment.score == 100 and assessment.stage == "abstract"
    assert assessment.recommendation == "HIGH PRIORITY"


def test_out_of_range_and_string_scores_are_coerced():
    data = '{"topic_match": "2", "method_match": 4, "novelty": 1.6}'
    assessment = assess_abstract(MockProvider([data]), "project", PAPER)
    assert (assessment.rubric.topic_match, assessment.rubric.method_match, assessment.rubric.novelty) == (2, 3, 2)


def test_retries_once_after_invalid_json():
    provider = MockProvider(["sorry, no json", f"```json\n{reply(2, 2, 2)}\n```"])
    assessment = assess_abstract(provider, "project", PAPER)
    assert assessment.score > 0 and len(provider.calls) == 2
    assert "not valid" in provider.calls[1][-1]["content"]


def test_raises_after_repeated_failures():
    with pytest.raises(AssessmentError):
        assess_abstract(MockProvider(["nope"]), "project", PAPER)


def test_assessment_round_trips_through_dict():
    original = assess_abstract(MockProvider([reply(2, 1, 3)]), "project", PAPER)
    restored = Assessment.from_dict(original.to_dict())
    assert restored == original
