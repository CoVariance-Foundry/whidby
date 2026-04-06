"""Shared test fixtures for the Claude-native research agent."""

from __future__ import annotations

MOCK_HYPOTHESIS = {
    "id": "test1234",
    "title": "Improve organic_competition via da_ceiling_adjustment",
    "description": "Test raising DA ceiling in inverse_scale",
    "target_proxy": "organic_competition",
    "target_signals": ["avg_top5_da", "local_biz_count", "avg_lighthouse_performance"],
    "expected_direction": "increase",
    "priority": 5,
    "status": "pending",
    "spec_section": "§7.2",
    "approach": "da_ceiling_adjustment",
}

MOCK_BASELINE_SNAPSHOT = {
    "metros": [
        {
            "cbsa_code": "38060",
            "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
            "scores": {
                "demand": 72,
                "organic_competition": 45,
                "local_competition": 58,
                "monetization": 81,
                "ai_resilience": 92,
                "opportunity": 71,
            },
            "signals": {
                "effective_search_volume": 4500,
                "avg_top5_da": 35,
                "local_biz_count": 12,
                "avg_lighthouse_performance": 0.65,
                "local_pack_review_count_avg": 42,
                "review_velocity_avg": 2.1,
                "gbp_completeness_avg": 0.7,
                "avg_cpc": 8.50,
                "business_density": 55,
                "lsa_present": False,
                "aio_trigger_rate": 0.06,
                "transactional_keyword_ratio": 0.45,
                "paa_density": 0.3,
                "volume_breadth": 15,
                "transactional_ratio": 0.42,
                "ads_top_present": True,
                "local_pack_present": True,
                "local_pack_position": 1,
            },
        },
        {
            "cbsa_code": "47900",
            "cbsa_name": "Washington-Arlington-Alexandria, DC-VA-MD-WV",
            "scores": {
                "demand": 85,
                "organic_competition": 30,
                "local_competition": 35,
                "monetization": 78,
                "ai_resilience": 88,
                "opportunity": 62,
            },
            "signals": {
                "effective_search_volume": 7200,
                "avg_top5_da": 52,
                "local_biz_count": 20,
                "avg_lighthouse_performance": 0.55,
                "local_pack_review_count_avg": 95,
                "review_velocity_avg": 3.5,
                "gbp_completeness_avg": 0.8,
                "avg_cpc": 12.00,
                "business_density": 78,
                "lsa_present": True,
                "aio_trigger_rate": 0.08,
                "transactional_keyword_ratio": 0.50,
                "paa_density": 0.4,
                "volume_breadth": 22,
                "transactional_ratio": 0.48,
                "ads_top_present": True,
                "local_pack_present": True,
                "local_pack_position": 1,
            },
        },
    ],
}

MOCK_BASELINE_SIGNALS = [
    MOCK_BASELINE_SNAPSHOT["metros"][0]["signals"],
    MOCK_BASELINE_SNAPSHOT["metros"][1]["signals"],
]

MOCK_MODIFICATIONS = [
    {
        "param": "da_inverse_scale_ceiling",
        "current": 60,
        "candidate": 50,
        "description": "Lower DA ceiling to be more sensitive to mid-authority domains",
    },
]

MOCK_TOOL_RESPONSE = {
    "data": {"status": "ok", "results": []},
    "cost_usd": 0.001,
}

MOCK_EXPERIMENT_PLAN = {
    "experiment_id": "exp12345",
    "hypothesis_id": "test1234",
    "hypothesis_title": "Improve organic_competition via da_ceiling_adjustment",
    "target_proxy": "organic_competition",
    "target_signals": ["avg_top5_da", "local_biz_count", "avg_lighthouse_performance"],
    "spec_section": "§7.2",
    "baseline_params": {},
    "modifications": MOCK_MODIFICATIONS,
    "expected_direction": "increase",
    "minimum_detectable_change": 3.0,
    "rollback_condition": (
        "Roll back if organic_competition score decreases by more than 3.0 points "
        "on average across metros, OR if composite opportunity score drops on more "
        "than 30% of metros."
    ),
    "sample_requirements": {
        "min_metros": 5,
        "min_keywords_per_metro": 3,
        "require_baseline_snapshot": True,
        "require_candidate_snapshot": True,
    },
    "status": "planned",
}
