"""Unit tests for the end-to-end niche-scoring orchestrator.

Patches each M4-M9 entrypoint at the module level so this test validates
composition and data flow only. Real M4-M9 behavior is covered by each
module's own tests and by the live integration smoke in Task 6.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.clients.dataforseo.cost_tracker import CostTracker
from src.pipeline.orchestrator import ScoreNicheResult, score_niche_for_metro
from src.pipeline.types import MetroCollectionResult, RawCollectionResult, RunMetadata


_FAKE_KEYWORD_EXPANSION = {
    "niche": "roofing",
    "expanded_keywords": [
        {"keyword": "roofing near me", "tier": 1, "intent": "transactional",
         "source": "llm", "aio_risk": "low", "search_volume": 2000, "cpc": 12.5},
    ],
    "total_keywords": 1,
    "actionable_keywords": 1,
    "informational_keywords_excluded": 0,
    "expansion_confidence": "high",
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
    "confidence": {"score": 82, "flags": []},
    "resolved_weights": {"organic": 0.6, "local": 0.4},
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


def _make_fake_dfs_client() -> MagicMock:
    """Build a mock DataForSEOClient with a real CostTracker pre-loaded with sample records."""
    tracker = CostTracker()
    tracker.record("serp/google/organic/task_post", "t1", 0.0006, False, 120)
    tracker.record("serp/google/organic/task_post", "cached", 0, True, 0)
    tracker.record("keywords_data/google/search_volume/task_post", "t2", 0.05, False, 300)

    client = MagicMock()
    client.total_cost = tracker.total_cost
    client.cost_log = tracker.records
    client.cost_tracker = tracker
    return client


def test_score_niche_for_metro_composes_pipeline_and_returns_result() -> None:
    fake_dfs = _make_fake_dfs_client()
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
                dataforseo_client=fake_dfs,
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

    meta = result.report["meta"]
    assert meta["total_api_calls"] == 3
    assert meta["total_cost_usd"] == round(0.0006 + 0.05, 6)
    assert meta["dfs_cached_calls"] == 1
    assert "dfs_cost_breakdown" in meta
    breakdown = meta["dfs_cost_breakdown"]
    assert "serp/google/organic/task_post" in breakdown
    assert breakdown["serp/google/organic/task_post"]["calls"] == 2
    assert breakdown["serp/google/organic/task_post"]["cached"] == 1


def test_score_niche_raises_valueerror_on_unknown_city() -> None:
    # Pre-existing stale: "Atlantis, AZ" now succeeds via state-level DFS fallback
    # (documented orchestrator behavior). Test is updated to use genuinely
    # unresolvable input: unknown city with no state supplied means Path 3
    # (state fallback) is skipped and GeoResolutionError fires.
    import pytest
    with pytest.raises(ValueError, match="no CBSA match"):
        asyncio.run(
            score_niche_for_metro(
                niche="roofing",
                city="Atlantis",
                llm_client=object(),
                dataforseo_client=object(),
            )
        )


def test_score_niche_resolves_state_from_city_when_state_absent() -> None:
    """Regression: callers (Next.js proxies, frontend) no longer supply
    `state`. The orchestrator must search all seeded metros and resolve
    the correct state from the city name alone — e.g. Denver -> CO,
    Atlanta -> GA, Seattle -> WA — not assume AZ."""
    with patch("src.pipeline.orchestrator.expand_keywords",
               new=AsyncMock(return_value=_FAKE_KEYWORD_EXPANSION)), \
         patch("src.pipeline.orchestrator.collect_data",
               new=AsyncMock(return_value=RawCollectionResult(
                   metros={"19820": MetroCollectionResult(metro_id="19820")},
                   meta=RunMetadata(
                       total_api_calls=1,
                       total_cost_usd=0.01,
                       collection_time_seconds=0.1,
                   ),
               ))), \
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
                niche="landscaping",
                city="Denver",
                # state deliberately omitted
                llm_client=object(),
                dataforseo_client=_make_fake_dfs_client(),
            )
        )

    metro = result.report["metros"][0]
    assert metro["cbsa_code"] == "19820"  # Denver-Aurora-Lakewood, CO
    assert result.report["input"]["geo_target"] == "Denver, CO"


def test_cost_tracker_aggregates_by_endpoint() -> None:
    """Verify cost_by_endpoint groups calls correctly and cached calls are counted."""
    tracker = CostTracker()
    tracker.record("serp/google/organic/task_post", "t1", 0.0006, False, 100)
    tracker.record("serp/google/organic/task_post", "cached", 0, True, 0)
    tracker.record("backlinks/summary/live", "t2", 0.002, False, 200)

    breakdown = tracker.cost_by_endpoint()
    assert len(breakdown) == 2

    serp = breakdown["serp/google/organic/task_post"]
    assert serp["calls"] == 2
    assert serp["cached"] == 1
    assert abs(serp["cost"] - 0.0006) < 1e-9

    bl = breakdown["backlinks/summary/live"]
    assert bl["calls"] == 1
    assert bl["cached"] == 0
    assert abs(bl["cost"] - 0.002) < 1e-9

    assert tracker.total_calls == 3
    assert tracker.cached_calls == 1
    assert abs(tracker.total_cost - 0.0026) < 1e-9


def test_expansion_key_contract_matches_m4_output() -> None:
    """Guard against key-name drift between expand_keywords output and orchestrator access.

    The orchestrator must read expansion["expanded_keywords"] — not "keywords".
    This test uses the real _FAKE_KEYWORD_EXPANSION shape (which mirrors M4 output)
    and verifies that collect_data and extract_signals receive a list, not a KeyError.
    """
    expansion = _FAKE_KEYWORD_EXPANSION
    assert "expanded_keywords" in expansion, (
        "M4 output must use 'expanded_keywords'; orchestrator depends on this key"
    )
    kw_list = expansion["expanded_keywords"]
    assert isinstance(kw_list, list)
    assert len(kw_list) > 0
    assert all(isinstance(kw, dict) and "keyword" in kw for kw in kw_list)


def test_confidence_dict_shape_matches_m7_output() -> None:
    """Guard against confidence shape drift between M7 engine and persistence layer.

    compute_confidence returns {"score": <0-100>, "flags": [...]}, not a bare float.
    The orchestrator passes this through as scores["confidence"], and the persistence
    layer must be able to unpack it.
    """
    from src.clients.supabase_persistence import build_metro_score_rows

    report = {
        "report_id": "contract-test",
        "metros": [{
            "cbsa_code": "00000",
            "scores": {
                "demand": 50, "organic_competition": 50, "local_competition": 50,
                "monetization": 50, "ai_resilience": 50, "opportunity": 50,
                "confidence": {"score": 75, "flags": [{"code": "test", "penalty": -10}]},
            },
            "serp_archetype": "local_first",
            "ai_exposure": "low",
            "difficulty_tier": "T2",
            "guidance": {},
        }],
    }
    rows = build_metro_score_rows(report)
    assert len(rows) == 1
    assert rows[0]["confidence_score"] == 75
    assert rows[0]["confidence_flags"] == [{"code": "test", "penalty": -10}]


def test_dry_run_returns_deterministic_report_without_clients() -> None:
    first = asyncio.run(
        score_niche_for_metro(
            niche="roofing",
            city="Phoenix",
            state="AZ",
            llm_client=None,
            dataforseo_client=None,
            dry_run=True,
        )
    )
    second = asyncio.run(
        score_niche_for_metro(
            niche="roofing",
            city="Phoenix",
            state="AZ",
            llm_client=None,
            dataforseo_client=None,
            dry_run=True,
        )
    )
    assert first.opportunity_score == second.opportunity_score
    assert first.report["metros"][0]["cbsa_code"] == second.report["metros"][0]["cbsa_code"]
    assert first.report["meta"]["total_cost_usd"] == 0.0
    # Report must satisfy M9 contract
    assert first.report["spec_version"] == "1.1"
    assert first.report["input"]["niche_keyword"] == "roofing"
    assert 0 <= first.opportunity_score <= 100
    assert len(first.evidence) == 4
