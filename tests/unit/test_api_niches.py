"""Unit tests for the FastAPI /api/niches routes."""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.research_agent.api import app


class _FakeScoreResult:
    def __init__(self) -> None:
        self.report = {
            "report_id": "abc",
            "generated_at": "2026-04-20T00:00:00+00:00",
            "spec_version": "1.1",
            "input": {"niche_keyword": "roofing", "geo_scope": "city",
                      "geo_target": "Phoenix, AZ", "report_depth": "standard",
                      "strategy_profile": "balanced"},
            "keyword_expansion": {"niche": "roofing", "keywords": []},
            "metros": [{"cbsa_code": "38060", "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                         "population": 5000000,
                         "scores": {"demand": 70, "organic_competition": 40,
                                    "local_competition": 55, "monetization": 65,
                                    "ai_resilience": 80, "opportunity": 72,
                                    "confidence": 0.82},
                         "confidence": 0.82, "serp_archetype": "local_first",
                         "ai_exposure": "low", "difficulty_tier": "T2",
                         "signals": {}, "guidance": {}}],
            "meta": {"total_api_calls": 0, "total_cost_usd": 0.0,
                      "processing_time_seconds": 0.1, "feedback_log_id": "fb"},
        }
        self.opportunity_score = 72
        self.evidence = [{"category": "demand", "label": "x", "value": 1.0,
                           "source": "s", "is_available": True}]


def test_post_niches_score_dry_run_returns_report_and_opportunity(monkeypatch: Any) -> None:
    async def _fake_orchestrator(**kwargs: Any) -> _FakeScoreResult:
        assert kwargs["dry_run"] is True
        return _FakeScoreResult()

    with patch("src.research_agent.api.score_niche_for_metro", new=_fake_orchestrator), \
         patch("src.research_agent.api._persist_report", return_value="abc"):
        client = TestClient(app)
        res = client.post("/api/niches/score", json={
            "niche": "roofing", "city": "Phoenix", "state": "AZ", "dry_run": True,
        })
    assert res.status_code == 200
    body = res.json()
    assert body["report_id"] == "abc"
    assert body["opportunity_score"] == 72
    assert body["evidence"][0]["category"] == "demand"


def test_post_niches_score_validation_error_on_empty_city() -> None:
    client = TestClient(app)
    res = client.post("/api/niches/score", json={"niche": "roofing", "city": "", "state": "AZ"})
    assert res.status_code == 400


def test_get_niches_report_reads_from_supabase(monkeypatch: Any) -> None:
    fake_row = {
        "id": "abc", "niche_keyword": "roofing", "geo_target": "Phoenix, AZ",
        "metros": [{"cbsa_code": "38060", "scores": {"opportunity": 72}}],
        "created_at": "2026-04-20T00:00:00+00:00", "spec_version": "1.1",
        "keyword_expansion": {"keywords": []}, "meta": {}, "report_depth": "standard",
        "strategy_profile": "balanced", "geo_scope": "city",
    }
    with patch("src.research_agent.api._read_report_by_id", return_value=fake_row):
        client = TestClient(app)
        res = client.get("/api/niches/abc")
    assert res.status_code == 200
    body = res.json()
    assert body["report_id"] == "abc"
    assert body["input"]["niche_keyword"] == "roofing"
