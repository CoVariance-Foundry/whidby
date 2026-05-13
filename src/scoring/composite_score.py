"""Composite opportunity score implementation."""

from __future__ import annotations

from src.config.constants import (
    M7_AI_FLOOR_COMPONENT_THRESHOLD,
    M7_AI_FLOOR_COMPOSITE_CAP,
    M7_THRESHOLD_GATE_HARD_CAP,
    M7_THRESHOLD_GATE_HARD_MIN_COMPONENT,
    M7_THRESHOLD_GATE_SOFT_CAP,
    M7_THRESHOLD_GATE_SOFT_MIN_COMPONENT,
)

from .normalization import clamp

_BASE_GATE_COMPONENTS = frozenset({
    "demand", "organic_competition", "local_competition",
    "monetization", "ai_resilience",
})


def compute_opportunity_score(
    *,
    component_scores: dict[str, float],
    weights: dict[str, float],
) -> float:
    """Compute composite opportunity score with gates and floors.

    Gates apply only to the 5 base components regardless of extra lens dimensions.
    """
    raw = sum(
        component_scores.get(name, 0.0) * weight
        for name, weight in weights.items()
    )

    gate_values = [
        component_scores[k]
        for k in _BASE_GATE_COMPONENTS
        if k in component_scores
    ]
    if gate_values:
        min_component = min(gate_values)
        if min_component < M7_THRESHOLD_GATE_HARD_MIN_COMPONENT:
            raw = min(raw, M7_THRESHOLD_GATE_HARD_CAP)
        elif min_component < M7_THRESHOLD_GATE_SOFT_MIN_COMPONENT:
            raw = min(raw, M7_THRESHOLD_GATE_SOFT_CAP)

    if component_scores.get("ai_resilience", 100.0) < M7_AI_FLOOR_COMPONENT_THRESHOLD:
        raw = min(raw, M7_AI_FLOOR_COMPOSITE_CAP)

    return clamp(raw)
