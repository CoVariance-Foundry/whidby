"""Deterministic fixtures for M7 scoring tests."""

from __future__ import annotations

from copy import deepcopy


BASE_METRO_SIGNAL = {
    "effective_search_volume": 1200.0,
    "avg_cpc": 10.0,
    "volume_breadth": 0.80,
    "transactional_ratio": 0.70,
    "transactional_keyword_ratio": 0.70,
    "avg_top5_da": 28.0,
    "local_biz_count": 6.0,
    "avg_lighthouse_performance": 55.0,
    "schema_adoption_rate": 0.45,
    "title_keyword_match_rate": 0.60,
    "aggregator_count": 1.0,
    "local_pack_present": True,
    "local_pack_position": 2,
    "local_pack_review_count_avg": 40.0,
    "review_velocity_avg": 3.0,
    "gbp_completeness_avg": 0.55,
    "gbp_photo_count_avg": 15.0,
    "gbp_posting_activity": 0.35,
    "business_density": 40.0,
    "lsa_present": True,
    "ads_top_present": True,
    "ads_present": True,
    "aggregator_presence": 2.0,
    "aio_trigger_rate": 0.08,
    "local_fulfillment_required": 1.0,
    "paa_density": 2.0,
    "niche_type": "local_service",
    "expansion_confidence": "high",
    "lighthouse_results_count": 5,
    "backlink_results_count": 5,
    "serp_results_count": 10,
    "review_results_count": 3,
    "gbp_results_count": 4,
    "total_search_volume": 800.0,
}


def metro_signal(**overrides: object) -> dict[str, object]:
    """Return a metro signal fixture with optional overrides."""
    signal = deepcopy(BASE_METRO_SIGNAL)
    signal.update(overrides)
    return signal


def metro_cohort() -> list[dict[str, object]]:
    """Return a deterministic cohort for percentile-relative tests."""
    return [
        metro_signal(effective_search_volume=200.0, avg_cpc=2.0, local_biz_count=3.0),
        metro_signal(effective_search_volume=600.0, avg_cpc=4.0, local_biz_count=4.0),
        metro_signal(effective_search_volume=1200.0, avg_cpc=10.0, local_biz_count=6.0),
        metro_signal(effective_search_volume=2400.0, avg_cpc=20.0, local_biz_count=8.0),
    ]

