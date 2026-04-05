"""Normalization utilities for M7 scoring."""

from __future__ import annotations

from bisect import bisect_right
from typing import Iterable


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    """Clamp a numeric value to an inclusive range."""
    return max(lower, min(upper, value))


def scale(value: float, floor: float, ceiling: float) -> float:
    """Scale value linearly into 0-100."""
    if ceiling <= floor:
        return 0.0
    position = (value - floor) / (ceiling - floor)
    return clamp(position * 100.0, 0.0, 100.0)


def inverse_scale(value: float, floor: float, ceiling: float) -> float:
    """Inverse of scale where lower raw values produce higher scores."""
    return clamp(100.0 - scale(value, floor=floor, ceiling=ceiling), 0.0, 100.0)


def percentile_rank(value: float, all_values: Iterable[float]) -> float:
    """Compute percentile rank in [0, 100] against a cohort."""
    series = sorted(float(v) for v in all_values)
    if not series:
        return 50.0
    if len(series) == 1:
        return 100.0 if value >= series[0] else 0.0
    idx = bisect_right(series, float(value)) - 1
    idx = max(0, min(idx, len(series) - 1))
    return (idx / (len(series) - 1)) * 100.0

