"""Integration tests for the DataForSEO client (M0).

These hit the real API. Requires DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD
environment variables. Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import os

import pytest

from src.clients.dataforseo.client import DataForSEOClient


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
