"""Explore refresh orchestration over cached market targets."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol, Sequence

from src.domain.services.market_service import MarketService, ScoreRequest, ScoreResult


DEFAULT_REFRESH_CADENCE_DAYS = 30


@dataclass(frozen=True)
class ExploreRefreshFlags:
    force: bool = False
    dry_run: bool = False
    strategy_profile: str = "balanced"
    max_items: int = 50
    concurrency: int = 2


@dataclass(frozen=True)
class RefreshTarget:
    id: str
    policy_id: str
    niche_keyword: str
    niche_normalized: str
    cbsa_code: str
    cbsa_name: str
    state: str | None
    latest_report_id: str | None
    latest_scored_at: datetime | None
    next_refresh_at: datetime | None
    latest_opportunity_score: int | None = None


@dataclass(frozen=True)
class QueuedExploreRefreshRun:
    """Prepared refresh run that can be executed outside the request path."""

    run_id: str
    targets: tuple[RefreshTarget, ...]
    flags: ExploreRefreshFlags
    now: datetime
    mode: str
    scope: str
    target_count: int


class ExploreRefreshStore(Protocol):
    """Persistence boundary for Explore refresh runs and target state."""

    def list_due_targets(self, now: datetime, limit: int) -> Sequence[RefreshTarget]:
        ...

    def create_run(self, payload: dict[str, Any]) -> str:
        ...

    def create_run_items(
        self,
        run_id: str,
        targets: Sequence[RefreshTarget],
    ) -> None:
        ...

    def mark_run_running(self, run_id: str) -> None:
        ...

    def mark_item_succeeded(self, payload: dict[str, Any]) -> None:
        ...

    def mark_item_failed(self, payload: dict[str, Any]) -> None:
        ...

    def mark_run_complete(
        self,
        run_id: str,
        success_count: int,
        failure_count: int,
    ) -> None:
        ...

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
        ...

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
        ...

    def list_targets_by_ids(self, target_ids: Sequence[str]) -> Sequence[RefreshTarget]:
        ...

    def list_targets_by_report_ids(
        self,
        report_ids: Sequence[str],
    ) -> Sequence[RefreshTarget]:
        ...

    def list_targets_for_filters(
        self,
        filters: dict[str, Any],
        limit: int,
    ) -> Sequence[RefreshTarget]:
        ...

    def get_run_status(self, run_id: str) -> dict[str, Any]:
        ...


def city_for_scoring(cbsa_name: str, state: str | None) -> str:
    """Convert CBSA display names to the city string expected by scoring."""
    name = cbsa_name.strip()
    state_clean = state.strip().upper() if state else ""
    if "," not in name or not state_clean:
        return name

    city_part, suffix = name.rsplit(",", 1)
    if suffix.strip().upper() == state_clean:
        return city_part.strip()
    return name


class ExploreRefreshService:
    """Coordinates due/manual Explore refreshes through MarketService."""

    def __init__(
        self,
        *,
        store: ExploreRefreshStore,
        market_service: MarketService,
    ) -> None:
        self._store = store
        self._market_service = market_service

    async def refresh_due_targets(
        self,
        *,
        now: datetime | None = None,
        flags: ExploreRefreshFlags | None = None,
        requested_by: str | None = None,
    ) -> dict[str, Any]:
        queued_run = self.queue_due_targets(
            now=now,
            flags=flags,
            requested_by=requested_by,
        )
        return await self.execute_queued_run(queued_run)

    async def refresh_selected_targets(
        self,
        targets: Sequence[RefreshTarget],
        *,
        now: datetime | None = None,
        flags: ExploreRefreshFlags | None = None,
        mode: str = "manual",
        scope: str = "selected",
        requested_by: str | None = None,
    ) -> dict[str, Any]:
        queued_run = self.queue_selected_targets(
            targets,
            now=now,
            flags=flags,
            mode=mode,
            scope=scope,
            requested_by=requested_by,
        )
        return await self.execute_queued_run(queued_run)

    def queue_due_targets(
        self,
        *,
        now: datetime | None = None,
        flags: ExploreRefreshFlags | None = None,
        requested_by: str | None = None,
    ) -> QueuedExploreRefreshRun:
        run_at = now or datetime.now(timezone.utc)
        run_flags = flags or ExploreRefreshFlags()
        due_targets = self._store.list_due_targets(
            run_at,
            self._target_limit(run_flags),
        )
        return self.queue_selected_targets(
            due_targets,
            now=run_at,
            flags=run_flags,
            mode="scheduled",
            scope="stale",
            requested_by=requested_by,
        )

    def queue_selected_targets(
        self,
        targets: Sequence[RefreshTarget],
        *,
        now: datetime | None = None,
        flags: ExploreRefreshFlags | None = None,
        mode: str = "manual",
        scope: str = "selected",
        requested_by: str | None = None,
    ) -> QueuedExploreRefreshRun:
        run_at = now or datetime.now(timezone.utc)
        run_flags = flags or ExploreRefreshFlags()
        selected_targets = self._limit_targets(targets, run_flags)

        run_id = self._store.create_run(
            {
                "policy_id": _single_policy_id(selected_targets),
                "mode": mode,
                "scope": scope,
                "flags": asdict(run_flags),
                "requested_by": requested_by,
                "target_count": len(selected_targets),
            }
        )
        self._store.create_run_items(run_id, selected_targets)
        return QueuedExploreRefreshRun(
            run_id=run_id,
            targets=tuple(selected_targets),
            flags=run_flags,
            now=run_at,
            mode=mode,
            scope=scope,
            target_count=len(selected_targets),
        )

    async def execute_queued_run(
        self,
        queued_run: QueuedExploreRefreshRun,
    ) -> dict[str, Any]:
        self._store.mark_run_running(queued_run.run_id)
        success_count = 0
        failure_count = 0
        sem = asyncio.Semaphore(queued_run.flags.concurrency)

        async def _score_one(target: RefreshTarget) -> None:
            nonlocal success_count, failure_count
            async with sem:
                try:
                    result = await self._score_target(target, queued_run.flags)
                    if not queued_run.flags.dry_run and not result.report_id:
                        raise ValueError("Scoring completed without a report_id")
                    self._mark_success(
                        run_id=queued_run.run_id,
                        target=target,
                        result=result,
                        flags=queued_run.flags,
                        now=queued_run.now,
                    )
                    success_count += 1
                except Exception as exc:
                    failure_count += 1
                    self._store.mark_item_failed(
                        {
                            "run_id": queued_run.run_id,
                            "target_id": target.id,
                            "old_report_id": target.latest_report_id,
                            "error_message": str(exc),
                        }
                    )

        await asyncio.gather(*[_score_one(t) for t in queued_run.targets])

        self._store.mark_run_complete(queued_run.run_id, success_count, failure_count)
        return {
            "run_id": queued_run.run_id,
            "target_count": queued_run.target_count,
            "success_count": success_count,
            "failure_count": failure_count,
        }

    def resolve_manual_targets(
        self,
        scope: str,
        target_ids: Sequence[str] | None = None,
        report_ids: Sequence[str] | None = None,
        filters: dict[str, Any] | None = None,
        force: bool = False,
        flags: ExploreRefreshFlags | None = None,
    ) -> list[RefreshTarget]:
        run_flags = flags or ExploreRefreshFlags()
        effective_force = force or run_flags.force
        if target_ids:
            return self._limit_targets(
                self._store.list_targets_by_ids(target_ids),
                run_flags,
            )
        if report_ids:
            return self._limit_targets(
                self._store.list_targets_by_report_ids(report_ids),
                run_flags,
            )

        normalized_scope = scope.strip().lower()
        if normalized_scope == "stale" and not effective_force:
            return self._limit_targets(
                self._store.list_due_targets(
                    datetime.now(timezone.utc),
                    self._target_limit(run_flags),
                ),
                run_flags,
            )
        if normalized_scope in {"all", "stale", "visible", "filtered"}:
            return self._limit_targets(
                self._store.list_targets_for_filters(
                    filters or {},
                    self._target_limit(run_flags),
                ),
                run_flags,
            )
        return []

    def get_run_status(self, run_id: str) -> dict[str, Any]:
        return self._store.get_run_status(run_id)

    async def _score_target(
        self,
        target: RefreshTarget,
        flags: ExploreRefreshFlags,
    ) -> ScoreResult:
        request = ScoreRequest(
            niche=target.niche_keyword,
            city=city_for_scoring(target.cbsa_name, target.state),
            state=target.state,
            strategy_profile=flags.strategy_profile,
            dry_run=flags.dry_run,
        )
        return await self._market_service.score(request)

    def _mark_success(
        self,
        *,
        run_id: str,
        target: RefreshTarget,
        result: ScoreResult,
        flags: ExploreRefreshFlags,
        now: datetime,
    ) -> None:
        opportunity_before = target.latest_opportunity_score
        opportunity_after = result.opportunity_score
        score_delta = _score_delta(opportunity_before, opportunity_after)

        if not flags.dry_run and result.report_id:
            next_refresh_at = now + timedelta(days=DEFAULT_REFRESH_CADENCE_DAYS)
            self._store.upsert_target_after_success(
                target_id=target.id,
                policy_id=target.policy_id,
                niche_keyword=target.niche_keyword,
                niche_normalized=target.niche_normalized,
                cbsa_code=target.cbsa_code,
                cbsa_name=target.cbsa_name,
                state=target.state,
                latest_report_id=result.report_id,
                latest_scored_at=now,
                next_refresh_at=next_refresh_at,
                latest_opportunity_score=opportunity_after,
                opportunity_before=opportunity_before,
                opportunity_after=opportunity_after,
                score_delta=score_delta,
                strategy_profile=flags.strategy_profile,
            )
            self._store.record_snapshot_from_report(
                run_id=run_id,
                target_id=target.id,
                report_id=result.report_id,
                report=result.report,
                niche_keyword=target.niche_keyword,
                niche_normalized=target.niche_normalized,
                cbsa_code=target.cbsa_code,
                cbsa_name=target.cbsa_name,
                state=target.state,
                strategy_profile=flags.strategy_profile,
                scored_at=now,
                opportunity_before=opportunity_before,
                opportunity_after=opportunity_after,
                score_delta=score_delta,
            )

        self._store.mark_item_succeeded(
            {
                "run_id": run_id,
                "target_id": target.id,
                "old_report_id": target.latest_report_id,
                "new_report_id": result.report_id,
                "opportunity_before": opportunity_before,
                "opportunity_after": opportunity_after,
                "score_delta": score_delta,
                "classification_label": result.classification_label,
            }
        )

    def _limit_targets(
        self,
        targets: Sequence[RefreshTarget],
        flags: ExploreRefreshFlags,
    ) -> list[RefreshTarget]:
        return list(targets)[: self._target_limit(flags)]

    @staticmethod
    def _target_limit(flags: ExploreRefreshFlags) -> int:
        return max(flags.max_items, 0)


def _single_policy_id(targets: Sequence[RefreshTarget]) -> str | None:
    policy_ids = {target.policy_id for target in targets}
    if len(policy_ids) == 1:
        return next(iter(policy_ids))
    return None


def _score_delta(
    opportunity_before: int | None,
    opportunity_after: int | None,
) -> int | None:
    if opportunity_before is None or opportunity_after is None:
        return None
    return opportunity_after - opportunity_before
