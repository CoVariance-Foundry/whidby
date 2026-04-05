"""Optional live integration test for M4 keyword expansion."""

from __future__ import annotations

import os

import pytest

from src.clients.dataforseo.client import DataForSEOClient
from src.clients.llm.client import LLMClient
from src.pipeline.keyword_expansion import expand_keywords


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_keyword_expansion_returns_structured_output() -> None:
    """Run only when API credentials are available."""
    if not all(
        [
            os.environ.get("ANTHROPIC_API_KEY"),
            os.environ.get("DATAFORSEO_LOGIN"),
            os.environ.get("DATAFORSEO_PASSWORD"),
        ]
    ):
        pytest.skip("Missing API credentials for live integration test.")

    llm = LLMClient()
    dfs = DataForSEOClient(
        login=os.environ["DATAFORSEO_LOGIN"],
        password=os.environ["DATAFORSEO_PASSWORD"],
    )
    result = await expand_keywords("plumber", llm_client=llm, dataforseo_client=dfs)
    assert result["total_keywords"] > 0
    assert len(result["expanded_keywords"]) == result["total_keywords"]
