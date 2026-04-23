"""Unit tests for GET /api/places/suggest."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import src.research_agent.api as api_module
from src.clients.dataforseo.types import APIResponse
from src.research_agent.places import DataForSEOLocationBridge


class _FakeMapboxResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "Mapbox request failed",
                request=httpx.Request("GET", "https://api.mapbox.com"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeMapboxAsyncClient:
    captured_params: dict[str, Any] = {}
    payload: dict[str, Any] = {}
    status_code: int = 200

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        pass

    async def __aenter__(self) -> "_FakeMapboxAsyncClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:  # noqa: ARG002
        return False

    async def get(self, url: str, params: dict[str, Any]) -> _FakeMapboxResponse:
        _FakeMapboxAsyncClient.captured_params = dict(params)
        assert "search/geocode/v6/forward" in url
        return _FakeMapboxResponse(_FakeMapboxAsyncClient.payload, _FakeMapboxAsyncClient.status_code)


class _FakeDataForSEOClientNoMatch:
    async def locations(self) -> APIResponse:
        return APIResponse(
            status="ok",
            data=[
                {
                    "location_code": 9001,
                    "location_name": "Berlin, Germany",
                    "country_iso_code": "DE",
                }
            ],
        )


class _FakeDataForSEOClientEmpty:
    def __init__(self) -> None:
        self.calls = 0

    async def locations(self) -> APIResponse:
        self.calls += 1
        return APIResponse(status="ok", data=[])


class _FakeDataForSEOClientError:
    def __init__(self) -> None:
        self.calls = 0

    async def locations(self) -> APIResponse:
        self.calls += 1
        return APIResponse(status="error", error="temporary error")


@pytest.fixture()
def client() -> TestClient:
    return TestClient(api_module.app)


def _mapbox_feature_payload(region_code: str = "AZ") -> dict[str, Any]:
    return {
        "features": [
            {
                "id": "place.12345",
                "properties": {
                    "name": "Phoenix",
                    "name_preferred": "Phoenix",
                    "full_address": "Phoenix, Arizona, United States",
                    "coordinates": {"longitude": -112.074, "latitude": 33.4484},
                    "context": {
                        "region": {"name": "Arizona", "region_code": region_code},
                        "country": {"name": "United States", "country_code": "US"},
                    },
                },
            }
        ]
    }


def test_places_suggest_short_query_returns_empty(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAPBOX_ACCESS_TOKEN", raising=False)
    response = client.get("/api/places/suggest", params={"q": "a"})
    assert response.status_code == 200
    assert response.json() == []


def test_places_suggest_missing_token_returns_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MAPBOX_ACCESS_TOKEN", raising=False)
    response = client.get("/api/places/suggest", params={"q": "pho"})
    assert response.status_code == 503
    assert "MAPBOX_ACCESS_TOKEN" in response.json()["detail"]


def test_places_suggest_mapbox_success_normalizes_output(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAPBOX_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(api_module, "_PLACES_DATAFORSEO_BRIDGE", None)
    monkeypatch.setattr(api_module, "_places_dataforseo_bridge", lambda: None)
    monkeypatch.setattr(
        "src.research_agent.places.httpx.AsyncClient",
        _FakeMapboxAsyncClient,
    )
    _FakeMapboxAsyncClient.payload = _mapbox_feature_payload()
    _FakeMapboxAsyncClient.captured_params = {}

    response = client.get(
        "/api/places/suggest",
        params={"q": "phoe", "limit": 99, "country": "US", "language": "en"},
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1

    top = rows[0]
    assert top["place_id"] == "place.12345"
    assert top["city"] == "Phoenix"
    assert top["region"] == "AZ"
    assert top["country"] == "United States"
    assert top["country_iso_code"] == "US"
    assert top["full_name"] == "Phoenix, Arizona, United States"
    assert top["latitude"] == pytest.approx(33.4484)
    assert top["longitude"] == pytest.approx(-112.074)
    assert top["dataforseo_location_code"] is None
    assert top["dataforseo_match_confidence"] is None

    assert _FakeMapboxAsyncClient.captured_params["types"] == "place"
    assert _FakeMapboxAsyncClient.captured_params["autocomplete"] == "true"
    assert _FakeMapboxAsyncClient.captured_params["permanent"] == "true"
    assert _FakeMapboxAsyncClient.captured_params["limit"] == 20
    assert _FakeMapboxAsyncClient.captured_params["country"] == "us"
    assert _FakeMapboxAsyncClient.captured_params["language"] == "en"


def test_places_suggest_bridge_returns_null_when_no_match(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAPBOX_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(
        "src.research_agent.places.httpx.AsyncClient",
        _FakeMapboxAsyncClient,
    )
    _FakeMapboxAsyncClient.payload = _mapbox_feature_payload()
    bridge = DataForSEOLocationBridge(_FakeDataForSEOClientNoMatch())
    monkeypatch.setattr(api_module, "_places_dataforseo_bridge", lambda: bridge)

    response = client.get("/api/places/suggest", params={"q": "phoe"})
    assert response.status_code == 200
    row = response.json()[0]
    assert row["dataforseo_location_code"] is None
    assert row["dataforseo_match_confidence"] is None


def test_places_suggest_region_prefers_trailing_region_code_segment(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAPBOX_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(api_module, "_PLACES_DATAFORSEO_BRIDGE", None)
    monkeypatch.setattr(api_module, "_places_dataforseo_bridge", lambda: None)
    monkeypatch.setattr(
        "src.research_agent.places.httpx.AsyncClient",
        _FakeMapboxAsyncClient,
    )
    _FakeMapboxAsyncClient.payload = _mapbox_feature_payload(region_code="US-AZ")

    response = client.get("/api/places/suggest", params={"q": "phoe"})
    assert response.status_code == 200
    row = response.json()[0]
    assert row["region"] == "AZ"


@pytest.mark.asyncio
async def test_location_bridge_caches_empty_success_rows_within_ttl() -> None:
    fake_client = _FakeDataForSEOClientEmpty()
    bridge = DataForSEOLocationBridge(fake_client)

    first = await bridge._location_rows()
    second = await bridge._location_rows()

    assert first == []
    assert second == []
    assert fake_client.calls == 1


@pytest.mark.asyncio
async def test_location_bridge_throttles_non_ok_responses_within_ttl() -> None:
    fake_client = _FakeDataForSEOClientError()
    bridge = DataForSEOLocationBridge(fake_client)

    first = await bridge._location_rows()
    second = await bridge._location_rows()

    assert first == []
    assert second == []
    assert fake_client.calls == 1
