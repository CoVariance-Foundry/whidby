"""Unit tests for the DataForSEO client (M0).

Tests are mocked — no network calls. Covers:
  Authentication, SERP queue flow, live endpoints, rate limiting,
  caching, cost tracking, error handling.
"""

from __future__ import annotations

import asyncio

import pytest

from src.clients.dataforseo.client import DataForSEOClient
from src.clients.dataforseo.types import APIResponse
from tests.fixtures.dataforseo_fixtures import (
    BUSINESS_LISTINGS_RESPONSE,
    ERROR_RESPONSE,
    SERP_LIVE_RESPONSE,
    SERP_TASK_GET_RESPONSE,
    SERP_TASK_PENDING_RESPONSE,
    SERP_TASK_POST_RESPONSE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(**overrides) -> DataForSEOClient:
    defaults = dict(login="test_user", password="test_pass", cache_ttl=60)
    defaults.update(overrides)
    return DataForSEOClient(**defaults)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestAuthentication:
    def test_auth_header_is_basic(self):
        client = _make_client()
        assert client._auth_header.startswith("Basic ")

    def test_different_credentials_produce_different_headers(self):
        c1 = _make_client(login="a", password="b")
        c2 = _make_client(login="x", password="y")
        assert c1._auth_header != c2._auth_header


# ---------------------------------------------------------------------------
# Standard queue flow (POST → poll → GET)
# ---------------------------------------------------------------------------

class TestLiveSERP:
    @pytest.mark.asyncio
    async def test_serp_organic_returns_results(self, mocker):
        client = _make_client()
        mocker.patch.object(client, "_post", return_value=SERP_LIVE_RESPONSE)
        result = await client.serp_organic(keyword="plumber", location_code=1012873)

        assert isinstance(result, APIResponse)
        assert result.status == "ok"
        assert result.data is not None
        assert result.cost > 0

    @pytest.mark.asyncio
    async def test_serp_maps_returns_results(self, mocker):
        client = _make_client()
        mocker.patch.object(client, "_post", return_value=SERP_LIVE_RESPONSE)
        result = await client.serp_maps(keyword="plumber", location_code=1012873)

        assert isinstance(result, APIResponse)
        assert result.status == "ok"
        assert result.data is not None


class TestStandardQueue:
    @pytest.mark.asyncio
    async def test_keyword_volume_returns_results(self, mocker):
        client = _make_client()
        mocker.patch.object(
            client, "_post", side_effect=[SERP_TASK_POST_RESPONSE, SERP_TASK_GET_RESPONSE]
        )
        mocker.patch("asyncio.sleep", return_value=None)
        result = await client.keyword_volume(keywords=["plumber"], location_code=1012873)

        assert isinstance(result, APIResponse)

    @pytest.mark.asyncio
    async def test_queue_polls_until_ready(self, mocker):
        """Simulate one 'pending' response before the final result arrives."""
        client = _make_client()
        mocker.patch.object(
            client,
            "_post",
            side_effect=[
                SERP_TASK_POST_RESPONSE,
                SERP_TASK_PENDING_RESPONSE,
                SERP_TASK_GET_RESPONSE,
            ],
        )
        mocker.patch("asyncio.sleep", return_value=None)

        result = await client.keyword_volume(keywords=["plumber"], location_code=1012873)
        assert result.status == "ok"


# ---------------------------------------------------------------------------
# Live endpoints
# ---------------------------------------------------------------------------

class TestLiveEndpoints:
    @pytest.mark.asyncio
    async def test_business_listings_returns_results(self, mocker):
        client = _make_client()
        mocker.patch.object(client, "_post", return_value=BUSINESS_LISTINGS_RESPONSE)

        result = await client.business_listings(
            category="Plumber", location_code=1012873, limit=100
        )
        assert result.status == "ok"
        assert result.data is not None
        assert result.cost > 0


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

class TestCaching:
    @pytest.mark.asyncio
    async def test_second_call_returns_cached(self, mocker):
        client = _make_client(cache_ttl=300)
        mocker.patch.object(client, "_post", return_value=SERP_LIVE_RESPONSE)

        r1 = await client.serp_organic(keyword="plumber", location_code=1012873)
        r2 = await client.serp_organic(keyword="plumber", location_code=1012873)

        assert r1.status == "ok"
        assert r2.status == "ok"
        assert r2.cached is True
        assert r2.cost == 0

    @pytest.mark.asyncio
    async def test_cache_miss_after_ttl(self, mocker):
        client = _make_client(cache_ttl=0)
        mocker.patch.object(
            client,
            "_post",
            side_effect=[SERP_LIVE_RESPONSE, SERP_LIVE_RESPONSE],
        )

        r1 = await client.serp_organic(keyword="plumber", location_code=1012873)
        r2 = await client.serp_organic(keyword="plumber", location_code=1012873)

        assert r1.cached is False
        assert r2.cached is False


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------

class TestCostTracking:
    @pytest.mark.asyncio
    async def test_costs_accumulate(self, mocker):
        client = _make_client()
        mocker.patch.object(
            client,
            "_post",
            side_effect=[SERP_LIVE_RESPONSE, BUSINESS_LISTINGS_RESPONSE],
        )

        await client.serp_organic(keyword="plumber", location_code=1012873)
        await client.business_listings(category="Plumber", location_code=1012873)

        assert len(client.cost_log) == 2
        assert all(r.cost >= 0 for r in client.cost_log)
        assert client.total_cost > 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_invalid_location_returns_error(self, mocker):
        client = _make_client()
        mocker.patch.object(client, "_post", return_value=ERROR_RESPONSE)

        result = await client.serp_organic(keyword="plumber", location_code=9999999)
        assert result.status == "error"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_server_error_retries_then_fails(self, mocker):
        client = _make_client()
        mocker.patch.object(
            client, "_raw_post", side_effect=Exception("Connection refused")
        )
        mocker.patch("asyncio.sleep", return_value=None)

        result = await client.serp_organic(keyword="plumber", location_code=1012873)
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_queued_endpoint_retries_then_fails(self, mocker):
        client = _make_client()
        mocker.patch.object(
            client, "_raw_post", side_effect=Exception("Connection refused")
        )
        mocker.patch("asyncio.sleep", return_value=None)

        result = await client.keyword_volume(keywords=["plumber"], location_code=1012873)
        assert result.status == "error"


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

class TestRateLimiting:
    def test_rate_limiter_exists(self):
        client = _make_client()
        assert client._rate_limiter is not None

    @pytest.mark.asyncio
    async def test_calls_within_rate_limit_proceed(self, mocker):
        """A small burst of calls should not be blocked."""
        client = _make_client()
        mocker.patch.object(
            client, "_post", return_value=BUSINESS_LISTINGS_RESPONSE
        )

        results = await asyncio.gather(
            *[
                client.business_listings(category="Plumber", location_code=1012873)
                for _ in range(5)
            ]
        )
        assert all(r.status == "ok" for r in results)
