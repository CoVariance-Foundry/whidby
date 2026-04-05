"""Monetization score implementation."""

from __future__ import annotations

from collections.abc import Mapping

from src.config.constants import (
    M7_DENSITY_CEILING,
    M7_DENSITY_FLOOR,
    M7_MONETIZATION_CPC_CEILING,
    M7_MONETIZATION_CPC_FLOOR,
)

from .normalization import clamp, scale


def compute_monetization_score(signals: Mapping[str, object]) -> float:
    """Compute monetization score in [0, 100]."""
    cpc_score = scale(
        float(signals.get("avg_cpc", 0.0)),
        floor=M7_MONETIZATION_CPC_FLOOR,
        ceiling=M7_MONETIZATION_CPC_CEILING,
    )
    density_score = scale(
        float(signals.get("business_density", 0.0)),
        floor=M7_DENSITY_FLOOR,
        ceiling=M7_DENSITY_CEILING,
    )
    has_ads = bool(signals.get("ads_top_present", False)) or bool(signals.get("ads_present", False))
    active_market = (
        float(bool(signals.get("lsa_present", False))) * 30.0
        + float(has_ads) * 20.0
        + min(float(signals.get("aggregator_presence", 0.0)), 3.0) * 10.0
    )
    gbp_score = float(signals.get("gbp_completeness_avg", 0.0)) * 100.0
    raw = (
        cpc_score * 0.35
        + density_score * 0.25
        + active_market * 0.25
        + gbp_score * 0.15
    )
    return clamp(raw)

