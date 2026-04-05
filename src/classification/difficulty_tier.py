"""Difficulty tier classification for M8."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.scoring.strategy_profiles import resolve_strategy_weights

from .types import DifficultyTier, ResolvedWeights


def compute_difficulty_tier(
    *,
    scores: Mapping[str, Any],
    strategy_profile: str,
    signals: Mapping[str, Any],
) -> tuple[DifficultyTier, float, ResolvedWeights]:
    """Compute one M8 difficulty tier from M7 competition scores.

    Args:
        scores: M7 score output for one metro.
        strategy_profile: Selected strategy profile.
        signals: M6 signals for one metro.

    Returns:
        A tuple of (difficulty_tier, combined_competition, resolved_weights).
    """
    organic_comp = _to_float(scores.get("organic_competition"))
    local_comp = _to_float(scores.get("local_competition"))

    weights = resolve_strategy_weights(strategy_profile, _strategy_signal_view(signals))
    organic_weight = _to_float(weights.get("organic"))
    local_weight = _to_float(weights.get("local"))
    total_comp_weight = organic_weight + local_weight

    if total_comp_weight <= 0:
        organic_proportion = 0.5
        local_proportion = 0.5
    else:
        organic_proportion = organic_weight / total_comp_weight
        local_proportion = local_weight / total_comp_weight

    combined_comp = (local_comp * local_proportion) + (organic_comp * organic_proportion)
    tier = _tier_from_combined_comp(combined_comp)
    resolved: ResolvedWeights = {"organic": organic_weight, "local": local_weight}
    return tier, combined_comp, resolved


def _tier_from_combined_comp(combined_comp: float) -> DifficultyTier:
    """Map weighted competition score into one difficulty bucket.

    M7 competition scores use inverse scaling: higher score means weaker
    competition and therefore easier ranking opportunity.
    """
    if combined_comp >= 70:
        return "EASY"
    if combined_comp >= 45:
        return "MODERATE"
    if combined_comp >= 25:
        return "HARD"
    return "VERY_HARD"


def _strategy_signal_view(signals: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the fields used by strategy auto-resolution from nested M6 signals."""
    local = signals.get("local_competition")
    if not isinstance(local, Mapping):
        return {}
    return {
        "local_pack_present": bool(local.get("local_pack_present", False)),
        "local_pack_position": local.get("local_pack_position"),
    }


def _to_float(value: Any) -> float:
    """Safely coerce numeric-like values to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
