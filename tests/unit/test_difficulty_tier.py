"""Unit tests for M8 difficulty tiering."""

from __future__ import annotations

from src.classification.difficulty_tier import compute_difficulty_tier
from tests.fixtures.m8_classification_fixtures import (
    build_easy_profile_input,
    build_hard_profile_input,
)


def test_compute_difficulty_tier_returns_easy_or_moderate_for_easy_profile() -> None:
    data = build_easy_profile_input()
    tier, combined, _ = compute_difficulty_tier(
        scores=data["scores"],
        strategy_profile=data["strategy_profile"],
        signals=data["signals"],
    )
    assert tier in {"EASY", "MODERATE"}
    assert combined >= 45

def test_compute_difficulty_tier_returns_hard_or_very_hard_for_headwind_profile() -> None:
    data = build_hard_profile_input()
    tier, combined, _ = compute_difficulty_tier(
        scores=data["scores"],
        strategy_profile=data["strategy_profile"],
        signals=data["signals"],
    )
    assert tier in {"HARD", "VERY_HARD"}
    assert combined < 45


def test_compute_difficulty_tier_uses_strategy_profile_weights() -> None:
    data = build_hard_profile_input()
    _, _, balanced_weights = compute_difficulty_tier(
        scores=data["scores"],
        strategy_profile="balanced",
        signals=data["signals"],
    )
    _, _, local_weights = compute_difficulty_tier(
        scores=data["scores"],
        strategy_profile="local_dominant",
        signals=data["signals"],
    )
    assert local_weights["local"] > balanced_weights["local"]
    assert local_weights["organic"] < balanced_weights["organic"]


def test_compute_difficulty_tier_boundary_at_exactly_70() -> None:
    scores = {"organic_competition": 70.0, "local_competition": 70.0}
    signals: dict = {"local_competition": {"local_pack_present": True, "local_pack_position": 2}}
    tier, combined, _ = compute_difficulty_tier(
        scores=scores, strategy_profile="balanced", signals=signals,
    )
    assert combined >= 70
    assert tier == "EASY"


def test_compute_difficulty_tier_boundary_at_exactly_45() -> None:
    scores = {"organic_competition": 45.0, "local_competition": 45.0}
    signals: dict = {"local_competition": {"local_pack_present": True, "local_pack_position": 2}}
    tier, combined, _ = compute_difficulty_tier(
        scores=scores, strategy_profile="balanced", signals=signals,
    )
    assert combined >= 45
    assert tier == "MODERATE"


def test_compute_difficulty_tier_boundary_at_exactly_25() -> None:
    scores = {"organic_competition": 25.0, "local_competition": 25.0}
    signals: dict = {"local_competition": {"local_pack_present": True, "local_pack_position": 2}}
    tier, combined, _ = compute_difficulty_tier(
        scores=scores, strategy_profile="balanced", signals=signals,
    )
    assert combined >= 25
    assert tier == "HARD"


def test_compute_difficulty_tier_below_25_is_very_hard() -> None:
    scores = {"organic_competition": 10.0, "local_competition": 10.0}
    signals: dict = {"local_competition": {"local_pack_present": True, "local_pack_position": 2}}
    tier, combined, _ = compute_difficulty_tier(
        scores=scores, strategy_profile="balanced", signals=signals,
    )
    assert combined < 25
    assert tier == "VERY_HARD"
