"""US1 tests for M7 score presence and range."""

from src.scoring.engine import compute_scores
from tests.fixtures.m07_scoring_fixtures import metro_cohort


def test_all_required_scores_exist_and_are_bounded() -> None:
    cohort = metro_cohort()
    result = compute_scores(
        metro_signals=cohort[2],
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    expected = {
        "demand",
        "organic_competition",
        "local_competition",
        "monetization",
        "ai_resilience",
        "opportunity",
        "confidence",
        "resolved_weights",
    }
    assert expected.issubset(result.keys())
    for key in (
        "demand",
        "organic_competition",
        "local_competition",
        "monetization",
        "ai_resilience",
        "opportunity",
    ):
        assert 0.0 <= float(result[key]) <= 100.0
    assert 0.0 <= float(result["confidence"]["score"]) <= 100.0

