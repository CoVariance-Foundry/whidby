"""Unit tests for the end-to-end niche-scoring orchestrator.

Patches each M4-M9 entrypoint at the module level so this test validates
composition and data flow only. Real M4-M9 behavior is covered by each
module's own tests and by the live integration smoke in Task 6.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from src.pipeline.orchestrator import ScoreNicheResult, score_niche_for_metro
from src.pipeline.types import MetroCollectionResult, RawCollectionResult, RunMetadata


_FAKE_KEYWORD_EXPANSION = {
    "niche": "roofing",
    "keywords": [
        {"keyword": "roofing near me", "tier": 1, "intent": "transactional",
         "source": "llm", "aio_risk": "low", "search_volume": 2000, "cpc": 12.5},
    ],
}

_FAKE_RAW_COLLECTION = RawCollectionResult(
    metros={
        "38060": MetroCollectionResult(
            metro_id="38060",
            serp_organic=[], serp_maps=[], keyword_volume=[],
            backlinks=[], lighthouse=[], google_reviews=[],
            gbp_info=[], business_listings=[],
        )
    },
    meta=RunMetadata(
        total_api_calls=8, total_cost_usd=0.12, collection_time_seconds=3.1,
    ),
)

_FAKE_SIGNALS = {
    "demand": {"tier_1_volume_effective": 4200},
    "organic_competition": {"median_top10_dr": 45},
    "local_competition": {"gbp_saturation": 0.6},
    "ai_resilience": {"aio_rate": 0.1},
    "monetization": {"median_cpc": 12.5},
}

_FAKE_SCORES = {
    "demand": 70, "organic_competition": 40, "local_competition": 55,
    "monetization": 65, "ai_resilience": 80, "opportunity": 72,
    "confidence": 0.82, "resolved_weights": {"organic": 0.6, "local": 0.4},
}

# classify_serp_archetype returns (archetype, rule_id) — match the real signature
_FAKE_SERP_ARCHETYPE_RESULT = ("local_first", "fallback_mixed")

# compute_difficulty_tier returns (tier, combined_comp, resolved_weights)
_FAKE_DIFFICULTY_RESULT = ("T2", 55.0, {"organic": 0.6, "local": 0.4})

# classify_and_generate_guidance returns a ClassificationGuidanceBundle dict
_FAKE_GUIDANCE_BUNDLE = {
    "serp_archetype": "local_first",
    "ai_exposure": "low",
    "difficulty_tier": "T2",
    "guidance": {"strategy": "lead local"},
    "metadata": {
        "serp_rule_id": "fallback_mixed",
        "difficulty_inputs": {
            "organic_competition": 40.0,
            "local_competition": 55.0,
            "resolved_weights": {"organic": 0.6, "local": 0.4},
        },
        "guidance_fallback_reason": None,
    },
}


def test_score_niche_for_metro_composes_pipeline_and_returns_result() -> None:
    with patch("src.pipeline.orchestrator.expand_keywords",
               new=AsyncMock(return_value=_FAKE_KEYWORD_EXPANSION)), \
         patch("src.pipeline.orchestrator.collect_data",
               new=AsyncMock(return_value=_FAKE_RAW_COLLECTION)), \
         patch("src.pipeline.orchestrator.extract_signals",
               return_value=_FAKE_SIGNALS), \
         patch("src.pipeline.orchestrator.compute_scores",
               return_value=_FAKE_SCORES), \
         patch("src.pipeline.orchestrator.classify_ai_exposure", return_value="low"), \
         patch("src.pipeline.orchestrator.classify_serp_archetype",
               return_value=_FAKE_SERP_ARCHETYPE_RESULT), \
         patch("src.pipeline.orchestrator.compute_difficulty_tier",
               return_value=_FAKE_DIFFICULTY_RESULT), \
         patch("src.pipeline.orchestrator.classify_and_generate_guidance",
               new=AsyncMock(return_value=_FAKE_GUIDANCE_BUNDLE)):
        result = asyncio.run(
            score_niche_for_metro(
                niche="roofing",
                city="Phoenix",
                state="AZ",
                strategy_profile="balanced",
                llm_client=object(),
                dataforseo_client=object(),
            )
        )

    assert isinstance(result, ScoreNicheResult)
    assert result.report["spec_version"] == "1.1"
    assert result.report["input"]["niche_keyword"] == "roofing"
    assert result.report["input"]["geo_target"] == "Phoenix, AZ"
    assert len(result.report["metros"]) == 1
    metro = result.report["metros"][0]
    assert metro["cbsa_code"] == "38060"
    assert metro["ai_exposure"] == "low"
    assert metro["serp_archetype"] == "local_first"
    assert metro["difficulty_tier"] == "T2"
    assert result.opportunity_score == 72
    assert len(result.evidence) == 4
    categories = {e["category"] for e in result.evidence}
    assert categories == {"demand", "competition", "monetization", "ai_resilience"}


def test_score_niche_raises_valueerror_on_unknown_city() -> None:
    import pytest
    with pytest.raises(ValueError, match="no CBSA match"):
        asyncio.run(
            score_niche_for_metro(
                niche="roofing",
                city="Atlantis",
                state="AZ",
                llm_client=object(),
                dataforseo_client=object(),
            )
        )
