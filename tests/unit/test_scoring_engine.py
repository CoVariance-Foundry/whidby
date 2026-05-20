"""Scoring engine regression tests (consolidated from test_m07_* files).

Tests compute_scores() and its sub-components for correctness, reproducibility,
strategy profiles, confidence, gates, percentiles, and signal shape handling.
"""

from __future__ import annotations

from copy import deepcopy

from src.scoring.ai_resilience_score import compute_ai_resilience_score
from src.scoring.composite_score import compute_opportunity_score
from src.scoring.confidence_score import compute_confidence
from src.scoring.engine import compute_scores
from src.scoring.local_competition_score import compute_local_competition_score
from src.scoring.monetization_score import compute_monetization_score
from src.scoring.organic_competition_score import compute_organic_competition_score
from src.scoring.strategy_profiles import resolve_strategy_weights
from tests.fixtures.m07_scoring_fixtures import metro_cohort, metro_signal


# ---------------------------------------------------------------------------
# Score presence and reproducibility
# ---------------------------------------------------------------------------


def test_all_required_scores_exist_and_are_bounded() -> None:
    cohort = metro_cohort()
    result = compute_scores(
        metro_signals=cohort[2],
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    expected = {
        "demand",
        "organic_competition",
        "local_competition",
        "monetization",
        "ai_resilience",
        "opportunity",
        "confidence",
        "resolved_weights",
    }
    assert expected.issubset(result.keys())
    for key in (
        "demand",
        "organic_competition",
        "local_competition",
        "monetization",
        "ai_resilience",
        "opportunity",
    ):
        assert 0.0 <= float(result[key]) <= 100.0
    assert 0.0 <= float(result["confidence"]["score"]) <= 100.0


def test_same_input_produces_identical_score_output() -> None:
    cohort = metro_cohort()
    metro = cohort[2]
    first = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    second = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    assert first == second


# ---------------------------------------------------------------------------
# Strategy profiles and weight constraints
# ---------------------------------------------------------------------------


def test_profile_weights_sum_to_expected_competition_budget() -> None:
    for profile in ("organic_first", "balanced", "local_dominant"):
        weights = resolve_strategy_weights(profile, metro_signal())
        assert round(weights["organic"] + weights["local"], 8) == 0.35
        assert weights["organic"] >= 0
        assert weights["local"] >= 0


def test_auto_profile_without_local_pack_is_organic_heavy() -> None:
    no_pack = metro_signal(local_pack_present=False)
    auto = resolve_strategy_weights("auto", no_pack)
    balanced = resolve_strategy_weights("balanced", no_pack)
    assert auto["organic"] > balanced["organic"]
    assert auto["local"] < balanced["local"]


def test_auto_no_pack_matches_organic_first_weights() -> None:
    no_pack = metro_signal(local_pack_present=False)
    auto = resolve_strategy_weights("auto", no_pack)
    organic_first = resolve_strategy_weights("organic_first", no_pack)
    assert auto == organic_first


def test_auto_above_fold_pack_shifts_toward_local() -> None:
    above_fold = metro_signal(local_pack_present=True, local_pack_position=2)
    w = resolve_strategy_weights("auto", above_fold)
    assert round(w["organic"] + w["local"], 8) == 0.35
    assert w["local"] > w["organic"]
    assert w["organic"] == 0.08
    assert w["local"] == 0.27


def test_auto_below_fold_pack_falls_back_to_balanced() -> None:
    below_fold = metro_signal(local_pack_present=True, local_pack_position=6)
    auto = resolve_strategy_weights("auto", below_fold)
    balanced = resolve_strategy_weights("balanced", below_fold)
    assert auto == balanced


def test_auto_missing_position_falls_back_to_balanced() -> None:
    no_position = metro_signal(local_pack_present=True)
    del no_position["local_pack_position"]
    auto = resolve_strategy_weights("auto", no_position)
    balanced = resolve_strategy_weights("balanced", no_position)
    assert auto == balanced


def test_auto_with_none_signals_falls_back_to_balanced() -> None:
    auto = resolve_strategy_weights("auto", None)
    balanced = resolve_strategy_weights("balanced", metro_signal())
    assert auto == balanced


def test_auto_weights_always_sum_to_competition_budget() -> None:
    for signals in [
        metro_signal(local_pack_present=False),
        metro_signal(local_pack_present=True, local_pack_position=1),
        metro_signal(local_pack_present=True, local_pack_position=5),
        None,
    ]:
        w = resolve_strategy_weights("auto", signals)
        assert round(w["organic"] + w["local"], 8) == 0.35


# ---------------------------------------------------------------------------
# Profile-dependent composite behavior
# ---------------------------------------------------------------------------


def test_profile_switch_changes_resolved_weights() -> None:
    cohort = metro_cohort()
    metro = cohort[2]
    organic_first = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="organic_first",
    )
    local_dominant = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="local_dominant",
    )
    assert organic_first["resolved_weights"] != local_dominant["resolved_weights"]


def test_profile_switch_can_change_opportunity() -> None:
    cohort = metro_cohort()
    metro = cohort[2]
    a = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="organic_first",
    )
    b = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="local_dominant",
    )
    assert a["opportunity"] != b["opportunity"]


def test_auto_above_fold_diverges_from_balanced_end_to_end() -> None:
    above_fold = metro_signal(local_pack_present=True, local_pack_position=1)
    cohort = [above_fold]
    auto_result = compute_scores(
        metro_signals=above_fold,
        all_metro_signals=cohort,
        strategy_profile="auto",
    )
    balanced_result = compute_scores(
        metro_signals=above_fold,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    assert auto_result["resolved_weights"] != balanced_result["resolved_weights"]


# ---------------------------------------------------------------------------
# Confidence penalties and flags
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Threshold gates and local-pack defaults
# ---------------------------------------------------------------------------


_BALANCED_WEIGHTS = {
    "demand": 0.25,
    "organic_competition": 0.15,
    "local_competition": 0.20,
    "monetization": 0.20,
    "ai_resilience": 0.15,
}


def test_no_local_pack_returns_default_score() -> None:
    score = compute_local_competition_score(metro_signal(local_pack_present=False))
    assert score == 75.0


def test_threshold_gate_caps_composite_when_component_below_5() -> None:
    score = compute_opportunity_score(
        component_scores={
            "demand": 4.0,
            "organic_competition": 80.0,
            "local_competition": 80.0,
            "monetization": 80.0,
            "ai_resilience": 80.0,
        },
        weights=_BALANCED_WEIGHTS,
    )
    assert score <= 20.0


def test_ai_floor_caps_composite_when_ai_resilience_is_low() -> None:
    score = compute_opportunity_score(
        component_scores={
            "demand": 90.0,
            "organic_competition": 90.0,
            "local_competition": 90.0,
            "monetization": 90.0,
            "ai_resilience": 10.0,
        },
        weights=_BALANCED_WEIGHTS,
    )
    assert score <= 50.0


# ---------------------------------------------------------------------------
# Competition inversion
# ---------------------------------------------------------------------------


def test_lower_da_competitor_gets_higher_organic_competition_score() -> None:
    weak_competitors = metro_signal(avg_top5_da=18.0, aggregator_count=0.0)
    strong_competitors = metro_signal(avg_top5_da=55.0, aggregator_count=3.0)
    weak_score = compute_organic_competition_score(weak_competitors)
    strong_score = compute_organic_competition_score(strong_competitors)
    assert weak_score > strong_score


def test_higher_competition_does_not_inflate_opportunity() -> None:
    weights = resolve_strategy_weights("balanced", metro_signal())
    composite_weights = {
        "demand": 0.25,
        "organic_competition": weights["organic"],
        "local_competition": weights["local"],
        "monetization": 0.20,
        "ai_resilience": 0.15,
    }
    easier = compute_opportunity_score(
        component_scores={
            "demand": 70.0,
            "organic_competition": 75.0,
            "local_competition": 72.0,
            "monetization": 65.0,
            "ai_resilience": 70.0,
        },
        weights=composite_weights,
    )
    harder = compute_opportunity_score(
        component_scores={
            "demand": 70.0,
            "organic_competition": 30.0,
            "local_competition": 25.0,
            "monetization": 65.0,
            "ai_resilience": 70.0,
        },
        weights=composite_weights,
    )
    assert easier > harder


# ---------------------------------------------------------------------------
# Cohort percentile behavior
# ---------------------------------------------------------------------------


def test_changing_cohort_changes_percentile_dependent_demand() -> None:
    metro = metro_signal(effective_search_volume=1000.0)
    low_cohort = [
        metro_signal(effective_search_volume=100.0),
        metro_signal(effective_search_volume=200.0),
        metro_signal(effective_search_volume=300.0),
    ]
    high_cohort = [
        metro_signal(effective_search_volume=1500.0),
        metro_signal(effective_search_volume=2000.0),
        metro_signal(effective_search_volume=2500.0),
    ]
    low_result = compute_scores(
        metro_signals=metro,
        all_metro_signals=low_cohort + [metro],
        strategy_profile="balanced",
    )
    high_result = compute_scores(
        metro_signals=metro,
        all_metro_signals=high_cohort + [metro],
        strategy_profile="balanced",
    )
    assert low_result["demand"] != high_result["demand"]


def test_non_percentile_component_stays_stable_when_only_cohort_changes() -> None:
    cohort = metro_cohort()
    metro = metro_signal(avg_top5_da=30.0, effective_search_volume=900.0)
    first = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    second = compute_scores(
        metro_signals=metro,
        all_metro_signals=[
            metro_signal(effective_search_volume=20.0),
            metro_signal(effective_search_volume=50.0),
            metro,
        ],
        strategy_profile="balanced",
    )
    assert first["organic_competition"] == second["organic_competition"]


# ---------------------------------------------------------------------------
# Monetization — ads key regression
# ---------------------------------------------------------------------------


def test_ads_top_present_contributes_to_monetization_score() -> None:
    with_ads = metro_signal(ads_top_present=True, ads_present=False, lsa_present=False)
    without_ads = metro_signal(ads_top_present=False, ads_present=False, lsa_present=False)
    assert compute_monetization_score(with_ads) > compute_monetization_score(without_ads)


def test_legacy_ads_present_still_contributes() -> None:
    with_legacy = metro_signal(ads_top_present=False, ads_present=True, lsa_present=False)
    without = metro_signal(ads_top_present=False, ads_present=False, lsa_present=False)
    assert compute_monetization_score(with_legacy) > compute_monetization_score(without)


def test_ads_top_present_and_ads_present_produce_equivalent_scores() -> None:
    base = metro_signal(lsa_present=False, ads_top_present=False, ads_present=False)
    via_canonical = dict(base, ads_top_present=True, ads_present=False)
    via_legacy = dict(base, ads_top_present=False, ads_present=True)
    assert compute_monetization_score(via_canonical) == compute_monetization_score(via_legacy)


# ---------------------------------------------------------------------------
# AI resilience — niche-type split
# ---------------------------------------------------------------------------


def test_local_service_niche_scores_higher_than_informational_with_same_exposure() -> None:
    shared = {
        "aio_trigger_rate": 0.18,
        "transactional_keyword_ratio": 0.50,
        "local_fulfillment_required": 1.0,
        "paa_density": 2.0,
    }
    local_service = compute_ai_resilience_score(
        metro_signal(niche_type="local_service", **shared)
    )
    informational = compute_ai_resilience_score(
        metro_signal(niche_type="informational", **shared)
    )
    assert local_service > informational


def test_high_aio_in_informational_niche_stays_low() -> None:
    score = compute_ai_resilience_score(
        metro_signal(
            niche_type="informational",
            aio_trigger_rate=0.45,
            transactional_keyword_ratio=0.10,
            paa_density=6.0,
            local_fulfillment_required=0.0,
        )
    )
    assert score < 40.0


# ---------------------------------------------------------------------------
# Nested M6 signal shape regression
# ---------------------------------------------------------------------------


def test_nested_m6_shape_scores_match_flat_shape() -> None:
    flat = {
        "effective_search_volume": 6498.35,
        "avg_cpc": 16.2,
        "volume_breadth": 1.0,
        "transactional_ratio": 0.8,
        "avg_top5_da": 50.0,
        "local_biz_count": 2.0,
        "avg_lighthouse_performance": 55.0,
        "schema_adoption_rate": 0.5,
        "title_keyword_match_rate": 1.0,
        "aggregator_count": 1.0,
        "local_pack_present": True,
        "local_pack_review_count_avg": 50.0,
        "review_velocity_avg": 1.7557,
        "gbp_completeness_avg": 0.8572,
        "gbp_photo_count_avg": 17.5,
        "gbp_posting_activity": 0.5,
        "business_density": 3.0,
        "lsa_present": True,
        "ads_present": True,
        "aggregator_presence": 1.0,
        "aio_trigger_rate": 0.5,
        "transactional_keyword_ratio": 0.6667,
        "paa_density": 2.5,
        "local_fulfillment_required": 1.0,
    }
    nested = {
        "demand": {
            "effective_search_volume": flat["effective_search_volume"],
            "avg_cpc": flat["avg_cpc"],
            "volume_breadth": flat["volume_breadth"],
            "transactional_ratio": flat["transactional_ratio"],
        },
        "organic_competition": {
            "avg_top5_da": flat["avg_top5_da"],
            "local_biz_count": flat["local_biz_count"],
            "avg_lighthouse_performance": flat["avg_lighthouse_performance"],
            "schema_adoption_rate": flat["schema_adoption_rate"],
            "title_keyword_match_rate": flat["title_keyword_match_rate"],
            "aggregator_count": flat["aggregator_count"],
        },
        "local_competition": {
            "local_pack_present": flat["local_pack_present"],
            "local_pack_review_count_avg": flat["local_pack_review_count_avg"],
            "review_velocity_avg": flat["review_velocity_avg"],
            "gbp_completeness_avg": flat["gbp_completeness_avg"],
            "gbp_photo_count_avg": flat["gbp_photo_count_avg"],
            "gbp_posting_activity": flat["gbp_posting_activity"],
        },
        "monetization": {
            "avg_cpc": flat["avg_cpc"],
            "business_density": flat["business_density"],
            "gbp_completeness_avg": flat["gbp_completeness_avg"],
            "lsa_present": flat["lsa_present"],
            "ads_present": flat["ads_present"],
            "aggregator_presence": flat["aggregator_presence"],
        },
        "ai_resilience": {
            "aio_trigger_rate": flat["aio_trigger_rate"],
            "transactional_keyword_ratio": flat["transactional_keyword_ratio"],
            "paa_density": flat["paa_density"],
            "local_fulfillment_required": flat["local_fulfillment_required"],
        },
    }

    flat_scores = compute_scores(
        metro_signals=flat,
        all_metro_signals=[flat],
        strategy_profile="balanced",
    )
    nested_scores = compute_scores(
        metro_signals=nested,
        all_metro_signals=[nested],
        strategy_profile="balanced",
    )

    assert nested_scores["demand"] == flat_scores["demand"]
    assert nested_scores["monetization"] == flat_scores["monetization"]
    assert nested_scores["opportunity"] == flat_scores["opportunity"]
