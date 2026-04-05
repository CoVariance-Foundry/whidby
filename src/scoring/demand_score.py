"""Demand score implementation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from src.config.constants import MEDIAN_LOCAL_SERVICE_CPC

from .normalization import clamp, percentile_rank


def compute_demand_score(
    signals: Mapping[str, object],
    all_metro_signals: Sequence[Mapping[str, object]],
) -> float:
    """Compute demand score in [0, 100]."""
    cohort_values = [
        float(metro.get("effective_search_volume", 0.0))
        for metro in all_metro_signals
    ]
    volume_percentile = percentile_rank(
        float(signals.get("effective_search_volume", 0.0)),
        cohort_values,
    )
    avg_cpc = float(signals.get("avg_cpc", 0.0))
    cpc_multiplier = min(avg_cpc / MEDIAN_LOCAL_SERVICE_CPC, 2.0) if MEDIAN_LOCAL_SERVICE_CPC else 1.0
    breadth_bonus = float(signals.get("volume_breadth", 0.0)) * 15.0
    intent_bonus = float(signals.get("transactional_ratio", 0.0)) * 10.0
    raw = (
        (volume_percentile * 0.60 * cpc_multiplier)
        + (breadth_bonus * 0.20)
        + (intent_bonus * 0.20)
    )
    return clamp(raw)

