"""M7 scoring engine orchestration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .ai_resilience_score import compute_ai_resilience_score
from .composite_score import compute_opportunity_score
from .confidence_score import compute_confidence
from .demand_score import compute_demand_score
from .local_competition_score import compute_local_competition_score
from .monetization_score import compute_monetization_score
from .organic_competition_score import compute_organic_competition_score
from .strategy_profiles import resolve_strategy_weights


def compute_scores(
    *,
    metro_signals: Mapping[str, Any],
    all_metro_signals: Sequence[Mapping[str, Any]],
    strategy_profile: str,
) -> dict[str, Any]:
    """Compute all M7 scores for a single metro."""
    demand = compute_demand_score(metro_signals, all_metro_signals)
    organic_competition = compute_organic_competition_score(metro_signals)
    local_competition = compute_local_competition_score(metro_signals)
    monetization = compute_monetization_score(metro_signals)
    ai_resilience = compute_ai_resilience_score(metro_signals)
    resolved_weights = resolve_strategy_weights(strategy_profile, metro_signals)
    opportunity = compute_opportunity_score(
        demand=demand,
        organic_competition=organic_competition,
        local_competition=local_competition,
        monetization=monetization,
        ai_resilience=ai_resilience,
        organic_weight=resolved_weights["organic"],
        local_weight=resolved_weights["local"],
    )
    confidence = compute_confidence(metro_signals)
    return {
        "demand": demand,
        "organic_competition": organic_competition,
        "local_competition": local_competition,
        "monetization": monetization,
        "ai_resilience": ai_resilience,
        "opportunity": opportunity,
        "confidence": confidence,
        "resolved_weights": resolved_weights,
    }


def compute_batch_scores(
    metros: Sequence[Mapping[str, Any]],
    strategy_profile: str,
) -> list[dict[str, Any]]:
    """Compute M7 scores for a metro batch using shared cohort context."""
    return [
        compute_scores(
            metro_signals=metro,
            all_metro_signals=metros,
            strategy_profile=strategy_profile,
        )
        for metro in metros
    ]

