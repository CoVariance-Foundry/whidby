"""M7 scoring engine orchestration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.config.constants import FIXED_WEIGHTS

from .ai_resilience_score import compute_ai_resilience_score
from .gbp_score import compute_gbp_score
from .composite_score import compute_opportunity_score
from .confidence_score import compute_confidence
from .demand_score import compute_demand_score
from .local_competition_score import compute_local_competition_score
from .monetization_score import compute_monetization_score
from .organic_competition_score import compute_organic_competition_score
from .strategy_profiles import resolve_strategy_weights


def _flatten_signal_shape(signals: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize M6 nested signal blocks into M7 flat keys."""
    flattened: dict[str, Any] = dict(signals)
    for category in (
        "demand",
        "organic_competition",
        "local_competition",
        "monetization",
        "ai_resilience",
    ):
        block = signals.get(category)
        if isinstance(block, Mapping):
            flattened.update(block)
    return flattened


def compute_scores(
    *,
    metro_signals: Mapping[str, Any],
    all_metro_signals: Sequence[Mapping[str, Any]],
    strategy_profile: str = "balanced",
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute all M7 scores for a single metro.

    When *weights* is provided the composite score uses those weights
    directly instead of deriving them from *strategy_profile*.
    """
    metro = _flatten_signal_shape(metro_signals)
    cohort = [_flatten_signal_shape(item) for item in all_metro_signals]

    demand = compute_demand_score(metro, cohort)
    organic_competition = compute_organic_competition_score(metro)
    local_competition = compute_local_competition_score(metro)
    monetization = compute_monetization_score(metro)
    ai_resilience = compute_ai_resilience_score(metro)
    gbp = compute_gbp_score(metro)

    component_scores = {
        "demand": demand,
        "organic_competition": organic_competition,
        "local_competition": local_competition,
        "monetization": monetization,
        "ai_resilience": ai_resilience,
        "gbp": gbp,
    }

    if weights is not None:
        composite_weights = weights
        resolved = None
    else:
        resolved = resolve_strategy_weights(strategy_profile, metro)
        composite_weights = {
            "demand": FIXED_WEIGHTS["demand"],
            "organic_competition": resolved["organic"],
            "local_competition": resolved["local"],
            "monetization": FIXED_WEIGHTS["monetization"],
            "ai_resilience": FIXED_WEIGHTS["ai_resilience"],
        }

    opportunity = compute_opportunity_score(
        component_scores=component_scores,
        weights=composite_weights,
    )
    confidence = compute_confidence(metro)
    return {
        "demand": demand,
        "organic_competition": organic_competition,
        "local_competition": local_competition,
        "monetization": monetization,
        "ai_resilience": ai_resilience,
        "gbp": gbp,
        "opportunity": opportunity,
        "confidence": confidence,
        "resolved_weights": resolved,
    }


def compute_batch_scores(
    metros: Sequence[Mapping[str, Any]],
    strategy_profile: str = "balanced",
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Compute M7 scores for a metro batch using shared cohort context."""
    return [
        compute_scores(
            metro_signals=metro,
            all_metro_signals=metros,
            strategy_profile=strategy_profile,
            weights=weights,
        )
        for metro in metros
    ]

