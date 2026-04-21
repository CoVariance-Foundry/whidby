"""Unit tests for hypothesis generation and experiment planning."""

from __future__ import annotations

from typing import Any


from src.research_agent.hypothesis.experiment_planner import (
    plan_batch,
    plan_experiment,
)
from src.research_agent.hypothesis.generator import (
    generate_hypotheses,
    generate_novel_hypothesis,
)
from src.research_agent.memory.graph_store import ResearchGraphStore
from src.research_agent.memory.models import GraphNode, NodeStatus, NodeType


def _sample_scoring_results() -> dict[str, Any]:
    return {
        "metros": [
            {
                "cbsa_code": "38060",
                "scores": {
                    "demand": 72,
                    "organic_competition": 30,
                    "local_competition": 45,
                    "monetization": 81,
                    "ai_resilience": 92,
                },
            },
            {
                "cbsa_code": "47900",
                "scores": {
                    "demand": 85,
                    "organic_competition": 25,
                    "local_competition": 35,
                    "monetization": 78,
                    "ai_resilience": 88,
                },
            },
        ]
    }


class TestGenerateHypotheses:
    def test_returns_hypotheses_for_weak_proxies(self):
        results = _sample_scoring_results()
        hypotheses = generate_hypotheses(results)
        assert len(hypotheses) > 0
        for h in hypotheses:
            assert "id" in h
            assert "title" in h
            assert "target_proxy" in h
            assert h["status"] == "pending"

    def test_respects_max_hypotheses(self):
        results = _sample_scoring_results()
        hypotheses = generate_hypotheses(results, max_hypotheses=2)
        assert len(hypotheses) <= 2

    def test_prioritizes_weakest_proxy(self):
        results = _sample_scoring_results()
        hypotheses = generate_hypotheses(results)
        first = hypotheses[0]
        assert first["target_proxy"] in (
            "organic_competition",
            "local_competition",
        )

    def test_skips_invalidated_hypotheses(self, tmp_path):
        graph = ResearchGraphStore(persist_path=str(tmp_path / "g.json"))
        results = _sample_scoring_results()
        first_run = generate_hypotheses(results, graph=graph)
        assert len(first_run) > 0

        for h in first_run:
            node = GraphNode(
                id=h["id"],
                node_type=NodeType.HYPOTHESIS,
                title=h["title"],
                status=NodeStatus.INVALIDATED,
                provenance_artifact="test",
            )
            graph.add_node(node)

        second_run = generate_hypotheses(results, graph=graph)
        first_titles = {h["title"] for h in first_run}
        second_titles = {h["title"] for h in second_run}
        assert not first_titles.intersection(second_titles)

    def test_empty_metros_returns_empty(self):
        hypotheses = generate_hypotheses({"metros": []})
        assert hypotheses == []

    def test_hypothesis_has_required_fields(self):
        results = _sample_scoring_results()
        hypotheses = generate_hypotheses(results, max_hypotheses=1)
        h = hypotheses[0]
        required = [
            "id", "title", "description", "target_proxy",
            "expected_direction", "priority", "status",
        ]
        for field in required:
            assert field in h, f"Missing field: {field}"


class TestGenerateNovelHypothesis:
    def test_creates_valid_hypothesis(self):
        h = generate_novel_hypothesis("Review velocity seems underweighted in Phoenix")
        assert h["status"] == "pending"
        assert "novel" in h["approach"]
        assert len(h["id"]) == 8


class TestPlanExperiment:
    def test_creates_valid_plan(self):
        hypothesis = {
            "id": "h1",
            "title": "Test",
            "target_proxy": "demand",
            "target_signals": ["effective_search_volume"],
            "expected_direction": "increase",
            "approach": "keyword_expansion_tuning",
        }
        plan = plan_experiment(hypothesis)
        assert "experiment_id" in plan
        assert plan["hypothesis_id"] == "h1"
        assert plan["target_proxy"] == "demand"
        assert plan["status"] == "planned"
        assert len(plan["modifications"]) > 0
        assert plan["minimum_detectable_change"] > 0
        assert "roll back" in plan["rollback_condition"].lower()

    def test_plan_batch(self):
        hypotheses = [
            {"id": f"h{i}", "title": f"H{i}", "target_proxy": "demand",
             "approach": "keyword_expansion_tuning", "expected_direction": "increase"}
            for i in range(3)
        ]
        plans = plan_batch(hypotheses)
        assert len(plans) == 3
        ids = {p["experiment_id"] for p in plans}
        assert len(ids) == 3

    def test_unknown_approach_produces_generic_mod(self):
        hypothesis = {
            "id": "h1",
            "title": "Test",
            "target_proxy": "demand",
            "approach": "unknown_approach_xyz",
            "expected_direction": "increase",
        }
        plan = plan_experiment(hypothesis)
        assert plan["modifications"][0]["param"] == "generic"
