"""Unit tests for the LLM client (M3).

All tests use mocked Anthropic responses — no API key required.
Covers: keyword expansion, intent classification, error handling,
token tracking, output parsing.
"""

from __future__ import annotations

import pytest

from src.clients.llm.client import LLMClient
from tests.fixtures.llm_fixtures import (
    AUDIT_COPY_TEXT,
    INTENT_INFORMATIONAL_JSON,
    INTENT_TRANSACTIONAL_JSON,
    KEYWORD_EXPANSION_JSON,
    MALFORMED_JSON,
    make_anthropic_message,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_llm(mocker, response_text: str) -> LLMClient:
    """Create an LLMClient with a mocked Anthropic messages.create call."""
    client = LLMClient(api_key="sk-test-fake")
    msg = make_anthropic_message(response_text)
    mocker.patch.object(
        client._anthropic.messages, "create", return_value=msg
    )
    return client


# ---------------------------------------------------------------------------
# Keyword Expansion
# ---------------------------------------------------------------------------

class TestKeywordExpansion:
    @pytest.mark.asyncio
    async def test_returns_valid_schema(self, mocker):
        client = _mock_llm(mocker, KEYWORD_EXPANSION_JSON)
        result = await client.keyword_expansion(niche="plumber")

        assert result.success is True
        assert "expanded_keywords" in result.data
        for kw in result.data["expanded_keywords"]:
            assert "tier" in kw
            assert "intent" in kw
            assert kw["intent"] in ("transactional", "commercial", "informational")

    @pytest.mark.asyncio
    async def test_tracks_tokens(self, mocker):
        client = _mock_llm(mocker, KEYWORD_EXPANSION_JSON)
        await client.keyword_expansion(niche="plumber")

        assert client.tracker.total_tokens > 0
        assert client.tracker.total_cost_usd > 0


# ---------------------------------------------------------------------------
# Intent Classification
# ---------------------------------------------------------------------------

class TestIntentClassification:
    @pytest.mark.asyncio
    async def test_transactional(self, mocker):
        client = _mock_llm(mocker, INTENT_TRANSACTIONAL_JSON)
        result = await client.classify_intent("emergency plumber near me")
        assert result == "transactional"

    @pytest.mark.asyncio
    async def test_informational(self, mocker):
        client = _mock_llm(mocker, INTENT_INFORMATIONAL_JSON)
        result = await client.classify_intent("how to fix a leaky faucet")
        assert result == "informational"


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_malformed_json_returns_error(self, mocker):
        client = _mock_llm(mocker, MALFORMED_JSON)
        result = await client.keyword_expansion(niche="plumber")
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_api_exception_returns_error(self, mocker):
        client = LLMClient(api_key="sk-test-fake")
        mocker.patch.object(
            client._anthropic.messages, "create", side_effect=Exception("API down")
        )
        result = await client.keyword_expansion(niche="plumber")
        assert result.success is False
        assert "API down" in result.error


# ---------------------------------------------------------------------------
# Free-form Generation (audit copy)
# ---------------------------------------------------------------------------

class TestGeneration:
    @pytest.mark.asyncio
    async def test_generate_returns_text(self, mocker):
        client = _mock_llm(mocker, AUDIT_COPY_TEXT)
        result = await client.generate(
            system="You are a local SEO audit writer.",
            prompt="Write a brief audit summary for Joe's Plumbing.",
        )
        assert result.success is True
        assert isinstance(result.data, str)
        assert len(result.data) > 0


# ---------------------------------------------------------------------------
# Token Tracker
# ---------------------------------------------------------------------------

class TestTokenTracker:
    @pytest.mark.asyncio
    async def test_multiple_calls_accumulate(self, mocker):
        client = _mock_llm(mocker, KEYWORD_EXPANSION_JSON)
        await client.keyword_expansion(niche="plumber")
        await client.keyword_expansion(niche="electrician")

        assert client.tracker.call_count == 2
        assert client.tracker.total_tokens > 0
