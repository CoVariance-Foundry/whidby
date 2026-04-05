"""Unit tests for M4 intent classification rules and fallback precedence."""

import pytest

from src.pipeline.intent_classifier import (
    aio_risk_for_intent,
    classify_keyword_intent,
    infer_intent_from_rules,
    is_actionable_intent,
)
from tests.fixtures.keyword_expansion_fixtures import FakeLLMClient


def test_infer_intent_from_rules() -> None:
    assert infer_intent_from_rules("how to unclog a drain") == "informational"
    assert infer_intent_from_rules("emergency plumber near me") == "transactional"
    assert infer_intent_from_rules("best plumber in phoenix") == "commercial"


@pytest.mark.asyncio
async def test_precedence_prefers_valid_llm_intent() -> None:
    llm = FakeLLMClient(classify_map={"plumber phoenix": "transactional"})
    result = await classify_keyword_intent("plumber phoenix", llm_client=llm, llm_intent="informational")
    assert result == "informational"


@pytest.mark.asyncio
async def test_fallback_calls_llm_then_defaults_to_commercial() -> None:
    llm = FakeLLMClient(classify_map={"plumber phoenix": "transactional"})
    result = await classify_keyword_intent("plumber phoenix", llm_client=llm, llm_intent=None)
    assert result == "transactional"

    llm_error = FakeLLMClient(raise_on_classify=True)
    fallback = await classify_keyword_intent("plumber phoenix", llm_client=llm_error, llm_intent=None)
    assert fallback == "commercial"


def test_aio_risk_and_actionable_policy() -> None:
    assert aio_risk_for_intent("transactional") == "low"
    assert aio_risk_for_intent("commercial") == "moderate"
    assert aio_risk_for_intent("informational") == "high"

    assert is_actionable_intent("transactional") is True
    assert is_actionable_intent("commercial") is True
    assert is_actionable_intent("informational") is False
