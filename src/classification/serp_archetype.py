"""SERP archetype classification rules for M8."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .types import SerpArchetype


def classify_serp_archetype(signals: Mapping[str, Any]) -> tuple[SerpArchetype, str]:
    """Classify a metro into one SERP archetype.

    Args:
        signals: M6 signal categories for one metro.

    Returns:
        A tuple of (archetype, matched_rule_id).
    """
    organic = _as_mapping(signals.get("organic_competition"))
    local = _as_mapping(signals.get("local_competition"))

    aggregator_count = _to_float(organic.get("aggregator_count"))
    local_biz_count = _to_float(organic.get("local_biz_count"))
    avg_top5_da = _to_float(organic.get("avg_top5_da"))

    has_local_pack = bool(local.get("local_pack_present", False))
    review_avg = _to_float(local.get("local_pack_review_count_avg"))
    velocity_avg = _to_float(local.get("review_velocity_avg"))

    agg_ratio = aggregator_count / 10.0
    local_ratio = local_biz_count / 10.0

    if agg_ratio >= 0.5:
        return "AGGREGATOR_DOMINATED", "agg_ratio_ge_0_5"
    if has_local_pack and review_avg > 100 and velocity_avg > 5:
        return "LOCAL_PACK_FORTIFIED", "pack_review_gt_100_and_velocity_gt_5"
    if has_local_pack and review_avg > 30:
        return "LOCAL_PACK_ESTABLISHED", "pack_review_gt_30"
    if has_local_pack and review_avg <= 30:
        return "LOCAL_PACK_VULNERABLE", "pack_review_lte_30"
    if local_ratio >= 0.4 and avg_top5_da < 25:
        return "FRAGMENTED_WEAK", "local_ratio_ge_0_4_and_da_lt_25"
    if local_ratio >= 0.4 and avg_top5_da >= 25:
        return "FRAGMENTED_COMPETITIVE", "local_ratio_ge_0_4_and_da_gte_25"
    if local_ratio < 0.3 and agg_ratio < 0.3:
        return "BARREN", "local_ratio_lt_0_3_and_agg_ratio_lt_0_3"
    return "MIXED", "fallback_mixed"


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """Return a dict-like object for nested signal sections."""
    if isinstance(value, Mapping):
        return value
    return {}


def _to_float(value: Any) -> float:
    """Safely coerce numeric-like values to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
