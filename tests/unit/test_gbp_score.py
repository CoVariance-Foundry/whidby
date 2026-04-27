"""Tests for GBP weakness component scorer."""

from src.scoring.gbp_score import compute_gbp_score
from tests.fixtures.m07_scoring_fixtures import metro_signal


def test_weak_gbp_produces_high_score() -> None:
    signals = metro_signal(
        gbp_completeness_avg=0.20,
        gbp_photo_count_avg=2.0,
        gbp_posting_activity=0.10,
    )
    score = compute_gbp_score(signals)
    assert score > 70.0


def test_strong_gbp_produces_low_score() -> None:
    signals = metro_signal(
        gbp_completeness_avg=0.95,
        gbp_photo_count_avg=45.0,
        gbp_posting_activity=0.90,
    )
    score = compute_gbp_score(signals)
    assert score < 20.0


def test_gbp_score_in_valid_range() -> None:
    score = compute_gbp_score(metro_signal())
    assert 0.0 <= score <= 100.0


def test_gbp_missing_signals_uses_defaults() -> None:
    score = compute_gbp_score({})
    assert 0.0 <= score <= 100.0
