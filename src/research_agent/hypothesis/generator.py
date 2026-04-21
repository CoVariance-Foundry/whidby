"""Hypothesis generation from weak-score patterns and confidence flags.

Analyzes scoring outputs to identify improvement opportunities and
generates structured hypotheses for the research loop.
"""

from __future__ import annotations

import uuid
from typing import Any

from src.research_agent.memory.graph_store import ResearchGraphStore

# Proxy metric definitions from Algo Spec V1.1
PROXY_METRICS = {
    "demand": {
        "signals": ["effective_search_volume", "volume_breadth", "transactional_ratio"],
        "weight": 0.25,
        "spec_section": "§7.1",
    },
    "organic_competition": {
        "signals": ["avg_top5_da", "local_biz_count", "avg_lighthouse_performance"],
        "weight": 0.20,
        "spec_section": "§7.2",
    },
    "local_competition": {
        "signals": [
            "local_pack_review_count_avg",
            "review_velocity_avg",
            "gbp_completeness_avg",
        ],
        "weight": 0.15,
        "spec_section": "§7.3",
    },
    "monetization": {
        "signals": ["avg_cpc", "business_density", "lsa_present"],
        "weight": 0.20,
        "spec_section": "§7.4",
    },
    "ai_resilience": {
        "signals": ["aio_trigger_rate", "transactional_keyword_ratio", "paa_density"],
        "weight": 0.15,
        "spec_section": "§7.5",
    },
}


def generate_hypotheses(
    scoring_results: dict[str, Any],
    graph: ResearchGraphStore | None = None,
    max_hypotheses: int = 5,
) -> list[dict[str, Any]]:
    """Generate hypotheses from scoring outputs by identifying weak proxies.

    Args:
        scoring_results: Dict with per-metro scoring data. Expected shape::

            {
                "metros": [
                    {"cbsa_code": "...", "scores": {"demand": 72, ...}, "signals": {...}},
                    ...
                ]
            }

        graph: Optional graph store to check for previously invalidated hypotheses.
        max_hypotheses: Maximum number of hypotheses to generate.

    Returns:
        List of hypothesis dicts ready for the backlog.
    """
    hypotheses: list[dict[str, Any]] = []
    invalidated_titles: set[str] = set()
    if graph:
        for node in graph.invalidated_hypotheses():
            invalidated_titles.add(node.title)

    metros = scoring_results.get("metros", [])
    if not metros:
        return hypotheses

    weakness_patterns = _identify_weakness_patterns(metros)

    for pattern in weakness_patterns:
        title = f"Improve {pattern['proxy']} via {pattern['approach']}"
        if title in invalidated_titles:
            continue

        hypothesis = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "description": pattern["description"],
            "target_proxy": pattern["proxy"],
            "target_signals": pattern["signals"],
            "expected_direction": "increase",
            "priority": pattern["priority"],
            "status": "pending",
            "spec_section": PROXY_METRICS.get(pattern["proxy"], {}).get(
                "spec_section", ""
            ),
            "approach": pattern["approach"],
        }
        hypotheses.append(hypothesis)

        if len(hypotheses) >= max_hypotheses:
            break

    return hypotheses


def generate_novel_hypothesis(
    context: str,
    graph: ResearchGraphStore | None = None,
) -> dict[str, Any]:
    """Generate a single novel hypothesis from free-form reasoning context.

    Used when the agent wants to propose something outside the standard
    weakness-pattern detection.

    Args:
        context: Free-form description of the observation or idea.
        graph: Optional graph store for dedup.

    Returns:
        A hypothesis dict.
    """
    return {
        "id": str(uuid.uuid4())[:8],
        "title": f"Novel hypothesis: {context[:60]}",
        "description": context,
        "target_proxy": "composite",
        "target_signals": [],
        "expected_direction": "increase",
        "priority": 3,
        "status": "pending",
        "spec_section": "",
        "approach": "novel_exploration",
    }


def _identify_weakness_patterns(
    metros: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Identify scoring weaknesses across metros and propose approaches."""
    patterns: list[dict[str, Any]] = []

    score_averages: dict[str, float] = {}
    for proxy in PROXY_METRICS:
        values = [
            m["scores"].get(proxy, 50)
            for m in metros
            if "scores" in m
        ]
        if values:
            score_averages[proxy] = sum(values) / len(values)

    sorted_proxies = sorted(score_averages.items(), key=lambda x: x[1])

    approach_map = {
        "demand": [
            ("keyword_expansion_tuning", "Adjust keyword expansion filters to capture more transactional volume"),
            ("volume_threshold_recalibration", "Recalibrate volume floor thresholds based on niche density"),
        ],
        "organic_competition": [
            ("da_ceiling_adjustment", "Test raising/lowering DA ceiling in inverse_scale"),
            ("aggregator_penalty_tuning", "Experiment with aggregator count penalty multiplier"),
        ],
        "local_competition": [
            ("review_barrier_recalibration", "Adjust review count barrier breakpoints"),
            ("velocity_weight_tuning", "Test different review velocity weights"),
        ],
        "monetization": [
            ("cpc_floor_adjustment", "Recalibrate CPC floor from market median data"),
            ("density_signal_enhancement", "Add new business density signals"),
        ],
        "ai_resilience": [
            ("aio_rate_threshold_tuning", "Adjust AIO trigger rate scoring breakpoints"),
            ("intent_safety_weight_tuning", "Experiment with transactional intent safety weights"),
        ],
    }

    priority = len(sorted_proxies)
    for proxy, avg_score in sorted_proxies:
        approaches = approach_map.get(proxy, [("generic_tuning", "Generic parameter tuning")])
        for approach_name, description in approaches:
            patterns.append(
                {
                    "proxy": proxy,
                    "approach": approach_name,
                    "description": description,
                    "signals": PROXY_METRICS[proxy]["signals"],
                    "avg_score": avg_score,
                    "priority": priority,
                }
            )
        priority -= 1

    return patterns
