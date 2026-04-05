"""Unit tests for GBP completeness helper."""

from __future__ import annotations

from src.pipeline.gbp_completeness import compute_gbp_completeness


def test_compute_gbp_completeness_five_of_seven_fields() -> None:
    profile = {
        "phone": "555-0100",
        "hours": True,
        "website": "https://example.com",
        "photos": ["p1"],
        "description": "desc",
        "services": [],
        "attributes": [],
    }
    score = compute_gbp_completeness(profile)
    assert round(score, 2) == 0.71


def test_compute_gbp_completeness_empty_profile_returns_zero() -> None:
    assert compute_gbp_completeness({}) == 0.0
