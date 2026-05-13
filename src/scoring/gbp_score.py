"""GBP weakness component scorer.

Measures Google Business Profile weakness — higher score means weaker
competitor GBP profiles (= more opportunity for GBP Blitz strategy).
"""

from __future__ import annotations

from typing import Any, Mapping

from src.config.constants import M7_PHOTO_COUNT_CEILING

from .normalization import clamp, inverse_scale


def compute_gbp_score(signals: Mapping[str, Any]) -> float:
    """Compute GBP weakness score in [0, 100]. Higher = weaker competitor GBP."""
    completeness = float(signals.get("gbp_completeness_avg", 0.5))
    photo_count = float(signals.get("gbp_photo_count_avg", 25.0))
    posting = float(signals.get("gbp_posting_activity", 0.5))

    completeness_weakness = (1.0 - completeness) * 100.0
    photo_weakness = inverse_scale(photo_count, floor=0.0, ceiling=M7_PHOTO_COUNT_CEILING)
    posting_weakness = (1.0 - posting) * 100.0

    raw = (
        completeness_weakness * 0.40
        + photo_weakness * 0.30
        + posting_weakness * 0.30
    )
    return clamp(raw)
