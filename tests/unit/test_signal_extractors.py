"""Unit tests for M6 extractor modules."""

from __future__ import annotations

from src.pipeline.extractors.ai_resilience import extract_ai_resilience_signals
from src.pipeline.extractors.demand_signals import extract_demand_signals
from src.pipeline.extractors.local_competition import extract_local_competition_signals
from src.pipeline.extractors.monetization import extract_monetization_signals
from src.pipeline.extractors.organic_competition import extract_organic_competition_signals
from src.pipeline.serp_parser import parse_serp_features
from tests.fixtures.m6_signal_extraction_fixtures import (
    build_keyword_expansion,
    build_no_local_pack_bundle,
    build_sample_bundle,
)


def test_extract_demand_signals_contract_shape() -> None:
    bundle = build_sample_bundle()
    keywords = build_keyword_expansion()
    aio_lookup = {"plumber near me": True}

    demand = extract_demand_signals(keywords, bundle["keyword_volume"], aio_lookup)

    assert set(demand.keys()) == {
        "total_search_volume",
        "effective_search_volume",
        "head_term_volume",
        "volume_breadth",
        "avg_cpc",
        "max_cpc",
        "cpc_volume_product",
        "transactional_ratio",
    }
    assert demand["total_search_volume"] > 0
    assert 0 <= demand["transactional_ratio"] <= 1
    assert demand["effective_search_volume"] < demand["total_search_volume"]


def test_extract_organic_competition_signals_counts_aggregators() -> None:
    bundle = build_sample_bundle()
    keywords = build_keyword_expansion()
    serp_context = parse_serp_features(bundle["serp_organic"])

    organic = extract_organic_competition_signals(
        backlinks_rows=bundle["backlinks"],
        lighthouse_rows=bundle["lighthouse"],
        serp_context=serp_context,
        keyword_expansion=keywords,
        cross_metro_domain_stats=None,
        total_metros=None,
    )
    assert set(organic.keys()) == {
        "avg_top5_da",
        "min_top5_da",
        "da_spread",
        "aggregator_count",
        "local_biz_count",
        "avg_lighthouse_performance",
        "avg_top5_lighthouse",
        "top5_da_coverage",
        "top5_lighthouse_coverage",
        "top5_organic_data_confidence",
        "schema_adoption_rate",
        "title_keyword_match_rate",
    }
    assert organic["aggregator_count"] >= 1


def test_extract_organic_competition_omits_missing_top5_values_from_averages() -> None:
    organic = extract_organic_competition_signals(
        backlinks_rows=[
            {"domain_authority": 40},
            {},
            {"da": None},
            {"da": 20},
        ],
        lighthouse_rows=[
            {"performance_score": 80},
            {},
            {"performance": None},
            {"performance": 60},
        ],
        serp_context={"organic_domains": ["local.example"]},
        keyword_expansion=[],
    )

    assert organic["avg_top5_da"] == 30.0
    assert organic["avg_top5_lighthouse"] == 70.0
    assert organic["avg_lighthouse_performance"] == 70.0
    assert organic["top5_da_coverage"] == 0.4
    assert organic["top5_lighthouse_coverage"] == 0.4
    assert organic["top5_organic_data_confidence"] == "low"


def test_extract_organic_competition_reports_missing_top5_values_as_null() -> None:
    organic = extract_organic_competition_signals(
        backlinks_rows=[{}, {"domain_authority": None}],
        lighthouse_rows=[{}, {"performance_score": None}],
        serp_context={"organic_domains": []},
        keyword_expansion=[],
    )

    assert organic["avg_top5_da"] is None
    assert organic["avg_top5_lighthouse"] is None
    assert organic["avg_lighthouse_performance"] is None
    assert organic["top5_da_coverage"] == 0.0
    assert organic["top5_lighthouse_coverage"] == 0.0
    assert organic["top5_organic_data_confidence"] == "missing"


def test_extract_local_competition_handles_missing_local_pack_defaults() -> None:
    bundle = build_no_local_pack_bundle()
    serp_context = parse_serp_features(bundle["serp_organic"])
    local = extract_local_competition_signals(
        serp_context=serp_context,
        serp_maps_rows=bundle["serp_maps"],
        google_reviews_rows=bundle["google_reviews"],
        gbp_info_rows=bundle["gbp_info"],
        business_listings_rows=bundle["business_listings"],
    )
    assert local["local_pack_present"] is False
    assert local["local_pack_position"] == 10
    assert local["local_pack_review_count_avg"] == 0.0


def test_extract_local_competition_produces_nonzero_values_with_data() -> None:
    """Happy-path: when maps/reviews/GBP/listings data is present, signals must be non-zero."""
    bundle = build_sample_bundle()
    serp_context = parse_serp_features(bundle["serp_organic"])
    local = extract_local_competition_signals(
        serp_context=serp_context,
        serp_maps_rows=bundle["serp_maps"],
        google_reviews_rows=bundle["google_reviews"],
        gbp_info_rows=bundle["gbp_info"],
        business_listings_rows=bundle["business_listings"],
    )
    assert local["local_pack_present"] is True
    assert local["local_pack_position"] < 10
    assert local["local_pack_review_count_avg"] > 0
    assert local["local_pack_review_count_max"] > 0
    assert local["local_pack_rating_avg"] > 3.0
    assert local["review_velocity_avg"] > 0
    assert local["gbp_completeness_avg"] > 0
    assert local["gbp_photo_count_avg"] > 0
    assert local["gbp_posting_activity"] > 0
    assert local["citation_consistency"] > 0


def test_extract_local_competition_uses_top3_review_floor_not_average() -> None:
    local = extract_local_competition_signals(
        serp_context={"local_pack_present": True, "local_pack_position": 1},
        serp_maps_rows=[
            {"position": 2, "rating": 4.9, "review_count": 200, "reviews_per_month": 8.0},
            {"position": 1, "rating": 4.6, "review_count": 20, "reviews_per_month": 2.0},
            {"position": 4, "rating": 4.2, "review_count": 400, "reviews_per_month": 12.0},
            {"position": 3, "rating": 4.8, "review_count": 120, "reviews_per_month": 6.0},
        ],
        google_reviews_rows=[],
        gbp_info_rows=[],
        business_listings_rows=[],
    )

    assert local["local_pack_review_count_avg"] == 185.0
    assert local["top3_review_count_min"] == 20.0
    assert local["top3_review_count_min"] < local["local_pack_review_count_avg"]
    assert local["top3_review_velocity_avg"] == 5.3333
    assert local["top3_review_count_coverage"] == 1.0
    assert local["top3_review_velocity_coverage"] == 1.0
    assert local["top3_review_data_confidence"] == "high"


def test_extract_local_competition_reports_top3_review_coverage() -> None:
    local = extract_local_competition_signals(
        serp_context={"local_pack_present": True, "local_pack_position": 1},
        serp_maps_rows=[
            {"position": 1, "rating": 4.6, "reviews_per_month": 2.0},
            {"position": 2, "rating": 4.9, "review_count": 200},
            {"position": 3, "rating": 4.8},
        ],
        google_reviews_rows=[],
        gbp_info_rows=[],
        business_listings_rows=[],
    )

    assert local["top3_review_count_min"] == 200.0
    assert local["top3_review_velocity_avg"] == 2.0
    assert local["top3_review_count_coverage"] == 0.3333
    assert local["top3_review_velocity_coverage"] == 0.3333
    assert local["top3_review_data_confidence"] == "low"


def test_extract_local_competition_uses_expected_top3_slots_for_single_row() -> None:
    local = extract_local_competition_signals(
        serp_context={"local_pack_present": True, "local_pack_position": 1},
        serp_maps_rows=[
            {"position": 1, "rating": 4.6, "review_count": 200, "reviews_per_month": 2.0},
        ],
        google_reviews_rows=[],
        gbp_info_rows=[],
        business_listings_rows=[],
    )

    assert local["top3_review_count_min"] == 200.0
    assert local["top3_review_velocity_avg"] == 2.0
    assert local["top3_review_count_coverage"] == 0.3333
    assert local["top3_review_velocity_coverage"] == 0.3333
    assert local["top3_review_data_confidence"] == "low"


def test_extract_local_competition_reports_medium_confidence_without_velocity_coverage() -> None:
    local = extract_local_competition_signals(
        serp_context={"local_pack_present": True, "local_pack_position": 1},
        serp_maps_rows=[
            {"position": 1, "rating": 4.6, "review_count": 100},
            {"position": 2, "rating": 4.9, "review_count": 200},
            {"position": 3, "rating": 4.8, "review_count": 300},
        ],
        google_reviews_rows=[],
        gbp_info_rows=[],
        business_listings_rows=[],
    )

    assert local["top3_review_count_coverage"] == 1.0
    assert local["top3_review_velocity_coverage"] == 0.0
    assert local["top3_review_data_confidence"] == "medium"


def test_extract_local_competition_reports_zero_coverage_when_top3_counts_missing() -> None:
    local = extract_local_competition_signals(
        serp_context={"local_pack_present": True, "local_pack_position": 1},
        serp_maps_rows=[
            {"position": 1, "rating": 4.6},
            {"position": 2, "rating": 4.9},
            {"position": 3, "rating": 4.8},
        ],
        google_reviews_rows=[],
        gbp_info_rows=[],
        business_listings_rows=[],
    )

    assert local["top3_review_count_min"] is None
    assert local["top3_review_velocity_avg"] is None
    assert local["top3_review_count_coverage"] == 0.0
    assert local["top3_review_data_confidence"] == "missing"


def test_extract_local_competition_prefers_rank_group_for_top3_selection() -> None:
    local = extract_local_competition_signals(
        serp_context={"local_pack_present": True, "local_pack_position": 1},
        serp_maps_rows=[
            {"rank_group": 4, "position": 1, "rating": 4.9, "review_count": 4},
            {"rank_group": 1, "position": 4, "rating": 4.6, "review_count": 100},
            {"rank_group": 2, "position": 5, "rating": 4.8, "review_count": 90},
            {"rank_group": 3, "position": 6, "rating": 4.2, "review_count": 80},
        ],
        google_reviews_rows=[],
        gbp_info_rows=[],
        business_listings_rows=[],
    )

    assert local["top3_review_count_min"] == 80.0


def test_extract_demand_signals_handles_nested_dfs_keyword_volume() -> None:
    """DFS keyword_volume returns items nested under a wrapper dict."""
    dfs_volume_rows = [
        {
            "se_type": "google",
            "items_count": 3,
            "items": [
                {"keyword": "roofing", "search_volume": 301000, "cpc": 5.47},
                {"keyword": "roof repair", "search_volume": 74000, "cpc": 6.21},
                {"keyword": "roof replacement", "search_volume": 27100, "cpc": 8.50},
            ],
        }
    ]
    keywords = [
        {"keyword": "roofing", "tier": 1, "intent": "transactional"},
        {"keyword": "roof repair", "tier": 2, "intent": "commercial"},
        {"keyword": "roof replacement", "tier": 2, "intent": "commercial"},
    ]
    demand = extract_demand_signals(keywords, dfs_volume_rows, {})

    assert demand["total_search_volume"] > 0
    assert demand["avg_cpc"] > 0
    assert demand["head_term_volume"] == 301000
    assert demand["volume_breadth"] == 1.0


def test_extract_ai_and_monetization_blocks_contract_shape() -> None:
    bundle = build_sample_bundle()
    keywords = build_keyword_expansion()
    serp_context = parse_serp_features(bundle["serp_organic"])
    demand = extract_demand_signals(keywords, bundle["keyword_volume"], {"plumber near me": True})
    organic = extract_organic_competition_signals(
        backlinks_rows=bundle["backlinks"],
        lighthouse_rows=bundle["lighthouse"],
        serp_context=serp_context,
        keyword_expansion=keywords,
    )
    local = extract_local_competition_signals(
        serp_context=serp_context,
        serp_maps_rows=bundle["serp_maps"],
        google_reviews_rows=bundle["google_reviews"],
        gbp_info_rows=bundle["gbp_info"],
        business_listings_rows=bundle["business_listings"],
    )
    ai = extract_ai_resilience_signals(serp_context, keywords)
    monetization = extract_monetization_signals(demand, local, organic, serp_context, bundle["business_listings"])

    assert set(ai.keys()) == {
        "aio_trigger_rate",
        "featured_snippet_rate",
        "transactional_keyword_ratio",
        "local_fulfillment_required",
        "paa_density",
    }
    assert set(monetization.keys()) == {
        "avg_cpc",
        "business_density",
        "gbp_completeness_avg",
        "lsa_present",
        "aggregator_presence",
        "ads_present",
    }

    assert local["local_pack_review_count_avg"] > 0
    assert local["local_pack_review_count_max"] > 0
    assert local["local_pack_rating_avg"] > 0
    assert local["review_velocity_avg"] > 0
    assert local["gbp_completeness_avg"] > 0
    assert local["gbp_photo_count_avg"] > 0
    assert local["citation_consistency"] > 0
