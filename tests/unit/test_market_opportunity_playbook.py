"""Unit tests for the ``market_opportunity`` recipe playbook.

Phase 1 Task 4 of 012-recipe-reports: verifies that the first concrete
:class:`Recipe` wires together Task 1's scoring formula, Task 3's report
template, and the DataForSEO + SerpAPI plugin tool names used to collect
signals.
"""

from __future__ import annotations

import re

from src.research_agent.plugins.report_plugin import ALLOWED_TEMPLATES
from src.research_agent.recipes.base import Recipe, RecipeRegistry
from src.research_agent.recipes.playbooks.market_opportunity import (
    RECIPE,
    _summarize,
    compute_market_opportunity_context,
)
from src.research_agent.recipes.scoring import OPPORTUNITY_WEIGHTS


# ---------------------------------------------------------------------------
# Recipe metadata
# ---------------------------------------------------------------------------


def test_recipe_is_a_recipe_instance() -> None:
    assert isinstance(RECIPE, Recipe)


def test_recipe_id() -> None:
    assert RECIPE.recipe_id == "market_opportunity"


def test_recipe_audience() -> None:
    assert RECIPE.audience == "rank_and_rent"


def test_recipe_required_plugins() -> None:
    assert RECIPE.required_plugins == ("dataforseo", "serpapi")


def test_recipe_optional_plugins_empty_for_phase_1() -> None:
    assert RECIPE.optional_plugins == ()


def test_recipe_template_name_is_allowed() -> None:
    assert RECIPE.template_name == "market_opportunity.html"
    assert RECIPE.template_name in ALLOWED_TEMPLATES


def test_inputs_schema_has_required_top_level_fields() -> None:
    schema = RECIPE.inputs_schema
    assert schema["type"] == "object"
    assert schema["required"] == ["service", "cities"]
    assert "service" in schema["properties"]
    assert "cities" in schema["properties"]


def test_inputs_schema_cities_item_requires_name_and_location_code() -> None:
    cities = RECIPE.inputs_schema["properties"]["cities"]
    assert cities["type"] == "array"
    assert cities.get("minItems") == 1
    item = cities["items"]
    assert item["type"] == "object"
    assert set(item["required"]) == {"name", "location_code"}
    assert "latlng" in item["properties"]


def test_recipe_scoring_fn_is_bound() -> None:
    assert RECIPE.scoring_fn is compute_market_opportunity_context


def test_system_prompt_mentions_every_required_tool_name() -> None:
    prompt = RECIPE.system_prompt
    for tool in (
        "fetch_keyword_volume",
        "fetch_serp_organic",
        "fetch_backlinks_summary",
        "fetch_serpapi_maps",
    ):
        assert tool in prompt, f"system_prompt missing reference to {tool!r}"


# ---------------------------------------------------------------------------
# compute_market_opportunity_context
# ---------------------------------------------------------------------------


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


def test_context_service_passes_through() -> None:
    ctx = compute_market_opportunity_context(_sample_collected())
    assert ctx["service"] == "concrete paver"


def test_context_recipe_id() -> None:
    ctx = compute_market_opportunity_context(_sample_collected())
    assert ctx["recipe_id"] == "market_opportunity"


def test_context_weights_equal_opportunity_weights() -> None:
    ctx = compute_market_opportunity_context(_sample_collected())
    assert ctx["weights"] == OPPORTUNITY_WEIGHTS


def test_each_market_has_score_and_components() -> None:
    ctx = compute_market_opportunity_context(_sample_collected())
    assert len(ctx["markets"]) == 3
    for market in ctx["markets"]:
        assert isinstance(market["score"], float)
        assert 0.0 <= market["score"] <= 1.0
        assert isinstance(market["components"], dict)
        assert market["components"]  # non-empty


def test_top_market_matches_summary_top_market() -> None:
    ctx = compute_market_opportunity_context(_sample_collected())
    top = max(ctx["markets"], key=lambda m: m["score"])
    assert ctx["summary"]["top_market"] == top["city"]


def test_summary_total_markets_equals_input_count() -> None:
    ctx = compute_market_opportunity_context(_sample_collected())
    assert ctx["summary"]["total_markets"] == 3


def test_summary_median_score_is_hand_computable() -> None:
    """Build a batch where the medians are obviously 0.5 by construction.

    Two markets -> median is the mean of both scores. Using identical
    signals gives each a 0.5 score (neutral batch), so median should be
    0.5.
    """
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


def test_summary_total_cost_passes_through() -> None:
    ctx = compute_market_opportunity_context(_sample_collected())
    assert ctx["summary"]["total_cost_usd"] == 2.37


def test_summary_total_cost_default_when_missing() -> None:
    collected = {"service": "svc", "markets": []}
    ctx = compute_market_opportunity_context(collected)
    assert ctx["summary"]["total_cost_usd"] == 0.0


def test_empty_markets_does_not_crash() -> None:
    ctx = compute_market_opportunity_context(
        {"service": "foo", "markets": [], "total_cost_usd": 0.0}
    )
    assert ctx["summary"]["total_markets"] == 0
    assert ctx["summary"]["top_market"] == "\u2014"  # em dash
    assert ctx["summary"]["median_score"] == 0.0
    assert ctx["markets"] == []


def test_generated_at_is_iso_8601_with_z_suffix() -> None:
    ctx = compute_market_opportunity_context(_sample_collected())
    assert re.match(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
        ctx["generated_at"],
    )


def test_notes_pass_through_when_present() -> None:
    ctx = compute_market_opportunity_context(_sample_collected())
    assert ctx["notes"] == ["serp call for Austin retried once"]


def test_notes_absent_when_not_supplied() -> None:
    ctx = compute_market_opportunity_context(
        {"service": "svc", "markets": [], "total_cost_usd": 0.0}
    )
    # Key may be absent or empty list; both are acceptable. Assert no crash
    # and that whatever is there is falsy.
    assert not ctx.get("notes")


# ---------------------------------------------------------------------------
# Nullable signal handling (regression for TypeError on None render)
# ---------------------------------------------------------------------------


def _collected_with_all_none_signals() -> dict:
    """All five signal fields are None --- mimics total API failure."""
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
    """Some signals present, others None --- partial API failure."""
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
# _summarize helper
# ---------------------------------------------------------------------------


def test_summarize_empty_list() -> None:
    s = _summarize([])
    assert s["total_markets"] == 0
    assert s["top_market"] == "\u2014"
    assert s["median_score"] == 0.0


def test_summarize_single_market() -> None:
    s = _summarize([{"city": "Solo", "score": 0.7}])
    assert s["total_markets"] == 1
    assert s["top_market"] == "Solo"
    assert s["median_score"] == 0.7


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
    # Two markets share the highest score. The alphabetically earlier
    # city must always win, regardless of input order.
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


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------


def test_registry_registration_round_trip() -> None:
    registry = RecipeRegistry()
    registry.register(RECIPE)
    assert registry.get("market_opportunity") is RECIPE
    assert "market_opportunity" in registry.list_recipes()
