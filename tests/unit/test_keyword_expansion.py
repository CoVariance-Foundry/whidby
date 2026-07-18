"""Unit tests for M4 keyword expansion orchestration."""

import asyncio
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
    assert (
        result["actionable_keywords"] + result["informational_keywords_excluded"]
        <= result["total_keywords"]
    )


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


@pytest.mark.asyncio
async def test_llm_and_dfs_sources_overlap() -> None:
    llm_started = asyncio.Event()
    dfs_started = asyncio.Event()

    class OverlapLLM(FakeLLMClient):
        observed_peer = False

        async def keyword_expansion(self, niche: str):
            llm_started.set()
            await asyncio.wait_for(dfs_started.wait(), timeout=0.1)
            self.observed_peer = True
            return await super().keyword_expansion(niche)

    class OverlapDFS(FakeDataForSEOClient):
        observed_peer = False

        async def keyword_suggestions(self, **kwargs):
            dfs_started.set()
            await asyncio.wait_for(llm_started.wait(), timeout=0.1)
            self.observed_peer = True
            return await super().keyword_suggestions(**kwargs)

    llm = OverlapLLM()
    dfs = OverlapDFS()

    result = await expand_keywords("plumber", llm_client=llm, dataforseo_client=dfs)

    assert result["total_keywords"] > 0
    assert llm.observed_peer is True
    assert dfs.observed_peer is True


@pytest.mark.asyncio
async def test_opaque_dfs_suggestions_do_not_fan_out_to_llm_classifier() -> None:
    class CountingLLM(FakeLLMClient):
        classify_calls = 0

        async def classify_intent(self, query: str) -> str:
            self.classify_calls += 1
            return await super().classify_intent(query)

    llm = CountingLLM()
    dfs = FakeDataForSEOClient(keywords=[f"opaque candidate {index}" for index in range(50)])

    result = await expand_keywords("plumber", llm_client=llm, dataforseo_client=dfs)

    assert result["total_keywords"] == 50
    assert llm.classify_calls == 0


@pytest.mark.asyncio
async def test_source_timeout_returns_seed_keyword_with_low_confidence(monkeypatch) -> None:
    class HangingLLM:
        async def keyword_expansion(self, _niche: str):
            await asyncio.Event().wait()

    class HangingDFS:
        async def keyword_suggestions(self, **_kwargs):
            await asyncio.Event().wait()

    monkeypatch.setattr(
        "src.pipeline.keyword_expansion.M4_INTERACTIVE_TIMEOUT_SECONDS",
        0.01,
        raising=False,
    )

    result = await asyncio.wait_for(
        expand_keywords(
            "  Plumber  ",
            llm_client=HangingLLM(),
            dataforseo_client=HangingDFS(),
        ),
        timeout=0.1,
    )

    assert result["expansion_confidence"] == "low"
    assert result["expanded_keywords"] == [
        {
            "keyword": "plumber",
            "tier": 1,
            "intent": "commercial",
            "source": "input",
            "aio_risk": "moderate",
            "actionable": True,
        }
    ]
