"""Unit tests for recommendation synthesis and reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Any


from src.research_agent.evaluation.evaluator import (
    compute_uplift_confidence,
    evaluate_experiment,
)
from src.research_agent.memory.graph_store import ResearchGraphStore
from src.research_agent.recommendations.recommender import (
    generate_improvement_report,
    synthesize_recommendations,
)


def _baseline_snapshot() -> dict[str, Any]:
    return {
        "metros": [
            {"scores": {"demand": 70, "organic_competition": 40, "local_competition": 50,
                         "monetization": 75, "ai_resilience": 88, "opportunity": 65}},
            {"scores": {"demand": 80, "organic_competition": 35, "local_competition": 45,
                         "monetization": 80, "ai_resilience": 90, "opportunity": 68}},
        ]
    }


def _improved_result() -> dict[str, Any]:
    return {
        "candidate_scores": {
            "metros": [
                {"scores": {"demand": 74, "organic_competition": 44, "local_competition": 54,
                             "monetization": 78, "ai_resilience": 89, "opportunity": 70}},
                {"scores": {"demand": 83, "organic_competition": 38, "local_competition": 48,
                             "monetization": 82, "ai_resilience": 91, "opportunity": 72}},
            ]
        }
    }


def _make_iteration_results(validated: bool = True) -> list[dict[str, Any]]:
    return [
        {
            "iteration": 1,
            "hypothesis_id": "h1",
            "experiment_id": "e1",
            "baseline_score": 66.5,
            "candidate_score": 71.0 if validated else 62.0,
            "delta": 4.5 if validated else -4.5,
            "validated": validated,
            "cost_usd": 0.05,
            "learning": "Test learning",
        }
    ]


class TestEvaluateExperiment:
    def test_computes_baseline_and_candidate(self):
        baseline_score, candidate_score, learning = evaluate_experiment(
            _baseline_snapshot(), _improved_result()
        )
        assert candidate_score > baseline_score
        assert "improved" in learning.lower()

    def test_handles_empty_snapshots(self):
        b, c, learning = evaluate_experiment({}, {})
        assert b == 0.0
        assert c == 0.0

    def test_per_proxy_breakdown_in_learning(self):
        _, _, learning = evaluate_experiment(
            _baseline_snapshot(), _improved_result()
        )
        assert "demand" in learning
        assert "monetization" in learning


class TestComputeUpliftConfidence:
    def test_high_confidence(self):
        baseline = [60, 65, 70, 68, 72]
        candidate = [70, 75, 80, 78, 82]
        result = compute_uplift_confidence(baseline, candidate)
        assert result["confidence"] == "high"
        assert result["mean_delta"] == 10.0

    def test_low_confidence(self):
        baseline = [60, 65, 70, 68, 72]
        candidate = [61, 64, 71, 67, 73]
        result = compute_uplift_confidence(baseline, candidate)
        assert result["confidence"] in ("low", "medium")

    def test_empty_input(self):
        result = compute_uplift_confidence([], [])
        assert result["confidence"] == "insufficient_data"

    def test_counts_improved_degraded(self):
        baseline = [60, 65, 70]
        candidate = [70, 60, 75]
        result = compute_uplift_confidence(baseline, candidate)
        assert result["improved_count"] == 2
        assert result["degraded_count"] == 1


class TestSynthesizeRecommendations:
    def test_produces_recommendations_from_validated(self):
        recs = synthesize_recommendations(_make_iteration_results(validated=True))
        assert len(recs) == 1
        assert recs[0]["status"] == "proposed"
        assert recs[0]["impact_score"] > 0

    def test_no_recommendations_for_invalidated(self):
        recs = synthesize_recommendations(_make_iteration_results(validated=False))
        assert len(recs) == 0

    def test_sorted_by_priority(self):
        results = _make_iteration_results(True)
        results.append({
            "iteration": 2,
            "hypothesis_id": "h2",
            "experiment_id": "e2",
            "baseline_score": 66.5,
            "candidate_score": 80.0,
            "delta": 13.5,
            "validated": True,
            "cost_usd": 0.10,
            "learning": "Big improvement",
        })
        recs = synthesize_recommendations(results)
        assert len(recs) == 2
        assert recs[0]["priority_score"] >= recs[1]["priority_score"]

    def test_promotes_to_graph(self, tmp_path: Path):
        graph = ResearchGraphStore(persist_path=str(tmp_path / "g.json"))
        results = _make_iteration_results(validated=True)
        synthesize_recommendations(results, graph=graph)
        summary = graph.export_summary()
        assert summary["total_nodes"] >= 1


class TestGenerateImprovementReport:
    def test_report_contains_summary(self):
        recs = synthesize_recommendations(_make_iteration_results(True))
        report = generate_improvement_report(recs, _make_iteration_results(True))
        assert "# Research Agent Improvement Report" in report
        assert "Total experiments run: 1" in report
        assert "Validated improvements: 1" in report

    def test_report_empty_recs(self):
        report = generate_improvement_report([], [])
        assert "No validated improvements" in report
