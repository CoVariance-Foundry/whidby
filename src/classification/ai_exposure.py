"""AI exposure classification for M8."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .types import AIExposure


def classify_ai_exposure(signals: Mapping[str, Any]) -> AIExposure:
    """Classify AI exposure from M6 AI resilience signals."""
    ai_resilience = signals.get("ai_resilience")
    aio_trigger_rate = 0.0
    if isinstance(ai_resilience, Mapping):
        aio_trigger_rate = _to_float(ai_resilience.get("aio_trigger_rate"))

    if aio_trigger_rate < 0.05:
        return "AI_SHIELDED"
    if aio_trigger_rate < 0.15:
        return "AI_MINIMAL"
    if aio_trigger_rate < 0.30:
        return "AI_MODERATE"
    return "AI_EXPOSED"


def _to_float(value: Any) -> float:
    """Safely coerce numeric-like values to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
