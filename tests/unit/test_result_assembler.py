"""Unit tests for result assembly contract guarantees."""

from __future__ import annotations

from src.pipeline.batch_executor import ExecutionState
from src.pipeline.result_assembler import assemble_raw_collection_result
from src.pipeline.types import build_collection_request
from tests.fixtures.m5_collection_fixtures import SAMPLE_KEYWORDS, SAMPLE_METROS


def test_assembler_keeps_required_categories_present() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    state = ExecutionState()
    result = assemble_raw_collection_result(request, state, duration_seconds=0.1)

    metro = result.metros["38060"]
    assert metro.serp_organic == []
    assert metro.serp_maps == []
    assert metro.keyword_volume == []
    assert metro.business_listings == []
    assert metro.google_reviews == []
    assert metro.gbp_info == []
    assert metro.backlinks == []
    assert metro.lighthouse == []


def test_assembler_preserves_multi_metro_partitioning() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, SAMPLE_METROS, "balanced")
    state = ExecutionState(
        task_results={"task-a": [{"keyword": "plumber"}], "task-b": [{"keyword": "roofer"}]},
        task_categories={"task-a": "keyword_volume", "task-b": "keyword_volume"},
        task_metros={"task-a": "38060", "task-b": "49740"},
        task_costs={"task-a": 0.05, "task-b": 0.05},
        total_api_calls=2,
    )
    result = assemble_raw_collection_result(request, state, duration_seconds=0.2)

    assert result.metros["38060"].keyword_volume[0]["keyword"] == "plumber"
    assert result.metros["49740"].keyword_volume[0]["keyword"] == "roofer"
    assert result.meta.total_cost_usd == 0.1
    assert result.meta.total_api_calls == 2

