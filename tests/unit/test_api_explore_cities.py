"""Unit tests for FastAPI Explore Cities endpoints."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.research_agent import api as api_module


class FakeExploreCityService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.detail_calls: list[str] = []
        self.list_error: RuntimeError | None = None
        self.detail_error: RuntimeError | None = None
        self.detail: dict[str, Any] | None = {
            "cbsa_code": "38060",
            "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
            "state": "AZ",
            "population": 4_900_000,
            "cached_scores": [
                {
                    "niche_normalized": "roofing",
                    "niche_keyword": "Roofing",
                    "presentation_score": 88,
                }
            ],
        }

    def list_cities(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        if self.list_error is not None:
            raise self.list_error
        return {
            "cities": [
                {
                    "cbsa_code": "38060",
                    "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                    "state": "AZ",
                    "population": 4_900_000,
                    "population_class": "large_1m_plus",
                    "median_household_income_usd": 82_000,
                    "business_density_per_1k": 3.2,
                    "establishment_growth_yoy": 0.08,
                    "growth_available": True,
                    "cached_services_count": 4,
                    "best_score": 88,
                    "score_system": "v2",
                    "stale": False,
                    "cached_scores": [],
                }
            ],
            "next_cursor": None,
            "growth_available": True,
            "service_filter": "roofing",
        }

    def load_city_detail(self, cbsa_code: str) -> dict[str, Any] | None:
        self.detail_calls.append(cbsa_code)
        if self.detail_error is not None:
            raise self.detail_error
        return self.detail


@pytest.fixture()
def client() -> TestClient:
    return TestClient(api_module.app)


def test_get_explore_cities_forwards_filters(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeExploreCityService()
    monkeypatch.setattr(api_module, "_get_explore_city_service", lambda: service)

    response = client.get(
        "/api/explore/cities",
        params=[
            ("service", "Roofing"),
            ("state", "AZ"),
            ("state", "CO"),
            ("population_min", "50000"),
            ("population_max", "500000"),
            ("income_min", "60000"),
            ("income_max", "120000"),
            ("growing_only", "true"),
            ("sort", "presentation_score"),
            ("direction", "desc"),
            ("limit", "25"),
            ("cursor", "50"),
        ],
    )

    assert response.status_code == 200
    assert response.json()["cities"][0]["cbsa_code"] == "38060"
    assert service.calls == [
        {
            "service_filter": "Roofing",
            "states": ["AZ", "CO"],
            "population_min": 50000,
            "population_max": 500000,
            "income_min": 60000,
            "income_max": 120000,
            "growing_only": True,
            "sort": "presentation_score",
            "direction": "desc",
            "limit": 25,
            "cursor": "50",
        }
    ]


def test_get_explore_cities_rejects_invalid_limit(client: TestClient) -> None:
    response = client.get("/api/explore/cities", params={"limit": "500"})

    assert response.status_code == 400


@pytest.mark.parametrize(
    "params",
    [
        {"sort": "unknown"},
        {"direction": "sideways"},
    ],
)
def test_get_explore_cities_rejects_invalid_sort_or_direction(
    client: TestClient,
    params: dict[str, str],
) -> None:
    response = client.get("/api/explore/cities", params=params)

    assert response.status_code == 400


def test_get_explore_cities_runtime_error_returns_sanitized_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeExploreCityService()
    service.list_error = RuntimeError("raw database password leaked")
    monkeypatch.setattr(api_module, "_get_explore_city_service", lambda: service)

    response = client.get("/api/explore/cities")

    assert response.status_code == 503
    assert response.json() == {"detail": "Explore cities service unavailable."}


def test_get_explore_city_detail_returns_detail(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeExploreCityService()
    monkeypatch.setattr(api_module, "_get_explore_city_service", lambda: service)

    response = client.get("/api/explore/cities/38060")

    assert response.status_code == 200
    assert response.json()["cbsa_code"] == "38060"
    assert response.json()["cached_scores"][0]["niche_keyword"] == "Roofing"
    assert service.detail_calls == ["38060"]


def test_get_explore_city_detail_returns_404_for_missing_city(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeExploreCityService()
    service.detail = None
    monkeypatch.setattr(api_module, "_get_explore_city_service", lambda: service)

    response = client.get("/api/explore/cities/99999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Explore city not found."}


def test_get_explore_city_detail_runtime_error_returns_sanitized_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeExploreCityService()
    service.detail_error = RuntimeError("raw database password leaked")
    monkeypatch.setattr(api_module, "_get_explore_city_service", lambda: service)

    response = client.get("/api/explore/cities/38060")

    assert response.status_code == 503
    assert response.json() == {"detail": "Explore cities service unavailable."}


def test_get_explore_city_service_singleton_wires_supabase_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: dict[str, Any] = {}

    class FakePersistence:
        def __init__(self) -> None:
            self._client = object()
            created["client"] = self._client

        @property
        def client(self) -> object:
            return self._client

    class FakeRepository:
        def __init__(self, client: Any) -> None:
            created["repository_client"] = client

    class FakeService:
        def __init__(self, repository: FakeRepository) -> None:
            self.repository = repository
            created["service_repository"] = repository

    monkeypatch.setattr(api_module, "_EXPLORE_CITY_SERVICE", None)
    monkeypatch.setattr(api_module, "SupabasePersistence", FakePersistence)
    monkeypatch.setattr(api_module, "SupabaseExploreRepository", FakeRepository)
    monkeypatch.setattr(api_module, "ExploreCityService", FakeService)

    first = api_module._get_explore_city_service()
    second = api_module._get_explore_city_service()

    assert first is second
    assert created["repository_client"] is created["client"]
    assert created["service_repository"] is first.repository
