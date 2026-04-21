"""Unit tests for GET /api/metros/suggest city autocomplete."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.research_agent.api import app

client = TestClient(app)


def test_suggest_phoenix_returns_phoenix_cbsa() -> None:
    res = client.get("/api/metros/suggest", params={"q": "phoe"})
    assert res.status_code == 200
    rows = res.json()
    assert isinstance(rows, list)
    assert any(r["cbsa_code"] == "38060" for r in rows)
    top = rows[0]
    assert top["state"] == "AZ"
    assert top["population"] > 0
    assert top["cbsa_name"].lower().startswith("phoenix")


def test_suggest_denver_resolves_to_colorado() -> None:
    res = client.get("/api/metros/suggest", params={"q": "denver"})
    assert res.status_code == 200
    rows = res.json()
    assert rows, "expected at least one row for 'denver'"
    assert rows[0]["state"] == "CO"


def test_suggest_short_query_returns_empty() -> None:
    res = client.get("/api/metros/suggest", params={"q": "a"})
    assert res.status_code == 200
    assert res.json() == []


def test_suggest_no_query_returns_4xx() -> None:
    # The app's custom RequestValidationError handler converts 422 → 400.
    res = client.get("/api/metros/suggest")
    assert res.status_code in (400, 422)


def test_suggest_respects_limit() -> None:
    res = client.get("/api/metros/suggest", params={"q": "san", "limit": 3})
    assert res.status_code == 200
    assert len(res.json()) <= 3


def test_suggest_orders_by_population_desc() -> None:
    res = client.get("/api/metros/suggest", params={"q": "s"})
    # q too short — empty per the short-query rule
    assert res.status_code == 200
    assert res.json() == []

    res = client.get("/api/metros/suggest", params={"q": "san"})
    rows = res.json()
    if len(rows) >= 2:
        assert rows[0]["population"] >= rows[1]["population"]


def test_suggest_emits_one_row_per_principal_city_match() -> None:
    # q="mesa" matches principal city "Mesa" inside Phoenix-Mesa-Chandler CBSA.
    res = client.get("/api/metros/suggest", params={"q": "mesa"})
    assert res.status_code == 200
    rows = res.json()
    phoenix_rows = [r for r in rows if r["cbsa_code"] == "38060"]
    assert phoenix_rows, "expected Phoenix CBSA row for 'mesa' prefix"
    assert phoenix_rows[0]["city"].lower() == "mesa"
