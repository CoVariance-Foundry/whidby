"""Unit tests for strategy run FastAPI contracts."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

import src.research_agent.api as api_module
from src.research_agent.api import app


class FakeStrategyRepository:
    def __init__(self) -> None:
        self.created_runs: list[dict[str, Any]] = []
        self.next_row: dict[str, Any] | None = None
        self.error: Exception | None = None

    def create_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.error:
            raise self.error
        self.created_runs.append(payload)
        if self.next_row is not None:
            return self.next_row
        return {"id": payload["id"]}


@pytest.fixture()
def fake_strategy_repository(monkeypatch: pytest.MonkeyPatch) -> FakeStrategyRepository:
    repo = FakeStrategyRepository()
    monkeypatch.setattr(api_module, "_get_strategy_repository", lambda: repo)
    return repo


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_strategy_runs_reject_over_100_pair_fresh_run(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
) -> None:
    response = client.post(
        "/api/strategy-runs",
        json={
            "strategy_id": "easy_win",
            "mode": "fresh",
            "targets": [
                {"cbsa_code": str(index), "niche_normalized": "roofing"} for index in range(101)
            ],
        },
    )

    assert response.status_code == 400
    assert "100" in response.json()["detail"]
    assert fake_strategy_repository.created_runs == []


def test_strategy_runs_allow_fresh_run_without_explicit_targets(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    monkeypatch.setattr(api_module.uuid, "uuid4", lambda: run_id)

    response = client.post(
        "/api/strategy-runs",
        json={
            "strategy_id": "easy_win",
            "mode": "fresh",
            "city": "Boise",
            "state": "ID",
            "service": "roofing",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "run_id": str(run_id),
        "strategy_id": "easy_win",
        "mode": "fresh",
        "status": "queued",
        "target_count": 0,
    }
    created_run = fake_strategy_repository.created_runs[0]
    assert created_run["input_payload"]["targets"] == []
    assert created_run["input_payload"]["city"] == "Boise"
    assert created_run["input_payload"]["service"] == "roofing"
    assert created_run["quota_consumed"] == 0


def test_strategy_runs_reject_empty_fresh_run_without_target_or_city_service(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
) -> None:
    response = client.post(
        "/api/strategy-runs",
        json={"strategy_id": "easy_win", "mode": "fresh", "targets": []},
    )

    assert response.status_code == 400
    assert fake_strategy_repository.created_runs == []


def test_strategy_runs_require_internal_token_in_production(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("STRATEGY_DISCOVERY_INTERNAL_TOKEN", "secret-token")

    response = client.post(
        "/api/strategy-runs",
        json={
            "strategy_id": "easy_win",
            "mode": "cached",
            "targets": [{"cbsa_code": "13820", "niche_normalized": "roofing"}],
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Strategy discovery access denied."
    assert fake_strategy_repository.created_runs == []


def test_strategy_runs_accept_internal_token_in_production(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("STRATEGY_DISCOVERY_INTERNAL_TOKEN", "secret-token")

    response = client.post(
        "/api/strategy-runs",
        headers={"Authorization": "Bearer secret-token"},
        json={
            "strategy_id": "easy_win",
            "mode": "cached",
            "targets": [{"cbsa_code": "13820", "niche_normalized": "roofing"}],
        },
    )

    assert response.status_code == 200
    assert len(fake_strategy_repository.created_runs) == 1


def test_strategy_runs_reject_invalid_strategy_id(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
) -> None:
    response = client.post(
        "/api/strategy-runs",
        json={
            "strategy_id": "blue_ocean",
            "mode": "cached",
            "targets": [{"cbsa_code": "13820", "niche_normalized": "roofing"}],
        },
    )

    assert response.status_code == 400
    assert fake_strategy_repository.created_runs == []


def test_strategy_runs_reject_invalid_account_id(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
) -> None:
    response = client.post(
        "/api/strategy-runs",
        json={
            "strategy_id": "easy_win",
            "mode": "cached",
            "account_id": "not-a-uuid",
            "targets": [{"cbsa_code": "13820", "niche_normalized": "roofing"}],
        },
    )

    assert response.status_code == 400
    assert fake_strategy_repository.created_runs == []


def test_strategy_runs_reject_blank_target_fields(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
) -> None:
    response = client.post(
        "/api/strategy-runs",
        json={
            "strategy_id": "easy_win",
            "mode": "cached",
            "targets": [{"cbsa_code": "", "niche_normalized": "roofing"}],
        },
    )

    assert response.status_code == 400
    assert fake_strategy_repository.created_runs == []


def test_strategy_runs_reject_whitespace_only_target_fields(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
) -> None:
    response = client.post(
        "/api/strategy-runs",
        json={
            "strategy_id": "easy_win",
            "mode": "cached",
            "targets": [{"cbsa_code": "   ", "niche_normalized": "roofing"}],
        },
    )

    assert response.status_code == 400
    assert fake_strategy_repository.created_runs == []


def test_strategy_runs_create_cached_run_response_shape(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    monkeypatch.setattr(api_module.uuid, "uuid4", lambda: run_id)

    response = client.post(
        "/api/strategy-runs",
        json={
            "strategy_id": "easy_win",
            "mode": "cached",
            "targets": [{"cbsa_code": "13820", "niche_normalized": "roofing"}],
            "account_id": "22222222-2222-2222-2222-222222222222",
            "created_by_user_id": "33333333-3333-3333-3333-333333333333",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "run_id": str(run_id),
        "strategy_id": "easy_win",
        "mode": "cached",
        "status": "succeeded",
        "target_count": 1,
    }
    assert fake_strategy_repository.created_runs == [
        {
            "id": str(run_id),
            "account_id": "22222222-2222-2222-2222-222222222222",
            "created_by_user_id": "33333333-3333-3333-3333-333333333333",
            "strategy_id": "easy_win",
            "mode": "cached",
            "status": "succeeded",
            "input_payload": {
                "targets": [
                    {
                        "cbsa_code": "13820",
                        "niche_normalized": "roofing",
                        "niche_keyword": None,
                        "primary_keyword": None,
                    }
                ],
                "city": None,
                "state": None,
                "service": None,
                "primary_keyword": None,
                "reference_city_id": None,
                "ai_resilience_filter": False,
                "limit": 50,
            },
            "result_count": 1,
            "quota_consumed": 0,
        }
    ]


def test_strategy_runs_return_persisted_status(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    monkeypatch.setattr(api_module.uuid, "uuid4", lambda: run_id)
    fake_strategy_repository.next_row = {"id": str(run_id), "status": "queued"}

    response = client.post(
        "/api/strategy-runs",
        json={
            "strategy_id": "easy_win",
            "mode": "cached",
            "targets": [{"cbsa_code": "13820", "niche_normalized": "roofing"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_strategy_runs_return_503_when_store_unavailable(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
) -> None:
    fake_strategy_repository.error = RuntimeError("write failed")

    response = client.post(
        "/api/strategy-runs",
        json={
            "strategy_id": "easy_win",
            "mode": "cached",
            "targets": [{"cbsa_code": "13820", "niche_normalized": "roofing"}],
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Strategy run store unavailable."


def test_strategy_runs_create_fresh_run_response_shape(
    client: TestClient,
    fake_strategy_repository: FakeStrategyRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    monkeypatch.setattr(api_module.uuid, "uuid4", lambda: run_id)

    response = client.post(
        "/api/strategy-runs",
        json={
            "strategy_id": "gbp_blitz",
            "mode": "fresh",
            "quota_consumed": 1,
            "targets": [
                {
                    "cbsa_code": "13820",
                    "niche_normalized": "roofing",
                    "niche_keyword": "roof repair",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "run_id": str(run_id),
        "strategy_id": "gbp_blitz",
        "mode": "fresh",
        "status": "queued",
        "target_count": 1,
    }
    created_run = fake_strategy_repository.created_runs[0]
    assert created_run["status"] == "queued"
    assert created_run["result_count"] == 0
    assert created_run["quota_consumed"] == 1
