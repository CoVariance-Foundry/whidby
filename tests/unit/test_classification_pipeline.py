"""Integration-flavored unit tests for M8 bundle orchestration."""

from __future__ import annotations

import pytest

from src.classification.guidance_generator import classify_and_generate_guidance
from src.clients.llm.types import LLMResult
from tests.fixtures.m8_classification_fixtures import (
    build_aggregator_dominated_input,
    build_ai_exposed_input,
    build_barren_input,
    build_hard_profile_input,
    build_local_pack_vulnerable_input,
)


class FakeSuccessfulLLMClient:
    """Simple async fake for successful guidance generation."""

    async def generate(self, **_: object) -> LLMResult:
        return LLMResult(success=True, data="Keep execution focused on high-intent terms and GBP quality.")


@pytest.mark.asyncio
async def test_classification_pipeline_returns_contract_shape() -> None:
    result = await classify_and_generate_guidance(
        build_local_pack_vulnerable_input(),
        FakeSuccessfulLLMClient(),
    )
    assert set(result.keys()) == {
        "serp_archetype",
        "ai_exposure",
        "difficulty_tier",
        "guidance",
        "metadata",
    }
    assert set(result["guidance"].keys()) == {
        "headline",
        "strategy",
        "priority_actions",
        "ai_resilience_note",
        "guidance_status",
    }


@pytest.mark.asyncio
async def test_classification_pipeline_emits_one_valid_enum_per_classification() -> None:
    fixtures = [
        build_local_pack_vulnerable_input(),
        build_aggregator_dominated_input(),
        build_barren_input(),
        build_ai_exposed_input(),
        build_hard_profile_input(),
    ]
    valid_archetypes = {
        "AGGREGATOR_DOMINATED",
        "LOCAL_PACK_FORTIFIED",
        "LOCAL_PACK_ESTABLISHED",
        "LOCAL_PACK_VULNERABLE",
        "FRAGMENTED_WEAK",
        "FRAGMENTED_COMPETITIVE",
        "BARREN",
        "MIXED",
    }
    valid_exposures = {"AI_SHIELDED", "AI_MINIMAL", "AI_MODERATE", "AI_EXPOSED"}
    valid_tiers = {"EASY", "MODERATE", "HARD", "VERY_HARD"}

    for fixture in fixtures:
        result = await classify_and_generate_guidance(fixture, FakeSuccessfulLLMClient())
        assert result["serp_archetype"] in valid_archetypes
        assert result["ai_exposure"] in valid_exposures
        assert result["difficulty_tier"] in valid_tiers


@pytest.mark.asyncio
async def test_classification_pipeline_tracks_rule_and_difficulty_metadata() -> None:
    result = await classify_and_generate_guidance(
        build_aggregator_dominated_input(),
        FakeSuccessfulLLMClient(),
    )
    metadata = result["metadata"]
    assert metadata["serp_rule_id"]
    assert set(metadata["difficulty_inputs"].keys()) == {
        "organic_competition",
        "local_competition",
        "resolved_weights",
    }


@pytest.mark.asyncio
async def test_classification_pipeline_rejects_missing_signals_section() -> None:
    data = build_local_pack_vulnerable_input()
    del data["signals"]
    with pytest.raises(ValueError, match="signals"):
        await classify_and_generate_guidance(data, FakeSuccessfulLLMClient())


@pytest.mark.asyncio
async def test_classification_pipeline_rejects_missing_scores_field() -> None:
    data = build_local_pack_vulnerable_input()
    del data["scores"]["local_competition"]
    with pytest.raises(ValueError, match="local_competition"):
        await classify_and_generate_guidance(data, FakeSuccessfulLLMClient())
