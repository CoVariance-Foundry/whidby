"""Tests for RecipeRunner (Phase 1 Task 5 of 012-recipe-reports).

Mocks the Anthropic client so no real API calls are made. Uses the real
ReportPlugin + ``tmp_path`` for filesystem integration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from src.research_agent.plugins.base import PluginRegistry, ToolPlugin
from src.research_agent.plugins.report_plugin import ReportPlugin
from src.research_agent.recipes.base import Recipe
from src.research_agent.recipes.playbooks.market_opportunity import (
    RECIPE as MARKET_RECIPE,
)
from src.research_agent.recipes.runner import (
    RecipeRunner,
    RecipeRunnerError,
    _extract_json_payload,
)


# ---------------------------------------------------------------------------
# Fake Anthropic SDK response objects
# ---------------------------------------------------------------------------


@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class _FakeToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class _FakeResponse:
    stop_reason: str
    content: list[Any] = field(default_factory=list)


class _FakeMessages:
    def __init__(self, outer: "_FakeAnthropicClient") -> None:
        self._outer = outer

    def create(self, **kwargs: Any) -> _FakeResponse:
        self._outer.calls.append(kwargs)
        if not self._outer.responses:
            raise AssertionError(
                "FakeAnthropicClient ran out of scripted responses at "
                f"call #{len(self._outer.calls)}"
            )
        return self._outer.responses.pop(0)


class _FakeAnthropicClient:
    """Sync fake mirroring ``anthropic.Anthropic``'s shape."""

    def __init__(self, responses: list[_FakeResponse]) -> None:
        self.responses: list[_FakeResponse] = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.messages = _FakeMessages(self)


# ---------------------------------------------------------------------------
# Mock tool plugins
# ---------------------------------------------------------------------------


class _MockDataForSEOPlugin(ToolPlugin):
    @property
    def name(self) -> str:
        return "dataforseo"

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "fetch_keyword_volume",
                "description": "fake",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "fetch_serp_organic",
                "description": "fake",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "fetch_backlinks_summary",
                "description": "fake",
                "input_schema": {"type": "object", "properties": {}},
            },
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"data": {"tool": tool_name}, "cost_usd": 0.05, "status": "ok"}


class _MockSerpAPIPlugin(ToolPlugin):
    @property
    def name(self) -> str:
        return "serpapi"

    def tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "fetch_serpapi_maps",
                "description": "fake",
                "input_schema": {"type": "object", "properties": {}},
            }
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"data": {"tool": tool_name}, "cost_usd": 0.01, "status": "ok"}


def _make_registry(include_serpapi: bool = True) -> PluginRegistry:
    registry = PluginRegistry()
    registry.register(_MockDataForSEOPlugin())
    if include_serpapi:
        registry.register(_MockSerpAPIPlugin())
    return registry


# ---------------------------------------------------------------------------
# Fixtures / sample inputs
# ---------------------------------------------------------------------------


_MARKET_INPUTS: dict[str, Any] = {
    "service": "concrete paver",
    "cities": [
        {"name": "Austin, TX", "location_code": 1026201},
        {"name": "Phoenix, AZ", "location_code": 1023191},
    ],
}


_MARKET_COLLECTED: dict[str, Any] = {
    "service": "concrete paver",
    "markets": [
        {
            "city": "Austin, TX",
            "search_volume": 1000,
            "avg_competitor_da": 40.0,
            "avg_backlink_strength": 500.0,
            "gmb_saturation": 0.4,
            "cpc_value": 6.0,
            "top_competitors": ["a.com", "b.com"],
        },
        {
            "city": "Phoenix, AZ",
            "search_volume": 500,
            "avg_competitor_da": 55.0,
            "avg_backlink_strength": 800.0,
            "gmb_saturation": 0.7,
            "cpc_value": 4.5,
            "top_competitors": ["c.com", "d.com"],
        },
    ],
    "total_cost_usd": 0.12,
    "notes": [],
}


def _market_collected_json() -> str:
    return json.dumps(_MARKET_COLLECTED)


# ---------------------------------------------------------------------------
# Plugin availability guard
# ---------------------------------------------------------------------------


def test_missing_required_plugin_raises_recipe_runner_error(tmp_path) -> None:
    registry = _make_registry(include_serpapi=False)
    runner = RecipeRunner(
        registry,
        report_plugin=ReportPlugin(),
        anthropic_client=_FakeAnthropicClient([]),
    )

    with pytest.raises(RecipeRunnerError) as exc_info:
        runner.run(MARKET_RECIPE, _MARKET_INPUTS, tmp_path)

    assert "serpapi" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_happy_path_two_round_loop(tmp_path) -> None:
    registry = _make_registry()

    round1 = _FakeResponse(
        stop_reason="tool_use",
        content=[
            _FakeToolUseBlock(
                id="call_1",
                name="fetch_keyword_volume",
                input={"keyword": "concrete paver", "location_code": 1026201},
            ),
            _FakeToolUseBlock(
                id="call_2",
                name="fetch_serp_organic",
                input={"keyword": "concrete paver", "location_code": 1026201},
            ),
        ],
    )
    round2 = _FakeResponse(
        stop_reason="end_turn",
        content=[_FakeTextBlock(text=_market_collected_json())],
    )

    fake_client = _FakeAnthropicClient([round1, round2])
    runner = RecipeRunner(
        registry,
        report_plugin=ReportPlugin(),
        anthropic_client=fake_client,
    )

    scoring_calls: list[dict[str, Any]] = []
    original_fn = MARKET_RECIPE.scoring_fn
    assert original_fn is not None

    def spy_scoring(collected: dict[str, Any]) -> dict[str, Any]:
        scoring_calls.append(collected)
        return original_fn(collected)

    recipe = Recipe(
        recipe_id=MARKET_RECIPE.recipe_id,
        audience=MARKET_RECIPE.audience,
        required_plugins=MARKET_RECIPE.required_plugins,
        optional_plugins=MARKET_RECIPE.optional_plugins,
        inputs_schema=MARKET_RECIPE.inputs_schema,
        system_prompt=MARKET_RECIPE.system_prompt,
        template_name=MARKET_RECIPE.template_name,
        scoring_fn=spy_scoring,
    )

    result = runner.run(recipe, _MARKET_INPUTS, tmp_path)

    assert result["status"] == "ok"
    assert result["rounds_used"] == 2
    # 2 dataforseo tool calls -> 2 * 0.05
    assert result["cost_usd"] == pytest.approx(0.10)

    report_path = result["report_path"]
    assert report_path
    from pathlib import Path
    p = Path(report_path)
    assert p.is_absolute()
    assert p.exists()

    rendered = p.read_text(encoding="utf-8")
    assert "Austin, TX" in rendered
    assert "Phoenix, AZ" in rendered

    # scoring_fn was called with the parsed collected JSON
    assert scoring_calls == [_MARKET_COLLECTED]

    # Audit log shape
    assert len(result["tool_calls"]) == 2
    for call in result["tool_calls"]:
        assert "tool_name" in call
        assert "arguments" in call
        assert "cost_usd" in call
        assert "latency_ms" in call


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------


def test_json_extraction_fenced_block() -> None:
    text = (
        "Here is the final payload:\n"
        "```json\n"
        '{"service": "plumber", "markets": []}\n'
        "```\n"
        "That's it."
    )
    response = _FakeResponse(
        stop_reason="end_turn",
        content=[_FakeTextBlock(text=text)],
    )
    payload = _extract_json_payload(response.content)
    assert payload == {"service": "plumber", "markets": []}


def test_json_extraction_raw_block() -> None:
    text = '{"service": "plumber", "markets": []}'
    response = _FakeResponse(
        stop_reason="end_turn",
        content=[_FakeTextBlock(text=text)],
    )
    payload = _extract_json_payload(response.content)
    assert payload == {"service": "plumber", "markets": []}


def test_json_extraction_embedded_in_prose() -> None:
    text = (
        'The scoring payload follows: {"service": "roofer", '
        '"markets": [{"city": "X"}]} -- done.'
    )
    response = _FakeResponse(
        stop_reason="end_turn",
        content=[_FakeTextBlock(text=text)],
    )
    payload = _extract_json_payload(response.content)
    assert payload == {"service": "roofer", "markets": [{"city": "X"}]}


def test_json_extraction_failure_raises() -> None:
    # No JSON of any form
    response = _FakeResponse(
        stop_reason="end_turn",
        content=[
            _FakeTextBlock(text="Sorry, I couldn't complete this task." * 50),
        ],
    )
    with pytest.raises(RecipeRunnerError) as exc_info:
        _extract_json_payload(response.content)
    msg = str(exc_info.value)
    assert "could not extract" in msg.lower()
    # Truncated excerpt of the block should be in the message
    assert "Sorry, I couldn't complete" in msg


def test_extract_skips_tool_use_blocks_and_reads_text() -> None:
    response = _FakeResponse(
        stop_reason="end_turn",
        content=[
            _FakeToolUseBlock(id="x", name="foo", input={}),
            _FakeTextBlock(text='{"service": "a", "markets": []}'),
        ],
    )
    payload = _extract_json_payload(response.content)
    assert payload == {"service": "a", "markets": []}


# ---------------------------------------------------------------------------
# Runner-level JSON extraction failure
# ---------------------------------------------------------------------------


def test_runner_raises_when_final_response_has_no_json(tmp_path) -> None:
    registry = _make_registry()
    response = _FakeResponse(
        stop_reason="end_turn",
        content=[_FakeTextBlock(text="I give up, no data available.")],
    )
    runner = RecipeRunner(
        registry,
        report_plugin=ReportPlugin(),
        anthropic_client=_FakeAnthropicClient([response]),
    )

    with pytest.raises(RecipeRunnerError):
        runner.run(MARKET_RECIPE, _MARKET_INPUTS, tmp_path)


# ---------------------------------------------------------------------------
# Partial status (max rounds reached but JSON extractable)
# ---------------------------------------------------------------------------


def test_partial_status_when_max_rounds_reached_with_json(tmp_path) -> None:
    registry = _make_registry()

    # Claude never emits end_turn: it keeps emitting tool_use rounds, but its
    # very last tool_use round ALSO carries a text block with parseable JSON.
    def tool_use_round_with_text(round_idx: int) -> _FakeResponse:
        content: list[Any] = [
            _FakeToolUseBlock(
                id=f"call_{round_idx}",
                name="fetch_keyword_volume",
                input={"keyword": "x"},
            )
        ]
        # Include parseable JSON in every text block; extractor will find it
        # in the partial-final response.
        content.append(_FakeTextBlock(text=_market_collected_json()))
        return _FakeResponse(stop_reason="tool_use", content=content)

    max_rounds = 3
    responses = [tool_use_round_with_text(i) for i in range(max_rounds)]
    fake_client = _FakeAnthropicClient(responses)

    runner = RecipeRunner(
        registry,
        report_plugin=ReportPlugin(),
        anthropic_client=fake_client,
        max_tool_rounds=max_rounds,
    )

    result = runner.run(MARKET_RECIPE, _MARKET_INPUTS, tmp_path)

    assert result["status"] == "partial"
    assert result["rounds_used"] == max_rounds


# ---------------------------------------------------------------------------
# Tool call logging shape
# ---------------------------------------------------------------------------


def test_tool_call_logging(tmp_path) -> None:
    registry = _make_registry()
    round1 = _FakeResponse(
        stop_reason="tool_use",
        content=[
            _FakeToolUseBlock(
                id="c1",
                name="fetch_serp_organic",
                input={"keyword": "roof"},
            ),
        ],
    )
    round2 = _FakeResponse(
        stop_reason="end_turn",
        content=[_FakeTextBlock(text=_market_collected_json())],
    )
    runner = RecipeRunner(
        registry,
        report_plugin=ReportPlugin(),
        anthropic_client=_FakeAnthropicClient([round1, round2]),
    )
    result = runner.run(MARKET_RECIPE, _MARKET_INPUTS, tmp_path)

    calls = result["tool_calls"]
    assert len(calls) == 1
    entry = calls[0]
    assert entry["tool_name"] == "fetch_serp_organic"
    assert entry["arguments"] == {"keyword": "roof"}
    assert entry["cost_usd"] == pytest.approx(0.05)
    assert isinstance(entry["latency_ms"], int)
    assert entry["latency_ms"] >= 0


# ---------------------------------------------------------------------------
# Scoring-fn optional path
# ---------------------------------------------------------------------------


def test_recipe_without_scoring_fn_uses_collected_as_context(tmp_path, monkeypatch) -> None:
    # A dummy recipe with no scoring_fn, pointing at the market template
    # (any allow-listed template works; we just need a valid render).
    dummy_context = {
        "service": "widget",
        "markets": [],
        "weights": {"search_volume": 1.0},
        "summary": {
            "total_markets": 0,
            "top_market": "\u2014",
            "median_score": 0.0,
            "total_cost_usd": 0.0,
        },
        "generated_at": "2026-04-20T00:00:00Z",
        "recipe_id": "no_scoring_dummy",
    }

    # Recipe requires no plugins so we can use an empty registry.
    recipe = Recipe(
        recipe_id="no_scoring_dummy",
        audience="agency",
        required_plugins=(),
        optional_plugins=(),
        inputs_schema={"type": "object"},
        system_prompt="Return the JSON context.",
        template_name="market_opportunity.html",
        scoring_fn=None,
    )

    response = _FakeResponse(
        stop_reason="end_turn",
        content=[_FakeTextBlock(text=json.dumps(dummy_context))],
    )
    registry = PluginRegistry()

    # Spy on ReportPlugin.execute to capture the context that was passed.
    report_plugin = ReportPlugin()
    captured: dict[str, Any] = {}
    original_execute = report_plugin.execute

    def spy_execute(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        captured["arguments"] = arguments
        return original_execute(tool_name, arguments)

    monkeypatch.setattr(report_plugin, "execute", spy_execute)

    runner = RecipeRunner(
        registry,
        report_plugin=report_plugin,
        anthropic_client=_FakeAnthropicClient([response]),
    )
    result = runner.run(recipe, {}, tmp_path)

    assert result["status"] == "ok"
    assert captured["arguments"]["context"] == dummy_context
    assert result["context"] == dummy_context
    assert result["collected"] == dummy_context
