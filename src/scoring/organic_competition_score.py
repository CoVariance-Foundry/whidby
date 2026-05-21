"""Organic competition score implementation."""

from __future__ import annotations

from collections.abc import Mapping

from src.config.constants import M7_DA_CEILING, M7_LOCAL_RATIO_DENOMINATOR

from .normalization import clamp, inverse_scale


def _number(value: object, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_organic_competition_score(signals: Mapping[str, object]) -> float:
    """Compute organic competition score where higher is easier."""
    da_score = inverse_scale(
        _number(signals.get("avg_top5_da"), M7_DA_CEILING / 2.0),
        floor=0.0,
        ceiling=M7_DA_CEILING,
    )
    local_ratio = _number(signals.get("local_biz_count"), 0.0) / M7_LOCAL_RATIO_DENOMINATOR
    local_score = clamp(local_ratio * 100.0)
    tech_weakness = (
        inverse_scale(_number(signals.get("avg_lighthouse_performance"), 50.0), 0.0, 100.0)
        * 0.5
        + (1.0 - _number(signals.get("schema_adoption_rate"), 0.0)) * 100.0 * 0.5
    )
    title_weakness = (1.0 - _number(signals.get("title_keyword_match_rate"), 0.0)) * 100.0
    agg_penalty = _number(signals.get("aggregator_count"), 0.0) * 8.0
    raw = (
        da_score * 0.35
        + local_score * 0.20
        + tech_weakness * 0.20
        + title_weakness * 0.15
        - agg_penalty * 0.10
    )
    return clamp(raw)
