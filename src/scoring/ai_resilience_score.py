"""AI resilience score implementation."""

from __future__ import annotations

from collections.abc import Mapping

from src.config.constants import M7_AIO_TRIGGER_CEILING, M7_PAA_DENSITY_CEILING

from .normalization import clamp, inverse_scale


def compute_ai_resilience_score(signals: Mapping[str, object]) -> float:
    """Compute AI resilience score where higher is more resilient."""
    aio_safety = inverse_scale(
        float(signals.get("aio_trigger_rate", 0.0)),
        floor=0.0,
        ceiling=M7_AIO_TRIGGER_CEILING,
    )
    intent_safety = float(signals.get("transactional_keyword_ratio", signals.get("transactional_ratio", 0.0))) * 100.0
    niche_type = str(signals.get("niche_type", "local_service")).strip().lower()
    local_fulfillment_required = float(signals.get("local_fulfillment_required", 1.0))
    if niche_type == "informational":
        local_fulfillment_required = 0.0
    fulfillment_bonus = local_fulfillment_required * 20.0
    paa_safety = inverse_scale(float(signals.get("paa_density", 0.0)), floor=0.0, ceiling=M7_PAA_DENSITY_CEILING)
    raw = (
        aio_safety * 0.40
        + intent_safety * 0.25
        + fulfillment_bonus * 0.15
        + paa_safety * 0.20
    )
    if niche_type == "informational" and float(signals.get("aio_trigger_rate", 0.0)) > 0.30:
        raw -= 10.0
    return clamp(raw)

