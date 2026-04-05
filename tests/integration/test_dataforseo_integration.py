"""Integration tests for the DataForSEO client (M0).

These hit the real API. Requires DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD
environment variables. Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import os

import pytest

from src.clients.dataforseo.client import DataForSEOClient
from src.pipeline.data_collection import collect_data
from tests.fixtures.m5_collection_fixtures import SAMPLE_KEYWORDS


pytestmark = pytest.mark.integration


def _real_client() -> DataForSEOClient:
    login = os.environ.get("DATAFORSEO_LOGIN", "")
    password = os.environ.get("DATAFORSEO_PASSWORD", "")
    if not login or not password:
        pytest.skip("DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD not set")
    return DataForSEOClient(login=login, password=password)


class TestRealAPI:
    @pytest.mark.asyncio
    async def test_locations_endpoint(self):
        client = _real_client()
        result = await client.locations()
        assert result.status == "ok"
        assert result.data is not None
        assert len(result.data) > 0

    @pytest.mark.asyncio
    async def test_business_listings_live(self):
        client = _real_client()
        result = await client.business_listings(
            category="Plumber", location_code=1012873, limit=5
        )
        assert result.status == "ok"
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_keyword_volume(self):
        client = _real_client()
        result = await client.keyword_volume(
            keywords=["plumber near me"], location_code=1012873
        )
        assert result.status == "ok"
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_serp_organic(self):
        client = _real_client()
        result = await client.serp_organic(
            keyword="plumber", location_code=1012873, depth=5
        )
        assert result.status == "ok"
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_keyword_suggestions(self):
        client = _real_client()
        result = await client.keyword_suggestions(
            keyword="plumber", limit=5
        )
        assert result.status == "ok"
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_cost_tracking(self):
        client = _real_client()
        await client.locations()
        await client.business_listings(
            category="Plumber", location_code=1012873, limit=3
        )
        assert len(client.cost_log) >= 2

    @pytest.mark.asyncio
    async def test_caching(self):
        client = _real_client()
        first = await client.locations()
        assert first.status == "ok"
        second = await client.locations()
        assert second.status == "ok"
        assert second.cached is True
        assert second.cost == 0

    @pytest.mark.asyncio
    async def test_m5_collect_data_contract_with_real_client(self):
        """Smoke test for M5 orchestration against real client boundary."""
        client = _real_client()
        metros = [{"metro_id": "38060", "location_code": 1012873, "principal_city": "Phoenix"}]
        result = await collect_data(SAMPLE_KEYWORDS, metros, "balanced", client)
        assert "38060" in result.metros
        assert result.meta.total_api_calls > 0
