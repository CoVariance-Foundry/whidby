"""Unit tests for M4 keyword expansion orchestration."""

from copy import deepcopy

import pytest

from src.pipeline.keyword_expansion import expand_keywords
from tests.fixtures.keyword_expansion_fixtures import (
    LLM_EXPANSION_PAYLOAD,
    FakeDataForSEOClient,
    FakeLLMClient,
)


@pytest.mark.asyncio
async def test_returns_non_empty_result_with_required_fields() -> None:
    llm = FakeLLMClient()
    dfs = FakeDataForSEOClient()
    result = await expand_keywords("plumber", llm_client=llm, dataforseo_client=dfs)

    assert result["niche"] == "plumber"
    assert result["total_keywords"] > 0
    assert "expanded_keywords" in result
    assert result["actionable_keywords"] + result["informational_keywords_excluded"] <= result["total_keywords"]


@pytest.mark.asyncio
async def test_deduplicates_format_variants() -> None:
    payload = deepcopy(LLM_EXPANSION_PAYLOAD)
    payload["expanded_keywords"].append(
        {
            "keyword": "plumber near me!!!",
            "tier": 1,
            "intent": "transactional",
            "source": "llm",
            "aio_risk": "low",
        }
    )
    llm = FakeLLMClient(expansion_payload=payload)
    dfs = FakeDataForSEOClient(keywords=["plumber near me "])
    result = await expand_keywords("plumber", llm_client=llm, dataforseo_client=dfs)

    keywords = [kw["keyword"] for kw in result["expanded_keywords"]]
    assert keywords.count("plumber near me") == 1


@pytest.mark.asyncio
async def test_valid_intent_tier_and_aio_for_every_keyword() -> None:
    llm = FakeLLMClient()
    dfs = FakeDataForSEOClient()
    result = await expand_keywords("plumber", llm_client=llm, dataforseo_client=dfs)

    allowed_intents = {"transactional", "commercial", "informational"}
    allowed_tiers = {1, 2, 3}
    allowed_risk = {"low", "moderate", "high"}
    for keyword in result["expanded_keywords"]:
        assert keyword["intent"] in allowed_intents
        assert keyword["tier"] in allowed_tiers
        assert keyword["aio_risk"] in allowed_risk


@pytest.mark.asyncio
async def test_informational_keywords_are_not_actionable() -> None:
    llm = FakeLLMClient()
    dfs = FakeDataForSEOClient()
    result = await expand_keywords("plumber", llm_client=llm, dataforseo_client=dfs)

    informational = [kw for kw in result["expanded_keywords"] if kw["intent"] == "informational"]
    assert result["informational_keywords_excluded"] == len(informational)
    assert all(kw["actionable"] is False for kw in informational)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("dfs_keywords", "expected"),
    [
        (
            [
                "plumber near me",
                "emergency plumber",
                "how to fix a leaky faucet",
            ],
            "high",
        ),
        (["plumber near me", "emergency plumber"], "medium"),
        (["totally unrelated keyword"], "low"),
    ],
)
async def test_confidence_threshold_mapping(dfs_keywords: list[str], expected: str) -> None:
    llm = FakeLLMClient()
    dfs = FakeDataForSEOClient(keywords=dfs_keywords)
    result = await expand_keywords("plumber", llm_client=llm, dataforseo_client=dfs)
    assert result["expansion_confidence"] == expected


@pytest.mark.asyncio
async def test_identical_input_produces_deterministic_order() -> None:
    llm = FakeLLMClient()
    dfs = FakeDataForSEOClient()

    first = await expand_keywords("plumber", llm_client=llm, dataforseo_client=dfs)
    second = await expand_keywords("plumber", llm_client=llm, dataforseo_client=dfs)
    assert first == second


@pytest.mark.asyncio
async def test_partial_source_failure_returns_low_confidence_structured_output() -> None:
    llm = FakeLLMClient()
    dfs = FakeDataForSEOClient(raise_on_suggestions=True)
    result = await expand_keywords("plumber", llm_client=llm, dataforseo_client=dfs)

    assert result["total_keywords"] > 0
    assert result["expansion_confidence"] == "low"
    assert isinstance(result["expanded_keywords"], list)


@pytest.mark.asyncio
async def test_contract_shape_and_counter_reconciliation() -> None:
    llm = FakeLLMClient()
    dfs = FakeDataForSEOClient()
    result = await expand_keywords("plumber", llm_client=llm, dataforseo_client=dfs)

    required_top = {
        "niche",
        "expanded_keywords",
        "total_keywords",
        "actionable_keywords",
        "informational_keywords_excluded",
        "expansion_confidence",
    }
    assert set(result.keys()) == required_top
    assert result["total_keywords"] == len(result["expanded_keywords"])
