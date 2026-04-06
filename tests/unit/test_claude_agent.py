"""Tests for ClaudeAgent tool-use loop (US3)."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

from tests.fixtures.agent_fixtures import MOCK_BASELINE_SNAPSHOT, MOCK_HYPOTHESIS
from src.research_agent.plugins.base import PluginRegistry, ToolPlugin


class _MockScoringPlugin(ToolPlugin):
    @property
    def name(self) -> str:
        return "scoring"

    def tool_definitions(self) -> list[dict]:
        return [
            {
                "name": "rescore_with_modifications",
                "description": "Re-score with modifications",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "baseline_signals": {"type": "array"},
                        "modifications": {"type": "array"},
                        "strategy_profile": {"type": "string"},
                    },
                    "required": ["baseline_signals", "modifications", "strategy_profile"],
                },
            }
        ]

    def execute(self, tool_name: str, arguments: dict) -> dict:
        return {
            "candidate_scores": {
                "metros": [
                    {"scores": {"opportunity": 75.0, "demand": 70, "organic_competition": 50,
                                "local_competition": 60, "monetization": 80, "ai_resilience": 90}},
                    {"scores": {"opportunity": 68.0, "demand": 82, "organic_competition": 35,
                                "local_competition": 40, "monetization": 75, "ai_resilience": 85}},
                ]
            },
            "cost_usd": 0.0,
        }


def _make_registry() -> PluginRegistry:
    registry = PluginRegistry()
    registry.register(_MockScoringPlugin())
    return registry


def _mock_end_turn_response():
    """Simulate Claude returning end_turn with a text block."""
    msg = MagicMock()
    msg.stop_reason = "end_turn"
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = '{"summary": "Experiment complete"}'
    msg.content = [text_block]
    msg.usage = MagicMock()
    msg.usage.input_tokens = 100
    msg.usage.output_tokens = 50
    return msg


def _mock_tool_use_response(tool_name: str = "rescore_with_modifications"):
    """Simulate Claude requesting a tool call."""
    msg = MagicMock()
    msg.stop_reason = "tool_use"
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = "call_001"
    tool_block.name = tool_name
    tool_block.input = {
        "baseline_signals": [{"avg_top5_da": 35}],
        "modifications": [],
        "strategy_profile": "balanced",
    }
    msg.content = [tool_block]
    msg.usage = MagicMock()
    msg.usage.input_tokens = 100
    msg.usage.output_tokens = 50
    return msg


class TestClaudeAgent:
    def test_run_experiment_returns_valid_result(self) -> None:
        from src.research_agent.agent.claude_agent import ClaudeAgent

        registry = _make_registry()
        agent = ClaudeAgent(registry=registry, api_key="test-key")

        with patch.object(agent, "_client") as mock_client:
            mock_client.messages.create.side_effect = [
                _mock_tool_use_response(),
                _mock_end_turn_response(),
            ]
            result = agent.run_experiment(
                hypothesis=copy.deepcopy(MOCK_HYPOTHESIS),
                baseline=copy.deepcopy(MOCK_BASELINE_SNAPSHOT),
                budget_remaining=50.0,
            )

        assert "candidate_scores" in result
        assert "cost_usd" in result
        assert "tool_calls" in result
        assert isinstance(result["tool_calls"], list)
        assert len(result["tool_calls"]) >= 1

    def test_budget_tracking_stops_agent(self) -> None:
        from src.research_agent.agent.claude_agent import ClaudeAgent

        registry = _make_registry()
        agent = ClaudeAgent(registry=registry, api_key="test-key")

        with patch.object(agent, "_client") as mock_client:
            mock_client.messages.create.return_value = _mock_end_turn_response()
            result = agent.run_experiment(
                hypothesis=copy.deepcopy(MOCK_HYPOTHESIS),
                baseline=copy.deepcopy(MOCK_BASELINE_SNAPSHOT),
                budget_remaining=0.0,
            )

        assert result["cost_usd"] == 0.0

    def test_tool_failure_handled_gracefully(self) -> None:
        from src.research_agent.agent.claude_agent import ClaudeAgent

        class _FailPlugin(ToolPlugin):
            @property
            def name(self) -> str:
                return "scoring"

            def tool_definitions(self) -> list[dict]:
                return [
                    {
                        "name": "rescore_with_modifications",
                        "description": "test",
                        "input_schema": {"type": "object", "properties": {}},
                    }
                ]

            def execute(self, tool_name: str, arguments: dict) -> dict:
                raise RuntimeError("Tool exploded")

        registry = PluginRegistry()
        registry.register(_FailPlugin())
        agent = ClaudeAgent(registry=registry, api_key="test-key")

        with patch.object(agent, "_client") as mock_client:
            mock_client.messages.create.side_effect = [
                _mock_tool_use_response(),
                _mock_end_turn_response(),
            ]
            result = agent.run_experiment(
                hypothesis=copy.deepcopy(MOCK_HYPOTHESIS),
                baseline=copy.deepcopy(MOCK_BASELINE_SNAPSHOT),
                budget_remaining=50.0,
            )

        assert len(result["tool_calls"]) >= 1
        failed_call = result["tool_calls"][0]
        assert "error" in failed_call

    def test_max_rounds_limit(self) -> None:
        from src.research_agent.agent.claude_agent import ClaudeAgent

        registry = _make_registry()
        agent = ClaudeAgent(registry=registry, api_key="test-key", max_tool_rounds=1)

        with patch.object(agent, "_client") as mock_client:
            mock_client.messages.create.side_effect = [
                _mock_tool_use_response(),
                _mock_tool_use_response(),
            ]
            result = agent.run_experiment(
                hypothesis=copy.deepcopy(MOCK_HYPOTHESIS),
                baseline=copy.deepcopy(MOCK_BASELINE_SNAPSHOT),
                budget_remaining=50.0,
            )

        assert len(result["tool_calls"]) == 1


class TestSystemPrompt:
    def test_prompt_includes_proxy_dimensions(self) -> None:
        from src.research_agent.agent.prompts import RESEARCH_SYSTEM_PROMPT

        for dim in ["Demand", "Organic Competition", "Local Competition",
                     "Monetization", "AI Resilience"]:
            assert dim in RESEARCH_SYSTEM_PROMPT

    def test_prompt_instructs_fast_mode(self) -> None:
        from src.research_agent.agent.prompts import RESEARCH_SYSTEM_PROMPT

        assert "rescore_with_modifications" in RESEARCH_SYSTEM_PROMPT
