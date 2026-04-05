"""US3 tests for threshold gates and local-pack defaults."""

from src.scoring.composite_score import compute_opportunity_score
from src.scoring.local_competition_score import compute_local_competition_score
from tests.fixtures.m07_scoring_fixtures import metro_signal


def test_no_local_pack_returns_default_score() -> None:
    score = compute_local_competition_score(metro_signal(local_pack_present=False))
    assert score == 75.0


def test_threshold_gate_caps_composite_when_component_below_5() -> None:
    score = compute_opportunity_score(
        demand=4.0,
        organic_competition=80.0,
        local_competition=80.0,
        monetization=80.0,
        ai_resilience=80.0,
        organic_weight=0.15,
        local_weight=0.20,
    )
    assert score <= 20.0


def test_ai_floor_caps_composite_when_ai_resilience_is_low() -> None:
    score = compute_opportunity_score(
        demand=90.0,
        organic_competition=90.0,
        local_competition=90.0,
        monetization=90.0,
        ai_resilience=10.0,
        organic_weight=0.15,
        local_weight=0.20,
    )
    assert score <= 50.0

