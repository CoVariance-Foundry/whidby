"""Confidence scoring for M7 outputs."""

from __future__ import annotations

from collections.abc import Mapping

from .normalization import clamp


def _safe_int(signals: Mapping[str, object], key: str, default: int) -> int:
    """Return int value for key, treating None or missing as default."""
    raw = signals.get(key)
    if raw is None:
        return default
    return int(raw)


def _safe_float(signals: Mapping[str, object], key: str, default: float) -> float:
    """Return float value for key, treating None or missing as default."""
    raw = signals.get(key)
    if raw is None:
        return default
    return float(raw)


def compute_confidence(signals: Mapping[str, object]) -> dict[str, object]:
    """Compute confidence score and flags for one metro."""
    penalties: list[dict[str, object]] = []

    raw_conf = signals.get("expansion_confidence")
    expansion_conf = str(raw_conf).strip().lower() if raw_conf is not None else "high"
    if expansion_conf == "low":
        penalties.append({"code": "keyword_expansion_uncertain", "penalty": -20})

    if _safe_int(signals, "lighthouse_results_count", 3) < 3:
        penalties.append({"code": "incomplete_onpage_data", "penalty": -10})
    if _safe_int(signals, "backlink_results_count", 3) < 3:
        penalties.append({"code": "incomplete_backlink_data", "penalty": -10})
    if _safe_int(signals, "serp_results_count", 10) == 0:
        penalties.append({"code": "no_serp_data", "penalty": -40})
    if _safe_int(signals, "review_results_count", 2) < 2:
        penalties.append({"code": "incomplete_review_data", "penalty": -10})
    if _safe_int(signals, "gbp_results_count", 3) < 3:
        penalties.append({"code": "incomplete_gbp_data", "penalty": -10})
    if _safe_float(signals, "total_search_volume", 100.0) < 50.0:
        penalties.append({"code": "very_low_volume", "penalty": -15})
    if _safe_float(signals, "aio_trigger_rate", 0.0) > 0.30:
        penalties.append({"code": "high_aio_exposure", "penalty": -10})

    score = 100.0 + sum(float(flag["penalty"]) for flag in penalties)
    return {"score": clamp(score), "flags": penalties}

