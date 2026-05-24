"""Strategy lens behavior for DiscoveryService."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.domain.entities import City, Market, Service
from src.domain.lenses import (
    BALANCED,
    EASY_WIN,
    EXPAND_CONQUER,
    GBP_BLITZ,
    KEYWORD_HIJACK,
)
from src.domain.queries import MarketQuery
from src.domain.services.discovery_service import DiscoveryService
from src.scoring.benchmark_warnings import METRIC_UNDERSAMPLED


BOISE = City(city_id="boise-id", name="Boise", state="ID", population=235_000)
TUCSON = City(city_id="tucson-az", name="Tucson", state="AZ", population=543_000)
PLUMBING = Service(service_id="plumbing", name="Plumbing")

BALANCED_SIGNALS: dict[str, dict[str, Any]] = {
    "demand": {"score": 75.0},
    "organic_competition": {"score": 68.0},
    "local_competition": {"score": 55.0},
    "monetization": {"score": 60.0},
    "ai_resilience": {"score": 80.0},
}


class FakeMarketStore:
    def __init__(self, markets: list[Market]):
        self._markets = markets

    def query_markets(self, query: MarketQuery) -> list[Market]:
        return list(self._markets)


def _strategy_market(city: City, strategy_row: dict[str, Any]) -> Market:
    return Market(
        city=city,
        service=PLUMBING,
        signals={"strategy_row": strategy_row},
    )


def _market_without_strategy_row(city: City) -> Market:
    return Market(city=city, service=PLUMBING, signals={})


def test_easy_win_uses_strategy_projection_score_and_evidence():
    high_projection = _strategy_market(
        BOISE,
        {
            "demand_strength": 140,
            "organic_difficulty": 10,
            "local_difficulty": 20,
            "ai_resilience": 90,
            "benchmark_confidence": "high",
        },
    )
    low_projection = _strategy_market(
        TUCSON,
        {
            "demand_strength": 20,
            "organic_difficulty": 90,
            "local_difficulty": 80,
            "ai_resilience": 40,
            "benchmark_confidence": "low",
        },
    )
    svc = DiscoveryService(FakeMarketStore([low_projection, high_projection]))

    results = asyncio.run(svc.discover(MarketQuery(lens=EASY_WIN)))

    assert [result.market.city.city_id for result in results] == [
        "boise-id",
        "tucson-az",
    ]
    assert [result.rank for result in results] == [1, 2]
    assert results[0].opportunity_score == 90.5
    assert results[0].lens_id == "easy_win"
    assert results[0].score_breakdown["projection_score"] == 90.5
    assert results[0].strategy_evidence == {
        "demand_strength": 140,
        "organic_difficulty": 10,
        "local_difficulty": 20,
        "ai_resilience": 90,
    }
    assert results[1].warnings == [METRIC_UNDERSAMPLED]


def test_gbp_blitz_uses_strategy_projection():
    market = _strategy_market(
        BOISE,
        {
            "demand_strength": 120,
            "local_pack_present": True,
            "top3_review_count_min": 8,
            "top3_review_velocity_avg": 0.5,
            "gbp_completeness_avg": 0.2,
        },
    )
    svc = DiscoveryService(FakeMarketStore([market]))

    results = asyncio.run(svc.discover(MarketQuery(lens=GBP_BLITZ)))

    assert results[0].lens_id == "gbp_blitz"
    assert results[0].opportunity_score == 90.3
    assert results[0].strategy_evidence == {
        "top3_review_count_min": 8,
        "top3_review_velocity_avg": 0.5,
        "gbp_completeness_avg": 0.2,
    }


def test_keyword_hijack_uses_strategy_projection():
    market = _strategy_market(
        BOISE,
        {
            "search_volume_monthly": 300,
            "cpc_usd": 50,
            "commercial_intent_score": 0.8,
            "local_pack_present": True,
            "exact_match_name_taken": False,
        },
    )
    svc = DiscoveryService(FakeMarketStore([market]))

    results = asyncio.run(svc.discover(MarketQuery(lens=KEYWORD_HIJACK)))

    assert results[0].lens_id == "keyword_hijack"
    assert results[0].opportunity_score == 95.0
    assert results[0].strategy_evidence == {
        "search_volume_monthly": 300.0,
        "cpc_usd": 50,
        "local_pack_present": True,
        "exact_match_name_available": True,
    }


def test_expand_conquer_requires_similarity_and_lower_competition():
    market = _strategy_market(
        BOISE,
        {
            "similarity_score": 0.92,
            "organic_difficulty": 30,
            "reference_organic_difficulty": 45,
            "local_difficulty": 25,
            "reference_local_difficulty": 35,
        },
    )
    svc = DiscoveryService(FakeMarketStore([market]))

    results = asyncio.run(svc.discover(MarketQuery(lens=EXPAND_CONQUER)))

    assert results[0].lens_id == "expand_conquer"
    assert results[0].opportunity_score == 72.12
    assert results[0].strategy_evidence == {
        "similarity_score": 0.92,
        "organic_difficulty": 30.0,
        "reference_organic_difficulty": 45.0,
        "local_difficulty": 25.0,
        "reference_local_difficulty": 35.0,
    }


def test_expand_conquer_blocks_higher_competition():
    market = _strategy_market(
        BOISE,
        {
            "similarity_score": 0.92,
            "organic_difficulty": 55,
            "reference_organic_difficulty": 45,
            "local_difficulty": 25,
            "reference_local_difficulty": 35,
        },
    )
    svc = DiscoveryService(FakeMarketStore([market]))

    results = asyncio.run(svc.discover(MarketQuery(lens=EXPAND_CONQUER)))

    assert results[0].lens_id == "expand_conquer"
    assert results[0].opportunity_score == 0.0
    assert results[0].warnings == ["competition_higher_than_reference"]


def test_strategy_scoring_applies_offset_after_ranking():
    best = _strategy_market(
        BOISE,
        {
            "demand_strength": 140,
            "organic_difficulty": 10,
            "local_difficulty": 20,
            "ai_resilience": 90,
        },
    )
    second = _strategy_market(
        TUCSON,
        {
            "demand_strength": 70,
            "organic_difficulty": 30,
            "local_difficulty": 40,
            "ai_resilience": 70,
        },
    )
    svc = DiscoveryService(FakeMarketStore([second, best]))

    results = asyncio.run(svc.discover(MarketQuery(lens=EASY_WIN, limit=1, offset=1)))

    assert len(results) == 1
    assert results[0].market.city.city_id == "tucson-az"
    assert results[0].rank == 2


def test_strategy_scoring_logs_and_skips_missing_strategy_rows(caplog):
    hydrated = _strategy_market(
        BOISE,
        {
            "demand_strength": 140,
            "organic_difficulty": 10,
            "local_difficulty": 20,
            "ai_resilience": 90,
        },
    )
    svc = DiscoveryService(FakeMarketStore([_market_without_strategy_row(TUCSON), hydrated]))

    with caplog.at_level(logging.WARNING):
        results = asyncio.run(svc.discover(MarketQuery(lens=EASY_WIN)))

    assert [result.market.city.city_id for result in results] == ["boise-id"]
    assert "skipped 1 markets without usable easy_win strategy rows" in caplog.text


def test_ai_resilience_filter_adds_warning_without_hiding_result():
    market = _strategy_market(
        BOISE,
        {
            "demand_strength": 140,
            "organic_difficulty": 10,
            "local_difficulty": 20,
            "ai_resilience": 50,
            "aio_trigger_rate": 0.2,
        },
    )
    svc = DiscoveryService(FakeMarketStore([market]))

    results = asyncio.run(svc.discover(MarketQuery(lens=EASY_WIN, ai_resilience_filter=True)))

    assert len(results) == 1
    assert results[0].warnings == ["ai_resilience_risk"]


def test_ai_resilience_filter_ignores_malformed_warning_values():
    market = _strategy_market(
        BOISE,
        {
            "search_volume_monthly": 300,
            "cpc_usd": 50,
            "commercial_intent_score": 0.8,
            "local_pack_present": True,
            "exact_match_name_taken": False,
            "ai_resilience": "not-a-number",
            "aio_trigger_rate": "also-not-a-number",
        },
    )
    svc = DiscoveryService(FakeMarketStore([market]))

    results = asyncio.run(svc.discover(MarketQuery(lens=KEYWORD_HIJACK, ai_resilience_filter=True)))

    assert len(results) == 1
    assert results[0].warnings == []


def test_strategy_scoring_skips_malformed_rows_without_failing(caplog):
    malformed = _strategy_market(
        TUCSON,
        {
            "demand_strength": "not-a-number",
            "organic_difficulty": 20,
        },
    )
    hydrated = _strategy_market(
        BOISE,
        {
            "demand_strength": 140,
            "organic_difficulty": 10,
            "local_difficulty": 20,
            "ai_resilience": 90,
        },
    )
    svc = DiscoveryService(FakeMarketStore([malformed, hydrated]))

    with caplog.at_level(logging.WARNING):
        results = asyncio.run(svc.discover(MarketQuery(lens=EASY_WIN)))

    assert [result.market.city.city_id for result in results] == ["boise-id"]
    assert "skipped malformed strategy row lens=easy_win" in caplog.text
    assert "skipped 1 markets without usable easy_win strategy rows" in caplog.text


def test_balanced_lens_keeps_existing_batch_scoring_behavior():
    strategy_only = _strategy_market(
        TUCSON,
        {
            "demand_strength": 140,
            "organic_difficulty": 1,
            "local_difficulty": 1,
            "ai_resilience": 100,
        },
    )
    balanced_market = Market(
        city=BOISE,
        service=PLUMBING,
        signals=BALANCED_SIGNALS,
    )
    svc = DiscoveryService(FakeMarketStore([strategy_only, balanced_market]))

    results = asyncio.run(svc.discover(MarketQuery(lens=BALANCED)))

    assert len(results) == 1
    assert results[0].market.city.city_id == "boise-id"
    assert results[0].lens_id == "balanced"
    assert results[0].opportunity_score == 63.95
    assert "projection_score" not in results[0].score_breakdown
