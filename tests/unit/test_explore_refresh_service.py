"""Unit tests for backend Explore refresh orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from src.clients.supabase_persistence import SupabaseExploreRefreshStore
from src.domain.services.explore_refresh_service import (
    DEFAULT_REFRESH_CADENCE_DAYS,
    ExploreRefreshFlags,
    ExploreRefreshService,
    RefreshTarget,
)
from src.domain.services.market_service import ScoreRequest, ScoreResult


_DYNAMIC_REPORT_ID = object()


class FakeExploreRefreshStore:
    def __init__(self, due_targets: list[RefreshTarget]) -> None:
        self.due_targets = due_targets
        self.due_calls: list[tuple[datetime, int]] = []
        self.runs: list[dict[str, Any]] = []
        self.run_items: list[tuple[str, list[RefreshTarget]]] = []
        self.running_runs: list[str] = []
        self.succeeded_items: list[dict[str, Any]] = []
        self.failed_items: list[dict[str, Any]] = []
        self.completed_runs: list[dict[str, Any]] = []
        self.upserts: list[dict[str, Any]] = []
        self.snapshots: list[dict[str, Any]] = []
        self.filter_calls: list[tuple[dict[str, Any], int]] = []

    def list_due_targets(self, now: datetime, limit: int) -> list[RefreshTarget]:
        self.due_calls.append((now, limit))
        return list(self.due_targets)

    def create_run(self, payload: dict[str, Any]) -> str:
        self.runs.append(payload)
        return f"run-{len(self.runs)}"

    def create_run_items(self, run_id: str, targets: list[RefreshTarget]) -> None:
        self.run_items.append((run_id, list(targets)))

    def mark_run_running(self, run_id: str) -> None:
        self.running_runs.append(run_id)

    def mark_item_succeeded(self, payload: dict[str, Any]) -> None:
        self.succeeded_items.append(payload)

    def mark_item_failed(self, payload: dict[str, Any]) -> None:
        self.failed_items.append(payload)

    def mark_run_complete(
        self,
        run_id: str,
        success_count: int,
        failure_count: int,
    ) -> None:
        self.completed_runs.append(
            {
                "run_id": run_id,
                "success_count": success_count,
                "failure_count": failure_count,
            }
        )

    def upsert_target_after_success(
        self,
        *,
        target_id: str,
        policy_id: str,
        niche_keyword: str,
        niche_normalized: str,
        cbsa_code: str,
        cbsa_name: str,
        state: str | None,
        latest_report_id: str,
        latest_scored_at: datetime,
        next_refresh_at: datetime,
        latest_opportunity_score: int,
        opportunity_before: int | None,
        opportunity_after: int,
        score_delta: int | None,
        strategy_profile: str,
    ) -> None:
        kwargs = {
            "target_id": target_id,
            "policy_id": policy_id,
            "niche_keyword": niche_keyword,
            "niche_normalized": niche_normalized,
            "cbsa_code": cbsa_code,
            "cbsa_name": cbsa_name,
            "state": state,
            "latest_report_id": latest_report_id,
            "latest_scored_at": latest_scored_at,
            "next_refresh_at": next_refresh_at,
            "latest_opportunity_score": latest_opportunity_score,
            "opportunity_before": opportunity_before,
            "opportunity_after": opportunity_after,
            "score_delta": score_delta,
            "strategy_profile": strategy_profile,
        }
        self.upserts.append(kwargs)

    def record_snapshot_from_report(
        self,
        *,
        run_id: str,
        target_id: str,
        report_id: str,
        report: dict[str, Any],
        niche_keyword: str,
        niche_normalized: str,
        cbsa_code: str,
        cbsa_name: str,
        state: str | None,
        strategy_profile: str,
        scored_at: datetime,
        opportunity_before: int | None,
        opportunity_after: int,
        score_delta: int | None,
    ) -> None:
        kwargs = {
            "run_id": run_id,
            "target_id": target_id,
            "report_id": report_id,
            "report": report,
            "niche_keyword": niche_keyword,
            "niche_normalized": niche_normalized,
            "cbsa_code": cbsa_code,
            "cbsa_name": cbsa_name,
            "state": state,
            "strategy_profile": strategy_profile,
            "scored_at": scored_at,
            "opportunity_before": opportunity_before,
            "opportunity_after": opportunity_after,
            "score_delta": score_delta,
        }
        self.snapshots.append(kwargs)

    def list_targets_by_ids(self, target_ids: list[str]) -> list[RefreshTarget]:
        return [target for target in self.due_targets if target.id in target_ids]

    def list_targets_by_report_ids(self, report_ids: list[str]) -> list[RefreshTarget]:
        return [
            target
            for target in self.due_targets
            if target.latest_report_id in report_ids
        ]

    def list_targets_for_filters(
        self,
        filters: dict[str, Any],
        limit: int,
    ) -> list[RefreshTarget]:
        self.filter_calls.append((filters, limit))
        return list(self.due_targets[:limit])

    def get_run_status(self, run_id: str) -> dict[str, Any]:
        return {"id": run_id, "status": "succeeded"}


class FakeMarketService:
    def __init__(self, report_id: object = _DYNAMIC_REPORT_ID) -> None:
        self.requests: list[ScoreRequest] = []
        self.report_id = report_id

    async def score(self, request: ScoreRequest) -> ScoreResult:
        self.requests.append(request)
        report_id = (
            f"report:{request.city}"
            if self.report_id is _DYNAMIC_REPORT_ID
            else self.report_id
        )
        return ScoreResult(
            report_id=report_id,
            opportunity_score=73,
            classification_label="Medium",
            evidence=[],
            report={"report_id": report_id, "city": request.city},
            entity_id=None,
            snapshot_id=None,
            niche=request.niche,
        )


class FakeSupabaseResult:
    def __init__(self, data: Any = None, error: Any = None) -> None:
        self.data = data
        self.error = error


class FakeSupabaseTable:
    def __init__(self, table_name: str, response_data: Any = None) -> None:
        self.table_name = table_name
        self.response_data = response_data
        self.calls: list[dict[str, Any]] = []

    def _record(self, method: str, *args: Any, **kwargs: Any) -> "FakeSupabaseTable":
        self.calls.append({"method": method, "args": args, "kwargs": kwargs})
        return self

    def select(self, *args: Any, **kwargs: Any) -> "FakeSupabaseTable":
        return self._record("select", *args, **kwargs)

    def eq(self, *args: Any, **kwargs: Any) -> "FakeSupabaseTable":
        return self._record("eq", *args, **kwargs)

    def lte(self, *args: Any, **kwargs: Any) -> "FakeSupabaseTable":
        return self._record("lte", *args, **kwargs)

    def in_(self, *args: Any, **kwargs: Any) -> "FakeSupabaseTable":
        return self._record("in_", *args, **kwargs)

    def order(self, *args: Any, **kwargs: Any) -> "FakeSupabaseTable":
        return self._record("order", *args, **kwargs)

    def limit(self, *args: Any, **kwargs: Any) -> "FakeSupabaseTable":
        return self._record("limit", *args, **kwargs)

    def insert(self, *args: Any, **kwargs: Any) -> "FakeSupabaseTable":
        return self._record("insert", *args, **kwargs)

    def update(self, *args: Any, **kwargs: Any) -> "FakeSupabaseTable":
        return self._record("update", *args, **kwargs)

    def single(self, *args: Any, **kwargs: Any) -> "FakeSupabaseTable":
        return self._record("single", *args, **kwargs)

    def execute(self) -> FakeSupabaseResult:
        self.calls.append({"method": "execute", "args": (), "kwargs": {}})
        return FakeSupabaseResult(data=self.response_data)


class FakeSupabaseClient:
    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self.responses = responses or {}
        self.created_tables: list[FakeSupabaseTable] = []

    def table(self, name: str) -> FakeSupabaseTable:
        fake_table = FakeSupabaseTable(name, self.responses.get(name, []))
        self.created_tables.append(fake_table)
        return fake_table


def _target(
    target_id: str,
    *,
    cbsa_name: str = "Austin-Round Rock-Georgetown, TX",
    state: str = "TX",
    latest_opportunity_score: int | None = None,
) -> RefreshTarget:
    return RefreshTarget(
        id=target_id,
        policy_id="policy-1",
        niche_keyword="roofing",
        niche_normalized="roofing",
        cbsa_code="12420",
        cbsa_name=cbsa_name,
        state=state,
        latest_report_id=f"old-{target_id}",
        latest_scored_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        next_refresh_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        latest_opportunity_score=latest_opportunity_score,
    )


@pytest.mark.asyncio
async def test_refresh_due_targets_scores_due_targets_and_records_success() -> None:
    now = datetime(2026, 5, 13, 19, 0, tzinfo=timezone.utc)
    store = FakeExploreRefreshStore([_target("target-1")])
    market_service = FakeMarketService()
    service = ExploreRefreshService(store=store, market_service=market_service)

    result = await service.refresh_due_targets(now=now)

    assert result == {
        "run_id": "run-1",
        "target_count": 1,
        "success_count": 1,
        "failure_count": 0,
    }
    assert store.due_calls == [(now, 50)]
    assert store.runs[0]["mode"] == "scheduled"
    assert store.runs[0]["scope"] == "stale"
    assert store.runs[0]["target_count"] == 1
    assert store.running_runs == ["run-1"]
    assert store.completed_runs == [
        {"run_id": "run-1", "success_count": 1, "failure_count": 0}
    ]

    request = market_service.requests[0]
    assert request == ScoreRequest(
        niche="roofing",
        city="Austin-Round Rock-Georgetown",
        state="TX",
        strategy_profile="balanced",
        dry_run=False,
    )
    assert store.succeeded_items[0]["new_report_id"] == (
        "report:Austin-Round Rock-Georgetown"
    )
    assert store.upserts[0]["target_id"] == "target-1"
    assert store.upserts[0]["latest_report_id"] == (
        "report:Austin-Round Rock-Georgetown"
    )
    assert store.upserts[0]["next_refresh_at"] == now + timedelta(
        days=DEFAULT_REFRESH_CADENCE_DAYS
    )
    assert store.snapshots[0]["report"] == {
        "report_id": "report:Austin-Round Rock-Georgetown",
        "city": "Austin-Round Rock-Georgetown",
    }


@pytest.mark.asyncio
async def test_refresh_due_targets_respects_max_items_even_if_store_overreturns() -> None:
    now = datetime(2026, 5, 13, 19, 0, tzinfo=timezone.utc)
    store = FakeExploreRefreshStore([_target("target-1"), _target("target-2")])
    market_service = FakeMarketService()
    service = ExploreRefreshService(store=store, market_service=market_service)

    result = await service.refresh_due_targets(
        now=now,
        flags=ExploreRefreshFlags(max_items=1),
    )

    assert store.due_calls == [(now, 1)]
    assert result["target_count"] == 1
    assert len(store.run_items[0][1]) == 1
    assert len(market_service.requests) == 1
    assert store.succeeded_items[0]["target_id"] == "target-1"


@pytest.mark.asyncio
async def test_dry_run_does_not_persist_even_when_score_returns_report_id() -> None:
    now = datetime(2026, 5, 13, 19, 0, tzinfo=timezone.utc)
    store = FakeExploreRefreshStore([_target("target-1")])
    market_service = FakeMarketService(report_id="dry-run-report")
    service = ExploreRefreshService(store=store, market_service=market_service)

    result = await service.refresh_due_targets(
        now=now,
        flags=ExploreRefreshFlags(dry_run=True),
    )

    assert result["success_count"] == 1
    assert result["failure_count"] == 0
    assert market_service.requests[0].dry_run is True
    assert store.succeeded_items[0]["new_report_id"] == "dry-run-report"
    assert store.upserts == []
    assert store.snapshots == []


@pytest.mark.asyncio
async def test_non_dry_run_missing_report_id_is_marked_failed() -> None:
    now = datetime(2026, 5, 13, 19, 0, tzinfo=timezone.utc)
    store = FakeExploreRefreshStore([_target("target-1")])
    market_service = FakeMarketService(report_id=None)
    service = ExploreRefreshService(store=store, market_service=market_service)

    result = await service.refresh_due_targets(now=now)

    assert result["success_count"] == 0
    assert result["failure_count"] == 1
    assert store.succeeded_items == []
    assert store.failed_items == [
        {
            "run_id": "run-1",
            "target_id": "target-1",
            "old_report_id": "old-target-1",
            "error_message": "Scoring completed without a report_id",
        }
    ]
    assert store.upserts == []
    assert store.snapshots == []


@pytest.mark.asyncio
async def test_success_payload_includes_before_after_and_delta_scores() -> None:
    now = datetime(2026, 5, 13, 19, 0, tzinfo=timezone.utc)
    store = FakeExploreRefreshStore(
        [_target("target-1", latest_opportunity_score=61)]
    )
    market_service = FakeMarketService()
    service = ExploreRefreshService(store=store, market_service=market_service)

    await service.refresh_due_targets(now=now)

    payload = store.succeeded_items[0]
    assert payload["opportunity_before"] == 61
    assert payload["opportunity_after"] == 73
    assert payload["score_delta"] == 12
    assert store.upserts[0]["score_delta"] == 12
    assert store.snapshots[0]["score_delta"] == 12


def test_resolve_manual_targets_flags_force_bypasses_stale_selection() -> None:
    store = FakeExploreRefreshStore([_target("target-1")])
    market_service = FakeMarketService()
    service = ExploreRefreshService(store=store, market_service=market_service)

    targets = service.resolve_manual_targets(
        "stale",
        filters={"state": "TX"},
        flags=ExploreRefreshFlags(force=True),
    )

    assert targets == [_target("target-1")]
    assert store.due_calls == []
    assert store.filter_calls == [({"state": "TX"}, 50)]


def test_queue_due_targets_creates_run_without_scoring() -> None:
    now = datetime(2026, 5, 13, 19, 0, tzinfo=timezone.utc)
    store = FakeExploreRefreshStore([_target("target-1")])
    market_service = FakeMarketService()
    service = ExploreRefreshService(store=store, market_service=market_service)

    queued_run = service.queue_due_targets(now=now)

    assert queued_run.run_id == "run-1"
    assert queued_run.target_count == 1
    assert queued_run.scope == "stale"
    assert queued_run.mode == "scheduled"
    assert store.due_calls == [(now, 50)]
    assert store.runs[0]["target_count"] == 1
    assert store.run_items == [("run-1", [_target("target-1")])]
    assert store.running_runs == []
    assert store.completed_runs == []
    assert market_service.requests == []


def test_supabase_store_list_due_targets_filters_and_maps_rows() -> None:
    now = datetime(2026, 5, 13, 19, 0, tzinfo=timezone.utc)
    latest_scored_at = "2026-04-01T12:00:00+00:00"
    next_refresh_at = "2026-05-01T00:00:00Z"
    client = FakeSupabaseClient(
        {
            "explore_refresh_targets": [
                {
                    "id": "target-1",
                    "policy_id": "policy-1",
                    "niche_keyword": "roofing",
                    "niche_normalized": "roofing",
                    "cbsa_code": "12420",
                    "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                    "state": "TX",
                    "latest_report_id": "old-report-1",
                    "latest_scored_at": latest_scored_at,
                    "next_refresh_at": next_refresh_at,
                }
            ],
            "explore_latest_target_scores": [
                {
                    "target_id": "target-1",
                    "opportunity_score": 68,
                }
            ],
        }
    )
    store = SupabaseExploreRefreshStore(client=client)

    targets = store.list_due_targets(now, 10)

    assert targets == [
        RefreshTarget(
            id="target-1",
            policy_id="policy-1",
            niche_keyword="roofing",
            niche_normalized="roofing",
            cbsa_code="12420",
            cbsa_name="Austin-Round Rock-Georgetown, TX",
            state="TX",
            latest_report_id="old-report-1",
            latest_scored_at=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
            next_refresh_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            latest_opportunity_score=68,
        )
    ]

    table = client.created_tables[0]
    assert table.table_name == "explore_refresh_targets"
    select_call = next(call for call in table.calls if call["method"] == "select")
    assert "latest_opportunity_score" not in select_call["args"][0]
    assert {"method": "eq", "args": ("active", True), "kwargs": {}} in table.calls
    assert {
        "method": "lte",
        "args": ("next_refresh_at", now.isoformat()),
        "kwargs": {},
    } in table.calls
    assert {"method": "order", "args": ("priority",), "kwargs": {"desc": False}} in table.calls
    assert {"method": "limit", "args": (10,), "kwargs": {}} in table.calls

    score_view = client.created_tables[1]
    assert score_view.table_name == "explore_latest_target_scores"
    assert {
        "method": "select",
        "args": ("target_id,opportunity_score",),
        "kwargs": {},
    } in score_view.calls
    assert {
        "method": "in_",
        "args": ("target_id", ["target-1"]),
        "kwargs": {},
    } in score_view.calls


def test_supabase_store_create_run_uses_insert_execute_without_select() -> None:
    client = FakeSupabaseClient(
        {
            "explore_refresh_runs": [
                {
                    "id": "run-1",
                }
            ]
        }
    )
    store = SupabaseExploreRefreshStore(client=client)

    run_id = store.create_run({"mode": "scheduled", "scope": "stale"})

    assert run_id == "run-1"
    table = client.created_tables[0]
    assert table.table_name == "explore_refresh_runs"
    assert [call["method"] for call in table.calls] == ["insert", "execute"]
    assert table.calls[0]["args"] == ({"mode": "scheduled", "scope": "stale"},)


def test_supabase_store_mark_run_complete_records_partial_failure_counts() -> None:
    client = FakeSupabaseClient({"explore_refresh_runs": []})
    store = SupabaseExploreRefreshStore(client=client)

    store.mark_run_complete("run-1", success_count=2, failure_count=1)

    table = client.created_tables[0]
    assert table.table_name == "explore_refresh_runs"
    update_call = next(call for call in table.calls if call["method"] == "update")
    payload = update_call["args"][0]
    assert payload["status"] == "partial_failed"
    assert payload["success_count"] == 2
    assert payload["failure_count"] == 1
    assert "completed_at" in payload
    assert {"method": "eq", "args": ("id", "run-1"), "kwargs": {}} in table.calls
