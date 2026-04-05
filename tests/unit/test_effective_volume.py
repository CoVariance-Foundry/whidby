"""Unit tests for AIO-adjusted effective volume."""

from __future__ import annotations

from src.pipeline.effective_volume import compute_effective_volume


def test_effective_volume_detected_aio_applies_full_ctr_reduction() -> None:
    value = compute_effective_volume(1000, "transactional", aio_detected_in_serp=True)
    assert round(value, 2) == 410.0


def test_effective_volume_transactional_expected_discount_is_small() -> None:
    value = compute_effective_volume(1000, "transactional", aio_detected_in_serp=False)
    assert 980 <= value <= 990


def test_effective_volume_informational_expected_discount_is_large() -> None:
    value = compute_effective_volume(1000, "informational", aio_detected_in_serp=False)
    assert 730 <= value <= 750
