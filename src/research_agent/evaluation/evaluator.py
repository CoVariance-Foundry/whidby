"""Baseline vs candidate scoring evaluator.

Compares scoring snapshots to measure the impact of parameter
modifications proposed by hypotheses.
"""

from __future__ import annotations

import statistics
from typing import Any


def evaluate_experiment(
    baseline_snapshot: dict[str, Any],
    experiment_result: dict[str, Any],
) -> tuple[float, float, str]:
    """Compare baseline and candidate scoring outcomes.

    Args:
        baseline_snapshot: Baseline scoring data with per-metro scores.
        experiment_result: Experiment result with candidate scores.

    Returns:
        Tuple of (baseline_composite, candidate_composite, learning_text).
    """
    baseline_scores = _extract_composites(baseline_snapshot)
    candidate_scores = _extract_composites(experiment_result)

    baseline_avg = statistics.mean(baseline_scores) if baseline_scores else 0.0
    candidate_avg = statistics.mean(candidate_scores) if candidate_scores else 0.0

    delta = candidate_avg - baseline_avg
    direction = "improved" if delta > 0 else "degraded" if delta < 0 else "unchanged"

    per_proxy = _per_proxy_comparison(baseline_snapshot, experiment_result)

    learning = _format_learning(
        baseline_avg=baseline_avg,
        candidate_avg=candidate_avg,
        delta=delta,
        direction=direction,
        per_proxy=per_proxy,
        n_metros=len(baseline_scores),
    )

    return baseline_avg, candidate_avg, learning


def compute_uplift_confidence(
    baseline_scores: list[float],
    candidate_scores: list[float],
) -> dict[str, Any]:
    """Compute statistical confidence metrics for an uplift.

    Returns mean delta, standard deviation, and a simple
    confidence band (not a full t-test; good enough for directional signal).
    """
    if not baseline_scores or not candidate_scores:
        return {"mean_delta": 0.0, "std_delta": 0.0, "confidence": "insufficient_data"}

    min_len = min(len(baseline_scores), len(candidate_scores))
    deltas = [
        candidate_scores[i] - baseline_scores[i] for i in range(min_len)
    ]

    mean_delta = statistics.mean(deltas)
    std_delta = statistics.stdev(deltas) if len(deltas) > 1 else 0.0

    if std_delta == 0:
        confidence = "high" if mean_delta != 0 else "no_change"
    elif abs(mean_delta) > 2 * std_delta:
        confidence = "high"
    elif abs(mean_delta) > std_delta:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "mean_delta": round(mean_delta, 4),
        "std_delta": round(std_delta, 4),
        "confidence": confidence,
        "n_metros": min_len,
        "improved_count": sum(1 for d in deltas if d > 0),
        "degraded_count": sum(1 for d in deltas if d < 0),
        "unchanged_count": sum(1 for d in deltas if d == 0),
    }


def _extract_composites(snapshot: dict[str, Any]) -> list[float]:
    """Extract composite opportunity scores from a snapshot."""
    metros = snapshot.get("metros", snapshot.get("candidate_scores", {}).get("metros", []))
    if isinstance(metros, list):
        return [
            m.get("scores", {}).get("opportunity", m.get("composite_score", 0))
            for m in metros
            if isinstance(m, dict)
        ]
    return []


def _per_proxy_comparison(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, dict[str, float]]:
    """Compare each proxy dimension between baseline and candidate."""
    proxies = ["demand", "organic_competition", "local_competition", "monetization", "ai_resilience"]
    result: dict[str, dict[str, float]] = {}

    baseline_metros = baseline.get("metros", [])
    candidate_metros = candidate.get("candidate_scores", {}).get("metros", candidate.get("metros", []))

    for proxy in proxies:
        b_vals = [
            m.get("scores", {}).get(proxy, 0)
            for m in baseline_metros
            if isinstance(m, dict)
        ]
        c_vals = [
            m.get("scores", {}).get(proxy, 0)
            for m in candidate_metros
            if isinstance(m, dict)
        ]
        b_avg = statistics.mean(b_vals) if b_vals else 0.0
        c_avg = statistics.mean(c_vals) if c_vals else 0.0
        result[proxy] = {
            "baseline_avg": round(b_avg, 2),
            "candidate_avg": round(c_avg, 2),
            "delta": round(c_avg - b_avg, 2),
        }

    return result


def _format_learning(
    baseline_avg: float,
    candidate_avg: float,
    delta: float,
    direction: str,
    per_proxy: dict[str, dict[str, float]],
    n_metros: int,
) -> str:
    """Format a human-readable learning summary."""
    lines = [
        f"Composite score {direction}: {baseline_avg:.2f} -> {candidate_avg:.2f} (delta: {delta:+.2f})",
        f"Evaluated across {n_metros} metros.",
        "",
        "Per-proxy breakdown:",
    ]
    for proxy, vals in per_proxy.items():
        lines.append(
            f"  {proxy}: {vals['baseline_avg']:.1f} -> {vals['candidate_avg']:.1f} ({vals['delta']:+.1f})"
        )
    return "\n".join(lines)
