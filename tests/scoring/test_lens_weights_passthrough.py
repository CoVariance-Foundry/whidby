"""Test that compute_scores accepts pre-built weights from a lens."""

from src.scoring.engine import compute_scores
from tests.fixtures.m07_scoring_fixtures import metro_cohort


def test_explicit_weights_override_strategy_profile():
    """When weights are provided, strategy_profile is ignored."""
    cohort = metro_cohort()
    metro = cohort[2]

    balanced_weights = {
        "demand": 0.25,
        "organic_competition": 0.15,
        "local_competition": 0.20,
        "monetization": 0.20,
        "ai_resilience": 0.15,
    }
    explicit = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        weights=balanced_weights,
    )
    from_profile = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    assert abs(explicit["opportunity"] - from_profile["opportunity"]) < 0.001


def test_lens_weights_with_gbp_produce_different_score():
    """Lens weights that include gbp produce different composite than balanced."""
    cohort = metro_cohort()
    metro = cohort[2]

    gbp_blitz_weights = {
        "demand": 0.15,
        "organic_competition": 0.10,
        "local_competition": 0.30,
        "monetization": 0.10,
        "ai_resilience": 0.05,
        "gbp": 0.30,
    }
    result = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        weights=gbp_blitz_weights,
    )
    balanced = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    assert result["opportunity"] != balanced["opportunity"]
    assert "gbp" in result


def test_resolved_weights_is_none_when_explicit_weights():
    """When explicit weights are used, resolved_weights is None."""
    cohort = metro_cohort()
    metro = cohort[2]
    result = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        weights={
            "demand": 0.25,
            "organic_competition": 0.15,
            "local_competition": 0.20,
            "monetization": 0.20,
            "ai_resilience": 0.15,
        },
    )
    assert result["resolved_weights"] is None
