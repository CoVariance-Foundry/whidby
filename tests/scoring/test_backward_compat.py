"""Regression: BALANCED lens must produce identical scores to current balanced profile."""

from src.scoring.engine import compute_scores
from tests.fixtures.m07_scoring_fixtures import metro_cohort

# Golden values captured from compute_scores() with cohort[2] and strategy_profile="balanced"
# on 2026-04-26 against the pre-refactor engine (commit on dev branch).
GOLDEN_DEMAND = 83.8
GOLDEN_ORGANIC = 45.866666666666674
GOLDEN_LOCAL = 71.0
GOLDEN_MONETIZATION = 45.82259528130671
GOLDEN_AI = 69.1
GOLDEN_OPPORTUNITY = 61.55951905626134
GOLDEN_WEIGHTS = {"organic": 0.15, "local": 0.20}
GOLDEN_CONFIDENCE = 100.0


def test_balanced_profile_golden_baseline():
    """Lock current balanced-profile output for BASE_METRO_SIGNAL."""
    cohort = metro_cohort()
    metro = cohort[2]
    result = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )

    assert abs(result["demand"] - GOLDEN_DEMAND) < 0.001
    assert abs(result["organic_competition"] - GOLDEN_ORGANIC) < 0.001
    assert abs(result["local_competition"] - GOLDEN_LOCAL) < 0.001
    assert abs(result["monetization"] - GOLDEN_MONETIZATION) < 0.001
    assert abs(result["ai_resilience"] - GOLDEN_AI) < 0.001
    assert abs(result["opportunity"] - GOLDEN_OPPORTUNITY) < 0.001
    assert result["resolved_weights"] == GOLDEN_WEIGHTS
    assert abs(result["confidence"]["score"] - GOLDEN_CONFIDENCE) < 0.001
    assert result["confidence"]["flags"] == []
