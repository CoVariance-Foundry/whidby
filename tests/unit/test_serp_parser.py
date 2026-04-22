"""Unit tests for M6 SERP parser."""

from __future__ import annotations

from src.pipeline.serp_parser import parse_serp_features
from tests.fixtures.m6_signal_extraction_fixtures import build_sample_bundle


def test_parse_serp_features_detects_aio_and_pack_features() -> None:
    bundle = build_sample_bundle()
    parsed = parse_serp_features(bundle["serp_organic"])

    assert parsed["aio_trigger_rate"] > 0
    assert parsed["local_pack_present"] is True
    assert parsed["local_pack_position"] == 2
    assert parsed["lsa_present"] is True
    assert parsed["ads_present"] is True
    assert parsed["featured_snippet_rate"] > 0
    assert parsed["paa_density"] > 0


def test_parse_serp_features_returns_safe_defaults_for_empty_input() -> None:
    parsed = parse_serp_features([])
    assert parsed["aio_trigger_rate"] == 0.0
    assert parsed["featured_snippet_rate"] == 0.0
    assert parsed["local_pack_present"] is False
    assert parsed["local_pack_position"] == 10


def test_parse_serp_features_handles_dfs_items_array_format() -> None:
    """DataForSEO live/advanced returns items as a typed array, not pre-parsed."""
    dfs_rows = [
        {
            "keyword": "roofing chicago",
            "items": [
                {"type": "organic", "rank_group": 1, "domain": "www.gaf.com", "title": "GAF Roofing", "url": "https://www.gaf.com"},
                {"type": "organic", "rank_group": 2, "domain": "www.owenscorning.com", "title": "Owens Corning Roofing", "url": "https://www.owenscorning.com"},
                {"type": "local_pack", "rank_group": 3, "rank_absolute": 3},
                {"type": "ai_overview", "rank_group": 0},
                {"type": "people_also_ask", "items": [{"question": "q1"}, {"question": "q2"}]},
                {"type": "featured_snippet", "rank_group": 4, "domain": "example.com", "title": "Roofing Guide", "url": "https://example.com"},
                {"type": "paid", "rank_group": 0, "domain": "ads.com"},
                {"type": "local_services_ads", "rank_group": 0},
            ],
        },
        {
            "keyword": "roof repair chicago",
            "items": [
                {"type": "organic", "rank_group": 1, "domain": "roofrepair.com", "title": "Roof Repair Chicago", "url": "https://roofrepair.com"},
            ],
        },
    ]
    parsed = parse_serp_features(dfs_rows)

    assert parsed["aio_trigger_rate"] == 0.5
    assert parsed["featured_snippet_rate"] == 0.5
    assert parsed["local_pack_present"] is True
    assert parsed["local_pack_position"] == 3
    assert parsed["lsa_present"] is True
    assert parsed["ads_present"] is True
    assert parsed["paa_density"] == 1.0
    assert len(parsed["organic_domains"]) >= 3
    assert "gaf.com" in parsed["organic_domains"]
    assert len(parsed["organic_titles"]) >= 3
