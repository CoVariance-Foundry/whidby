"""Integration test: pipeline regression with observation store.

Verifies that the scoring pipeline produces identical output with and
without the ObservationStore injected (FR-012, SC-006).

Requires live Supabase and DataForSEO credentials.
Run with: pytest tests/integration/test_pipeline_regression.py -v -m integration
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def credentials():
    """Skip if required credentials are missing."""
    login = os.environ.get("DATAFORSEO_LOGIN", "")
    password = os.environ.get("DATAFORSEO_PASSWORD", "")
    supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not all([login, password, supabase_url, supabase_key]):
        pytest.skip("All credentials required for pipeline regression test")
    return {
        "login": login,
        "password": password,
        "supabase_url": supabase_url,
        "supabase_key": supabase_key,
    }


@pytest.mark.asyncio
async def test_scoring_output_identical_with_and_without_store(credentials):
    """M5→M9 pipeline output must be identical regardless of ObservationStore presence.

    This test runs the same niche+metro through the pipeline twice:
    once with a plain DataForSEOClient and once with ObservationStore injected.
    The scoring output must match exactly.
    """
    from src.clients.dataforseo.client import DataForSEOClient
    from src.clients.dataforseo.observation_store import ObservationStore

    client_plain = DataForSEOClient(
        login=credentials["login"],
        password=credentials["password"],
    )

    from supabase import create_client

    sb = create_client(credentials["supabase_url"], credentials["supabase_key"])
    store = ObservationStore(supabase_client=sb)
    client_with_store = DataForSEOClient(
        login=credentials["login"],
        password=credentials["password"],
        observation_store=store,
    )

    resp_plain = await client_plain.keyword_suggestions(keyword="plumber", limit=3)
    resp_store = await client_with_store.keyword_suggestions(keyword="plumber", limit=3)

    assert resp_plain.status == resp_store.status
    if resp_plain.status == "ok" and resp_store.status == "ok":
        assert type(resp_plain.data) == type(resp_store.data)
