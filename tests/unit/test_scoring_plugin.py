"""Tests for the ScoringPlugin (US1)."""

from __future__ import annotations

import copy

import pytest

from tests.fixtures.agent_fixtures import MOCK_BASELINE_SIGNALS, MOCK_MODIFICATIONS


class TestScoringPlugin:
    def _make_plugin(self):
        from src.research_agent.plugins.scoring_plugin import ScoringPlugin

        return ScoringPlugin()

    def test_tool_definitions_returns_valid_schemas(self) -> None:
        plugin = self._make_plugin()
        defs = plugin.tool_definitions()
        assert len(defs) >= 1
        for d in defs:
            assert "name" in d
            assert "description" in d
            assert "input_schema" in d
            assert d["input_schema"]["type"] == "object"

    def test_rescore_produces_real_scores(self) -> None:
        plugin = self._make_plugin()
        result = plugin.execute(
            "rescore_with_modifications",
            {
                "baseline_signals": copy.deepcopy(MOCK_BASELINE_SIGNALS),
                "modifications": MOCK_MODIFICATIONS,
                "strategy_profile": "balanced",
            },
        )
        assert "candidate_scores" in result
        metros = result["candidate_scores"]["metros"]
        assert len(metros) == 2
        for metro in metros:
            scores = metro["scores"]
            assert "opportunity" in scores
            assert "demand" in scores
            assert "organic_competition" in scores
            assert "local_competition" in scores
            assert "monetization" in scores
            assert "ai_resilience" in scores
            assert 0 <= scores["opportunity"] <= 100

    def test_rescore_cost_is_zero(self) -> None:
        plugin = self._make_plugin()
        result = plugin.execute(
            "rescore_with_modifications",
            {
                "baseline_signals": copy.deepcopy(MOCK_BASELINE_SIGNALS),
                "modifications": [],
                "strategy_profile": "balanced",
            },
        )
        assert result["cost_usd"] == 0.0

    def test_rescore_with_modification_changes_scores(self) -> None:
        plugin = self._make_plugin()
        baseline_result = plugin.execute(
            "rescore_with_modifications",
            {
                "baseline_signals": copy.deepcopy(MOCK_BASELINE_SIGNALS),
                "modifications": [],
                "strategy_profile": "balanced",
            },
        )
        modified_result = plugin.execute(
            "rescore_with_modifications",
            {
                "baseline_signals": copy.deepcopy(MOCK_BASELINE_SIGNALS),
                "modifications": [
                    {
                        "param": "avg_top5_da",
                        "current": None,
                        "candidate": 10,
                        "description": "Force low DA",
                    }
                ],
                "strategy_profile": "balanced",
            },
        )
        baseline_opp = baseline_result["candidate_scores"]["metros"][0]["scores"][
            "opportunity"
        ]
        modified_opp = modified_result["candidate_scores"]["metros"][0]["scores"][
            "opportunity"
        ]
        assert baseline_opp != modified_opp

    def test_name_is_scoring(self) -> None:
        plugin = self._make_plugin()
        assert plugin.name == "scoring"

    def test_unknown_tool_raises(self) -> None:
        plugin = self._make_plugin()
        with pytest.raises(KeyError, match="nonexistent"):
            plugin.execute("nonexistent", {})
