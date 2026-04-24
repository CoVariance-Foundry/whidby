"""Unit tests for top-level M6 signal extraction."""

from __future__ import annotations

import pytest

from src.pipeline.signal_extraction import extract_signals
from tests.fixtures.m6_signal_extraction_fixtures import (
    build_keyword_expansion,
    build_no_local_pack_bundle,
    build_sample_bundle,
)


def test_extract_signals_returns_all_categories_and_required_keys() -> None:
    signals = extract_signals(build_sample_bundle(), build_keyword_expansion())

    assert set(signals.keys()) == {
        "demand",
        "organic_competition",
        "local_competition",
        "ai_resilience",
        "monetization",
    }
    assert len(signals["demand"]) == 8
    assert len(signals["organic_competition"]) == 8
    assert len(signals["local_competition"]) == 10
    assert len(signals["ai_resilience"]) == 5
    assert len(signals["monetization"]) == 6

    assert signals["demand"]["total_search_volume"] > 0
    assert signals["demand"]["avg_cpc"] > 0

    assert signals["organic_competition"]["avg_top5_da"] > 0
    assert signals["organic_competition"]["title_keyword_match_rate"] > 0

    assert signals["local_competition"]["local_pack_review_count_avg"] > 0
    assert signals["local_competition"]["local_pack_rating_avg"] > 0
    assert signals["local_competition"]["gbp_completeness_avg"] > 0
    assert signals["local_competition"]["citation_consistency"] > 0

    assert signals["ai_resilience"]["aio_trigger_rate"] > 0

    assert signals["monetization"]["avg_cpc"] > 0


def test_extract_signals_effective_volume_and_aio_detection_behavior() -> None:
    signals = extract_signals(build_sample_bundle(), build_keyword_expansion())
    assert signals["demand"]["effective_search_volume"] < signals["demand"]["total_search_volume"]
    assert signals["ai_resilience"]["aio_trigger_rate"] > 0


def test_extract_signals_supports_missing_local_pack_defaults() -> None:
    signals = extract_signals(build_no_local_pack_bundle(), build_keyword_expansion())
    local = signals["local_competition"]
    assert local["local_pack_present"] is False
    assert local["local_pack_position"] == 10
    assert local["local_pack_review_count_avg"] == 0.0


def test_extract_signals_cross_metro_domain_context_applies_national_heuristic() -> None:
    bundle = build_sample_bundle()
    # Force one non-aggregator domain into cross-metro national classification.
    cross_stats = {"localplumbingco.com": 8}
    signals = extract_signals(bundle, build_keyword_expansion(), cross_stats, total_metros=20)
    assert signals["organic_competition"]["aggregator_count"] >= 2


def test_extract_signals_validates_required_input_types() -> None:
    with pytest.raises(ValueError):
        extract_signals({}, "not-a-list")


def test_extract_signals_handles_raw_dfs_nested_responses() -> None:
    """Verify normalizers bridge DFS-shaped data to non-zero local competition signals."""
    dfs_shaped_bundle = {
        "serp_organic": [
            {
                "keyword": "plumber near me",
                "items": [
                    {"type": "organic", "domain": "yelp.com", "title": "Best plumber near me"},
                    {"type": "local_pack", "rank_group": 2},
                ],
            }
        ],
        "serp_maps": [
            {
                "keyword": "plumber near me",
                "items": [
                    {"type": "maps_search", "rating": {"value": 4.5, "votes_count": 80}},
                    {"type": "maps_search", "rating": {"value": 4.1, "votes_count": 35}},
                ],
            }
        ],
        "keyword_volume": [
            {"items": [{"keyword": "plumber near me", "search_volume": 5000, "cpc": 20.0}]}
        ],
        "google_reviews": [
            {
                "rating": {"value": 4.5, "votes_count": 80},
                "reviews_count": 80,
                "items": [
                    {"timestamp": "2026-01-01 10:00:00 +00:00", "rating": {"value": 5}},
                    {"timestamp": "2026-02-01 10:00:00 +00:00", "rating": {"value": 4}},
                    {"timestamp": "2026-03-01 10:00:00 +00:00", "rating": {"value": 5}},
                ],
            }
        ],
        "gbp_info": [
            {
                "items": [
                    {
                        "type": "google_business_info",
                        "phone": "+16025551234",
                        "url": "https://joesplumbing.com",
                        "description": "Local plumber",
                        "work_time": {"work_hours": {"timetable": {"monday": []}}},
                        "total_photos": 10,
                        "category": "Plumber",
                        "attributes": {"available_attributes": [{"attribute": "licensed"}]},
                    }
                ]
            }
        ],
        "business_listings": [
            {
                "total_count": 1,
                "items": [
                    {
                        "title": "Joe's Plumbing",
                        "phone": "+16025551234",
                        "address": "123 Main St",
                        "domain": "joesplumbing.com",
                        "rating": {"value": 4.5, "votes_count": 80},
                    }
                ],
            }
        ],
        "backlinks": [{"domain": "yelp.com", "domain_authority": 90}],
        "lighthouse": [{"url": "https://joesplumbing.com", "performance_score": 62}],
    }
    keywords = [{"keyword": "plumber near me", "tier": 1, "intent": "transactional"}]

    signals = extract_signals(dfs_shaped_bundle, keywords)
    local = signals["local_competition"]

    assert local["local_pack_review_count_avg"] > 0, "Reviews should be non-zero after normalization"
    assert local["local_pack_rating_avg"] > 0, "Rating should be non-zero after normalization"
    assert local["review_velocity_avg"] > 0, "Review velocity should be non-zero"
    assert local["gbp_completeness_avg"] > 0, "GBP completeness should be non-zero"
    assert local["citation_consistency"] > 0, "Citation consistency should be non-zero"
