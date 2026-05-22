"""Unit tests for competitor intel FastAPI contracts."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

import src.research_agent.api as api_module


class FakeCompetitorIntelService:
    def __init__(self) -> None:
        self.read_requests: list[dict[str, Any]] = []
        self.run_requests: list[dict[str, Any]] = []
        self.error: Exception | None = None

    def get_read_model(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.error:
            raise self.error
        self.read_requests.append(request)
        return {
            "status": "ready_to_run",
            "target": {
                "city": request.get("city"),
                "service": request.get("service"),
                "niche_normalized": request.get("niche_normalized") or "roofing",
            },
        }

    def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.error:
            raise self.error
        self.run_requests.append(request)
        return {
            "run_id": str(uuid.UUID("55555555-5555-5555-5555-555555555555")),
            "status": "succeeded",
            "state": "aggregate_only",
            "quota_consumed": request.get("quota_consumed", 0),
            "target": {"niche_normalized": "roofing"},
            "result": {"status": "aggregate_only"},
        }


class FakeReportsQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.ids: list[str] = []

    def select(self, *_args: Any, **_kwargs: Any) -> "FakeReportsQuery":
        return self

    def in_(self, _column: str, ids: list[str]) -> "FakeReportsQuery":
        self.ids = ids
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=[row for row in self.rows if str(row["id"]) in self.ids])


class FakeReportsClient:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def table(self, name: str) -> FakeReportsQuery:
        assert name == "reports"
        return FakeReportsQuery(self.rows)


class FakeQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.eq_filters: list[tuple[str, Any]] = []
        self.in_filters: list[tuple[str, list[str]]] = []
        self.ilike_filters: list[tuple[str, str]] = []
        self.limit_value: int | None = None
        self.insert_payload: dict[str, Any] | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> "FakeQuery":
        return self

    def eq(self, column: str, value: Any) -> "FakeQuery":
        self.eq_filters.append((column, value))
        return self

    def in_(self, column: str, values: list[str]) -> "FakeQuery":
        self.in_filters.append((column, values))
        return self

    def ilike(self, column: str, pattern: str) -> "FakeQuery":
        self.ilike_filters.append((column, pattern))
        return self

    def order(self, *_args: Any, **_kwargs: Any) -> "FakeQuery":
        return self

    def limit(self, value: int) -> "FakeQuery":
        self.limit_value = value
        return self

    def insert(self, payload: dict[str, Any]) -> "FakeQuery":
        self.insert_payload = payload
        return self

    def execute(self) -> SimpleNamespace:
        rows = list(self.rows)
        for column, value in self.eq_filters:
            rows = [row for row in rows if row.get(column) == value]
        for column, values in self.in_filters:
            rows = [row for row in rows if str(row.get(column)) in values]
        for column, pattern in self.ilike_filters:
            prefix = pattern.removesuffix("%").lower()
            rows = [row for row in rows if str(row.get(column, "")).lower().startswith(prefix)]
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return SimpleNamespace(data=rows)


class FakeSupabaseClient:
    def __init__(self, rows_by_table: dict[str, list[dict[str, Any]]]) -> None:
        self.rows_by_table = rows_by_table
        self.queries: dict[str, FakeQuery] = {}

    def table(self, name: str) -> FakeQuery:
        query = FakeQuery(self.rows_by_table.get(name, []))
        self.queries[name] = query
        return query


@pytest.fixture()
def fake_service(monkeypatch: pytest.MonkeyPatch) -> FakeCompetitorIntelService:
    service = FakeCompetitorIntelService()
    monkeypatch.setattr(api_module, "_get_competitor_intel_service", lambda: service)
    return service


@pytest.fixture()
def client() -> TestClient:
    return TestClient(api_module.app)


def test_get_competitor_intel_returns_snake_case_status_shape(
    client: TestClient,
    fake_service: FakeCompetitorIntelService,
) -> None:
    response = client.get(
        "/api/competitor-intel",
        params={"city": "Boise", "state": "ID", "service": "roofing"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready_to_run",
        "target": {
            "city": "Boise",
            "service": "roofing",
            "niche_normalized": "roofing",
        },
    }
    assert fake_service.read_requests[0]["state"] == "ID"


def test_post_competitor_intel_runs_returns_run_shape(
    client: TestClient,
    fake_service: FakeCompetitorIntelService,
) -> None:
    response = client.post(
        "/api/competitor-intel/runs",
        json={
            "city": "Boise",
            "state": "ID",
            "service": "roofing",
            "quota_consumed": 2,
            "account_id": "33333333-3333-3333-3333-333333333333",
            "created_by_user_id": "44444444-4444-4444-4444-444444444444",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "run_id": "55555555-5555-5555-5555-555555555555",
        "status": "succeeded",
        "state": "aggregate_only",
        "quota_consumed": 2,
        "target": {"niche_normalized": "roofing"},
        "result": {"status": "aggregate_only"},
    }
    assert fake_service.run_requests[0]["account_id"] == ("33333333-3333-3333-3333-333333333333")


def test_post_competitor_intel_runs_rejects_missing_target(
    client: TestClient,
    fake_service: FakeCompetitorIntelService,
) -> None:
    response = client.post("/api/competitor-intel/runs", json={"service": "roofing"})

    assert response.status_code == 400
    assert fake_service.run_requests == []


def test_get_competitor_intel_returns_error_friendly_shape(
    client: TestClient,
    fake_service: FakeCompetitorIntelService,
) -> None:
    fake_service.error = RuntimeError("store unavailable")

    response = client.get(
        "/api/competitor-intel",
        params={"city": "Boise", "service": "roofing"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "code": "competitor_intel_unavailable",
        "message": "Competitor intel service is unavailable.",
    }


def test_competitor_intel_repository_visibility_matches_account_scope() -> None:
    assert api_module._SupabaseCompetitorIntelRepository._report_is_visible(
        {"access_scope": "cached", "owner_account_id": None},
        account_id=None,
    )
    assert api_module._SupabaseCompetitorIntelRepository._report_is_visible(
        {
            "access_scope": "account",
            "owner_account_id": "33333333-3333-3333-3333-333333333333",
        },
        account_id="33333333-3333-3333-3333-333333333333",
    )
    assert not api_module._SupabaseCompetitorIntelRepository._report_is_visible(
        {
            "access_scope": "account",
            "owner_account_id": "99999999-9999-9999-9999-999999999999",
        },
        account_id="33333333-3333-3333-3333-333333333333",
    )


def test_competitor_intel_repository_keeps_report_agnostic_fact_rows() -> None:
    repository = api_module._SupabaseCompetitorIntelRepository(FakeReportsClient([]))

    rows = repository._filter_rows_by_report_visibility(
        [{"report_id": None, "domain": "orphan.test"}, {"report_id": "", "domain": "empty.test"}],
        account_id="33333333-3333-3333-3333-333333333333",
    )

    assert [row["domain"] for row in rows] == ["orphan.test", "empty.test"]


def test_competitor_intel_repository_keeps_only_visible_report_rows() -> None:
    repository = api_module._SupabaseCompetitorIntelRepository(
        FakeReportsClient(
            [
                {"id": "cached-report", "access_scope": "cached", "owner_account_id": None},
                {
                    "id": "owned-report",
                    "access_scope": "account",
                    "owner_account_id": "33333333-3333-3333-3333-333333333333",
                },
                {
                    "id": "other-report",
                    "access_scope": "account",
                    "owner_account_id": "99999999-9999-9999-9999-999999999999",
                },
            ]
        )
    )

    rows = repository._filter_rows_by_report_visibility(
        [
            {"report_id": "cached-report", "domain": "cached.test"},
            {"report_id": "owned-report", "domain": "owned.test"},
            {"report_id": "other-report", "domain": "other.test"},
            {"report_id": None, "domain": "orphan.test"},
        ],
        account_id="33333333-3333-3333-3333-333333333333",
    )

    assert [row["domain"] for row in rows] == ["cached.test", "owned.test", "orphan.test"]


def test_competitor_intel_repository_filters_visibility_before_row_limit() -> None:
    client = FakeSupabaseClient(
        {
            "seo_facts": [
                {
                    "report_id": "other-report",
                    "cbsa_code": "13820",
                    "niche_normalized": "roofing",
                    "keyword": "boise roofing",
                },
                {
                    "report_id": "cached-report",
                    "cbsa_code": "13820",
                    "niche_normalized": "roofing",
                    "keyword": "boise roofing",
                },
            ],
            "reports": [
                {
                    "id": "cached-report",
                    "access_scope": "cached",
                    "owner_account_id": None,
                },
                {
                    "id": "other-report",
                    "access_scope": "account",
                    "owner_account_id": "99999999-9999-9999-9999-999999999999",
                },
            ],
        }
    )
    repository = api_module._SupabaseCompetitorIntelRepository(client)

    rows = repository.fetch_keyword_facts(
        cbsa_code="13820",
        niche_normalized="roofing",
        keyword="boise roofing",
        account_id="33333333-3333-3333-3333-333333333333",
        limit=1,
    )

    assert [row["report_id"] for row in rows] == ["cached-report"]
    assert client.queries["seo_facts"].limit_value is None


def test_competitor_intel_repository_does_not_guess_ambiguous_metro() -> None:
    client = FakeSupabaseClient(
        {
            "metros": [
                {"cbsa_code": "11111", "cbsa_name": "Springfield, IL", "state": "IL"},
                {"cbsa_code": "22222", "cbsa_name": "Springfield, MO", "state": "MO"},
            ]
        }
    )
    repository = api_module._SupabaseCompetitorIntelRepository(client)

    assert repository.find_metro(city="Springfield", state=None) is None


def test_competitor_intel_repository_uses_state_to_disambiguate_metro() -> None:
    client = FakeSupabaseClient(
        {
            "metros": [
                {"cbsa_code": "11111", "cbsa_name": "Springfield, IL", "state": "IL"},
                {"cbsa_code": "22222", "cbsa_name": "Springfield, MO", "state": "MO"},
            ]
        }
    )
    repository = api_module._SupabaseCompetitorIntelRepository(client)

    row = repository.find_metro(city="Springfield", state="MO")

    assert row == {"cbsa_code": "22222", "cbsa_name": "Springfield, MO", "state": "MO"}


def test_competitor_intel_repository_requires_persisted_run_id() -> None:
    repository = api_module._SupabaseCompetitorIntelRepository(
        FakeSupabaseClient({"competitor_intel_runs": [{}]})
    )

    with pytest.raises(RuntimeError, match="returned no run id"):
        repository.create_run_record({"status": "queued"})
