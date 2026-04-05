"""US1 tests for deterministic reproducibility."""

from src.scoring.engine import compute_scores
from tests.fixtures.m07_scoring_fixtures import metro_cohort


def test_same_input_produces_identical_score_output() -> None:
    cohort = metro_cohort()
    metro = cohort[2]
    first = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    second = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    assert first == second

