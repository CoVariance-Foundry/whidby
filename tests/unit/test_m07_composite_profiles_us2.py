"""US2 tests for profile-dependent composite behavior."""

from src.scoring.engine import compute_scores
from tests.fixtures.m07_scoring_fixtures import metro_cohort, metro_signal


def test_profile_switch_changes_resolved_weights() -> None:
    cohort = metro_cohort()
    metro = cohort[2]
    organic_first = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="organic_first",
    )
    local_dominant = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="local_dominant",
    )
    assert organic_first["resolved_weights"] != local_dominant["resolved_weights"]


def test_profile_switch_can_change_opportunity() -> None:
    cohort = metro_cohort()
    metro = cohort[2]
    a = compute_scores(metro_signals=metro, all_metro_signals=cohort, strategy_profile="organic_first")
    b = compute_scores(metro_signals=metro, all_metro_signals=cohort, strategy_profile="local_dominant")
    assert a["opportunity"] != b["opportunity"]


def test_auto_above_fold_diverges_from_balanced_end_to_end() -> None:
    above_fold = metro_signal(local_pack_present=True, local_pack_position=1)
    cohort = [above_fold]
    auto_result = compute_scores(
        metro_signals=above_fold,
        all_metro_signals=cohort,
        strategy_profile="auto",
    )
    balanced_result = compute_scores(
        metro_signals=above_fold,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    assert auto_result["resolved_weights"] != balanced_result["resolved_weights"]

