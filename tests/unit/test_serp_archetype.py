"""Unit tests for M8 SERP archetype classification."""

from __future__ import annotations

from src.classification.serp_archetype import classify_serp_archetype
from tests.fixtures.m8_classification_fixtures import (
    build_aggregator_dominated_input,
    build_barren_input,
    build_local_pack_vulnerable_input,
)


def test_classify_serp_archetype_detects_aggregator_dominated() -> None:
    data = build_aggregator_dominated_input()
    archetype, rule_id = classify_serp_archetype(data["signals"])
    assert archetype == "AGGREGATOR_DOMINATED"
    assert rule_id == "agg_ratio_ge_0_5"


def test_classify_serp_archetype_detects_local_pack_vulnerable() -> None:
    data = build_local_pack_vulnerable_input()
    archetype, rule_id = classify_serp_archetype(data["signals"])
    assert archetype == "LOCAL_PACK_VULNERABLE"
    assert rule_id == "pack_review_lte_30"


def test_classify_serp_archetype_detects_barren_when_no_pack_and_low_density() -> None:
    data = build_barren_input()
    archetype, _ = classify_serp_archetype(data["signals"])
    assert archetype == "BARREN"


def test_classify_serp_archetype_returns_mixed_fallback_for_ambiguous_signals() -> None:
    data = build_local_pack_vulnerable_input()
    data["signals"]["organic_competition"]["local_biz_count"] = 3
    data["signals"]["organic_competition"]["aggregator_count"] = 3
    data["signals"]["local_competition"]["local_pack_present"] = False
    data["signals"]["local_competition"]["local_pack_review_count_avg"] = 0
    archetype, rule_id = classify_serp_archetype(data["signals"])
    assert archetype == "MIXED"
    assert rule_id == "fallback_mixed"
