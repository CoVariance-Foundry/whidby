"""Live integration smoke: one small niche, one metro, real APIs.

Tests the full M4→M9 pipeline against live DataForSEO + Anthropic APIs.
Skipped when credentials are not set. Marked with @pytest.mark.integration
so default pytest runs skip it.
"""

from __future__ import annotations

import os

import pytest

from src.clients.dataforseo.client import DataForSEOClient
from src.clients.llm.client import LLMClient
from src.pipeline.orchestrator import score_niche_for_metro

pytestmark = pytest.mark.integration


def _get_real_dfs_client() -> DataForSEOClient:
    """Return a real DataForSEO client or skip the test."""
    login = os.environ.get("DATAFORSEO_LOGIN", "")
    password = os.environ.get("DATAFORSEO_PASSWORD", "")
    if not login or not password:
        pytest.skip("DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD not set")
    return DataForSEOClient(login=login, password=password)


@pytest.mark.skipif(
    not all(os.getenv(k) for k in ("DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD", "ANTHROPIC_API_KEY")),
    reason="live API credentials required",
)
class TestOrchestrator:
    """Live end-to-end orchestrator tests against real APIs."""

    @pytest.mark.asyncio
    async def test_end_to_end_roofing_phoenix(self) -> None:
        """Smoke test: score roofing niche in Phoenix, AZ with live APIs."""
        dfs = _get_real_dfs_client()
        llm = LLMClient()
        result = await score_niche_for_metro(
            niche="roofing",
            city="Phoenix",
            state="AZ",
            llm_client=llm,
            dataforseo_client=dfs,
        )
        assert 0 <= result.opportunity_score <= 100
        assert result.report["metros"][0]["cbsa_name"].lower().startswith("phoenix")

    @pytest.mark.asyncio
    async def test_end_to_end_plumbing_denver(self) -> None:
        """Smoke test: score plumbing niche in Denver, CO with live APIs."""
        dfs = _get_real_dfs_client()
        llm = LLMClient()
        result = await score_niche_for_metro(
            niche="plumbing",
            city="Denver",
            state="CO",
            llm_client=llm,
            dataforseo_client=dfs,
        )
        assert 0 <= result.opportunity_score <= 100
        assert result.report["metros"][0]["cbsa_name"].lower().startswith("denver")

    @pytest.mark.asyncio
    async def test_unknown_metro_raises_error(self) -> None:
        """Verify unknown metro raises ValueError."""
        dfs = _get_real_dfs_client()
        llm = LLMClient()
        with pytest.raises(ValueError, match="no CBSA match"):
            await score_niche_for_metro(
                niche="roofing",
                city="NonExistentCity",
                state="ZZ",
                llm_client=llm,
                dataforseo_client=dfs,
            )
