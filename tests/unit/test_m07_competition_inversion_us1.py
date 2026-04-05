"""US1 tests for competition inversion behavior."""

from src.scoring.composite_score import compute_opportunity_score
from src.scoring.organic_competition_score import compute_organic_competition_score
from src.scoring.strategy_profiles import resolve_strategy_weights
from tests.fixtures.m07_scoring_fixtures import metro_signal


def test_lower_da_competitor_gets_higher_organic_competition_score() -> None:
    weak_competitors = metro_signal(avg_top5_da=18.0, aggregator_count=0.0)
    strong_competitors = metro_signal(avg_top5_da=55.0, aggregator_count=3.0)
    weak_score = compute_organic_competition_score(weak_competitors)
    strong_score = compute_organic_competition_score(strong_competitors)
    assert weak_score > strong_score


def test_higher_competition_does_not_inflate_opportunity() -> None:
    weights = resolve_strategy_weights("balanced", metro_signal())
    easier = compute_opportunity_score(
        demand=70.0,
        organic_competition=75.0,
        local_competition=72.0,
        monetization=65.0,
        ai_resilience=70.0,
        organic_weight=weights["organic"],
        local_weight=weights["local"],
    )
    harder = compute_opportunity_score(
        demand=70.0,
        organic_competition=30.0,
        local_competition=25.0,
        monetization=65.0,
        ai_resilience=70.0,
        organic_weight=weights["organic"],
        local_weight=weights["local"],
    )
    assert easier > harder

