"""Unit tests for top-level M5 orchestration."""

from __future__ import annotations

import pytest

from src.pipeline.data_collection import collect_data
from tests.fixtures.m5_collection_fixtures import FakeDataForSEOClient, SAMPLE_KEYWORDS, SAMPLE_METROS


@pytest.mark.asyncio
async def test_collect_data_single_metro_contract_shape() -> None:
    client = FakeDataForSEOClient()
    result = await collect_data(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced", client)

    assert "38060" in result.metros
    metro = result.metros["38060"]
    assert hasattr(metro, "serp_organic")
    assert hasattr(metro, "serp_maps")
    assert hasattr(metro, "keyword_volume")
    assert hasattr(result, "meta")
    assert result.meta.total_api_calls > 0
    assert result.meta.total_cost_usd > 0


@pytest.mark.asyncio
async def test_collect_data_multi_metro_partitioning() -> None:
    client = FakeDataForSEOClient()
    result = await collect_data(SAMPLE_KEYWORDS, SAMPLE_METROS, "balanced", client)

    assert set(result.metros.keys()) == {"38060", "49740"}


@pytest.mark.asyncio
async def test_collect_data_partial_failure_retains_results() -> None:
    client = FakeDataForSEOClient(fail_task_type="google_reviews")
    result = await collect_data(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced", client)

    assert len(result.meta.errors) >= 1
    assert result.metros["38060"].keyword_volume

