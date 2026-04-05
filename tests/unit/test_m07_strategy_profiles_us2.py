"""US2 tests for strategy profiles and weight constraints."""

from src.scoring.strategy_profiles import resolve_strategy_weights
from tests.fixtures.m07_scoring_fixtures import metro_signal


def test_profile_weights_sum_to_expected_competition_budget() -> None:
    for profile in ("organic_first", "balanced", "local_dominant"):
        weights = resolve_strategy_weights(profile, metro_signal())
        assert round(weights["organic"] + weights["local"], 8) == 0.35
        assert weights["organic"] >= 0
        assert weights["local"] >= 0


def test_auto_profile_without_local_pack_is_organic_heavy() -> None:
    no_pack = metro_signal(local_pack_present=False)
    auto = resolve_strategy_weights("auto", no_pack)
    balanced = resolve_strategy_weights("balanced", no_pack)
    assert auto["organic"] > balanced["organic"]
    assert auto["local"] < balanced["local"]


def test_auto_no_pack_matches_organic_first_weights() -> None:
    no_pack = metro_signal(local_pack_present=False)
    auto = resolve_strategy_weights("auto", no_pack)
    organic_first = resolve_strategy_weights("organic_first", no_pack)
    assert auto == organic_first


def test_auto_above_fold_pack_shifts_toward_local() -> None:
    above_fold = metro_signal(local_pack_present=True, local_pack_position=2)
    w = resolve_strategy_weights("auto", above_fold)
    assert round(w["organic"] + w["local"], 8) == 0.35
    assert w["local"] > w["organic"]
    assert w["organic"] == 0.08
    assert w["local"] == 0.27


def test_auto_below_fold_pack_falls_back_to_balanced() -> None:
    below_fold = metro_signal(local_pack_present=True, local_pack_position=6)
    auto = resolve_strategy_weights("auto", below_fold)
    balanced = resolve_strategy_weights("balanced", below_fold)
    assert auto == balanced


def test_auto_missing_position_falls_back_to_balanced() -> None:
    no_position = metro_signal(local_pack_present=True)
    del no_position["local_pack_position"]
    auto = resolve_strategy_weights("auto", no_position)
    balanced = resolve_strategy_weights("balanced", no_position)
    assert auto == balanced


def test_auto_with_none_signals_falls_back_to_balanced() -> None:
    auto = resolve_strategy_weights("auto", None)
    balanced = resolve_strategy_weights("balanced", metro_signal())
    assert auto == balanced


def test_auto_weights_always_sum_to_competition_budget() -> None:
    for signals in [
        metro_signal(local_pack_present=False),
        metro_signal(local_pack_present=True, local_pack_position=1),
        metro_signal(local_pack_present=True, local_pack_position=5),
        None,
    ]:
        w = resolve_strategy_weights("auto", signals)
        assert round(w["organic"] + w["local"], 8) == 0.35

