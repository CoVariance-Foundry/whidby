"""Tests for the experiment runner (US1) — verifies the Claude agent path."""

from __future__ import annotations

import copy
import tempfile
from typing import Any
from unittest.mock import MagicMock, patch

from tests.fixtures.agent_fixtures import MOCK_BASELINE_SNAPSHOT, MOCK_HYPOTHESIS
from src.research_agent.memory.filesystem_store import FilesystemStore


def _mock_tool_use_response():
    """Simulate Claude requesting rescore_with_modifications."""
    msg = MagicMock()
    msg.stop_reason = "tool_use"
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = "call_001"
    tool_block.name = "rescore_with_modifications"
    tool_block.input = {
        "baseline_signals": [
            MOCK_BASELINE_SNAPSHOT["metros"][0]["signals"],
            MOCK_BASELINE_SNAPSHOT["metros"][1]["signals"],
        ],
        "modifications": [
            {"param": "avg_top5_da", "candidate": 25},
        ],
        "strategy_profile": "balanced",
    }
    msg.content = [tool_block]
    msg.usage = MagicMock()
    msg.usage.input_tokens = 100
    msg.usage.output_tokens = 50
    return msg


def _mock_end_turn_response():
    msg = MagicMock()
    msg.stop_reason = "end_turn"
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = '{"summary": "done"}'
    msg.content = [text_block]
    msg.usage = MagicMock()
    msg.usage.input_tokens = 100
    msg.usage.output_tokens = 50
    return msg


class TestExperimentRunner:
    def _make_runner_and_fs(self) -> tuple[Any, FilesystemStore]:
        from src.research_agent.agent import claude_experiment_runner

        fs = FilesystemStore(run_id="test-run", base_dir=tempfile.mkdtemp())
        fs.save_snapshot("baseline", copy.deepcopy(MOCK_BASELINE_SNAPSHOT))
        return claude_experiment_runner, fs

    @patch("src.research_agent.agent.claude_agent.anthropic.Anthropic")
    def test_runner_returns_candidate_scores(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [
            _mock_tool_use_response(),
            _mock_end_turn_response(),
        ]

        runner, fs = self._make_runner_and_fs()
        result = runner(copy.deepcopy(MOCK_HYPOTHESIS), fs)

        assert "candidate_scores" in result
        assert "metros" in result["candidate_scores"]
        assert len(result["candidate_scores"]["metros"]) > 0

    @patch("src.research_agent.agent.claude_agent.anthropic.Anthropic")
    def test_runner_returns_experiment_id(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [
            _mock_tool_use_response(),
            _mock_end_turn_response(),
        ]

        runner, fs = self._make_runner_and_fs()
        result = runner(copy.deepcopy(MOCK_HYPOTHESIS), fs)
        assert "experiment_id" in result
        assert isinstance(result["experiment_id"], str)

    @patch("src.research_agent.agent.claude_agent.anthropic.Anthropic")
    def test_runner_returns_modifications(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [
            _mock_tool_use_response(),
            _mock_end_turn_response(),
        ]

        runner, fs = self._make_runner_and_fs()
        result = runner(copy.deepcopy(MOCK_HYPOTHESIS), fs)
        assert "modifications" in result
        assert isinstance(result["modifications"], list)

    @patch("src.research_agent.agent.claude_agent.anthropic.Anthropic")
    def test_runner_returns_cost_usd(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [
            _mock_tool_use_response(),
            _mock_end_turn_response(),
        ]

        runner, fs = self._make_runner_and_fs()
        result = runner(copy.deepcopy(MOCK_HYPOTHESIS), fs)
        assert "cost_usd" in result
        assert isinstance(result["cost_usd"], (int, float))

    @patch("src.research_agent.agent.claude_agent.anthropic.Anthropic")
    def test_runner_candidate_scores_have_per_proxy_breakdown(
        self, mock_anthropic_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [
            _mock_tool_use_response(),
            _mock_end_turn_response(),
        ]

        runner, fs = self._make_runner_and_fs()
        result = runner(copy.deepcopy(MOCK_HYPOTHESIS), fs)
        metro = result["candidate_scores"]["metros"][0]
        scores = metro["scores"]
        for key in [
            "demand",
            "organic_competition",
            "local_competition",
            "monetization",
            "ai_resilience",
            "opportunity",
        ]:
            assert key in scores, f"Missing score key: {key}"
            assert 0 <= scores[key] <= 100

    @patch("src.research_agent.agent.claude_agent.anthropic.Anthropic")
    def test_runner_produces_nonzero_delta(self, mock_anthropic_cls: MagicMock) -> None:
        from src.research_agent.evaluation.evaluator import evaluate_experiment

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [
            _mock_tool_use_response(),
            _mock_end_turn_response(),
        ]

        runner, fs = self._make_runner_and_fs()
        result = runner(copy.deepcopy(MOCK_HYPOTHESIS), fs)
        baseline_avg, candidate_avg, learning = evaluate_experiment(
            MOCK_BASELINE_SNAPSHOT, result
        )
        assert candidate_avg != 0.0
        assert learning is not None

    def test_runner_matches_experiment_runner_signature(self) -> None:
        from src.research_agent.agent import claude_experiment_runner

        import inspect

        sig = inspect.signature(claude_experiment_runner)
        params = list(sig.parameters.keys())
        assert len(params) == 2

    @patch("src.research_agent.agent.claude_agent.anthropic.Anthropic")
    def test_runner_includes_tool_calls_log(self, mock_anthropic_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [
            _mock_tool_use_response(),
            _mock_end_turn_response(),
        ]

        runner, fs = self._make_runner_and_fs()
        result = runner(copy.deepcopy(MOCK_HYPOTHESIS), fs)
        assert "tool_calls" in result
        assert isinstance(result["tool_calls"], list)
        assert len(result["tool_calls"]) >= 1
        assert result["tool_calls"][0]["tool_name"] == "rescore_with_modifications"
