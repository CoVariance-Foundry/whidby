"""Unit tests for strategy discovery FastAPI contracts."""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.domain.entities import City, Market, ScoredMarket, Service
from src.research_agent.api import app

BOISE = City(city_id="boise-id", name="Boise", state="ID", population=235_000)
PLUMBING = Service(service_id="plumbing", name="Plumbing", fulfillment_type="physical")
SIGNALS: dict[str, dict[str, Any]] = {
    "demand": {"score": 78.0},
    "organic_competition": {"score": 66.0},
    "local_competition": {"score": 54.0},
    "monetization": {"score": 70.0},
    "ai_resilience": {"score": 82.0},
}


def test_get_strategies_returns_launch_catalog_and_modifier() -> None:
    client = TestClient(app)

    resp = client.get("/api/strategies")

    assert resp.status_code == 200
    data = resp.json()
    strategies = data["strategies"]
    strategy_ids = [strategy["strategy_id"] for strategy in strategies]
    assert strategy_ids == [
        "easy_win",
        "gbp_blitz",
        "keyword_hijack",
        "expand_conquer",
        "cash_cow",
    ]
    statuses = {strategy["strategy_id"]: strategy["status"] for strategy in strategies}
    assert statuses["easy_win"] == "launch"
    assert statuses["gbp_blitz"] == "launch"
    assert statuses["keyword_hijack"] == "launch"
    assert statuses["expand_conquer"] == "launch"
    assert statuses["cash_cow"] == "phase_2"
    input_shapes = {strategy["strategy_id"]: strategy["input_shape"] for strategy in strategies}
    assert input_shapes["easy_win"] == "city_service"
    assert input_shapes["gbp_blitz"] == "city_service"
    assert input_shapes["keyword_hijack"] == "city_service_keyword"
    assert input_shapes["expand_conquer"] == "reference_city_service"
    assert input_shapes["cash_cow"] == "cached_scan"
    assert data["global_modifiers"] == [
        {
            "modifier_id": "ai_resilience",
            "name": "AI Resilience",
            "behavior": "warn_not_hide",
        }
    ]


def test_post_discover_accepts_keyword_hijack_primary_keyword_and_echoes_query() -> None:
    scored = ScoredMarket(
        market=Market(city=BOISE, service=PLUMBING, signals=SIGNALS),
        opportunity_score=91.24,
        lens_id="keyword_hijack",
        rank=1,
        score_breakdown={"projection_score": 91.24, "demand": 30.0},
        strategy_evidence={
            "primary_keyword": "boise plumber",
            "search_volume_monthly": 720,
            "local_pack_present": True,
        },
        warnings=["ai_resilience_risk"],
    )

    async def _fake_discover(query):
        assert query.lens.lens_id == "keyword_hijack"
        return [scored]

    with patch("src.research_agent.api._get_discovery_service") as mock_svc:
        mock_svc.return_value.discover = _fake_discover
        client = TestClient(app)
        resp = client.post(
            "/api/discover",
            json={
                "lens_id": "keyword_hijack",
                "primary_keyword": "boise plumber",
                "ai_resilience_filter": True,
                "limit": 10,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["query"]["primary_keyword"] == "boise plumber"
    assert data["query"]["ai_resilience_filter"] is True
    market = data["markets"][0]
    assert market["lens_id"] == "keyword_hijack"
    assert market["score_breakdown"] == {"projection_score": 91.24, "demand": 30.0}
    assert market["strategy_evidence"] == {
        "primary_keyword": "boise plumber",
        "search_volume_monthly": 720,
        "local_pack_present": True,
    }
    assert market["warnings"] == ["ai_resilience_risk"]
