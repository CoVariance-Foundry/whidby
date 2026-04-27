"""Tests for DiscoveryService — multi-market discovery."""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.domain.entities import City, Market, ScoredMarket, Service
from src.domain.lenses import BALANCED
from src.domain.queries import CityFilter, MarketQuery, ServiceFilter
from src.domain.services.discovery_service import (
    DiscoveryService,
    _evaluate_predicate,
    _passes_city_filters,
    _passes_service_filters,
)


# --- Test data ---

BOISE = City(city_id="boise-id", name="Boise", state="ID", population=235_000)
PHOENIX = City(city_id="phoenix-az", name="Phoenix", state="AZ", population=1_600_000)
SMALL_TOWN = City(city_id="small-ks", name="Smallville", state="KS", population=45_000)

PLUMBING = Service(service_id="plumbing", name="Plumbing", fulfillment_type="physical")
WEB_DESIGN = Service(service_id="web-design", name="Web Design", fulfillment_type="remote")

FULL_SIGNALS: dict[str, dict[str, Any]] = {
    "demand": {"score": 75.0},
    "organic_competition": {"score": 68.0},
    "local_competition": {"score": 55.0},
    "monetization": {"score": 60.0},
    "ai_resilience": {"score": 80.0},
    "gbp": {"score": 45.0},
}


# --- _evaluate_predicate tests ---


def test_predicate_greater_than():
    assert _evaluate_predicate(100, ">", 50) is True
    assert _evaluate_predicate(50, ">", 100) is False


def test_predicate_less_than():
    assert _evaluate_predicate(30, "<", 100) is True
    assert _evaluate_predicate(100, "<", 30) is False


def test_predicate_equality():
    assert _evaluate_predicate("physical", "=", "physical") is True
    assert _evaluate_predicate("remote", "=", "physical") is False


def test_predicate_not_equal():
    assert _evaluate_predicate("remote", "!=", "physical") is True


def test_predicate_gte_lte():
    assert _evaluate_predicate(100, ">=", 100) is True
    assert _evaluate_predicate(99, "<=", 100) is True


def test_predicate_in_operator():
    assert _evaluate_predicate("AZ", "in", ["AZ", "CA", "TX"]) is True
    assert _evaluate_predicate("ID", "in", ["AZ", "CA"]) is False


def test_predicate_like_operator():
    assert _evaluate_predicate("Growth Sunbelt", "like", "sunbelt") is True
    assert _evaluate_predicate("Growth Sunbelt", "like", "arctic") is False


def test_predicate_unknown_operator_raises():
    with pytest.raises(ValueError, match="Unknown filter operator"):
        _evaluate_predicate(1, "~", 1)


# --- Filter helper tests ---


def test_passes_city_filters_population():
    filters = [CityFilter("population", ">", 200_000)]
    assert _passes_city_filters(PHOENIX, filters) is True
    assert _passes_city_filters(SMALL_TOWN, filters) is False


def test_passes_city_filters_state_in():
    filters = [CityFilter("state", "in", ["AZ", "CA"])]
    assert _passes_city_filters(PHOENIX, filters) is True
    assert _passes_city_filters(BOISE, filters) is False


def test_passes_service_filters_fulfillment_type():
    filters = [ServiceFilter("fulfillment_type", "=", "physical")]
    assert _passes_service_filters(PLUMBING, filters) is True
    assert _passes_service_filters(WEB_DESIGN, filters) is False


def test_passes_filters_missing_field_returns_false():
    filters = [CityFilter("nonexistent_field", ">", 0)]
    assert _passes_city_filters(BOISE, filters) is False


# --- Fake MarketStore ---


class FakeMarketStore:
    """Returns pre-configured markets regardless of query."""

    def __init__(self, markets: list[Market] | None = None):
        self._markets = markets or []

    def persist_report(self, report: dict[str, Any]) -> str:
        return "fake-id"

    def read_report(self, report_id: str) -> dict[str, Any] | None:
        return None

    def query_markets(self, query: MarketQuery) -> list[Market]:
        return list(self._markets)


def _make_markets() -> list[Market]:
    return [
        Market(city=BOISE, service=PLUMBING, signals=FULL_SIGNALS),
        Market(city=PHOENIX, service=PLUMBING, signals=FULL_SIGNALS),
        Market(city=BOISE, service=WEB_DESIGN, signals=FULL_SIGNALS),
        Market(city=SMALL_TOWN, service=PLUMBING, signals=FULL_SIGNALS),
    ]


@pytest.fixture
def discovery() -> DiscoveryService:
    store = FakeMarketStore(markets=_make_markets())
    return DiscoveryService(market_store=store)


def test_discover_returns_scored_markets(discovery: DiscoveryService):
    query = MarketQuery(lens=BALANCED)
    results = asyncio.run(discovery.discover(query))
    assert len(results) > 0
    assert all(isinstance(r, ScoredMarket) for r in results)


def test_discover_with_city_population_filter(discovery: DiscoveryService):
    query = MarketQuery(
        city_filters=[CityFilter("population", ">", 200_000)],
        lens=BALANCED,
    )
    results = asyncio.run(discovery.discover(query))
    assert len(results) > 0
    for r in results:
        assert r.market.city.population > 200_000


def test_discover_with_service_filter(discovery: DiscoveryService):
    query = MarketQuery(
        service_filters=[ServiceFilter("fulfillment_type", "=", "physical")],
        lens=BALANCED,
    )
    results = asyncio.run(discovery.discover(query))
    assert len(results) > 0
    for r in results:
        assert r.market.service.fulfillment_type == "physical"


def test_discover_combined_filters(discovery: DiscoveryService):
    """City + service filters narrow results to intersection."""
    query = MarketQuery(
        city_filters=[CityFilter("population", ">", 200_000)],
        service_filters=[ServiceFilter("fulfillment_type", "=", "physical")],
        lens=BALANCED,
    )
    results = asyncio.run(discovery.discover(query))
    for r in results:
        assert r.market.city.population > 200_000
        assert r.market.service.fulfillment_type == "physical"


def test_discover_respects_limit(discovery: DiscoveryService):
    query = MarketQuery(lens=BALANCED, limit=2)
    results = asyncio.run(discovery.discover(query))
    assert len(results) <= 2


def test_discover_respects_offset(discovery: DiscoveryService):
    all_results = asyncio.run(discovery.discover(MarketQuery(lens=BALANCED)))
    offset_results = asyncio.run(discovery.discover(MarketQuery(lens=BALANCED, offset=1)))
    assert len(offset_results) == len(all_results) - 1


def test_discover_results_are_ranked(discovery: DiscoveryService):
    query = MarketQuery(lens=BALANCED)
    results = asyncio.run(discovery.discover(query))
    ranks = [r.rank for r in results]
    assert ranks == list(range(1, len(ranks) + 1))


def test_discover_empty_store_returns_empty():
    store = FakeMarketStore(markets=[])
    svc = DiscoveryService(market_store=store)
    results = asyncio.run(svc.discover(MarketQuery(lens=BALANCED)))
    assert results == []


def test_discover_filter_excludes_all_returns_empty(discovery: DiscoveryService):
    query = MarketQuery(
        city_filters=[CityFilter("population", ">", 99_000_000)],
        lens=BALANCED,
    )
    results = asyncio.run(discovery.discover(query))
    assert results == []


# --- Portfolio ranking tests ---


def test_portfolio_same_city_bonus():
    """Markets in same city as portfolio entries get a score boost."""
    existing = Market(city=BOISE, service=PLUMBING)
    store = FakeMarketStore(markets=_make_markets())
    svc = DiscoveryService(market_store=store)
    query = MarketQuery(lens=BALANCED, portfolio_context=[existing])
    results = asyncio.run(svc.discover(query))
    boise_markets = [r for r in results if r.market.city.city_id == "boise-id"]
    assert len(boise_markets) > 0
    assert min(r.rank for r in boise_markets) <= len(results) // 2


def test_portfolio_same_service_penalty():
    """Markets with same service as portfolio entries get penalized."""
    existing = Market(city=PHOENIX, service=PLUMBING)
    store = FakeMarketStore(markets=_make_markets())
    svc = DiscoveryService(market_store=store)
    query_with_portfolio = MarketQuery(lens=BALANCED, portfolio_context=[existing])
    query_without = MarketQuery(lens=BALANCED)

    with_portfolio = asyncio.run(svc.discover(query_with_portfolio))
    without = asyncio.run(svc.discover(query_without))

    wd_rank_with = next(
        r.rank for r in with_portfolio
        if r.market.service.service_id == "web-design"
    )
    wd_rank_without = next(
        r.rank for r in without
        if r.market.service.service_id == "web-design"
    )
    assert wd_rank_with <= wd_rank_without


def test_portfolio_empty_context_no_change():
    """Empty portfolio context list doesn't alter ranking."""
    store = FakeMarketStore(markets=_make_markets())
    svc = DiscoveryService(market_store=store)
    query = MarketQuery(lens=BALANCED, portfolio_context=[])
    results = asyncio.run(svc.discover(query))
    ranks = [r.rank for r in results]
    assert ranks == list(range(1, len(ranks) + 1))


def test_portfolio_reranked_results_have_sequential_ranks():
    """After portfolio ranking, ranks are sequential starting at 1."""
    existing = Market(city=BOISE, service=PLUMBING)
    store = FakeMarketStore(markets=_make_markets())
    svc = DiscoveryService(market_store=store)
    query = MarketQuery(lens=BALANCED, portfolio_context=[existing])
    results = asyncio.run(svc.discover(query))
    ranks = [r.rank for r in results]
    assert ranks == list(range(1, len(ranks) + 1))
