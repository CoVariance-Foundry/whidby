"""Unit tests for the Supabase report persistence adapter."""
from __future__ import annotations

from typing import Any

from src.clients.supabase_persistence import (
    SupabasePersistence,
    build_report_row,
    build_keyword_rows,
    build_metro_signal_rows,
    build_metro_score_rows,
)


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
            "keywords": [
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
                    "confidence": 0.82, "resolved_weights": {"organic": 0.6, "local": 0.4},
                },
                "confidence": 0.82,
                "serp_archetype": "local_first",
                "ai_exposure": "low",
                "difficulty_tier": "T2",
                "signals": {"demand": {"tier_1_volume_effective": 4200}},
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


def test_build_report_row_maps_core_fields() -> None:
    row = build_report_row(_sample_report())
    assert row["id"] == "11111111-1111-1111-1111-111111111111"
    assert row["niche_keyword"] == "roofing"
    assert row["geo_scope"] == "city"
    assert row["geo_target"] == "Phoenix, AZ"
    assert row["strategy_profile"] == "balanced"
    assert row["feedback_log_id"] == "22222222-2222-2222-2222-222222222222"
    assert isinstance(row["metros"], list)


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


class _FakeTable:
    def __init__(self, sink: list[dict]) -> None:
        self.sink = sink

    def insert(self, payload: Any) -> "_FakeTable":
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

    def table(self, name: str) -> _FakeTable:
        self.tables.setdefault(name, [])
        return _FakeTable(self.tables[name])


def test_persist_report_writes_to_all_four_tables() -> None:
    fake = _FakeSupabase()
    adapter = SupabasePersistence(client=fake)
    report_id = adapter.persist_report(_sample_report())
    assert report_id == "11111111-1111-1111-1111-111111111111"
    assert len(fake.tables["reports"]) == 1
    assert len(fake.tables["report_keywords"]) == 1
    assert len(fake.tables["metro_signals"]) == 1
    assert len(fake.tables["metro_scores"]) == 1
