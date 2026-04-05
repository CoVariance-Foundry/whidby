"""Strategy profile resolution for M7 composite scoring."""

from __future__ import annotations

from typing import Mapping

from src.config.constants import STRATEGY_PROFILES

_AUTO_ABOVE_FOLD_WEIGHTS = {"organic": 0.08, "local": 0.27}


def _resolve_auto(signals: Mapping[str, object] | None) -> dict[str, float]:
    """Resolve auto profile weights from SERP structure signals.

    Branches (Algo Spec V1.1 §3.4):
      - signals missing/None -> balanced fallback
      - no local pack -> organic_first behavior (table intent)
      - pack present, position <= 3 (above-fold) -> 0.08 / 0.27
      - pack present, position > 3 or missing -> balanced fallback
    """
    if signals is None:
        return _weights_from_profile("balanced")

    if not bool(signals.get("local_pack_present", False)):
        return _weights_from_profile("organic_first")

    position = signals.get("local_pack_position")
    if position is not None and float(position) <= 3:
        return dict(_AUTO_ABOVE_FOLD_WEIGHTS)

    return _weights_from_profile("balanced")


def _weights_from_profile(name: str) -> dict[str, float]:
    """Build normalized weight dict from a named static profile."""
    weights = STRATEGY_PROFILES.get(name, STRATEGY_PROFILES["balanced"])
    organic = float(weights["organic_weight"])
    local = float(weights["local_weight"])
    total = organic + local
    if total <= 0:
        return {"organic": 0.15, "local": 0.20}
    factor = 0.35 / total
    return {"organic": organic * factor, "local": local * factor}


def resolve_strategy_weights(
    strategy_profile: str,
    signals: Mapping[str, object] | None = None,
) -> dict[str, float]:
    """Resolve organic/local competition weights for a profile."""
    profile = strategy_profile.strip().lower()
    if profile == "auto":
        return _resolve_auto(signals)

    return _weights_from_profile(profile if profile in STRATEGY_PROFILES else "balanced")

