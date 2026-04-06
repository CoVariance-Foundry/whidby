"""Fixtures for M8 classification and guidance tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _base_input() -> dict[str, Any]:
    return {
        "niche": "plumber",
        "metro_name": "Phoenix, AZ",
        "strategy_profile": "balanced",
        "signals": {
            "organic_competition": {
                "aggregator_count": 1,
                "local_biz_count": 4,
                "avg_top5_da": 24,
            },
            "local_competition": {
                "local_pack_present": True,
                "local_pack_position": 2,
                "local_pack_review_count_avg": 22,
                "review_velocity_avg": 2.1,
            },
            "ai_resilience": {
                "aio_trigger_rate": 0.04,
            },
        },
        "scores": {
            "organic_competition": 30.0,
            "local_competition": 35.0,
            "opportunity": 67.0,
        },
    }


def build_local_pack_vulnerable_input() -> dict[str, Any]:
    """Fixture aligned to LOCAL_PACK_VULNERABLE and AI_SHIELDED."""
    return deepcopy(_base_input())


def build_aggregator_dominated_input() -> dict[str, Any]:
    """Fixture aligned to AGGREGATOR_DOMINATED archetype."""
    data = _base_input()
    data["signals"]["organic_competition"]["aggregator_count"] = 6
    data["signals"]["organic_competition"]["local_biz_count"] = 2
    return deepcopy(data)


def build_barren_input() -> dict[str, Any]:
    """Fixture aligned to BARREN archetype."""
    data = _base_input()
    data["signals"]["organic_competition"]["aggregator_count"] = 2
    data["signals"]["organic_competition"]["local_biz_count"] = 2
    data["signals"]["local_competition"]["local_pack_present"] = False
    data["signals"]["local_competition"]["local_pack_position"] = 10
    data["signals"]["local_competition"]["local_pack_review_count_avg"] = 0
    return deepcopy(data)


def build_ai_exposed_input() -> dict[str, Any]:
    """Fixture aligned to AI_EXPOSED classification."""
    data = _base_input()
    data["signals"]["ai_resilience"]["aio_trigger_rate"] = 0.42
    return deepcopy(data)


def build_easy_profile_input() -> dict[str, Any]:
    """Fixture aligned to EASY/MODERATE outcome.

    High M7 scores indicate weak competition (inverse-scaled), so ranking is easy.
    """
    data = _base_input()
    data["scores"]["organic_competition"] = 80.0
    data["scores"]["local_competition"] = 75.0
    return deepcopy(data)


def build_hard_profile_input() -> dict[str, Any]:
    """Fixture aligned to HARD/VERY_HARD outcome.

    Low M7 scores indicate strong competition (inverse-scaled), so ranking is hard.
    """
    data = _base_input()
    data["scores"]["organic_competition"] = 18.0
    data["scores"]["local_competition"] = 20.0
    data["signals"]["ai_resilience"]["aio_trigger_rate"] = 0.33
    return deepcopy(data)
