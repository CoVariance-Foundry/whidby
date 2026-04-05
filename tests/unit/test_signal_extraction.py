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
