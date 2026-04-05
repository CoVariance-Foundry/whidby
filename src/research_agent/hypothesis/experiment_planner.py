"""Convert hypotheses into controlled experiments tied to algo spec proxies.

Each experiment defines:
  - target proxy and signals to measure
  - parameter modifications to test
  - expected uplift direction and minimum detectable change
  - rollback condition
  - data collection requirements
"""

from __future__ import annotations

import uuid
from typing import Any

from src.research_agent.hypothesis.generator import PROXY_METRICS


def plan_experiment(
    hypothesis: dict[str, Any],
    baseline_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a structured experiment plan from a hypothesis.

    Args:
        hypothesis: A hypothesis dict from the generator.
        baseline_params: Current scoring parameters to use as control.
            If None, uses defaults from the algo spec.

    Returns:
        An experiment plan dict with all fields needed for execution.
    """
    proxy = hypothesis.get("target_proxy", "composite")
    approach = hypothesis.get("approach", "generic")
    proxy_spec = PROXY_METRICS.get(proxy, {})

    modifications = _derive_modifications(approach, baseline_params or {})

    return {
        "experiment_id": str(uuid.uuid4())[:8],
        "hypothesis_id": hypothesis.get("id", ""),
        "hypothesis_title": hypothesis.get("title", ""),
        "target_proxy": proxy,
        "target_signals": hypothesis.get("target_signals", []),
        "spec_section": proxy_spec.get("spec_section", hypothesis.get("spec_section", "")),
        "baseline_params": baseline_params or {},
        "modifications": modifications,
        "expected_direction": hypothesis.get("expected_direction", "increase"),
        "minimum_detectable_change": _min_detectable_change(proxy),
        "rollback_condition": _rollback_condition(proxy),
        "sample_requirements": _sample_requirements(proxy),
        "status": "planned",
    }


def plan_batch(
    hypotheses: list[dict[str, Any]],
    baseline_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Plan experiments for a batch of hypotheses."""
    return [plan_experiment(h, baseline_params) for h in hypotheses]


def _derive_modifications(
    approach: str, baseline: dict[str, Any]
) -> list[dict[str, Any]]:
    """Generate parameter modifications based on approach type."""
    mod_templates: dict[str, list[dict[str, Any]]] = {
        "keyword_expansion_tuning": [
            {"param": "kd_filter_max", "current": 40, "candidate": 50, "description": "Raise KD ceiling from 40 to 50 to capture more keywords"},
            {"param": "volume_floor", "current": 200, "candidate": 100, "description": "Lower volume floor to include long-tail terms"},
        ],
        "volume_threshold_recalibration": [
            {"param": "volume_normalization_ceiling", "current": None, "candidate": "p90", "description": "Use 90th percentile instead of max for volume normalization"},
        ],
        "da_ceiling_adjustment": [
            {"param": "da_inverse_scale_ceiling", "current": 60, "candidate": 50, "description": "Lower DA ceiling to be more sensitive to mid-authority domains"},
        ],
        "aggregator_penalty_tuning": [
            {"param": "aggregator_penalty_per_count", "current": 8, "candidate": 5, "description": "Reduce aggregator penalty from 8 to 5 per occurrence"},
        ],
        "review_barrier_recalibration": [
            {"param": "review_count_ceiling", "current": 200, "candidate": 150, "description": "Lower review barrier ceiling to penalize review-heavy markets more"},
        ],
        "velocity_weight_tuning": [
            {"param": "velocity_weight", "current": 0.25, "candidate": 0.35, "description": "Increase review velocity weight from 0.25 to 0.35"},
        ],
        "cpc_floor_adjustment": [
            {"param": "median_local_service_cpc", "current": 5.0, "candidate": 4.0, "description": "Adjust median CPC baseline from $5 to $4"},
        ],
        "density_signal_enhancement": [
            {"param": "density_ceiling", "current": 100, "candidate": 75, "description": "Lower density ceiling to amplify sparse-market signal"},
        ],
        "aio_rate_threshold_tuning": [
            {"param": "aio_ceiling", "current": 0.50, "candidate": 0.30, "description": "Lower AIO rate ceiling from 50% to 30%"},
        ],
        "intent_safety_weight_tuning": [
            {"param": "intent_safety_weight", "current": 0.25, "candidate": 0.35, "description": "Increase transactional intent safety weight"},
        ],
    }

    return mod_templates.get(
        approach,
        [{"param": "generic", "current": None, "candidate": None, "description": "Manual parameter exploration"}],
    )


def _min_detectable_change(proxy: str) -> float:
    """Minimum score delta to consider the experiment meaningful."""
    defaults = {
        "demand": 2.0,
        "organic_competition": 3.0,
        "local_competition": 3.0,
        "monetization": 2.5,
        "ai_resilience": 2.0,
        "composite": 1.5,
    }
    return defaults.get(proxy, 2.0)


def _rollback_condition(proxy: str) -> str:
    """Describe when to roll back the modification."""
    return (
        f"Roll back if {proxy} score decreases by more than "
        f"{_min_detectable_change(proxy)} points on average across metros, "
        f"OR if composite opportunity score drops on more than 30% of metros."
    )


def _sample_requirements(proxy: str) -> dict[str, Any]:
    """Minimum data requirements for a valid experiment."""
    return {
        "min_metros": 5,
        "min_keywords_per_metro": 3,
        "require_baseline_snapshot": True,
        "require_candidate_snapshot": True,
    }
