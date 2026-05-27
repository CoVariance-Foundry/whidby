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
from src.scoring.benchmark_repository import SeoBenchmarkCell


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


class _FakeBenchmarkRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get(self, *, niche_normalized: str, population_class: str) -> SeoBenchmarkCell | None:
        self.calls.append((niche_normalized, population_class))
        return SeoBenchmarkCell.from_mapping(
            {
                "niche_normalized": niche_normalized,
                "naics_code": "238160",
                "population_class": population_class,
                "median_total_volume_per_capita": 0.002,
                "median_avg_cpc": 10.0,
                "median_top3_review_count_min": 40,
                "median_top3_review_velocity": 3.0,
                "median_aggregator_count": 2.0,
                "median_local_biz_count": 5.0,
                "median_establishments_per_100k": 50.0,
                "median_lsa_present_rate": 0.2,
                "median_ads_present_rate": 0.5,
                "median_aio_trigger_rate": 0.1,
                "sample_size_metros": 12,
                "sample_size_observations": 100,
                "confidence_label": "medium",
            }
        )


class _FakeCityDataProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def get_business_density(self, city_id: str, naics: str | None = None) -> dict[str, int]:
        self.calls.append((city_id, naics))
        return {"establishments": 350}


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
    assert "population" not in metro["signals"]
    assert "population_class" not in metro["signals"]
    assert "v2_scores" not in metro
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
    assert "seo_evidence_artifacts" not in result.report
    assert result.seo_evidence_artifacts == []


def test_score_niche_emits_private_artifacts_for_current_run_only() -> None:
    fake_dfs = _make_fake_dfs_client()

    async def collect_with_current_cost(*args, **kwargs):
        fake_dfs.cost_tracker.record(
            "serp/google/maps/live/advanced",
            "maps-other-request",
            0.002,
            False,
            90,
            {"keyword": "roofing near me", "location_code": 1012873},
            collected_at="2026-05-24T14:00:00+00:00",
            collection_context_id="score-other",
            response_hash="maps-other-hash",
        )
        fake_dfs.cost_tracker.record(
            "serp/google/maps/live/advanced",
            "maps-current",
            0.002,
            False,
            110,
            {"keyword": "roofing near me", "location_code": 1012873},
            collected_at="2026-05-24T14:00:01+00:00",
            response_hash="maps-current-hash",
        )
        fake_dfs.cost_tracker.record(
            "backlinks/summary/live",
            "backlinks-current",
            0.002,
            False,
            80,
            {"target": "example.com"},
            collected_at="2026-05-24T14:00:02+00:00",
            response_hash="backlinks-current-hash",
        )
        fake_dfs.cost_tracker.record(
            "business_data/google/reviews/task_post",
            "reviews-other",
            0.005,
            False,
            300,
            {"cid": "cid-current", "location_code": 1012873},
            collected_at="2026-05-24T14:00:03+00:00",
            collection_context_id="score-other",
            response_hash="reviews-other-hash",
        )
        fake_dfs.cost_tracker.record(
            "business_data/google/reviews/task_post",
            "reviews-current",
            0.005,
            False,
            320,
            {"cid": "cid-current", "location_code": 1012873},
            collected_at="2026-05-24T14:00:04+00:00",
            response_hash="reviews-current-hash",
        )
        fake_dfs.cost_log = fake_dfs.cost_tracker.records
        return RawCollectionResult(
            metros={
                "38060": MetroCollectionResult(
                    metro_id="38060",
                    serp_organic=[
                        {
                            "keyword": "roofing near me",
                            "items": [
                                {
                                    "domain": "example.com",
                                    "url": "https://example.com",
                                }
                            ],
                        }
                    ],
                    serp_maps=[
                        {
                            "keyword": "roofing near me",
                            "items": [
                                {
                                    "type": "maps_search",
                                    "title": "Current Roof",
                                    "cid": "cid-current",
                                }
                            ],
                        }
                    ],
                    keyword_volume=[],
                    backlinks=[],
                    lighthouse=[],
                    google_reviews=[],
                    gbp_info=[],
                    business_listings=[],
                )
            },
            meta=RunMetadata(
                total_api_calls=3,
                total_cost_usd=0.006,
                collection_time_seconds=0.2,
            ),
        )

    with patch("src.pipeline.orchestrator.expand_keywords",
               new=AsyncMock(return_value=_FAKE_KEYWORD_EXPANSION)), \
         patch("src.pipeline.orchestrator.collect_data",
               new=AsyncMock(side_effect=collect_with_current_cost)), \
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

    assert "seo_evidence_artifacts" not in result.report
    assert [artifact["evidence_family"] for artifact in result.seo_evidence_artifacts] == [
        "maps",
        "backlinks",
        "reviews",
    ]
    assert result.seo_evidence_artifacts[0]["endpoint_path"] == (
        "serp/google/maps/live/advanced"
    )
    assert result.seo_evidence_artifacts[0]["request_hash"]
    assert result.seo_evidence_artifacts[0]["response_hash"] == "maps-current-hash"
    assert all(
        artifact["response_hash"] not in {"maps-other-hash", "reviews-other-hash"}
        for artifact in result.seo_evidence_artifacts
    )


def test_score_niche_emits_private_local_pack_listing_facts_from_raw_maps() -> None:
    fake_dfs = _make_fake_dfs_client()
    raw = RawCollectionResult(
        metros={
            "38060": MetroCollectionResult(
                metro_id="38060",
                serp_organic=[],
                serp_maps=[
                    {
                        "keyword": "roofing near me",
                        "datetime": "2026-05-24T13:59:00+00:00",
                        "items": [
                            {
                                "type": "maps_search",
                                "rank_group": 1,
                                "title": "Phoenix Roof Pros",
                                "cid": "cid-1",
                                "place_id": "place-1",
                                "url": "https://phoenixroof.example/maps",
                                "rating": {"value": 4.7, "votes_count": 88},
                            },
                            {
                                "type": "maps_search",
                                "rank_group": 2,
                                "title": "Second Roof",
                                "place_id": "place-2",
                            },
                        ],
                    }
                ],
                keyword_volume=[],
                backlinks=[],
                lighthouse=[],
                google_reviews=[
                    {
                        "cid": "cid-1",
                        "business_name": "Phoenix Roof Pros",
                        "review_retrieval_mode": "cid",
                        "review_timestamps": [
                            "2026-05-01T00:00:00+00:00",
                            "2026-05-20T00:00:00+00:00",
                        ],
                    }
                ],
                gbp_info=[],
                business_listings=[],
            )
        },
        meta=RunMetadata(total_api_calls=1, total_cost_usd=0.002, collection_time_seconds=0.2),
    )

    async def collect_with_maps_cost(*args, **kwargs):
        fake_dfs.cost_tracker.record(
            "serp/google/maps/live/advanced",
            "maps-current",
            0.002,
            False,
            110,
            {"keyword": "roofing near me", "location_code": 1012873},
            collected_at="2026-05-24T14:00:01+00:00",
            response_hash="maps-current-hash",
        )
        fake_dfs.cost_log = fake_dfs.cost_tracker.records
        return raw

    with patch("src.pipeline.orchestrator.expand_keywords",
               new=AsyncMock(return_value=_FAKE_KEYWORD_EXPANSION)), \
         patch("src.pipeline.orchestrator.collect_data",
               new=AsyncMock(side_effect=collect_with_maps_cost)), \
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

    assert "local_pack_listing_facts" not in result.report
    first = result.local_pack_listing_facts[0]
    assert first["cbsa_code"] == "38060"
    assert first["cid"] == "cid-1"
    assert first["place_id"] == "place-1"
    assert first["source_query"] == "roofing near me"
    assert first["dataforseo_location_code"] == 1012873
    assert first["listing_url"] == "https://phoenixroof.example/maps"
    assert first["domain"] == "phoenixroof.example"
    assert first["upstream_result_at"] == "2026-05-24T13:59:00+00:00"
    assert first["review_retrieval_mode"] == "cid"
    assert first["review_window_start"] == "2026-05-01T00:00:00+00:00"
    assert first["review_window_end"] == "2026-05-20T00:00:00+00:00"
    maps_artifact = result.seo_evidence_artifacts[0]
    assert maps_artifact["evidence_family"] == "maps"
    assert first["evidence_artifact_id"] == maps_artifact["id"]


def test_score_niche_for_metro_attaches_v2_scores_when_repository_is_provided() -> None:
    fake_dfs = _make_fake_dfs_client()
    repo = _FakeBenchmarkRepository()
    city_provider = _FakeCityDataProvider()
    signals = {
        "demand": {
            "total_search_volume": 2_000,
            "avg_cpc": 12.0,
            "transactional_ratio": 0.7,
            "effective_search_volume": 99_999,
        },
        "organic_competition": {
            "aggregator_count": 2.0,
            "local_biz_count": 5.0,
            "avg_top5_da": 30.0,
            "median_top10_dr": 45,
        },
        "local_competition": {
            "local_pack_present": True,
            "top3_review_count_min": 60,
            "review_velocity_avg": 4.5,
            "gbp_saturation": 0.6,
        },
        "monetization": {
            "lsa_present": True,
            "ads_present": True,
            "median_cpc": 12.5,
        },
        "ai_resilience": {
            "aio_trigger_rate": 0.08,
            "transactional_keyword_ratio": 0.7,
            "local_fulfillment_required": 1.0,
            "paa_density": 2.0,
        },
    }

    with patch("src.pipeline.orchestrator.expand_keywords",
               new=AsyncMock(return_value=_FAKE_KEYWORD_EXPANSION)), \
         patch("src.pipeline.orchestrator.collect_data",
               new=AsyncMock(return_value=_FAKE_RAW_COLLECTION)), \
         patch("src.pipeline.orchestrator.extract_signals",
               return_value=signals), \
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
                benchmark_repository=repo,
                city_data_provider=city_provider,
            )
        )

    assert repo.calls == [("roofing", "metro_1m_5m")]
    assert city_provider.calls == [("38060", "238160")]
    metro = result.report["metros"][0]
    assert metro["v2_scores"]["spec_version"] == "2.0"
    assert metro["v2_scores"]["benchmark"]["confidence_label"] == "medium"
    assert metro["v2_scores"]["scores"]["demand_strength"]["value"] == 17
    assert metro["v2_scores"]["scores"]["monetization_signal"]["value"] == 32
    assert metro["v2_scores"]["flags"]["cbp_data_missing"] is False
    assert "opportunity" in metro["scores"]
    assert "population" not in metro["signals"]
    assert "population_class" not in metro["signals"]
    assert "cbp_establishments" not in metro["signals"]


def test_score_niche_preserves_explicit_production_cbsa_target() -> None:
    fake_dfs = _make_fake_dfs_client()
    repo = _FakeBenchmarkRepository()
    city_provider = _FakeCityDataProvider()
    collect = AsyncMock(
        return_value=RawCollectionResult(
            metros={"47380": MetroCollectionResult(metro_id="47380")},
            meta=RunMetadata(
                total_api_calls=1,
                total_cost_usd=0.01,
                collection_time_seconds=0.1,
            ),
        )
    )

    with patch("src.pipeline.orchestrator.expand_keywords",
               new=AsyncMock(return_value=_FAKE_KEYWORD_EXPANSION)), \
         patch("src.pipeline.orchestrator.collect_data", new=collect), \
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
                city="Waco",
                state="TX",
                dataforseo_location_code=1026822,
                cbsa_code="47380",
                cbsa_name="Waco, TX",
                population=299_217,
                llm_client=object(),
                dataforseo_client=fake_dfs,
                benchmark_repository=repo,
                city_data_provider=city_provider,
            )
        )

    assert collect.await_args.kwargs["metros"] == [
        {
            "metro_id": "47380",
            "location_code": 1026822,
            "principal_city": "Waco",
        }
    ]
    assert repo.calls == [("roofing", "medium_100_300k")]
    assert city_provider.calls == [("47380", "238160")]
    metro = result.report["metros"][0]
    assert metro["cbsa_code"] == "47380"
    assert metro["cbsa_name"] == "Waco, TX"
    assert metro["population"] == 299_217
    assert metro["v2_scores"]["cbsa_code"] == "47380"


def test_score_niche_requires_positive_population_for_explicit_cbsa_target() -> None:
    import pytest

    for invalid_population in (None, 0):
        with pytest.raises(ValueError, match="positive population"):
            asyncio.run(
                score_niche_for_metro(
                    niche="roofing",
                    city="Waco",
                    state="TX",
                    dataforseo_location_code=1026822,
                    cbsa_code="47380",
                    cbsa_name="Waco, TX",
                    population=invalid_population,
                    llm_client=object(),
                    dataforseo_client=_make_fake_dfs_client(),
                    benchmark_repository=_FakeBenchmarkRepository(),
                )
            )


def test_v2_population_class_derives_from_population_when_signal_missing() -> None:
    from src.pipeline.orchestrator import _population_class_for_benchmarks

    assert _population_class_for_benchmarks(49_999) == "micro_under_50k"
    assert _population_class_for_benchmarks(50_000) == "small_50_100k"
    assert _population_class_for_benchmarks(100_000) == "medium_100_300k"
    assert _population_class_for_benchmarks(300_000) == "large_300k_1m"
    assert _population_class_for_benchmarks(1_000_000) == "metro_1m_5m"
    assert _population_class_for_benchmarks(5_000_000) == "mega_5m_plus"
    assert _population_class_for_benchmarks(0) is None


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


def test_cost_tracker_flush_keeps_api_usage_log_shape() -> None:
    class _Table:
        def __init__(self) -> None:
            self.rows: list[dict[str, object]] = []

        def insert(self, rows):
            self.rows = rows
            return self

        def execute(self):
            return None

    class _Client:
        def __init__(self) -> None:
            self.table_obj = _Table()

        def table(self, name: str) -> _Table:
            assert name == "api_usage_log"
            return self.table_obj

    tracker = CostTracker()
    tracker.record(
        "serp/google/maps/live/advanced",
        "maps-1",
        0.002,
        False,
        100,
        {"keyword": "roofing"},
        collected_at="2026-05-24T14:00:00+00:00",
        response_hash="private-hash",
    )
    client = _Client()

    assert tracker.flush_to_supabase("11111111-1111-1111-1111-111111111111", client=client) == 1
    assert set(client.table_obj.rows[0]) == {
        "endpoint",
        "task_id",
        "cost",
        "cached",
        "latency_ms",
        "parameters",
        "report_id",
    }


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


def test_dry_run_attaches_v2_scores_when_repository_is_provided() -> None:
    repo = _FakeBenchmarkRepository()

    result = asyncio.run(
        score_niche_for_metro(
            niche="roofing",
            city="Phoenix",
            state="AZ",
            llm_client=None,
            dataforseo_client=None,
            benchmark_repository=repo,
            dry_run=True,
        )
    )

    assert repo.calls == [("roofing", "metro_1m_5m")]
    metro = result.report["metros"][0]
    assert metro["cbsa_code"] == "38060"
    assert "opportunity" in metro["scores"]
    assert metro["v2_scores"]["spec_version"] == "2.0"
    assert metro["v2_scores"]["benchmark"]["confidence_label"] == "medium"
