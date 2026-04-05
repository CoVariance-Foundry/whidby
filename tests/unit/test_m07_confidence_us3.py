"""US3 tests for confidence penalties and flags."""

from copy import deepcopy

from src.scoring.confidence_score import compute_confidence
from tests.fixtures.m07_scoring_fixtures import metro_signal


def test_missing_data_applies_expected_confidence_penalties() -> None:
    low_quality = metro_signal(
        expansion_confidence="low",
        lighthouse_results_count=1,
        backlink_results_count=1,
        serp_results_count=0,
        review_results_count=0,
        gbp_results_count=0,
        total_search_volume=25.0,
        aio_trigger_rate=0.45,
    )
    result = compute_confidence(low_quality)
    codes = {flag["code"] for flag in result["flags"]}
    assert "keyword_expansion_uncertain" in codes
    assert "no_serp_data" in codes
    assert result["score"] < 100


def test_explicit_none_values_do_not_raise() -> None:
    null_signals = metro_signal(
        lighthouse_results_count=None,
        backlink_results_count=None,
        serp_results_count=None,
        review_results_count=None,
        gbp_results_count=None,
        total_search_volume=None,
        aio_trigger_rate=None,
        expansion_confidence=None,
    )
    result = compute_confidence(null_signals)
    assert 0.0 <= float(result["score"]) <= 100.0
    assert isinstance(result["flags"], list)


def test_none_counts_match_missing_key_behavior() -> None:
    with_none = metro_signal(lighthouse_results_count=None)
    without_key = deepcopy(metro_signal())
    del without_key["lighthouse_results_count"]
    assert compute_confidence(with_none) == compute_confidence(without_key)


def test_zero_counts_still_trigger_penalties() -> None:
    zero_signals = metro_signal(serp_results_count=0, lighthouse_results_count=0)
    result = compute_confidence(zero_signals)
    codes = {flag["code"] for flag in result["flags"]}
    assert "no_serp_data" in codes
    assert "incomplete_onpage_data" in codes


def test_expansion_confidence_none_does_not_trigger_penalty() -> None:
    result = compute_confidence(metro_signal(expansion_confidence=None))
    codes = {flag["code"] for flag in result["flags"]}
    assert "keyword_expansion_uncertain" not in codes

