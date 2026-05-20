"""Unit tests for market_opportunity scoring context and null-signal handling."""

from __future__ import annotations

from src.research_agent.recipes.playbooks.market_opportunity import (
    _summarize,
    compute_market_opportunity_context,
)


def _sample_collected() -> dict:
    """Three markets with varying signal strength; hand-computable rankings."""
    return {
        "service": "concrete paver",
        "markets": [
            {
                "city": "Austin, TX",
                "search_volume": 2400,
                "avg_competitor_da": 45.0,
                "avg_backlink_strength": 1200.0,
                "gmb_saturation": 0.60,
                "cpc_value": 18.50,
                "top_competitors": [{"domain": "austinpavers.com"}],
            },
            {
                "city": "Tulsa, OK",
                "search_volume": 880,
                "avg_competitor_da": 22.0,
                "avg_backlink_strength": 140.0,
                "gmb_saturation": 0.25,
                "cpc_value": 11.20,
                "top_competitors": [{"domain": "tulsapavers.com"}],
            },
            {
                "city": "Fresno, CA",
                "search_volume": 1400,
                "avg_competitor_da": 31.0,
                "avg_backlink_strength": 510.0,
                "gmb_saturation": 0.40,
                "cpc_value": 14.00,
                "top_competitors": [{"domain": "fresnopavers.com"}],
            },
        ],
        "total_cost_usd": 2.37,
        "notes": ["serp call for Austin retried once"],
    }


# ---------------------------------------------------------------------------
# Scoring context computation
# ---------------------------------------------------------------------------


def test_context_has_expected_top_level_keys() -> None:
    collected = _sample_collected()
    ctx = compute_market_opportunity_context(collected)
    assert set(ctx.keys()) >= {
        "service",
        "markets",
        "weights",
        "summary",
        "generated_at",
        "recipe_id",
    }


def test_each_market_has_score_and_components() -> None:
    ctx = compute_market_opportunity_context(_sample_collected())
    assert len(ctx["markets"]) == 3
    for market in ctx["markets"]:
        assert isinstance(market["score"], float)
        assert 0.0 <= market["score"] <= 1.0
        assert isinstance(market["components"], dict)
        assert market["components"]


def test_top_market_matches_summary_top_market() -> None:
    ctx = compute_market_opportunity_context(_sample_collected())
    top = max(ctx["markets"], key=lambda m: m["score"])
    assert ctx["summary"]["top_market"] == top["city"]


def test_summary_median_score_is_hand_computable() -> None:
    collected = {
        "service": "foo",
        "markets": [
            {
                "city": "A",
                "search_volume": 100,
                "avg_competitor_da": 30.0,
                "avg_backlink_strength": 200.0,
                "gmb_saturation": 0.5,
                "cpc_value": 10.0,
            },
            {
                "city": "B",
                "search_volume": 100,
                "avg_competitor_da": 30.0,
                "avg_backlink_strength": 200.0,
                "gmb_saturation": 0.5,
                "cpc_value": 10.0,
            },
        ],
        "total_cost_usd": 0.0,
    }
    ctx = compute_market_opportunity_context(collected)
    assert ctx["summary"]["median_score"] == 0.5


def test_empty_markets_does_not_crash() -> None:
    ctx = compute_market_opportunity_context(
        {"service": "foo", "markets": [], "total_cost_usd": 0.0}
    )
    assert ctx["summary"]["total_markets"] == 0
    assert ctx["summary"]["top_market"] == "—"
    assert ctx["summary"]["median_score"] == 0.0
    assert ctx["markets"] == []


# ---------------------------------------------------------------------------
# Nullable signal handling (regression for TypeError on None render)
# ---------------------------------------------------------------------------


def _collected_with_all_none_signals() -> dict:
    return {
        "service": "plumber",
        "markets": [
            {
                "city": "Portland, OR",
                "search_volume": None,
                "avg_competitor_da": None,
                "avg_backlink_strength": None,
                "gmb_saturation": None,
                "cpc_value": None,
            },
        ],
        "total_cost_usd": 0.0,
    }


def _collected_with_partial_none_signals() -> dict:
    return {
        "service": "electrician",
        "markets": [
            {
                "city": "Boise, ID",
                "search_volume": 900,
                "avg_competitor_da": None,
                "avg_backlink_strength": 340.0,
                "gmb_saturation": None,
                "cpc_value": 12.50,
            },
        ],
        "total_cost_usd": 0.50,
    }


def test_all_none_signals_stripped_from_context() -> None:
    ctx = compute_market_opportunity_context(_collected_with_all_none_signals())
    market = ctx["markets"][0]
    for field in (
        "search_volume",
        "avg_competitor_da",
        "avg_backlink_strength",
        "gmb_saturation",
        "cpc_value",
    ):
        assert field not in market, f"{field} should be stripped when None"


def test_partial_none_signals_stripped_present_kept() -> None:
    ctx = compute_market_opportunity_context(_collected_with_partial_none_signals())
    market = ctx["markets"][0]
    assert market["search_volume"] == 900
    assert market["avg_backlink_strength"] == 340.0
    assert market["cpc_value"] == 12.50
    assert "avg_competitor_da" not in market
    assert "gmb_saturation" not in market


def test_all_none_signals_still_produces_valid_score() -> None:
    ctx = compute_market_opportunity_context(_collected_with_all_none_signals())
    market = ctx["markets"][0]
    assert isinstance(market["score"], float)
    assert 0.0 <= market["score"] <= 1.0


def test_partial_none_signals_still_produces_valid_score() -> None:
    ctx = compute_market_opportunity_context(_collected_with_partial_none_signals())
    market = ctx["markets"][0]
    assert isinstance(market["score"], float)
    assert 0.0 <= market["score"] <= 1.0


# ---------------------------------------------------------------------------
# _summarize edge cases
# ---------------------------------------------------------------------------


def test_summarize_three_markets_median_is_middle_score() -> None:
    s = _summarize(
        [
            {"city": "A", "score": 0.2},
            {"city": "B", "score": 0.8},
            {"city": "C", "score": 0.5},
        ]
    )
    assert s["total_markets"] == 3
    assert s["top_market"] == "B"
    assert s["median_score"] == 0.5


def test_summarize_top_market_tie_break_is_deterministic() -> None:
    forward = _summarize(
        [
            {"city": "Austin, TX", "score": 0.9},
            {"city": "Boise, ID", "score": 0.9},
        ]
    )
    reversed_order = _summarize(
        [
            {"city": "Boise, ID", "score": 0.9},
            {"city": "Austin, TX", "score": 0.9},
        ]
    )
    assert forward["top_market"] == "Austin, TX"
    assert reversed_order["top_market"] == "Austin, TX"
