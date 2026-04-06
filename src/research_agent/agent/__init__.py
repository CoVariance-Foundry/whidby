"""Claude-native tool-use agent for research experiment execution."""

from __future__ import annotations

import logging
from typing import Any

from src.research_agent.agent.claude_agent import ClaudeAgent
from src.research_agent.hypothesis.experiment_planner import plan_experiment
from src.research_agent.memory.filesystem_store import FilesystemStore
from src.research_agent.plugins import PluginRegistry
from src.research_agent.plugins.dataforseo_plugin import DataForSEOPlugin
from src.research_agent.plugins.llm_plugin import LLMPlugin
from src.research_agent.plugins.metro_plugin import MetroDBPlugin
from src.research_agent.plugins.scoring_plugin import ScoringPlugin

logger = logging.getLogger(__name__)


def _build_registry() -> PluginRegistry:
    """Build the default plugin registry with all available plugins."""
    registry = PluginRegistry()
    registry.register(ScoringPlugin())
    registry.register_safe(DataForSEOPlugin())
    registry.register_safe(MetroDBPlugin())
    registry.register_safe(LLMPlugin())
    return registry


def claude_experiment_runner(
    hypothesis: dict[str, Any],
    fs: FilesystemStore,
) -> dict[str, Any]:
    """Run a scoring experiment using the Claude agent with tool-use reasoning.

    Matches the ``ExperimentRunner`` signature
    ``Callable[[dict, FilesystemStore], dict]``.

    The Claude agent receives the hypothesis and baseline data, reasons about
    which tools to call (fast-mode re-scoring vs full-mode data collection),
    executes them via the plugin registry, and returns structured results.

    Args:
        hypothesis: Hypothesis dict from the generator/backlog.
        fs: Filesystem store for the current run.

    Returns:
        Experiment result dict with ``experiment_id``, ``cost_usd``,
        ``modifications``, ``candidate_scores``, and ``tool_calls``.
    """
    plan = plan_experiment(hypothesis)
    experiment_id = plan["experiment_id"]
    modifications = plan.get("modifications", [])

    baseline = fs.load_snapshot("baseline")
    if baseline is None:
        baseline = {}

    registry = _build_registry()
    agent = ClaudeAgent(registry=registry)

    agent_result = agent.run_experiment(
        hypothesis=hypothesis,
        baseline=baseline,
        budget_remaining=50.0,
    )

    candidate_scores = agent_result.get("candidate_scores", {"metros": []})
    cost_usd = agent_result.get("cost_usd", 0.0)
    tool_calls = agent_result.get("tool_calls", [])

    cbsa_codes = [m.get("cbsa_code", "") for m in baseline.get("metros", [])]
    for i, metro in enumerate(candidate_scores.get("metros", [])):
        if i < len(cbsa_codes):
            metro["cbsa_code"] = cbsa_codes[i]

    fs.save_experiment_result(experiment_id, {
        "experiment_id": experiment_id,
        "cost_usd": cost_usd,
        "modifications": modifications,
        "candidate_scores": candidate_scores,
        "tool_calls": tool_calls,
    })

    return {
        "experiment_id": experiment_id,
        "cost_usd": cost_usd,
        "modifications": modifications,
        "candidate_scores": candidate_scores,
        "plan": plan,
        "tool_calls": tool_calls,
    }
