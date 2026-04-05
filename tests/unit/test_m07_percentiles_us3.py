"""US3 tests for cohort percentile behavior."""

from src.scoring.engine import compute_scores
from tests.fixtures.m07_scoring_fixtures import metro_cohort, metro_signal


def test_changing_cohort_changes_percentile_dependent_demand() -> None:
    metro = metro_signal(effective_search_volume=1000.0)
    low_cohort = [
        metro_signal(effective_search_volume=100.0),
        metro_signal(effective_search_volume=200.0),
        metro_signal(effective_search_volume=300.0),
    ]
    high_cohort = [
        metro_signal(effective_search_volume=1500.0),
        metro_signal(effective_search_volume=2000.0),
        metro_signal(effective_search_volume=2500.0),
    ]
    low_result = compute_scores(metro_signals=metro, all_metro_signals=low_cohort + [metro], strategy_profile="balanced")
    high_result = compute_scores(
        metro_signals=metro,
        all_metro_signals=high_cohort + [metro],
        strategy_profile="balanced",
    )
    assert low_result["demand"] != high_result["demand"]


def test_non_percentile_component_stays_stable_when_only_cohort_changes() -> None:
    cohort = metro_cohort()
    metro = metro_signal(avg_top5_da=30.0, effective_search_volume=900.0)
    first = compute_scores(metro_signals=metro, all_metro_signals=cohort, strategy_profile="balanced")
    second = compute_scores(
        metro_signals=metro,
        all_metro_signals=[metro_signal(effective_search_volume=20.0), metro_signal(effective_search_volume=50.0), metro],
        strategy_profile="balanced",
    )
    assert first["organic_competition"] == second["organic_competition"]

