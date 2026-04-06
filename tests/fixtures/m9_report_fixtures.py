"""Fixtures for M9 report generation and feedback logging tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def make_run_input() -> dict[str, Any]:
    """Build a representative M4-M8 run payload for M9 tests."""
    return {
        "run_id": "run-123",
        "generated_at": "2026-04-05T00:00:00+00:00",
        "input": {"niche": "roofing", "strategy_profile": "balanced"},
        "keyword_expansion": {"seed_keywords": ["roof repair"], "expanded_count": 3},
        "metros": [
            make_metro(
                cbsa_code="38060",
                cbsa_name="Phoenix-Mesa-Chandler, AZ",
                opportunity=84.2,
            ),
            make_metro(
                cbsa_code="41740",
                cbsa_name="San Diego-Chula Vista-Carlsbad, CA",
                opportunity=72.1,
            ),
            make_metro(
                cbsa_code="19100",
                cbsa_name="Dallas-Fort Worth-Arlington, TX",
                opportunity=84.2,
            ),
        ],
        "meta": {
            "total_api_calls": 31,
            "total_cost_usd": 7.345,
            "processing_time_seconds": 42.8,
        },
    }


def make_metro(cbsa_code: str, cbsa_name: str, opportunity: float) -> dict[str, Any]:
    """Build a metro payload with required fields."""
    return {
        "cbsa_code": cbsa_code,
        "cbsa_name": cbsa_name,
        "population": 1000000,
        "scores": {
            "demand": 76.0,
            "organic_competition": 48.0,
            "local_competition": 41.0,
            "monetization": 69.0,
            "ai_resilience": 64.0,
            "opportunity": opportunity,
        },
        "confidence": {"score": 0.79, "coverage": 0.9},
        "serp_archetype": "service_dominant",
        "ai_exposure": "medium",
        "difficulty_tier": "moderate",
        "signals": {"review_velocity": 12.0, "gbp_completeness": 0.7},
        "guidance": {"next_step": "target suburb clusters"},
    }


def make_tie_break_run_input() -> dict[str, Any]:
    """Build run payload where metros tie on opportunity."""
    run_input = make_run_input()
    run_input["metros"] = [
        make_metro("49740", "Yuma, AZ", 80.0),
        make_metro("38060", "Phoenix-Mesa-Chandler, AZ", 80.0),
    ]
    return run_input


def make_invalid_run_input_missing_path() -> dict[str, Any]:
    """Build invalid run payload missing a required nested field."""
    run_input = make_run_input()
    del run_input["meta"]["total_cost_usd"]
    return run_input


def make_run_input_with_invalid_metro_scores() -> dict[str, Any]:
    """Build run payload where a metro has non-numeric opportunity."""
    run_input = make_run_input()
    run_input["metros"][0]["scores"]["opportunity"] = "not-a-number"
    return run_input


def make_run_input_with_metro_missing_field() -> dict[str, Any]:
    """Build run payload where a metro is missing scores.demand."""
    run_input = make_run_input()
    del run_input["metros"][0]["scores"]["demand"]
    return run_input


def make_run_input_with_non_dict_metro() -> dict[str, Any]:
    """Build run payload where a metro entry is not a dict."""
    run_input = make_run_input()
    run_input["metros"][1] = "not-a-dict"
    return run_input


def make_run_input_with_invalid_meta_type() -> dict[str, Any]:
    """Build run payload where meta.total_api_calls is non-numeric."""
    run_input = make_run_input()
    run_input["meta"]["total_api_calls"] = "abc"
    return run_input


def make_minimal_invalid_report_for_feedback() -> dict[str, Any]:
    """Build a minimal dict that passes old validation but not the full contract."""
    return {
        "report_id": "rpt-fake",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "metros": [{"cbsa_code": "12345"}],
    }


def deep_copy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy for mutation-safety assertions."""
    return deepcopy(payload)
