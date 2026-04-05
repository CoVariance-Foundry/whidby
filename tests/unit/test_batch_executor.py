"""Unit tests for M5 execution ordering, dedup, and failure isolation."""

from __future__ import annotations

import pytest

from src.pipeline.batch_executor import execute_collection_plan
from src.pipeline.collection_plan import build_collection_plan
from src.pipeline.types import build_collection_request
from tests.fixtures.m5_collection_fixtures import FakeDataForSEOClient, SAMPLE_KEYWORDS, SAMPLE_METROS


@pytest.mark.asyncio
async def test_executor_runs_base_and_dependent_categories() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    client = FakeDataForSEOClient()

    state = await execute_collection_plan(plan, request, client)

    categories = set(state.task_categories.values())
    assert "keyword_volume" in categories
    assert "serp_organic" in categories
    assert "serp_maps" in categories
    assert "backlinks" in categories
    assert "lighthouse" in categories
    assert state.total_api_calls > 0


@pytest.mark.asyncio
async def test_executor_applies_partial_failure_isolation() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    client = FakeDataForSEOClient(fail_task_type="serp_organic")

    state = await execute_collection_plan(plan, request, client)

    assert any(error.task_type == "serp_organic" for error in state.failures)
    assert state.total_api_calls > 0


@pytest.mark.asyncio
async def test_executor_maintains_multi_metro_state_partition() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, SAMPLE_METROS, "balanced")
    plan = build_collection_plan(request)
    client = FakeDataForSEOClient()

    state = await execute_collection_plan(plan, request, client)

    assert {"38060", "49740"}.issubset(set(state.task_metros.values()))

