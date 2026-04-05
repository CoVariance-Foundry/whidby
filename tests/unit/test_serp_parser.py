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
