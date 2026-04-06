"""Claude-native tool-use agent for research experiment execution.

Uses ``anthropic.Anthropic.messages.create()`` with the ``tools`` parameter
to reason about which tools to call for a given hypothesis, then executes
them via the PluginRegistry.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import anthropic

from src.config.constants import DEFAULT_MODEL
from src.research_agent.agent.prompts import RESEARCH_SYSTEM_PROMPT
from src.research_agent.plugins.base import PluginRegistry

logger = logging.getLogger(__name__)


class ClaudeAgent:
    """AI reasoning component that executes experiments via tool-use.

    Args:
        registry: Plugin registry with loaded tools.
        api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var).
        model: Model to use for reasoning (default from constants).
        max_tool_rounds: Maximum tool-use loop iterations before stopping.
    """

    def __init__(
        self,
        registry: PluginRegistry,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_tool_rounds: int = 10,
    ) -> None:
        self._registry = registry
        self._model = model
        self._max_tool_rounds = max_tool_rounds
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = anthropic.Anthropic(api_key=key)

    def run_experiment(
        self,
        hypothesis: dict[str, Any],
        baseline: dict[str, Any],
        budget_remaining: float,
    ) -> dict[str, Any]:
        """Execute a full experiment via Claude tool-use reasoning.

        Args:
            hypothesis: Hypothesis dict from the generator.
            baseline: Baseline scoring snapshot with metros and signals.
            budget_remaining: Remaining budget in USD for this session.

        Returns:
            Experiment result dict with candidate_scores, cost_usd,
            and tool_calls audit log.
        """
        tools = self._registry.get_tool_definitions()
        tool_calls_log: list[dict[str, Any]] = []
        cumulative_cost = 0.0
        last_candidate_scores: dict[str, Any] = {"metros": []}

        user_content = self._build_user_message(hypothesis, baseline, budget_remaining)
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_content},
        ]

        for _round in range(self._max_tool_rounds):
            if cumulative_cost >= budget_remaining:
                logger.info("Budget exhausted (%.4f >= %.4f), stopping agent",
                            cumulative_cost, budget_remaining)
                break

            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                temperature=0,
                system=RESEARCH_SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                break

            if response.stop_reason != "tool_use":
                break

            tool_use_blocks = [
                b for b in response.content if b.type == "tool_use"
            ]

            if not tool_use_blocks:
                break

            messages.append({"role": "assistant", "content": response.content})

            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                record = self._execute_tool(block)
                tool_calls_log.append(record)
                cumulative_cost += record.get("cost_usd", 0.0)

                if "candidate_scores" in record.get("result", {}):
                    last_candidate_scores = record["result"]["candidate_scores"]

                tool_result_content: dict[str, Any] = {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                }
                if "error" in record:
                    tool_result_content["content"] = json.dumps({"error": record["error"]})
                    tool_result_content["is_error"] = True
                else:
                    tool_result_content["content"] = json.dumps(
                        record.get("result", {}), default=str
                    )

                tool_results.append(tool_result_content)

            messages.append({"role": "user", "content": tool_results})

        return {
            "candidate_scores": last_candidate_scores,
            "cost_usd": cumulative_cost,
            "tool_calls": tool_calls_log,
        }

    def _execute_tool(self, block: Any) -> dict[str, Any]:
        """Execute a single tool call and return an audit record."""
        start = time.monotonic()
        record: dict[str, Any] = {
            "tool_name": block.name,
            "arguments": block.input,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            result = self._registry.execute(block.name, block.input)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            record["result"] = result
            record["cost_usd"] = result.get("cost_usd", 0.0)
            record["latency_ms"] = elapsed_ms
            logger.info(
                "Tool %s executed in %dms, cost=$%.4f",
                block.name, elapsed_ms, record["cost_usd"],
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            record["error"] = str(e)
            record["cost_usd"] = 0.0
            record["latency_ms"] = elapsed_ms
            logger.error("Tool %s failed: %s", block.name, e, exc_info=True)

        return record

    @staticmethod
    def _build_user_message(
        hypothesis: dict[str, Any],
        baseline: dict[str, Any],
        budget_remaining: float,
    ) -> str:
        baseline_summary = []
        for m in baseline.get("metros", []):
            scores = m.get("scores", {})
            baseline_summary.append(
                f"  - {m.get('cbsa_name', m.get('cbsa_code', '?'))}: "
                f"opportunity={scores.get('opportunity', '?')}"
            )

        signals_sample = []
        for m in baseline.get("metros", [])[:1]:
            sigs = m.get("signals", {})
            if sigs:
                sig_str = ", ".join(f"{k}={v}" for k, v in list(sigs.items())[:5])
                signals_sample.append(f"  Sample signals: {sig_str}")

        return (
            f"## Hypothesis\n"
            f"Title: {hypothesis.get('title', '')}\n"
            f"Description: {hypothesis.get('description', '')}\n"
            f"Target proxy: {hypothesis.get('target_proxy', '')}\n"
            f"Approach: {hypothesis.get('approach', '')}\n"
            f"Expected direction: {hypothesis.get('expected_direction', '')}\n\n"
            f"## Baseline Scores\n"
            + "\n".join(baseline_summary)
            + "\n\n"
            + "\n".join(signals_sample)
            + f"\n\n## Budget\n"
            f"Remaining: ${budget_remaining:.2f}\n\n"
            f"## Instructions\n"
            f"Run the experiment for this hypothesis. Use the appropriate "
            f"tools to produce candidate scores. For parameter-only "
            f"modifications, use rescore_with_modifications with the "
            f"baseline signals.\n"
        )
