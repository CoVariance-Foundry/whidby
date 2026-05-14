"""Unit tests for FastAPI Explore refresh endpoints."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import src.research_agent.api as api_module
from src.domain.services.explore_refresh_service import (
    ExploreRefreshFlags,
    QueuedExploreRefreshRun,
)
from src.research_agent.api import app


class FakeExploreRefreshService:
    def __init__(self) -> None:
        self.due_calls: list[dict[str, Any]] = []
        self.resolve_calls: list[dict[str, Any]] = []
        self.selected_calls: list[dict[str, Any]] = []
        self.executed_runs: list[str] = []
        self.status_calls: list[str] = []
        self.targets = ["target-1", "target-2"]

    async def refresh_due_targets(self, **kwargs: Any) -> dict[str, Any]:
        self.due_calls.append(kwargs)
        return {"run_id": "due-run-1", "target_count": 2}

    def queue_due_targets(self, **kwargs: Any) -> QueuedExploreRefreshRun:
        self.due_calls.append(kwargs)
        return QueuedExploreRefreshRun(
            run_id="due-run-1",
            targets=tuple(self.targets),  # type: ignore[arg-type]
            flags=kwargs["flags"],
            now=kwargs["now"],
            mode="scheduled",
            scope="stale",
            target_count=len(self.targets),
        )

    def resolve_manual_targets(self, **kwargs: Any) -> list[str]:
        self.resolve_calls.append(kwargs)
        return self.targets

    async def refresh_selected_targets(
        self,
        targets: list[str],
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.selected_calls.append({"targets": targets, **kwargs})
        return {"run_id": "manual-run-1", "target_count": len(targets)}

    def queue_selected_targets(
        self,
        targets: list[str],
        **kwargs: Any,
    ) -> QueuedExploreRefreshRun:
        self.selected_calls.append({"targets": targets, **kwargs})
        return QueuedExploreRefreshRun(
            run_id="manual-run-1",
            targets=tuple(targets),  # type: ignore[arg-type]
            flags=kwargs["flags"],
            now=kwargs["now"],
            mode=kwargs.get("mode", "manual"),
            scope=kwargs["scope"],
            target_count=len(targets),
        )

    async def execute_queued_run(self, queued_run: QueuedExploreRefreshRun) -> dict[str, Any]:
        self.executed_runs.append(queued_run.run_id)
        return {"run_id": queued_run.run_id, "target_count": queued_run.target_count}

    def get_run_status(self, run_id: str) -> dict[str, Any]:
        self.status_calls.append(run_id)
        return {"run_id": run_id, "status": "running", "items": []}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def fake_service(monkeypatch: pytest.MonkeyPatch) -> FakeExploreRefreshService:
    service = FakeExploreRefreshService()
    monkeypatch.setattr(api_module, "_get_explore_refresh_service", lambda: service)
    return service


def test_post_explore_refresh_due_rejects_missing_or_wrong_cron_secret(
    client: TestClient,
    fake_service: FakeExploreRefreshService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXPLORE_REFRESH_CRON_SECRET", "expected-secret")

    missing = client.post("/api/explore/refresh/due")
    wrong = client.post(
        "/api/explore/refresh/due",
        headers={"x-cron-secret": "wrong-secret"},
    )

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert fake_service.due_calls == []


def test_post_explore_refresh_due_fails_closed_without_backend_cron_secret(
    client: TestClient,
    fake_service: FakeExploreRefreshService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EXPLORE_REFRESH_CRON_SECRET", raising=False)

    response = client.post(
        "/api/explore/refresh/due",
        headers={"x-cron-secret": "anything"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Explore refresh cron secret is not configured"
    }
    assert fake_service.due_calls == []


def test_post_explore_refresh_due_accepts_secret_and_uses_default_flags(
    client: TestClient,
    fake_service: FakeExploreRefreshService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXPLORE_REFRESH_CRON_SECRET", "expected-secret")

    response = client.post(
        "/api/explore/refresh/due",
        headers={"x-cron-secret": "expected-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {"run_id": "due-run-1", "status": "queued"}
    assert len(fake_service.due_calls) == 1
    assert fake_service.due_calls[0]["flags"] == ExploreRefreshFlags()
    assert fake_service.due_calls[0]["now"].tzinfo is not None
    assert fake_service.executed_runs == ["due-run-1"]


def test_post_explore_refresh_runs_resolves_and_refreshes_selected_targets(
    client: TestClient,
    fake_service: FakeExploreRefreshService,
) -> None:
    payload = {
        "scope": "visible",
        "target_ids": ["target-1"],
        "report_ids": ["report-1"],
        "filters": {"state": "AZ", "min_opportunity_score": 70},
        "flags": {
            "force": True,
            "dry_run": True,
            "strategy_profile": "growth",
            "max_items": 25,
            "concurrency": 3,
        },
    }

    response = client.post("/api/explore/refresh/runs", json=payload)

    expected_flags = ExploreRefreshFlags(
        force=True,
        dry_run=True,
        strategy_profile="growth",
        max_items=25,
        concurrency=3,
    )
    assert response.status_code == 200
    assert response.json() == {"run_id": "manual-run-1", "status": "queued"}
    assert fake_service.resolve_calls == [
        {
            "scope": "visible",
            "target_ids": ["target-1"],
            "report_ids": ["report-1"],
            "filters": {"state": "AZ", "min_opportunity_score": 70},
            "flags": expected_flags,
        }
    ]
    assert len(fake_service.selected_calls) == 1
    selected_call = fake_service.selected_calls[0]
    assert selected_call["targets"] == fake_service.targets
    assert selected_call["flags"] == expected_flags
    assert selected_call["requested_by"] is None
    assert selected_call["scope"] == "visible"
    assert selected_call["now"].tzinfo is not None
    assert fake_service.executed_runs == ["manual-run-1"]


def test_post_explore_refresh_runs_rejects_invalid_strategy_profile(
    client: TestClient,
    fake_service: FakeExploreRefreshService,
) -> None:
    response = client.post(
        "/api/explore/refresh/runs",
        json={
            "scope": "selected",
            "target_ids": ["target-1"],
            "flags": {"strategy_profile": "aggressive"},
        },
    )

    assert response.status_code == 400
    assert fake_service.resolve_calls == []
    assert fake_service.selected_calls == []


def test_get_explore_refresh_run_status_delegates_to_service(
    client: TestClient,
    fake_service: FakeExploreRefreshService,
) -> None:
    response = client.get("/api/explore/refresh/runs/run-123")

    assert response.status_code == 200
    assert response.json() == {"run_id": "run-123", "status": "running", "items": []}
    assert fake_service.status_calls == ["run-123"]
