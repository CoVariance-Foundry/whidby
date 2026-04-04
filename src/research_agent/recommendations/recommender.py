"""Recommendation synthesis from validated experiment outcomes.

Produces prioritized improvement proposals that map directly to
algo spec sections, scoring formulas, and implementation points.
"""

from __future__ import annotations

import uuid
from typing import Any

from src.research_agent.evaluation.evaluator import compute_uplift_confidence
from src.research_agent.memory.graph_store import ResearchGraphStore
from src.research_agent.memory.models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeStatus,
    NodeType,
)


def synthesize_recommendations(
    iteration_results: list[dict[str, Any]],
    graph: ResearchGraphStore | None = None,
) -> list[dict[str, Any]]:
    """Generate prioritized recommendations from experiment results.

    Args:
        iteration_results: List of IterationResult.to_dict() outputs.
        graph: Optional graph store for evidence aggregation.

    Returns:
        List of recommendation dicts sorted by impact * confidence.
    """
    validated = [r for r in iteration_results if r.get("validated")]
    if not validated:
        return []

    recommendations: list[dict[str, Any]] = []

    for result in validated:
        delta = result.get("delta", 0.0)
        cost = result.get("cost_usd", 0.0)

        rec = {
            "id": str(uuid.uuid4())[:8],
            "hypothesis_id": result.get("hypothesis_id", ""),
            "title": f"Apply changes from experiment {result.get('experiment_id', '')}",
            "description": result.get("learning", ""),
            "impact_score": abs(delta),
            "confidence": _confidence_label(delta),
            "cost_usd": cost,
            "priority_score": abs(delta) * _confidence_multiplier(delta),
            "status": "proposed",
            "evidence": {
                "baseline_score": result.get("baseline_score", 0),
                "candidate_score": result.get("candidate_score", 0),
                "delta": delta,
                "experiment_id": result.get("experiment_id", ""),
            },
        }
        recommendations.append(rec)

    recommendations.sort(key=lambda r: r["priority_score"], reverse=True)

    if graph:
        _promote_recommendations_to_graph(recommendations, graph)

    return recommendations


def generate_improvement_report(
    recommendations: list[dict[str, Any]],
    iteration_results: list[dict[str, Any]],
) -> str:
    """Generate a human-readable improvement report.

    Args:
        recommendations: Output from synthesize_recommendations.
        iteration_results: All iteration results for context.

    Returns:
        Formatted markdown report string.
    """
    total_experiments = len(iteration_results)
    validated_count = sum(1 for r in iteration_results if r.get("validated"))
    total_cost = sum(r.get("cost_usd", 0) for r in iteration_results)

    lines = [
        "# Research Agent Improvement Report",
        "",
        "## Summary",
        f"- Total experiments run: {total_experiments}",
        f"- Validated improvements: {validated_count}",
        f"- Total API cost: ${total_cost:.2f}",
        f"- Recommendations generated: {len(recommendations)}",
        "",
        "## Recommendations (by priority)",
        "",
    ]

    for i, rec in enumerate(recommendations, 1):
        evidence = rec.get("evidence", {})
        lines.extend([
            f"### {i}. {rec['title']}",
            "",
            f"**Impact:** {rec['impact_score']:.3f} | "
            f"**Confidence:** {rec['confidence']} | "
            f"**Priority:** {rec['priority_score']:.3f}",
            "",
            f"**Evidence:**",
            f"- Baseline: {evidence.get('baseline_score', 0):.2f}",
            f"- Candidate: {evidence.get('candidate_score', 0):.2f}",
            f"- Delta: {evidence.get('delta', 0):+.3f}",
            f"- Experiment cost: ${rec.get('cost_usd', 0):.2f}",
            "",
            f"**Learning:** {rec.get('description', 'N/A')}",
            "",
            "---",
            "",
        ])

    if not recommendations:
        lines.append("No validated improvements found in this run.")

    return "\n".join(lines)


def _confidence_label(delta: float) -> str:
    abs_delta = abs(delta)
    if abs_delta > 5.0:
        return "high"
    if abs_delta > 2.0:
        return "medium"
    return "low"


def _confidence_multiplier(delta: float) -> float:
    label = _confidence_label(delta)
    return {"high": 1.0, "medium": 0.7, "low": 0.4}.get(label, 0.5)


def _promote_recommendations_to_graph(
    recommendations: list[dict[str, Any]],
    graph: ResearchGraphStore,
) -> None:
    """Promote high-confidence recommendations to the knowledge graph."""
    for rec in recommendations:
        if rec["confidence"] in ("high", "medium"):
            node = GraphNode(
                id=rec["id"],
                node_type=NodeType.RECOMMENDATION,
                title=rec["title"],
                description=rec["description"],
                status=NodeStatus.ACTIVE,
                confidence=rec["impact_score"],
                provenance_artifact=rec.get("evidence", {}).get("experiment_id"),
                metadata={
                    "priority_score": rec["priority_score"],
                    "evidence": rec["evidence"],
                },
            )
            graph.add_node(node)

            hypothesis_id = rec.get("hypothesis_id")
            if hypothesis_id and graph.get_node(hypothesis_id):
                graph.add_edge(
                    GraphEdge(
                        source_id=node.id,
                        target_id=hypothesis_id,
                        edge_type=EdgeType.DERIVED_FROM,
                        weight=rec["impact_score"],
                    )
                )
