"""Unit tests for M5 request validation and collection planning."""

from __future__ import annotations

import pytest

from src.pipeline.collection_plan import MAX_VOLUME_BATCH_SIZE, build_collection_plan
from src.pipeline.types import build_collection_request
from tests.fixtures.m5_collection_fixtures import SAMPLE_KEYWORDS, SAMPLE_METROS


def test_request_validation_rejects_empty_keywords() -> None:
    with pytest.raises(ValueError, match="keywords must be non-empty"):
        build_collection_request([], SAMPLE_METROS, "balanced")


def test_request_validation_rejects_duplicate_metro_ids() -> None:
    metros = [SAMPLE_METROS[0], SAMPLE_METROS[0]]
    with pytest.raises(ValueError, match="duplicate metro_id"):
        build_collection_request(SAMPLE_KEYWORDS, metros, "balanced")


def test_plan_includes_serp_for_only_eligible_keywords() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)

    serp_tasks = [task for task in plan.base_tasks if task.task_type == "serp_organic"]
    assert len(serp_tasks) == 2
    assert all("leaking faucet" not in task.payload["keyword"] for task in serp_tasks)


def test_plan_batches_keyword_volume_by_700_limit() -> None:
    keywords = [
        {"keyword": f"kw-{index}", "tier": 1, "intent": "transactional"}
        for index in range(MAX_VOLUME_BATCH_SIZE + 5)
    ]
    request = build_collection_request(keywords, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    volume_tasks = [task for task in plan.base_tasks if task.task_type == "keyword_volume"]

    assert len(volume_tasks) == 2
    assert len(volume_tasks[0].payload["keywords"]) == MAX_VOLUME_BATCH_SIZE
    assert len(volume_tasks[1].payload["keywords"]) == 5


def test_plan_is_partitioned_for_multiple_metros() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, SAMPLE_METROS, "balanced")
    plan = build_collection_plan(request)
    metro_ids = {task.metro_id for task in plan.base_tasks}

    assert metro_ids == {"38060", "49740"}
    assert len([task for task in plan.base_tasks if task.task_type == "keyword_volume"]) == 2

