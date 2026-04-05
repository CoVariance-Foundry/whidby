"""Unit tests for review velocity helper."""

from __future__ import annotations

from src.pipeline.review_velocity import compute_reviews_per_month


def test_compute_reviews_per_month_from_timestamp_span() -> None:
    timestamps = [
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
        "2026-03-01T00:00:00Z",
    ]
    rate = compute_reviews_per_month(timestamps)
    assert rate > 1.0


def test_compute_reviews_per_month_empty_returns_zero() -> None:
    assert compute_reviews_per_month([]) == 0.0


def test_compute_reviews_per_month_single_timestamp_returns_one() -> None:
    assert compute_reviews_per_month(["2026-01-01T00:00:00Z"]) == 1.0
