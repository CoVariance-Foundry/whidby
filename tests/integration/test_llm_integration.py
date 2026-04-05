"""Integration tests for the LLM client (M3).

These hit the real Anthropic API. Requires ANTHROPIC_API_KEY env var.
Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import os

import pytest

from src.clients.llm.client import LLMClient


pytestmark = pytest.mark.integration


def _real_client() -> LLMClient:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return LLMClient(api_key=api_key)


class TestRealLLM:
    @pytest.mark.asyncio
    async def test_keyword_expansion(self):
        client = _real_client()
        result = await client.keyword_expansion("plumber")
        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert result.tokens_used > 0
        assert result.cost_usd > 0

    @pytest.mark.asyncio
    async def test_classify_intent(self):
        client = _real_client()
        intent = await client.classify_intent("plumber near me")
        assert isinstance(intent, str)
        assert len(intent) > 0

    @pytest.mark.asyncio
    async def test_generate(self):
        client = _real_client()
        result = await client.generate(
            system="You are a helpful assistant.",
            prompt="Say hello in exactly 3 words.",
            max_tokens=32,
        )
        assert result.success is True
        assert isinstance(result.data, str)
        assert len(result.data) > 0

    @pytest.mark.asyncio
    async def test_token_tracker(self):
        client = _real_client()
        await client.classify_intent("roof repair cost")
        assert client.tracker.total_tokens > 0
        assert client.tracker.total_cost_usd > 0
