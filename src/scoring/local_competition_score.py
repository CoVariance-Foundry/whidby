"""Local competition score implementation."""

from __future__ import annotations

from collections.abc import Mapping

from src.config.constants import (
    M7_NO_LOCAL_PACK_DEFAULT_SCORE,
    M7_PHOTO_COUNT_CEILING,
    M7_REVIEW_BARRIER_CEILING,
    M7_REVIEW_VELOCITY_CEILING,
)

from .normalization import clamp, inverse_scale


def compute_local_competition_score(signals: Mapping[str, object]) -> float:
    """Compute local pack competition score where higher is easier."""
    if not bool(signals.get("local_pack_present", False)):
        return M7_NO_LOCAL_PACK_DEFAULT_SCORE

    review_barrier = inverse_scale(
        float(signals.get("local_pack_review_count_avg", 0.0)),
        floor=0.0,
        ceiling=M7_REVIEW_BARRIER_CEILING,
    )
    velocity_score = inverse_scale(
        float(signals.get("review_velocity_avg", 0.0)),
        floor=0.0,
        ceiling=M7_REVIEW_VELOCITY_CEILING,
    )
    gbp_weakness = (1.0 - float(signals.get("gbp_completeness_avg", 0.0))) * 100.0
    photo_weakness = inverse_scale(float(signals.get("gbp_photo_count_avg", 0.0)), 0.0, M7_PHOTO_COUNT_CEILING)
    posting_weakness = (1.0 - float(signals.get("gbp_posting_activity", 0.0))) * 100.0
    raw = (
        review_barrier * 0.30
        + velocity_score * 0.25
        + gbp_weakness * 0.20
        + photo_weakness * 0.10
        + posting_weakness * 0.15
    )
    return clamp(raw)

