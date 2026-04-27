"""Unit tests for /api/discover and /api/lenses endpoints."""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.domain.entities import City, Market, ScoredMarket, Service
from src.research_agent.api import app

BOISE = City(city_id="boise-id", name="Boise", state="ID", population=235_000)
PLUMBING = Service(service_id="plumbing", name="Plumbing", fulfillment_type="physical")
SIGNALS: dict[str, dict[str, Any]] = {
    "demand": {"score": 75.0},
    "organic_competition": {"score": 68.0},
    "local_competition": {"score": 55.0},
    "monetization": {"score": 60.0},
    "ai_resilience": {"score": 80.0},
}

SCORED = ScoredMarket(
    market=Market(city=BOISE, service=PLUMBING, signals=SIGNALS),
    opportunity_score=68.5,
    lens_id="balanced",
    rank=1,
    score_breakdown={"demand": 18.75, "organic_competition": 10.2},
)


def test_post_discover_returns_markets():
    """Basic /api/discover returns expected shape."""

    async def _fake_discover(query):
        return [SCORED]

    with patch("src.research_agent.api._get_discovery_service") as mock_svc:
        mock_svc.return_value.discover = _fake_discover
        client = TestClient(app)
        resp = client.post("/api/discover", json={"lens_id": "balanced", "limit": 10})

    assert resp.status_code == 200
    data = resp.json()
    assert "markets" in data
    assert len(data["markets"]) == 1
    assert data["markets"][0]["rank"] == 1
    assert data["markets"][0]["opportunity_score"] == 68.5
    assert data["markets"][0]["city"]["name"] == "Boise"
    assert data["markets"][0]["service"]["name"] == "Plumbing"
    assert data["lens"]["lens_id"] == "balanced"


def test_post_discover_default_lens():
    """Omitting lens_id defaults to balanced."""

    async def _fake_discover(query):
        assert query.lens.lens_id == "balanced"
        return []

    with patch("src.research_agent.api._get_discovery_service") as mock_svc:
        mock_svc.return_value.discover = _fake_discover
        client = TestClient(app)
        resp = client.post("/api/discover", json={})

    assert resp.status_code == 200
    assert resp.json()["markets"] == []


def test_post_discover_with_city_filters():
    """City filters are parsed and forwarded to query."""

    async def _fake_discover(query):
        assert len(query.city_filters) == 1
        assert query.city_filters[0].field == "population"
        assert query.city_filters[0].operator == ">"
        assert query.city_filters[0].value == 200_000
        return []

    with patch("src.research_agent.api._get_discovery_service") as mock_svc:
        mock_svc.return_value.discover = _fake_discover
        client = TestClient(app)
        resp = client.post(
            "/api/discover",
            json={
                "city_filters": [
                    {"field": "population", "operator": ">", "value": 200_000}
                ],
            },
        )

    assert resp.status_code == 200


def test_post_discover_rejects_portfolio_ids():
    """portfolio_market_ids returns 400 until Phase 7."""
    client = TestClient(app)
    resp = client.post(
        "/api/discover",
        json={
            "portfolio_market_ids": ["some-id"],
        },
    )
    assert resp.status_code == 400
    assert "not yet supported" in resp.json()["detail"].lower()


def test_post_discover_rejects_reference_city():
    """reference_city_id returns 400 until Phase 7."""
    client = TestClient(app)
    resp = client.post(
        "/api/discover",
        json={
            "reference_city_id": "some-city",
        },
    )
    assert resp.status_code == 400
    assert "not yet supported" in resp.json()["detail"].lower()


def test_get_lenses_returns_all():
    """/api/lenses returns all 9 lens definitions."""
    client = TestClient(app)
    resp = client.get("/api/lenses")
    assert resp.status_code == 200
    data = resp.json()
    assert "lenses" in data
    assert len(data["lenses"]) == 9
    ids = [lens["lens_id"] for lens in data["lenses"]]
    assert "balanced" in ids
    assert "easy_win" in ids
    assert "gbp_blitz" in ids


def test_get_lenses_shape():
    """/api/lenses entries have expected fields."""
    client = TestClient(app)
    resp = client.get("/api/lenses")
    lens = resp.json()["lenses"][0]
    assert "lens_id" in lens
    assert "name" in lens
    assert "description" in lens
    assert "weights" in lens
    assert isinstance(lens["weights"], dict)
