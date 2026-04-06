"""Unit tests for M8 AI exposure classification."""

from __future__ import annotations

from src.classification.ai_exposure import classify_ai_exposure
from tests.fixtures.m8_classification_fixtures import (
    build_ai_exposed_input,
    build_local_pack_vulnerable_input,
)


def test_classify_ai_exposure_returns_shielded_below_point_zero_five() -> None:
    data = build_local_pack_vulnerable_input()
    data["signals"]["ai_resilience"]["aio_trigger_rate"] = 0.04
    assert classify_ai_exposure(data["signals"]) == "AI_SHIELDED"


def test_classify_ai_exposure_returns_minimal_between_point_zero_five_and_point_fifteen() -> None:
    data = build_local_pack_vulnerable_input()
    data["signals"]["ai_resilience"]["aio_trigger_rate"] = 0.12
    assert classify_ai_exposure(data["signals"]) == "AI_MINIMAL"


def test_classify_ai_exposure_returns_moderate_between_point_fifteen_and_point_thirty() -> None:
    data = build_local_pack_vulnerable_input()
    data["signals"]["ai_resilience"]["aio_trigger_rate"] = 0.2
    assert classify_ai_exposure(data["signals"]) == "AI_MODERATE"


def test_classify_ai_exposure_returns_exposed_at_or_above_point_thirty() -> None:
    data = build_ai_exposed_input()
    assert classify_ai_exposure(data["signals"]) == "AI_EXPOSED"


def test_classify_ai_exposure_boundary_at_exactly_point_zero_five() -> None:
    data = build_local_pack_vulnerable_input()
    data["signals"]["ai_resilience"]["aio_trigger_rate"] = 0.05
    assert classify_ai_exposure(data["signals"]) == "AI_MINIMAL"


def test_classify_ai_exposure_boundary_at_exactly_point_fifteen() -> None:
    data = build_local_pack_vulnerable_input()
    data["signals"]["ai_resilience"]["aio_trigger_rate"] = 0.15
    assert classify_ai_exposure(data["signals"]) == "AI_MODERATE"


def test_classify_ai_exposure_boundary_at_exactly_point_thirty() -> None:
    data = build_local_pack_vulnerable_input()
    data["signals"]["ai_resilience"]["aio_trigger_rate"] = 0.30
    assert classify_ai_exposure(data["signals"]) == "AI_EXPOSED"


def test_classify_ai_exposure_boundary_just_below_point_zero_five() -> None:
    data = build_local_pack_vulnerable_input()
    data["signals"]["ai_resilience"]["aio_trigger_rate"] = 0.0499
    assert classify_ai_exposure(data["signals"]) == "AI_SHIELDED"
