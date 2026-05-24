"""Unit tests for the Supabase report persistence adapter."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from src.clients.supabase_persistence import (
    SupabasePersistence,
    build_organic_competitor_fact_rows,
    build_local_pack_listing_fact_rows,
    build_report_row,
    build_keyword_rows,
    build_metro_signal_rows,
    build_metro_score_rows,
    build_metro_score_v2_rows,
    build_seo_fact_rows,
    build_seo_evidence_artifact_rows,
)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def _sample_report() -> dict[str, Any]:
    return {
        "report_id": "11111111-1111-1111-1111-111111111111",
        "generated_at": "2026-04-20T00:00:00+00:00",
        "spec_version": "1.1",
        "input": {
            "niche_keyword": "roofing",
            "geo_scope": "city",
            "geo_target": "Phoenix, AZ",
            "report_depth": "standard",
            "strategy_profile": "balanced",
        },
        "keyword_expansion": {
            "niche": "roofing",
            "expanded_keywords": [
                {"keyword": "roofing near me", "tier": 1, "intent": "transactional",
                 "source": "llm", "aio_risk": "low", "search_volume": 2000, "cpc": 12.5},
            ],
        },
        "metros": [
            {
                "cbsa_code": "38060",
                "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                "population": 5000000,
                "scores": {
                    "demand": 70, "organic_competition": 40, "local_competition": 55,
                    "monetization": 65, "ai_resilience": 80, "opportunity": 72,
                    "confidence": {"score": 82, "flags": []},
                    "resolved_weights": {"organic": 0.6, "local": 0.4},
                },
                "confidence": {"score": 82, "flags": []},
                "serp_archetype": "local_first",
                "ai_exposure": "low",
                "difficulty_tier": "T2",
                "signals": {
                    "demand": {"tier_1_volume_effective": 4200},
                    "organic_competition": {
                        "aio_present": True,
                        "aggregator_count": 3,
                        "local_biz_count": 4,
                        "avg_top5_da": 32.5,
                        "avg_top5_lighthouse": 74.25,
                        "top5_da_coverage": 0.8,
                        "top5_lighthouse_coverage": 0.6,
                        "top5_organic_data_confidence": "medium",
                        "featured_snippet_present": False,
                        "paa_count": 2,
                    },
                    "local_competition": {
                        "local_pack_present": True,
                        "local_pack_position": 2,
                        "top3_review_count_min": 25.0,
                        "top3_review_count_avg": 48.6,
                        "top3_review_velocity_avg": 3.25,
                        "top3_rating_avg": 4.6,
                    },
                    "monetization": {"ads_present": True, "lsa_present": False},
                    "ai_resilience": {"aio_trigger_rate": 0.1},
                },
                "guidance": {"strategy": "lead with local"},
            }
        ],
        "meta": {
            "total_api_calls": 12,
            "total_cost_usd": 0.18,
            "processing_time_seconds": 33.4,
            "feedback_log_id": "22222222-2222-2222-2222-222222222222",
        },
    }


def _sample_v2_report() -> dict[str, Any]:
    report = deepcopy(_sample_report())
    report["input"]["niche_keyword"] = " Roofing "
    report["metros"][0]["v2_scores"] = {
        "niche_normalized": "roof repair",
        "cbsa_code": "38060",
        "scores": {
            "demand_strength": {"value": 140, "higher_is_better": True},
            "organic_difficulty": {"value": 42, "higher_is_better": False},
            "local_difficulty": {"value": 36, "higher_is_better": False},
            "monetization_signal": {"value": 118, "higher_is_better": True},
            "ai_resilience": {"value": 77, "higher_is_better": True},
        },
        "benchmark": {
            "population_class": "metro_1m_5m",
            "confidence_label": "medium",
            "sample_size": 9,
        },
        "flags": {
            "no_local_pack_detected": False,
            "benchmark_undersampled": True,
            "cbp_data_missing": False,
        },
        "spec_version": "2.0",
    }
    return report


def _sample_competitor_report() -> dict[str, Any]:
    report = _sample_v2_report()
    report["raw_evidence_artifacts"] = [
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "provider": "dataforseo",
            "endpoint_path": "/v3/serp/google/maps/live/advanced",
            "evidence_family": "maps",
            "normalized_request_params": {
                "keyword": "roof repair phoenix",
                "location_code": 1000013,
            },
            "response_payload": {"tasks": [{"id": "task-1", "result_count": 2}]},
            "response_storage_uri": "s3://whidby-seo-evidence/maps/task-1.json",
            "cache_status": "miss",
            "cost_usd": 0.002,
            "collected_at": "2026-04-20T00:03:00+00:00",
            "source_window_start": "2026-04-01T00:00:00+00:00",
            "source_window_end": "2026-04-20T00:00:00+00:00",
        }
    ]
    report["metros"][0]["signals"]["organic_competition"]["top_organic_results"] = [
        {
            "keyword": "roof repair phoenix",
            "result_rank": 1,
            "title": "Phoenix Roof Repair Pros",
            "domain": "example-roofing.com",
            "url": "https://example-roofing.com/roof-repair",
            "domain_authority": 24.5,
            "backlinks_count": 320,
            "referring_domains_count": 42,
            "performance_score": 72,
            "has_localbusiness_schema": False,
            "schema_types": ["WebPage"],
            "title_keyword_match": True,
            "is_local_business": True,
            "snippet": "Emergency roof repair in Phoenix.",
        },
        {
            "keyword": "roof repair phoenix",
            "rank_group": 2,
            "title": "Yelp Roof Repair",
            "domain": "yelp.com",
            "url": "https://www.yelp.com/search?find_desc=roof+repair",
        },
    ]
    report["metros"][0]["signals"]["local_competition"]["top_local_pack_items"] = [
        {
            "keyword": "roof repair phoenix",
            "listing_rank": 1,
            "business_name": "Phoenix Roof Repair Pros",
            "cid": "1234567890123456789",
            "place_id": "ChIJroofrepairphoenix",
            "source_query": "roof repair phoenix",
            "location_code": 1000013,
            "result_type": "maps_search",
            "url": "https://www.google.com/maps?cid=1234567890123456789",
            "review_retrieval_mode": "cid",
            "review_window_start": "2026-04-01T00:00:00+00:00",
            "review_window_end": "2026-04-20T00:00:00+00:00",
            "upstream_result_at": "2026-04-20T00:03:00+00:00",
            "evidence_artifact_id": "33333333-3333-3333-3333-333333333333",
            "exact_match_name": True,
            "review_count": 88,
            "review_velocity_monthly": 4.25,
            "rating": 4.7,
            "gbp_completeness": 0.8,
            "photo_count": 12,
            "has_recent_post": True,
            "categories": ["Roofing contractor"],
        },
        {
            "keyword": "roof repair phoenix",
            "rank_group": 2,
            "title": "Desert Roofing",
            "rating": {"value": 4.4, "votes_count": 51},
            "category": "Roofing contractor",
            "total_photos": 8,
        },
    ]
    return report


def test_build_report_row_maps_core_fields() -> None:
    row = build_report_row(_sample_report())
    assert row["id"] == "11111111-1111-1111-1111-111111111111"
    assert row["niche_keyword"] == "roofing"
    assert row["geo_scope"] == "city"
    assert row["geo_target"] == "Phoenix, AZ"
    assert row["strategy_profile"] == "balanced"
    assert row["feedback_log_id"] == "22222222-2222-2222-2222-222222222222"
    assert isinstance(row["metros"], list)
    assert row["access_scope"] == "cached"
    assert row["owner_account_id"] is None


def test_build_report_row_maps_account_ownership() -> None:
    report = _sample_report()
    report["owner_account_id"] = "33333333-3333-3333-3333-333333333333"
    report["created_by_user_id"] = "44444444-4444-4444-4444-444444444444"
    report["access_scope"] = "account"
    row = build_report_row(report)
    assert row["owner_account_id"] == "33333333-3333-3333-3333-333333333333"
    assert row["created_by_user_id"] == "44444444-4444-4444-4444-444444444444"
    assert row["access_scope"] == "account"


def test_build_keyword_rows_one_per_keyword() -> None:
    rows = build_keyword_rows(_sample_report())
    assert len(rows) == 1
    assert rows[0]["keyword"] == "roofing near me"
    assert rows[0]["tier"] == 1
    assert rows[0]["report_id"] == "11111111-1111-1111-1111-111111111111"


def test_build_metro_signal_and_score_rows() -> None:
    signal_rows = build_metro_signal_rows(_sample_report())
    score_rows = build_metro_score_rows(_sample_report())
    assert len(signal_rows) == 1 and len(score_rows) == 1
    assert signal_rows[0]["cbsa_code"] == "38060"
    assert score_rows[0]["opportunity_score"] == 72


def test_build_metro_score_v2_rows_maps_score_vector() -> None:
    rows = build_metro_score_v2_rows(_sample_v2_report())
    assert rows == [
        {
            "report_id": "11111111-1111-1111-1111-111111111111",
            "niche_normalized": "roof repair",
            "cbsa_code": "38060",
            "serp_archetype": "local_first",
            "ai_exposure": "low",
            "spec_version": "2.0",
            "demand_strength": 140,
            "demand_strength_higher_is_better": True,
            "organic_difficulty": 42,
            "organic_difficulty_higher_is_better": False,
            "local_difficulty": 36,
            "local_difficulty_higher_is_better": False,
            "monetization_signal": 118,
            "monetization_signal_higher_is_better": True,
            "ai_resilience": 77,
            "ai_resilience_higher_is_better": True,
            "benchmark_population_class": "metro_1m_5m",
            "benchmark_confidence": "medium",
            "benchmark_sample_size": 9,
            "no_local_pack_detected": False,
            "benchmark_undersampled": True,
            "cbp_data_missing": False,
        }
    ]


def test_build_metro_score_v2_rows_returns_empty_without_v2_scores() -> None:
    assert build_metro_score_v2_rows(_sample_report()) == []


def test_build_seo_fact_rows_maps_schema_columns_only() -> None:
    rows = build_seo_fact_rows(_sample_v2_report())
    assert len(rows) == 1
    allowed_columns = {
        "niche_keyword",
        "niche_normalized",
        "cbsa_code",
        "keyword",
        "keyword_tier",
        "intent",
        "search_volume_monthly",
        "cpc_usd",
        "aio_present",
        "local_pack_present",
        "local_pack_position",
        "aggregator_count_top10",
        "local_biz_count_top10",
        "featured_snippet_present",
        "paa_count",
        "ads_present",
        "lsa_present",
        "top3_review_count_min",
        "top3_review_count_avg",
        "top3_review_velocity_avg",
        "top3_rating_avg",
        "avg_top5_da",
        "avg_top5_lighthouse",
        "top5_da_coverage",
        "top5_lighthouse_coverage",
        "top5_organic_data_confidence",
        "snapshot_date",
        "report_id",
        "source",
    }
    assert set(rows[0]) == allowed_columns
    assert rows[0]["niche_keyword"] == " Roofing "
    assert rows[0]["niche_normalized"] == "roof repair"
    assert rows[0]["keyword_tier"] == 1
    assert rows[0]["search_volume_monthly"] == 2000
    assert rows[0]["cpc_usd"] == 12.5
    assert rows[0]["snapshot_date"] == "2026-04-20"
    assert rows[0]["aggregator_count_top10"] == 3
    assert rows[0]["local_biz_count_top10"] == 4
    assert rows[0]["top3_review_count_min"] == 25
    assert rows[0]["top3_review_count_avg"] == 49
    assert rows[0]["avg_top5_da"] == 32.5
    assert rows[0]["avg_top5_lighthouse"] == 74.25
    assert rows[0]["top5_da_coverage"] == 0.8
    assert rows[0]["top5_lighthouse_coverage"] == 0.6
    assert rows[0]["top5_organic_data_confidence"] == "medium"
    assert rows[0]["source"] == "orchestrator"


def test_build_seo_fact_rows_preserves_missing_v2_facts_as_null() -> None:
    report = _sample_v2_report()
    local = report["metros"][0]["signals"]["local_competition"]
    organic = report["metros"][0]["signals"]["organic_competition"]
    local["top3_review_count_min"] = None
    local["top3_review_velocity_avg"] = None
    organic["avg_top5_da"] = None
    organic["avg_top5_lighthouse"] = None
    organic["top5_da_coverage"] = 0.0
    organic["top5_lighthouse_coverage"] = 0.0
    organic["top5_organic_data_confidence"] = "missing"

    rows = build_seo_fact_rows(report)

    assert rows[0]["top3_review_count_min"] is None
    assert rows[0]["top3_review_velocity_avg"] is None
    assert rows[0]["avg_top5_da"] is None
    assert rows[0]["avg_top5_lighthouse"] is None
    assert rows[0]["top5_da_coverage"] == 0.0
    assert rows[0]["top5_lighthouse_coverage"] == 0.0
    assert rows[0]["top5_organic_data_confidence"] == "missing"


def test_build_seo_fact_rows_uses_utc_snapshot_date() -> None:
    report = _sample_v2_report()
    report["generated_at"] = "2026-04-20T23:30:00-07:00"

    rows = build_seo_fact_rows(report)

    assert rows[0]["snapshot_date"] == "2026-04-21"


def test_build_seo_fact_rows_requires_snapshot_date_for_v2_rows() -> None:
    report = _sample_v2_report()
    report["generated_at"] = "not a date"

    with pytest.raises(ValueError, match="generated_at is required"):
        build_seo_fact_rows(report)


def test_build_seo_fact_rows_normalizes_keyword_tier_and_intent() -> None:
    report = _sample_v2_report()
    report["keyword_expansion"]["expanded_keywords"] = [
        {"keyword": "bad tier", "tier": "5", "intent": "navigational"},
        {"keyword": "missing metadata"},
        {"keyword": "commercial kw", "tier": "2", "intent": " Commercial "},
    ]

    rows = build_seo_fact_rows(report)

    assert [
        (row["keyword"], row["keyword_tier"], row["intent"])
        for row in rows
    ] == [
        ("bad tier", 3, "informational"),
        ("missing metadata", 3, "informational"),
        ("commercial kw", 2, "commercial"),
    ]


def test_build_seo_fact_rows_skips_legacy_metros_without_v2_scores() -> None:
    report = _sample_v2_report()
    legacy_metro = deepcopy(report["metros"][0])
    legacy_metro["cbsa_code"] = "99999"
    legacy_metro.pop("v2_scores")
    report["metros"].append(legacy_metro)

    rows = build_seo_fact_rows(report)

    assert len(rows) == 1
    assert rows[0]["cbsa_code"] == "38060"


def test_build_organic_competitor_fact_rows_maps_compact_signal_items() -> None:
    rows = build_organic_competitor_fact_rows(_sample_competitor_report())

    assert len(rows) == 2
    assert rows[0] == {
        "cbsa_code": "38060",
        "niche_normalized": "roof repair",
        "keyword": "roof repair phoenix",
        "result_rank": 1,
        "title": "Phoenix Roof Repair Pros",
        "domain": "example-roofing.com",
        "url": "https://example-roofing.com/roof-repair",
        "result_type": "organic",
        "domain_authority": 24.5,
        "backlinks_count": 320,
        "referring_domains_count": 42,
        "lighthouse_score": 72.0,
        "has_localbusiness_schema": False,
        "schema_types": ["WebPage"],
        "title_keyword_match": True,
        "is_aggregator": False,
        "is_local_business": True,
        "evidence": {"snippet": "Emergency roof repair in Phoenix."},
        "source": "dataforseo",
        "snapshot_date": "2026-04-20",
        "report_id": "11111111-1111-1111-1111-111111111111",
    }
    assert rows[1]["result_rank"] == 2
    assert rows[1]["domain"] == "yelp.com"
    assert rows[1]["is_aggregator"] is True


def test_build_local_pack_listing_fact_rows_maps_existing_fact_shape() -> None:
    rows = build_local_pack_listing_fact_rows(_sample_competitor_report())

    assert len(rows) == 2
    assert rows[0] == {
        "cbsa_code": "38060",
        "niche_normalized": "roof repair",
        "keyword": "roof repair phoenix",
        "listing_rank": 1,
        "business_name": "Phoenix Roof Repair Pros",
        "cid": "1234567890123456789",
        "place_id": "ChIJroofrepairphoenix",
        "source_query": "roof repair phoenix",
        "dataforseo_location_code": 1000013,
        "result_type": "maps_search",
        "listing_url": "https://www.google.com/maps?cid=1234567890123456789",
        "domain": "google.com",
        "review_retrieval_mode": "cid",
        "review_window_start": "2026-04-01T00:00:00+00:00",
        "review_window_end": "2026-04-20T00:00:00+00:00",
        "upstream_result_at": "2026-04-20T00:03:00+00:00",
        "evidence_artifact_id": "33333333-3333-3333-3333-333333333333",
        "exact_match_name": True,
        "review_count": 88,
        "review_velocity_monthly": 4.25,
        "rating": 4.7,
        "gbp_completeness": 0.8,
        "photo_count": 12,
        "has_recent_post": True,
        "categories": ["Roofing contractor"],
        "source": "dataforseo",
        "snapshot_date": "2026-04-20",
        "report_id": "11111111-1111-1111-1111-111111111111",
    }
    assert rows[1]["business_name"] == "Desert Roofing"
    assert rows[1]["cid"] is None
    assert rows[1]["place_id"] is None
    assert rows[1]["review_retrieval_mode"] is None
    assert rows[1]["review_count"] == 51
    assert rows[1]["rating"] == 4.4
    assert rows[1]["categories"] == ["Roofing contractor"]
    assert rows[0]["cid"] or rows[0]["place_id"]
    assert rows[0]["listing_url"] == "https://www.google.com/maps?cid=1234567890123456789"
    assert rows[0]["domain"] == "google.com"


def test_build_seo_evidence_artifact_rows_maps_and_hashes_provenance() -> None:
    report = _sample_competitor_report()

    rows = build_seo_evidence_artifact_rows(report)

    assert len(rows) == 1
    row = rows[0]
    normalized_params = {
        "keyword": "roof repair phoenix",
        "location_code": 1000013,
    }
    expected_request_hash = hashlib.sha256(
        json.dumps(
            {
                "provider": "dataforseo",
                "endpoint_path": "/v3/serp/google/maps/live/advanced",
                "normalized_request_params": normalized_params,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    expected_response_hash = hashlib.sha256(
        json.dumps(
            {"tasks": [{"id": "task-1", "result_count": 2}]},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert row["id"] == "33333333-3333-3333-3333-333333333333"
    assert row["provider"] == "dataforseo"
    assert row["endpoint_path"] == "/v3/serp/google/maps/live/advanced"
    assert row["evidence_family"] == "maps"
    assert row["normalized_request_params"] == normalized_params
    assert row["request_hash"] == expected_request_hash
    assert row["response_hash"] == expected_response_hash
    assert row["response_storage_uri"] == "s3://whidby-seo-evidence/maps/task-1.json"
    assert row["cache_status"] == "miss"
    assert row["cost_usd"] == 0.002
    assert row["collected_at"] == "2026-04-20T00:03:00+00:00"
    assert row["source_window_start"] == "2026-04-01T00:00:00+00:00"
    assert row["source_window_end"] == "2026-04-20T00:00:00+00:00"


def test_build_seo_evidence_artifact_rows_skips_incomplete_artifacts() -> None:
    report = {
        **_sample_v2_report(),
        "seo_evidence_artifacts": [
            {"endpoint_path": "/v3/serp/google/organic/live/advanced"},
            {"evidence_family": "serp"},
        ],
    }

    assert build_seo_evidence_artifact_rows(report) == []


def test_whi127_migration_adds_local_identifiers_and_evidence_artifacts() -> None:
    migration = (
        MIGRATIONS_DIR / "20260524135200_whi127_evidence_lineage.sql"
    ).read_text()

    assert "CREATE TABLE IF NOT EXISTS public.seo_evidence_artifacts" in migration
    assert "ALTER TABLE public.local_pack_listing_facts" in migration
    for column in (
        "cid TEXT",
        "place_id TEXT",
        "source_query TEXT",
        "dataforseo_location_code INTEGER",
        "result_type TEXT",
        "listing_url TEXT",
        "domain TEXT",
        "review_retrieval_mode TEXT",
        "review_window_start TIMESTAMPTZ",
        "review_window_end TIMESTAMPTZ",
        "upstream_result_at TIMESTAMPTZ",
        "evidence_artifact_id UUID",
    ):
        assert column in migration
    assert "idx_local_pack_listing_facts_cid" in migration
    assert "idx_local_pack_listing_facts_place_id" in migration
    assert "REFERENCES public.seo_evidence_artifacts(id) ON DELETE SET NULL" in migration
    assert "UNIQUE (provider, endpoint_path, request_hash)" in migration
    assert "jsonb_typeof(normalized_request_params) = 'object'" in migration
    assert "ALTER TABLE public.seo_evidence_artifacts ENABLE ROW LEVEL SECURITY" in migration
    assert "FOR ALL TO service_role USING (true) WITH CHECK (true)" in migration
    for evidence_family in (
        "serp",
        "maps",
        "reviews",
        "backlinks",
        "lighthouse",
        "keyword_volume",
        "keyword_overview",
    ):
        assert evidence_family in migration
    for cache_status in ("hit", "miss", "bypass", "replay", "unknown"):
        assert cache_status in migration


def test_competitor_fact_builders_require_snapshot_date_only_when_rows_exist() -> None:
    report = _sample_competitor_report()
    report["generated_at"] = "not a date"

    with pytest.raises(ValueError, match="organic_competitor_facts"):
        build_organic_competitor_fact_rows(report)

    with pytest.raises(ValueError, match="local_pack_listing_facts"):
        build_local_pack_listing_fact_rows(report)


class _FakeTable:
    def __init__(self, sink: list[dict], calls: list[dict[str, Any]], name: str) -> None:
        self.sink = sink
        self.calls = calls
        self.name = name

    def insert(self, payload: Any) -> "_FakeTable":
        self.calls.append({"table": self.name, "method": "insert", "payload": payload})
        if isinstance(payload, list):
            self.sink.extend(payload)
        else:
            self.sink.append(payload)
        return self

    def upsert(self, payload: Any, **kwargs: Any) -> "_FakeTable":
        self.calls.append(
            {"table": self.name, "method": "upsert", "payload": payload, "kwargs": kwargs}
        )
        if isinstance(payload, list):
            self.sink.extend(payload)
        else:
            self.sink.append(payload)
        return self

    def execute(self) -> Any:
        class _R:
            data = self.sink
        return _R()


class _FakeSupabase:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {}
        self.calls: list[dict[str, Any]] = []

    def table(self, name: str) -> _FakeTable:
        self.tables.setdefault(name, [])
        return _FakeTable(self.tables[name], self.calls, name)


class _FakeTableWithoutUpsert:
    def __init__(self, sink: list[dict], calls: list[dict[str, Any]], name: str) -> None:
        self.sink = sink
        self.calls = calls
        self.name = name

    def insert(self, payload: Any) -> "_FakeTableWithoutUpsert":
        self.calls.append({"table": self.name, "method": "insert", "payload": payload})
        if isinstance(payload, list):
            self.sink.extend(payload)
        else:
            self.sink.append(payload)
        return self

    def execute(self) -> Any:
        class _R:
            data = self.sink
        return _R()


class _FakeSupabaseWithoutSeoFactsUpsert(_FakeSupabase):
    def table(self, name: str) -> _FakeTable | _FakeTableWithoutUpsert:
        self.tables.setdefault(name, [])
        if name == "seo_facts":
            return _FakeTableWithoutUpsert(self.tables[name], self.calls, name)
        return _FakeTable(self.tables[name], self.calls, name)


def test_persist_report_writes_to_all_six_tables_when_v2_data_exists() -> None:
    fake = _FakeSupabase()
    adapter = SupabasePersistence(client=fake)
    report_id = adapter.persist_report(_sample_v2_report())
    assert report_id == "11111111-1111-1111-1111-111111111111"
    assert len(fake.tables["reports"]) == 1
    assert len(fake.tables["report_keywords"]) == 1
    assert len(fake.tables["metro_signals"]) == 1
    assert len(fake.tables["metro_scores"]) == 1
    assert len(fake.tables["metro_score_v2"]) == 1
    assert len(fake.tables["seo_facts"]) == 1
    score_v2_call = next(
        call
        for call in fake.calls
        if call["table"] == "metro_score_v2" and call["method"] == "upsert"
    )
    assert score_v2_call["kwargs"] == {"on_conflict": "report_id,cbsa_code"}
    fact_call = next(
        call
        for call in fake.calls
        if call["table"] == "seo_facts" and call["method"] == "upsert"
    )
    assert fact_call["kwargs"] == {
        "on_conflict": "niche_normalized,cbsa_code,keyword,snapshot_date"
    }


def test_persist_report_upserts_competitor_read_model_facts() -> None:
    fake = _FakeSupabase()
    adapter = SupabasePersistence(client=fake)

    adapter.persist_report(_sample_competitor_report())

    assert len(fake.tables["seo_evidence_artifacts"]) == 1
    assert len(fake.tables["organic_competitor_facts"]) == 2
    assert len(fake.tables["local_pack_listing_facts"]) == 2
    evidence_call = next(
        call
        for call in fake.calls
        if call["table"] == "seo_evidence_artifacts" and call["method"] == "upsert"
    )
    assert evidence_call["kwargs"] == {
        "on_conflict": "provider,endpoint_path,request_hash"
    }
    organic_call = next(
        call
        for call in fake.calls
        if call["table"] == "organic_competitor_facts" and call["method"] == "upsert"
    )
    assert organic_call["kwargs"] == {
        "on_conflict": "cbsa_code,niche_normalized,keyword,result_rank,result_type,snapshot_date"
    }
    local_pack_call = next(
        call
        for call in fake.calls
        if call["table"] == "local_pack_listing_facts" and call["method"] == "upsert"
    )
    assert local_pack_call["kwargs"] == {
        "on_conflict": "cbsa_code,niche_normalized,keyword,listing_rank,snapshot_date"
    }


def test_persist_report_still_works_for_legacy_report_without_v2_scores() -> None:
    fake = _FakeSupabase()
    adapter = SupabasePersistence(client=fake)
    report_id = adapter.persist_report(_sample_report())
    assert report_id == "11111111-1111-1111-1111-111111111111"
    assert "metro_score_v2" not in fake.tables
    assert "seo_facts" not in fake.tables


def test_persist_report_requires_upsert_for_seo_facts() -> None:
    fake = _FakeSupabaseWithoutSeoFactsUpsert()
    adapter = SupabasePersistence(client=fake)

    with pytest.raises(RuntimeError, match="lacks upsert"):
        adapter.persist_report(_sample_v2_report())

    assert not any(call["method"] == "insert" for call in fake.calls)
    assert not any(
        call["table"] == "seo_facts" and call["method"] == "insert"
        for call in fake.calls
    )


def test_persist_report_validates_v2_facts_before_partial_writes() -> None:
    fake = _FakeSupabase()
    adapter = SupabasePersistence(client=fake)
    report = _sample_v2_report()
    report["generated_at"] = None

    with pytest.raises(ValueError, match="generated_at is required"):
        adapter.persist_report(report)

    assert fake.calls == []
    assert fake.tables == {}
