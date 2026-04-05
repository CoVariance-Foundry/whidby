"""Composite opportunity score implementation."""

from __future__ import annotations

from src.config.constants import (
    FIXED_WEIGHTS,
    M7_AI_FLOOR_COMPONENT_THRESHOLD,
    M7_AI_FLOOR_COMPOSITE_CAP,
    M7_THRESHOLD_GATE_HARD_CAP,
    M7_THRESHOLD_GATE_HARD_MIN_COMPONENT,
    M7_THRESHOLD_GATE_SOFT_CAP,
    M7_THRESHOLD_GATE_SOFT_MIN_COMPONENT,
)

from .normalization import clamp


def compute_opportunity_score(
    *,
    demand: float,
    organic_competition: float,
    local_competition: float,
    monetization: float,
    ai_resilience: float,
    organic_weight: float,
    local_weight: float,
) -> float:
    """Compute composite opportunity score with gates and floors."""
    raw = (
        demand * FIXED_WEIGHTS["demand"]
        + organic_competition * organic_weight
        + local_competition * local_weight
        + monetization * FIXED_WEIGHTS["monetization"]
        + ai_resilience * FIXED_WEIGHTS["ai_resilience"]
    )
    min_component = min(demand, organic_competition, local_competition, monetization, ai_resilience)
    if min_component < M7_THRESHOLD_GATE_HARD_MIN_COMPONENT:
        raw = min(raw, M7_THRESHOLD_GATE_HARD_CAP)
    elif min_component < M7_THRESHOLD_GATE_SOFT_MIN_COMPONENT:
        raw = min(raw, M7_THRESHOLD_GATE_SOFT_CAP)
    if ai_resilience < M7_AI_FLOOR_COMPONENT_THRESHOLD:
        raw = min(raw, M7_AI_FLOOR_COMPOSITE_CAP)
    return clamp(raw)

