"""Unit tests for M8 guidance generation behavior."""

from __future__ import annotations

import pytest

from src.classification.guidance_generator import classify_and_generate_guidance
from src.clients.llm.types import LLMResult
from tests.fixtures.m8_classification_fixtures import (
    build_ai_exposed_input,
    build_local_pack_vulnerable_input,
)


class FakeSuccessfulLLMClient:
    """Simple async fake for successful guidance refinement."""

    async def generate(self, **_: object) -> LLMResult:
        return LLMResult(success=True, data="Focus first on high-intent service pages and local conversion assets.")


class FakeFailingLLMClient:
    """Simple async fake for failed guidance refinement."""

    async def generate(self, **_: object) -> LLMResult:
        return LLMResult(success=False, error="timeout")


@pytest.mark.asyncio
async def test_guidance_generator_renders_niche_and_metro_context() -> None:
    data = build_local_pack_vulnerable_input()
    result = await classify_and_generate_guidance(data, FakeSuccessfulLLMClient())
    strategy = result["guidance"]["strategy"]
    assert "plumber" in strategy
    assert "Phoenix, AZ" in strategy
    assert result["guidance"]["guidance_status"] == "generated"


@pytest.mark.asyncio
async def test_guidance_generator_changes_output_for_different_archetypes() -> None:
    local_pack_data = build_local_pack_vulnerable_input()
    aggregator_data = build_local_pack_vulnerable_input()
    aggregator_data["signals"]["organic_competition"]["aggregator_count"] = 7

    local_pack_result = await classify_and_generate_guidance(local_pack_data, FakeSuccessfulLLMClient())
    aggregator_result = await classify_and_generate_guidance(aggregator_data, FakeSuccessfulLLMClient())

    assert local_pack_result["serp_archetype"] != aggregator_result["serp_archetype"]
    assert local_pack_result["guidance"]["headline"] != aggregator_result["guidance"]["headline"]


@pytest.mark.asyncio
async def test_guidance_generator_sets_ai_note_for_moderate_or_exposed() -> None:
    data = build_ai_exposed_input()
    result = await classify_and_generate_guidance(data, FakeSuccessfulLLMClient())
    assert result["ai_exposure"] == "AI_EXPOSED"
    assert result["guidance"]["ai_resilience_note"] is not None


@pytest.mark.asyncio
async def test_guidance_generator_falls_back_on_llm_failure() -> None:
    data = build_local_pack_vulnerable_input()
    result = await classify_and_generate_guidance(data, FakeFailingLLMClient())
    assert result["guidance"]["guidance_status"] == "fallback_template"
    assert result["metadata"]["guidance_fallback_reason"] == "timeout"


class FakeContradictoryLLMClient:
    """Async fake returning text that contradicts an EASY difficulty tier."""

    async def generate(self, **_: object) -> LLMResult:
        return LLMResult(success=True, data="This market is very hard and not recommended for entry.")


@pytest.mark.asyncio
async def test_guidance_generator_guardrail_rejects_contradictory_llm_text() -> None:
    data = build_local_pack_vulnerable_input()
    data["scores"]["organic_competition"] = 80.0
    data["scores"]["local_competition"] = 75.0
    result = await classify_and_generate_guidance(data, FakeContradictoryLLMClient())
    assert result["guidance"]["guidance_status"] == "fallback_template"
    assert result["metadata"]["guidance_fallback_reason"] is not None
    assert "contradiction_guardrail" in result["metadata"]["guidance_fallback_reason"]


@pytest.mark.asyncio
async def test_guidance_generator_rejects_missing_required_signal_section() -> None:
    data = build_local_pack_vulnerable_input()
    del data["signals"]["ai_resilience"]
    with pytest.raises(ValueError, match="ai_resilience"):
        await classify_and_generate_guidance(data, FakeSuccessfulLLMClient())


@pytest.mark.asyncio
async def test_guidance_generator_rejects_missing_nested_numeric_field() -> None:
    data = build_local_pack_vulnerable_input()
    del data["signals"]["organic_competition"]["aggregator_count"]
    with pytest.raises(ValueError, match="aggregator_count"):
        await classify_and_generate_guidance(data, FakeSuccessfulLLMClient())


@pytest.mark.asyncio
async def test_guidance_generator_rejects_non_numeric_score_value() -> None:
    data = build_local_pack_vulnerable_input()
    data["scores"]["organic_competition"] = "not-a-number"
    with pytest.raises(ValueError, match="organic_competition"):
        await classify_and_generate_guidance(data, FakeSuccessfulLLMClient())
