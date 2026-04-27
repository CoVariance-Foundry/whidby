"""Tests for lens-based domain scoring."""

import pytest
from src.domain.entities import City, Service, Market, ScoredMarket
from src.domain.lenses import BALANCED, GBP_BLITZ, AI_PROOF
from src.domain.scoring import (
    score_market,
    score_markets_batch,
    MissingSignalsError,
    FilterNotMetError,
)


def _make_market(**score_overrides: float) -> Market:
    """Create a Market with pre-computed component scores."""
    base_scores = {
        "demand": 75.0,
        "organic_competition": 68.0,
        "local_competition": 55.0,
        "monetization": 60.0,
        "ai_resilience": 80.0,
        "gbp": 45.0,
    }
    base_scores.update(score_overrides)
    signals = {name: {"score": score} for name, score in base_scores.items()}
    return Market(
        city=City(city_id="boise-id", name="Boise", state="ID"),
        service=Service(service_id="plumbing", name="Plumbing"),
        signals=signals,
    )


def test_score_market_returns_scored_market():
    market = _make_market()
    result = score_market(market, BALANCED)
    assert isinstance(result, ScoredMarket)
    assert result.lens_id == "balanced"
    assert result.opportunity_score > 0
    assert len(result.score_breakdown) > 0


def test_score_market_balanced_breakdown_matches_weights():
    market = _make_market()
    result = score_market(market, BALANCED)
    for name, weight in BALANCED.weights.items():
        expected = market.signals.get(name, {}).get("score", 0.0) * weight
        assert abs(result.score_breakdown[name] - expected) < 0.01


def test_score_market_missing_required_signals():
    signals = {"monetization": {"score": 60.0}}
    market = Market(
        city=City(city_id="boise-id", name="Boise", state="ID"),
        service=Service(service_id="plumbing", name="Plumbing"),
        signals=signals,
    )
    with pytest.raises(MissingSignalsError):
        score_market(market, BALANCED)


def test_score_market_filter_not_met():
    market = _make_market()
    market_signals = dict(market.signals)
    market_signals["local_competition"] = {"score": 55.0, "avg_reviews": 50.0}
    market_with_filter = Market(
        city=market.city,
        service=market.service,
        signals=market_signals,
    )
    with pytest.raises(FilterNotMetError):
        score_market(market_with_filter, GBP_BLITZ)


def test_score_market_filter_passes():
    market = _make_market()
    market_signals = dict(market.signals)
    market_signals["local_competition"] = {"score": 55.0, "avg_reviews": 15.0}
    market_ok = Market(
        city=market.city,
        service=market.service,
        signals=market_signals,
    )
    result = score_market(market_ok, GBP_BLITZ)
    assert result.lens_id == "gbp_blitz"


def test_balanced_score_in_valid_range():
    market = _make_market()
    result = score_market(market, BALANCED)
    assert 0 <= result.opportunity_score <= 100


def test_different_lenses_produce_different_scores():
    market = _make_market()
    balanced = score_market(market, BALANCED)
    ai_proof = score_market(market, AI_PROOF)
    assert balanced.opportunity_score != ai_proof.opportunity_score


def test_batch_scoring_sorts_by_opportunity():
    markets = [
        _make_market(demand=50.0),
        _make_market(demand=90.0),
        _make_market(demand=70.0),
    ]
    results = score_markets_batch(markets, BALANCED)
    scores = [r.opportunity_score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_batch_scoring_assigns_ranks():
    markets = [_make_market(demand=d) for d in [90.0, 70.0, 50.0]]
    results = score_markets_batch(markets, BALANCED)
    ranks = [r.rank for r in results]
    assert ranks == [1, 2, 3]


def test_batch_scoring_skips_ineligible():
    ok_market = _make_market()
    bad_market = Market(
        city=City(city_id="x", name="X", state="XX"),
        service=Service(service_id="x", name="X"),
        signals={"monetization": {"score": 60.0}},
    )
    results = score_markets_batch([ok_market, bad_market, ok_market], BALANCED)
    assert len(results) == 2


def test_gate_fires_through_score_market():
    """Hard-cap gate applies when a base component is below threshold."""
    market = _make_market(demand=3.0)
    result = score_market(market, BALANCED)
    assert result.opportunity_score <= 20.0


def test_batch_scoring_skips_filter_failures():
    """Markets failing lens filters are excluded from batch results."""
    ok_signals = dict(_make_market().signals)
    ok_signals["local_competition"] = {"score": 55.0, "avg_reviews": 15.0}
    ok_market = Market(
        city=City(city_id="ok", name="OK", state="OK"),
        service=Service(service_id="plumbing", name="Plumbing"),
        signals=ok_signals,
    )
    bad_signals = dict(_make_market().signals)
    bad_signals["local_competition"] = {"score": 55.0, "avg_reviews": 50.0}
    bad_market = Market(
        city=City(city_id="bad", name="Bad", state="BD"),
        service=Service(service_id="plumbing", name="Plumbing"),
        signals=bad_signals,
    )
    results = score_markets_batch([ok_market, bad_market], GBP_BLITZ)
    assert len(results) == 1
    assert results[0].lens_id == "gbp_blitz"
