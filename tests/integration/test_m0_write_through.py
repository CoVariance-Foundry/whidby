"""Integration test: M0 write-through observation store.

Requires a live Supabase instance with observations table and Storage bucket.
Run with: pytest tests/integration/test_m0_write_through.py -v -m integration
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def supabase_client():
    """Create a Supabase client from environment variables."""
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        pytest.skip("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")

    from supabase import create_client

    return create_client(url, key)


@pytest.fixture
def dfs_client_with_store(supabase_client):
    """Create a DataForSEOClient with ObservationStore attached."""
    login = os.environ.get("DATAFORSEO_LOGIN", "")
    password = os.environ.get("DATAFORSEO_PASSWORD", "")
    if not login or not password:
        pytest.skip("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD required")

    from src.clients.dataforseo.client import DataForSEOClient
    from src.clients.dataforseo.observation_store import ObservationStore

    store = ObservationStore(supabase_client=supabase_client, bucket_name="observations")
    return DataForSEOClient(login=login, password=password, observation_store=store)


@pytest.mark.asyncio
async def test_api_call_creates_observation(dfs_client_with_store, supabase_client):
    """First call creates an observation row and uploads payload to Storage."""
    resp = await dfs_client_with_store.keyword_suggestions(
        keyword="plumber",
        limit=5,
    )
    assert resp.status == "ok"
    assert resp.cost > 0 or resp.cached

    from src.clients.dataforseo.query_hash import compute_query_hash

    qhash = compute_query_hash(
        "dataforseo_labs/google/keyword_suggestions/live",
        {
            "keyword": "plumber",
            "location_name": "United States",
            "language_code": "en",
            "limit": 5,
        },
    )

    rows = (
        supabase_client.table("observations")
        .select("*")
        .eq("query_hash", qhash)
        .order("observed_at", desc=True)
        .limit(1)
        .execute()
    ).data

    assert len(rows) >= 1
    obs = rows[0]
    assert obs["status"] == "ok"
    assert obs["storage_path"] is not None


@pytest.mark.asyncio
async def test_second_call_is_cache_hit(dfs_client_with_store):
    """Second identical call within TTL returns cached data at zero cost."""
    resp1 = await dfs_client_with_store.keyword_suggestions(keyword="plumber", limit=5)
    assert resp1.status == "ok"

    resp2 = await dfs_client_with_store.keyword_suggestions(keyword="plumber", limit=5)
    assert resp2.status == "ok"
    assert resp2.cached is True
    assert resp2.cost == 0
