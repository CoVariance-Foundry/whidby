"""ScoringPlugin wrapping M7 compute_batch_scores for parameter-only experiments.

Provides the ``rescore_with_modifications`` tool that applies signal overrides
to baseline data and re-runs M7 scoring without any external API calls.
"""

from __future__ import annotations

import copy
from typing import Any

from src.research_agent.plugins.base import ToolPlugin
from src.scoring.engine import compute_batch_scores


class ScoringPlugin(ToolPlugin):
    """Plugin for fast-mode scoring experiments using the M7 pipeline."""

    @property
    def name(self) -> str:
        return "scoring"

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "rescore_with_modifications",
                "description": (
                    "Re-score baseline metro signals with parameter modifications "
                    "applied. Uses the M7 scoring engine (compute_batch_scores) to "
                    "produce real candidate scores. Zero API cost."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "baseline_signals": {
                            "type": "array",
                            "description": (
                                "List of per-metro signal dicts (flat key-value "
                                "mappings) from the baseline snapshot."
                            ),
                            "items": {"type": "object"},
                        },
                        "modifications": {
                            "type": "array",
                            "description": (
                                "List of modification dicts, each with 'param' "
                                "(signal key to override), 'candidate' (new value)."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "param": {"type": "string"},
                                    "candidate": {},
                                },
                            },
                        },
                        "strategy_profile": {
                            "type": "string",
                            "description": (
                                "Scoring strategy profile name "
                                "(e.g. 'balanced', 'organic_first', 'local_dominant')."
                            ),
                        },
                    },
                    "required": [
                        "baseline_signals",
                        "modifications",
                        "strategy_profile",
                    ],
                },
            },
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "rescore_with_modifications":
            return self._rescore(arguments)
        raise KeyError(f"Unknown tool: '{tool_name}'")

    def _rescore(self, arguments: dict[str, Any]) -> dict[str, Any]:
        baseline_signals = arguments["baseline_signals"]
        modifications = arguments.get("modifications", [])
        strategy_profile = arguments.get("strategy_profile", "balanced")

        modified_signals = _apply_modifications(baseline_signals, modifications)
        scores_list = compute_batch_scores(modified_signals, strategy_profile)

        metros = []
        for i, scores in enumerate(scores_list):
            metros.append({"scores": scores})

        return {
            "candidate_scores": {"metros": metros},
            "cost_usd": 0.0,
        }


def _apply_modifications(
    signals: list[dict[str, Any]],
    modifications: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply parameter overrides to copies of the signal dicts."""
    modified = copy.deepcopy(signals)
    for mod in modifications:
        param = mod.get("param", "")
        candidate_value = mod.get("candidate")
        if not param or candidate_value is None:
            continue
        for metro_signals in modified:
            if param in metro_signals:
                metro_signals[param] = candidate_value
    return modified
