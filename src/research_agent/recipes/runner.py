"""RecipeRunner: one-shot orchestrator for cross-referenced SEO reports.

A :class:`RecipeRunner` executes a :class:`~src.research_agent.recipes.base.Recipe`
end-to-end: it validates that the recipe's required plugins are registered,
runs a bounded Claude tool-use loop (using the recipe's ``system_prompt``),
extracts the final JSON output contract from Claude's last response, hands
the parsed payload to the recipe's pure ``scoring_fn`` (if any), and asks
``ReportPlugin.compose_report`` to render the HTML artifact.

Relationship to :class:`~src.research_agent.agent.claude_agent.ClaudeAgent`:
recipes are **one-shot** (a single recipe -> a single report artifact),
while experiments are **iterative** (the Ralph loop runs many experiments
per session and threads budget through them). The two runners share the
same tool-use loop *shape* today but deliberately do not share a base
class -- the shared abstraction will emerge in Phase 2 once we have
multiple recipe runners and/or multiple experiment runners to compare.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from src.config.constants import DEFAULT_MODEL
from src.research_agent.plugins.base import PluginRegistry
from src.research_agent.plugins.report_plugin import ReportPlugin
from src.research_agent.recipes.base import Recipe

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_ERROR_EXCERPT_LENGTH = 200


class RecipeRunnerError(RuntimeError):
    """Raised when a recipe cannot be executed end-to-end.

    Covers: missing required plugins, failure to extract the final JSON
    payload from Claude's response, and tool-use round exhaustion with no
    parseable output.
    """


def _extract_json_payload(response_content: list[Any]) -> dict[str, Any]:
    r"""Extract the recipe's JSON output contract from a Claude response.

    Iterates ``response_content`` blocks in REVERSE order (the contract JSON
    is typically the last text block Claude emits, after any narrative
    prose); for each ``text`` block tries, in sequence:

    1. ``json.loads`` on the stripped text (raw JSON object emitted by Claude).
    2. Fenced code block match (``\`\`\`json ... \`\`\``` or ``\`\`\` ... \`\`\``).
    3. First top-level ``{...}`` substring with balanced braces.

    Returns the first successfully parsed JSON object. Raises
    :class:`RecipeRunnerError` with a truncated excerpt of the last text
    block if nothing parses, or an explicit "empty response content" message
    if the response had no text blocks at all.
    """
    text_blocks = [
        b for b in response_content if getattr(b, "type", None) == "text"
    ]
    if not response_content:
        raise RecipeRunnerError(
            "could not extract final JSON from Claude response: "
            "response content was empty"
        )
    if not text_blocks:
        raise RecipeRunnerError(
            "could not extract final JSON from Claude response: "
            "response had no text blocks"
        )

    last_text_excerpt = ""

    for block in reversed(text_blocks):
        text: str = getattr(block, "text", "") or ""
        stripped = text.strip()
        if not stripped:
            continue
        if not last_text_excerpt:
            last_text_excerpt = stripped[:_ERROR_EXCERPT_LENGTH]

        # 1. Whole block is raw JSON.
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed

        # 2. Fenced code block.
        match = _JSON_FENCE_RE.search(stripped)
        if match:
            try:
                parsed = json.loads(match.group(1))
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                return parsed

        # 3. Balanced-brace scan.
        parsed = _scan_balanced_object(stripped)
        if isinstance(parsed, dict):
            return parsed

    raise RecipeRunnerError(
        "could not extract final JSON from Claude response; "
        f"last text block excerpt: {last_text_excerpt!r}"
    )


def _scan_balanced_object(text: str) -> dict[str, Any] | None:
    """Return the first balanced-brace JSON object parsed from *text*, else None.

    Walks the string character by character, tracks brace depth (ignoring
    braces inside string literals), and attempts ``json.loads`` on each
    closing-brace candidate. Returns the first dict that parses cleanly.
    """
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        parsed = json.loads(candidate)
                    except json.JSONDecodeError:
                        break
                    if isinstance(parsed, dict):
                        return parsed
                    break
        start = text.find("{", start + 1)
    return None


class RecipeRunner:
    """Execute a recipe end-to-end: tool-use -> scoring -> HTML render.

    Args:
        registry: Plugin registry with the tool plugins the recipe may call.
        report_plugin: :class:`ReportPlugin` instance used to render the
            final HTML artifact.
        anthropic_client: Pre-constructed Anthropic client. ``None`` means
            build a default client from ``ANTHROPIC_API_KEY``.
        model: Claude model id; defaults to ``DEFAULT_MODEL``.
        max_tool_rounds: Hard ceiling on tool-use loop iterations.
    """

    def __init__(
        self,
        registry: PluginRegistry,
        *,
        report_plugin: ReportPlugin,
        anthropic_client: anthropic.Anthropic | None = None,
        model: str = DEFAULT_MODEL,
        max_tool_rounds: int = 12,
    ) -> None:
        self._registry = registry
        self._report_plugin = report_plugin
        self._model = model
        self._max_tool_rounds = max_tool_rounds
        if anthropic_client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            self._anthropic_client = anthropic.Anthropic(api_key=api_key)
        else:
            self._anthropic_client = anthropic_client

    def run(
        self,
        recipe: Recipe,
        inputs: dict[str, Any],
        output_dir: Path | str,
    ) -> dict[str, Any]:
        """Run *recipe* with *inputs* and write the report to *output_dir*."""
        self._check_required_plugins(recipe)

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": self._build_user_message(inputs)},
        ]
        tool_definitions = self._registry.get_tool_definitions()
        tool_calls_log: list[dict[str, Any]] = []
        cumulative_cost = 0.0
        last_response: Any = None
        rounds_used = 0
        hit_end_turn = False

        for _round in range(self._max_tool_rounds):
            rounds_used += 1
            response = self._anthropic_client.messages.create(
                model=self._model,
                max_tokens=4096,
                temperature=0,
                system=recipe.system_prompt,
                tools=tool_definitions,
                messages=messages,
            )
            last_response = response

            if response.stop_reason == "end_turn":
                hit_end_turn = True
                break

            if response.stop_reason != "tool_use":
                # Unknown stop reason (e.g. max_tokens); bail out of the
                # loop but still try to extract JSON below.
                break

            tool_use_blocks = [
                b for b in response.content if getattr(b, "type", None) == "tool_use"
            ]
            if not tool_use_blocks:
                break

            messages.append({"role": "assistant", "content": response.content})

            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                record = self._execute_tool(block)
                tool_calls_log.append(record)
                cumulative_cost += float(record.get("cost_usd", 0.0))

                result_content: dict[str, Any] = {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                }
                if "error" in record:
                    result_content["content"] = json.dumps(
                        {"error": record["error"]}
                    )
                    result_content["is_error"] = True
                else:
                    result_content["content"] = json.dumps(
                        record.get("result", {}), default=str
                    )
                tool_results.append(result_content)

            messages.append({"role": "user", "content": tool_results})

        if last_response is None:
            raise RecipeRunnerError(
                "recipe runner exhausted without ever calling the model"
            )

        # Extract JSON from whatever the final response was (end_turn or
        # partial tool_use with embedded JSON).
        collected = _extract_json_payload(last_response.content)

        if recipe.scoring_fn is None:
            context = dict(collected)
        else:
            context = recipe.scoring_fn(collected)

        report_result = self._report_plugin.execute(
            "compose_report",
            {
                "recipe_id": recipe.recipe_id,
                "template_name": recipe.template_name,
                "context": context,
                "output_dir": str(output_dir),
            },
        )

        status = "ok" if hit_end_turn else "partial"

        return {
            "report_path": report_result["report_path"],
            "bytes": report_result["bytes"],
            "context": context,
            "collected": collected,
            "tool_calls": tool_calls_log,
            "cost_usd": cumulative_cost,
            "rounds_used": rounds_used,
            "status": status,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_required_plugins(self, recipe: Recipe) -> None:
        registered = set(self._registry.list_plugins())
        missing = [p for p in recipe.required_plugins if p not in registered]
        if missing:
            raise RecipeRunnerError(
                f"recipe '{recipe.recipe_id}' is missing required plugins: "
                f"{missing}"
            )

    @staticmethod
    def _build_user_message(inputs: dict[str, Any]) -> str:
        payload = json.dumps(inputs, indent=2, default=str)
        return (
            "## Recipe inputs\n"
            "```json\n"
            f"{payload}\n"
            "```\n\n"
            "Respond per the output contract in the system prompt."
        )

    def _execute_tool(self, block: Any) -> dict[str, Any]:
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
            record["cost_usd"] = float(result.get("cost_usd", 0.0))
            record["latency_ms"] = elapsed_ms
            logger.info(
                "Recipe tool %s executed in %dms, cost=$%.4f",
                block.name,
                elapsed_ms,
                record["cost_usd"],
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            record["error"] = str(exc)
            record["cost_usd"] = 0.0
            record["latency_ms"] = elapsed_ms
            logger.error(
                "Recipe tool %s failed: %s", block.name, exc, exc_info=True
            )
        return record
