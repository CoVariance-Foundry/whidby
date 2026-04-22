"""Regression tests for nested M6 signal shapes passed into M7."""

from __future__ import annotations

from src.scoring.engine import compute_scores


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
