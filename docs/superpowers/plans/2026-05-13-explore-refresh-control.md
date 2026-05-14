# Explore Refresh Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a refresh-control module for consumer `/explore` so operators can refresh selected, filtered, stale, or all cached market reports, default freshness to 30 days, and preserve every scored report as analyzable trend history.

**Architecture:** Store refresh policy, target, run, run-item, and report-snapshot lineage in Supabase. Run scoring through the existing FastAPI scoring pipeline, not from the browser; the consumer app calls server routes that create refresh runs, inspect status, and display stale/trend state. A daily cron checks due targets, while manual runs can force selected or filtered refreshes.

**Tech Stack:** Supabase/Postgres migrations, Python FastAPI + domain service, existing `MarketService`/`ScoreRequest`, Next.js App Router route handlers, React client components, Vitest, pytest, Playwright smoke, DocGuard.

---

## File Structure

Create:
- `supabase/migrations/015_explore_refresh_control.sql` - refresh policy/run/lineage schema, RLS, latest/trend views.
- `src/domain/services/explore_refresh_service.py` - selects due targets, creates runs, executes items through `MarketService`.
- `tests/unit/test_explore_refresh_service.py` - service unit tests with fake market/scoring stores.
- `tests/unit/test_explore_refresh_schema.py` - migration structure assertions.
- `apps/app/src/lib/explore-refresh/types.ts` - consumer refresh types.
- `apps/app/src/lib/explore-refresh/fetch-refresh-status.ts` - route-client helpers for status reads.
- `apps/app/src/app/api/explore/refresh/runs/route.ts` - authenticated manual refresh-run proxy.
- `apps/app/src/app/api/explore/refresh/runs/[runId]/route.ts` - authenticated run status proxy.
- `apps/app/src/app/api/explore/refresh/due/route.ts` - cron-protected due-run proxy.
- `apps/app/src/components/explore/RefreshControlPanel.tsx` - table-level refresh controls.
- `apps/app/src/components/explore/RefreshRunStatus.tsx` - run/result status display.

Modify:
- `src/research_agent/api.py` - add FastAPI refresh endpoints and wire service dependency.
- `src/clients/supabase_persistence.py` or create an adapter beside it if current API is too broad - add refresh lineage persistence helpers.
- `apps/app/src/lib/explore/load-explore-data.ts` - include freshness fields from latest snapshot/view.
- `apps/app/src/lib/explore/types.ts` - add freshness/trend fields to `ExploreCitySummary`/`ExploreCachedScore`.
- `apps/app/src/components/explore/ExplorePageClient.tsx` - render refresh panel, stale badges, and run status.
- `apps/app/src/components/explore/CityDrawer.tsx` - show service-level freshness and per-service refresh action.
- `apps/app/src/components/explore/ExploreTable.tsx` - show stale state and last refreshed column.
- `apps/app/e2e/reports-smoke.spec.ts` - extend `/explore` smoke to assert refresh controls render without triggering paid scans.
- `vercel.json` - add daily cron route if the repo already uses `vercel.json`; otherwise create it with only the cron entry.
- `docs-canonical/ARCHITECTURE.md` - document refresh control path.
- `docs-canonical/DATA-MODEL.md` - document refresh entities before schema/code changes.
- `docs-canonical/TEST-SPEC.md` - document refresh-control test obligations.
- `.codex/project_context.md` - concise completed-work context after implementation.

Do not touch unrelated dirty files: `.mcp.json`, `AGENTS.md`, or `docs/superpowers/plans/2026-04-29-phase-7-data-providers.md`.

---

## Data Model Decisions

The refresh cadence parameter lives in `public.explore_refresh_policies.cadence_days`, defaulting to `30`.

The daily scheduler runs every day, but a target is due only when:

```sql
target.next_refresh_at <= now()
```

or when a manual run sets `force = true`.

Each score remains in the existing `reports` table and child tables. The new `explore_report_snapshots` table creates a normalized trend grain:

```text
one row per report_id + cbsa_code + refresh target
```

This avoids duplicating report JSON while making trend queries fast and stable.

---

## Task 1: Canonical Data Model Update First

**Files:**
- Modify: `docs-canonical/DATA-MODEL.md`
- Modify: `docs-canonical/ARCHITECTURE.md`
- Modify: `docs-canonical/TEST-SPEC.md`

- [ ] **Step 1: Add refresh entities to DATA-MODEL before migration**

Add this entity block under the existing Supabase entity table:

```markdown
| ExploreRefreshPolicy | Supabase `explore_refresh_policies` table | policy_id (UUID) | Refresh cadence, scope defaults, and pipeline flags for Explore cached market reports |
| ExploreRefreshTarget | Supabase `explore_refresh_targets` table | target_id (UUID) | Service + CBSA market target monitored for staleness and scheduled refresh |
| ExploreRefreshRun | Supabase `explore_refresh_runs` table | run_id (UUID) | Manual or scheduled refresh execution envelope |
| ExploreRefreshRunItem | Supabase `explore_refresh_run_items` table | item_id (UUID) | Per-target refresh result linking old report to new report and errors |
| ExploreReportSnapshot | Supabase `explore_report_snapshots` table | snapshot_id (UUID) | Normalized historical score row per report + CBSA for trend analysis |
```

Add this schema section:

```markdown
### ExploreRefreshPolicy

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | UUID | Yes | primary key | Policy identifier |
| `name` | text | Yes | non-empty | Operator-facing policy name |
| `enabled` | boolean | Yes | default true | Whether scheduled refresh can pick targets for this policy |
| `cadence_days` | integer | Yes | 1-365, default 30 | Target freshness window; targets older than this become due |
| `scope` | text | Yes | `all_cached`, `stale_only`, `filtered` | Default scheduled run scope |
| `flags` | jsonb | Yes | object | Pipeline flags: `force`, `dry_run`, `strategy_profile`, `max_items`, `concurrency` |
| `created_at` | timestamptz | Yes | default now | Creation time |
| `updated_at` | timestamptz | Yes | default now | Last policy update |

### ExploreRefreshTarget

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | UUID | Yes | primary key | Target identifier |
| `policy_id` | UUID | Yes | references `explore_refresh_policies(id)` | Owning policy |
| `niche_keyword` | text | Yes | non-empty | Service keyword shown in Explore |
| `niche_normalized` | text | Yes | lower-case normalized keyword | Stable service key |
| `cbsa_code` | text | Yes | references `metros(cbsa_code)` | Metro key |
| `cbsa_name` | text | Yes | non-empty | Display metro name at time target was created |
| `state` | text | No | 2-letter US state when known | State sent to scoring pipeline |
| `latest_report_id` | UUID | No | references `reports(id)` | Most recent report for this target |
| `latest_scored_at` | timestamptz | No | from latest report/snapshot | Last successful score time |
| `next_refresh_at` | timestamptz | No | indexed | Next scheduled due time |
| `active` | boolean | Yes | default true | Whether the scheduler can refresh this target |
| `priority` | integer | Yes | default 100 | Lower values run first |

### ExploreRefreshRun

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | UUID | Yes | primary key | Run identifier |
| `policy_id` | UUID | No | references `explore_refresh_policies(id)` | Policy used for scheduled/default flags |
| `mode` | text | Yes | `manual`, `scheduled` | Who started the run |
| `scope` | text | Yes | `selected`, `visible`, `stale`, `all` | Target selection mode |
| `status` | text | Yes | `queued`, `running`, `succeeded`, `partial_failed`, `failed`, `canceled` | Run lifecycle |
| `flags` | jsonb | Yes | object | Effective scoring flags for the run |
| `requested_by` | UUID | No | app user id when available | User who started a manual run |
| `target_count` | integer | Yes | default 0 | Number of items queued |
| `success_count` | integer | Yes | default 0 | Number of items that produced a report |
| `failure_count` | integer | Yes | default 0 | Number of failed items |
| `started_at` | timestamptz | No | set when processing starts | Start time |
| `completed_at` | timestamptz | No | set when terminal | End time |

### ExploreRefreshRunItem

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | UUID | Yes | primary key | Run-item identifier |
| `run_id` | UUID | Yes | references `explore_refresh_runs(id)` | Parent run |
| `target_id` | UUID | Yes | references `explore_refresh_targets(id)` | Target refreshed |
| `old_report_id` | UUID | No | references `reports(id)` | Previous latest report |
| `new_report_id` | UUID | No | references `reports(id)` | New report generated by scoring |
| `status` | text | Yes | `queued`, `running`, `succeeded`, `failed`, `skipped` | Item lifecycle |
| `error_message` | text | No | clipped to 2000 chars | Failure reason |
| `opportunity_before` | integer | No | 0-100 | Previous opportunity score |
| `opportunity_after` | integer | No | 0-100 | New opportunity score |
| `score_delta` | integer | No | generated by service | Difference after - before |
| `started_at` | timestamptz | No | set when item starts | Start time |
| `completed_at` | timestamptz | No | set when item completes | End time |

### ExploreReportSnapshot

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | UUID | Yes | primary key | Snapshot identifier |
| `report_id` | UUID | Yes | references `reports(id)` | Source report |
| `run_id` | UUID | No | references `explore_refresh_runs(id)` | Refresh run that created the report |
| `target_id` | UUID | No | references `explore_refresh_targets(id)` | Target represented by this snapshot |
| `niche_keyword` | text | Yes | non-empty | Service keyword |
| `niche_normalized` | text | Yes | lower-case normalized keyword | Stable service key |
| `cbsa_code` | text | Yes | references `metros(cbsa_code)` | Metro key |
| `cbsa_name` | text | Yes | non-empty | Metro display name |
| `state` | text | No | 2-letter state when known | State |
| `strategy_profile` | text | Yes | copied from report | Strategy profile |
| `scored_at` | timestamptz | Yes | copied from report created_at | Score timestamp used for trend ordering |
| `opportunity_score` | integer | No | 0-100 | Composite score |
| `demand_score` | integer | No | 0-100 | Demand score |
| `organic_competition_score` | integer | No | 0-100 | Organic score |
| `local_competition_score` | integer | No | 0-100 | Local score |
| `monetization_score` | integer | No | 0-100 | Monetization score |
| `ai_resilience_score` | integer | No | 0-100 | AI score |
| `confidence_score` | integer | No | 0-100 | Confidence score |
| `serp_archetype` | text | No | backend enum | SERP archetype |
| `ai_exposure` | text | No | backend enum | AI exposure |
| `difficulty_tier` | text | No | backend enum | Difficulty tier |
| `meta` | jsonb | Yes | default `{}` | Source metadata for analysis |
```

- [ ] **Step 2: Update architecture**

Add one sentence to the consumer `/explore` bullet:

```markdown
Refresh control stores 30-day default freshness policy in `explore_refresh_policies`, queues refresh runs through the FastAPI scoring bridge, and records normalized `explore_report_snapshots` for trend analysis.
```

- [ ] **Step 3: Update test spec**

Add this obligation:

```markdown
| Explore refresh control | Refresh policy defaults, target selection, run status, snapshot lineage, trend deltas, cron auth | `tests/unit/test_explore_refresh_service.py`, `tests/unit/test_explore_refresh_schema.py`, `apps/app/src/components/explore/*.test.tsx`, `apps/app/e2e/reports-smoke.spec.ts` |
```

- [ ] **Step 4: Run DocGuard structure check**

Run:

```bash
npx docguard-cli guard
```

Expected: PASS or existing repo-wide WARN only. New architecture/data-model/test-spec sections should not introduce structural failures.

- [ ] **Step 5: Commit docs**

```bash
git add docs-canonical/DATA-MODEL.md docs-canonical/ARCHITECTURE.md docs-canonical/TEST-SPEC.md
git commit -m "docs: specify explore refresh control model"
```

---

## Task 2: Supabase Schema For Refresh Policy, Runs, And Trend Snapshots

**Files:**
- Create: `supabase/migrations/015_explore_refresh_control.sql`
- Test: `tests/unit/test_explore_refresh_schema.py`

- [ ] **Step 1: Write schema test**

Create `tests/unit/test_explore_refresh_schema.py`:

```python
from pathlib import Path


MIGRATION = Path("supabase/migrations/015_explore_refresh_control.sql")


def test_refresh_schema_has_policy_run_and_snapshot_tables() -> None:
    sql = MIGRATION.read_text()
    for table in (
        "explore_refresh_policies",
        "explore_refresh_targets",
        "explore_refresh_runs",
        "explore_refresh_run_items",
        "explore_report_snapshots",
    ):
        assert f"CREATE TABLE IF NOT EXISTS public.{table}" in sql


def test_refresh_policy_defaults_to_30_days() -> None:
    sql = MIGRATION.read_text()
    assert "cadence_days INTEGER NOT NULL DEFAULT 30" in sql
    assert "cadence_days BETWEEN 1 AND 365" in sql


def test_refresh_schema_exposes_latest_and_trend_views() -> None:
    sql = MIGRATION.read_text()
    assert "CREATE OR REPLACE VIEW public.explore_latest_target_scores" in sql
    assert "CREATE OR REPLACE VIEW public.explore_target_trends" in sql
    assert "LAG(opportunity_score)" in sql
```

- [ ] **Step 2: Run failing schema test**

Run:

```bash
pytest tests/unit/test_explore_refresh_schema.py -v
```

Expected: FAIL because migration file does not exist.

- [ ] **Step 3: Add migration**

Create `supabase/migrations/015_explore_refresh_control.sql`:

```sql
-- 015_explore_refresh_control.sql
-- Explore refresh policy, run lineage, and report snapshot history.

CREATE TABLE IF NOT EXISTS public.explore_refresh_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL DEFAULT 'base-30-day-refresh',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    cadence_days INTEGER NOT NULL DEFAULT 30 CHECK (cadence_days BETWEEN 1 AND 365),
    scope TEXT NOT NULL DEFAULT 'all_cached'
        CHECK (scope IN ('all_cached', 'stale_only', 'filtered')),
    flags JSONB NOT NULL DEFAULT '{
        "force": false,
        "dry_run": false,
        "strategy_profile": "balanced",
        "max_items": 50,
        "concurrency": 2
    }'::jsonb,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.explore_refresh_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL REFERENCES public.explore_refresh_policies(id) ON DELETE CASCADE,
    niche_keyword TEXT NOT NULL,
    niche_normalized TEXT NOT NULL,
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code),
    cbsa_name TEXT NOT NULL,
    state TEXT,
    latest_report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    latest_scored_at TIMESTAMPTZ,
    next_refresh_at TIMESTAMPTZ,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (policy_id, niche_normalized, cbsa_code)
);

CREATE TABLE IF NOT EXISTS public.explore_refresh_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID REFERENCES public.explore_refresh_policies(id) ON DELETE SET NULL,
    mode TEXT NOT NULL CHECK (mode IN ('manual', 'scheduled')),
    scope TEXT NOT NULL CHECK (scope IN ('selected', 'visible', 'stale', 'all')),
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'partial_failed', 'failed', 'canceled')),
    flags JSONB NOT NULL DEFAULT '{}'::jsonb,
    requested_by UUID,
    target_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.explore_refresh_run_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES public.explore_refresh_runs(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES public.explore_refresh_targets(id) ON DELETE CASCADE,
    old_report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    new_report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'skipped')),
    error_message TEXT,
    opportunity_before INTEGER,
    opportunity_after INTEGER,
    score_delta INTEGER,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.explore_report_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES public.reports(id) ON DELETE CASCADE,
    run_id UUID REFERENCES public.explore_refresh_runs(id) ON DELETE SET NULL,
    target_id UUID REFERENCES public.explore_refresh_targets(id) ON DELETE SET NULL,
    niche_keyword TEXT NOT NULL,
    niche_normalized TEXT NOT NULL,
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code),
    cbsa_name TEXT NOT NULL,
    state TEXT,
    strategy_profile TEXT NOT NULL DEFAULT 'balanced',
    scored_at TIMESTAMPTZ NOT NULL,
    opportunity_score INTEGER,
    demand_score INTEGER,
    organic_competition_score INTEGER,
    local_competition_score INTEGER,
    monetization_score INTEGER,
    ai_resilience_score INTEGER,
    confidence_score INTEGER,
    serp_archetype TEXT,
    ai_exposure TEXT,
    difficulty_tier TEXT,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (report_id, cbsa_code)
);

CREATE INDEX IF NOT EXISTS idx_explore_targets_due
    ON public.explore_refresh_targets(next_refresh_at, priority)
    WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_explore_targets_market
    ON public.explore_refresh_targets(niche_normalized, cbsa_code);
CREATE INDEX IF NOT EXISTS idx_explore_runs_status
    ON public.explore_refresh_runs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_explore_run_items_run
    ON public.explore_refresh_run_items(run_id, status);
CREATE INDEX IF NOT EXISTS idx_explore_snapshots_target_time
    ON public.explore_report_snapshots(target_id, scored_at DESC);
CREATE INDEX IF NOT EXISTS idx_explore_snapshots_market_time
    ON public.explore_report_snapshots(niche_normalized, cbsa_code, scored_at DESC);

CREATE OR REPLACE VIEW public.explore_latest_target_scores AS
SELECT DISTINCT ON (target_id)
    target_id,
    report_id,
    niche_keyword,
    niche_normalized,
    cbsa_code,
    cbsa_name,
    state,
    strategy_profile,
    scored_at,
    opportunity_score,
    demand_score,
    organic_competition_score,
    local_competition_score,
    monetization_score,
    ai_resilience_score,
    confidence_score,
    serp_archetype,
    ai_exposure,
    difficulty_tier
FROM public.explore_report_snapshots
WHERE target_id IS NOT NULL
ORDER BY target_id, scored_at DESC;

CREATE OR REPLACE VIEW public.explore_target_trends AS
SELECT
    s.*,
    LAG(opportunity_score) OVER (
        PARTITION BY target_id
        ORDER BY scored_at
    ) AS previous_opportunity_score,
    opportunity_score - LAG(opportunity_score) OVER (
        PARTITION BY target_id
        ORDER BY scored_at
    ) AS opportunity_delta
FROM public.explore_report_snapshots s
WHERE target_id IS NOT NULL;

ALTER TABLE public.explore_refresh_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.explore_refresh_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.explore_refresh_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.explore_refresh_run_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.explore_report_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read explore refresh policies"
    ON public.explore_refresh_policies FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read explore refresh targets"
    ON public.explore_refresh_targets FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read explore refresh runs"
    ON public.explore_refresh_runs FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read explore refresh run items"
    ON public.explore_refresh_run_items FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can read explore report snapshots"
    ON public.explore_report_snapshots FOR SELECT TO authenticated USING (true);

CREATE POLICY "Service role manages explore refresh policies"
    ON public.explore_refresh_policies FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role manages explore refresh targets"
    ON public.explore_refresh_targets FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role manages explore refresh runs"
    ON public.explore_refresh_runs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role manages explore refresh run items"
    ON public.explore_refresh_run_items FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role manages explore report snapshots"
    ON public.explore_report_snapshots FOR ALL TO service_role USING (true) WITH CHECK (true);
```

- [ ] **Step 4: Run schema tests**

Run:

```bash
pytest tests/unit/test_explore_refresh_schema.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit schema**

```bash
git add supabase/migrations/015_explore_refresh_control.sql tests/unit/test_explore_refresh_schema.py
git commit -m "feat: add explore refresh schema"
```

---

## Task 3: Backend Refresh Service

**Files:**
- Create: `src/domain/services/explore_refresh_service.py`
- Test: `tests/unit/test_explore_refresh_service.py`

- [ ] **Step 1: Write service tests**

Create `tests/unit/test_explore_refresh_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from src.domain.services.explore_refresh_service import (
    ExploreRefreshFlags,
    ExploreRefreshService,
    RefreshTarget,
)
from src.domain.services.market_service import ScoreResult


@dataclass
class FakeRefreshStore:
    targets: list[RefreshTarget]
    created_runs: list[dict[str, Any]] = field(default_factory=list)
    completed_items: list[dict[str, Any]] = field(default_factory=list)

    def list_due_targets(self, *, now: datetime, limit: int) -> list[RefreshTarget]:
        due = [target for target in self.targets if target.next_refresh_at <= now]
        return due[:limit]

    def create_run(self, payload: dict[str, Any]) -> str:
        self.created_runs.append(payload)
        return "run-1"

    def create_run_items(self, run_id: str, targets: list[RefreshTarget]) -> None:
        self.created_runs[-1]["items"] = [target.id for target in targets]

    def mark_run_running(self, run_id: str) -> None:
        self.created_runs[-1]["status"] = "running"

    def mark_item_succeeded(self, payload: dict[str, Any]) -> None:
        self.completed_items.append({"status": "succeeded", **payload})

    def mark_item_failed(self, payload: dict[str, Any]) -> None:
        self.completed_items.append({"status": "failed", **payload})

    def mark_run_complete(self, run_id: str, *, success_count: int, failure_count: int) -> None:
        self.created_runs[-1]["success_count"] = success_count
        self.created_runs[-1]["failure_count"] = failure_count

    def upsert_target_after_success(self, **kwargs: Any) -> None:
        self.created_runs[-1]["target_update"] = kwargs

    def record_snapshot_from_report(self, **kwargs: Any) -> None:
        self.created_runs[-1].setdefault("snapshots", []).append(kwargs)


class FakeMarketService:
    async def score(self, request: Any) -> ScoreResult:
        return ScoreResult(
            report_id=f"report-{request.niche}-{request.city}",
            opportunity_score=81,
            classification_label="High",
            evidence=[],
            report={
                "niche_keyword": request.niche,
                "geo_target": request.city,
                "strategy_profile": request.strategy_profile,
                "metros": [
                    {
                        "cbsa_code": "12420",
                        "cbsa_name": "Austin-Round Rock-Georgetown, TX",
                        "scores": {"opportunity": 81},
                    }
                ],
            },
            entity_id=None,
            snapshot_id=None,
            niche=request.niche,
        )


def make_target(next_refresh_at: datetime) -> RefreshTarget:
    return RefreshTarget(
        id="target-1",
        policy_id="policy-1",
        niche_keyword="roofing",
        niche_normalized="roofing",
        cbsa_code="12420",
        cbsa_name="Austin-Round Rock-Georgetown, TX",
        state="TX",
        latest_report_id="old-report",
        latest_scored_at=next_refresh_at - timedelta(days=30),
        next_refresh_at=next_refresh_at,
    )


@pytest.mark.asyncio
async def test_refresh_due_targets_scores_and_records_snapshot() -> None:
    now = datetime(2026, 5, 13, tzinfo=timezone.utc)
    store = FakeRefreshStore(targets=[make_target(now - timedelta(minutes=1))])
    service = ExploreRefreshService(store=store, market_service=FakeMarketService())

    run_id = await service.refresh_due_targets(
        now=now,
        flags=ExploreRefreshFlags(max_items=10, strategy_profile="balanced"),
    )

    assert run_id == "run-1"
    assert store.created_runs[0]["target_count"] == 1
    assert store.completed_items[0]["status"] == "succeeded"
    assert store.completed_items[0]["old_report_id"] == "old-report"
    assert store.completed_items[0]["new_report_id"] == "report-roofing-Austin-Round Rock-Georgetown"
    assert store.created_runs[0]["snapshots"][0]["report_id"] == "report-roofing-Austin-Round Rock-Georgetown"


@pytest.mark.asyncio
async def test_refresh_due_targets_respects_max_items() -> None:
    now = datetime(2026, 5, 13, tzinfo=timezone.utc)
    store = FakeRefreshStore(
        targets=[
            make_target(now - timedelta(days=1)),
            make_target(now - timedelta(days=2)),
        ]
    )
    service = ExploreRefreshService(store=store, market_service=FakeMarketService())

    await service.refresh_due_targets(
        now=now,
        flags=ExploreRefreshFlags(max_items=1, strategy_profile="balanced"),
    )

    assert store.created_runs[0]["target_count"] == 1
```

- [ ] **Step 2: Run failing service tests**

Run:

```bash
pytest tests/unit/test_explore_refresh_service.py -v
```

Expected: FAIL because `src.domain.services.explore_refresh_service` does not exist.

- [ ] **Step 3: Add service module**

Create `src/domain/services/explore_refresh_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from src.domain.services.market_service import MarketService, ScoreRequest


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
    next_refresh_at: datetime


class ExploreRefreshStore(Protocol):
    def list_due_targets(self, *, now: datetime, limit: int) -> list[RefreshTarget]: ...
    def create_run(self, payload: dict[str, Any]) -> str: ...
    def create_run_items(self, run_id: str, targets: list[RefreshTarget]) -> None: ...
    def mark_run_running(self, run_id: str) -> None: ...
    def mark_item_succeeded(self, payload: dict[str, Any]) -> None: ...
    def mark_item_failed(self, payload: dict[str, Any]) -> None: ...
    def mark_run_complete(self, run_id: str, *, success_count: int, failure_count: int) -> None: ...
    def upsert_target_after_success(self, **kwargs: Any) -> None: ...
    def record_snapshot_from_report(self, **kwargs: Any) -> None: ...


def city_for_scoring(cbsa_name: str, state: str | None) -> str:
    city = cbsa_name.strip()
    if not state:
        return city
    suffix = f", {state.strip()}"
    if city.lower().endswith(suffix.lower()):
        return city[: -len(suffix)].strip()
    return city


class ExploreRefreshService:
    def __init__(self, *, store: ExploreRefreshStore, market_service: MarketService) -> None:
        self._store = store
        self._market = market_service

    async def refresh_due_targets(
        self,
        *,
        now: datetime,
        flags: ExploreRefreshFlags,
        requested_by: str | None = None,
    ) -> str:
        targets = self._store.list_due_targets(now=now, limit=flags.max_items)
        run_id = self._store.create_run(
            {
                "mode": "scheduled",
                "scope": "stale",
                "status": "queued",
                "flags": flags.__dict__,
                "requested_by": requested_by,
                "target_count": len(targets),
            }
        )
        self._store.create_run_items(run_id, targets)
        await self._execute_targets(run_id=run_id, targets=targets, flags=flags, now=now)
        return run_id

    async def refresh_selected_targets(
        self,
        *,
        targets: list[RefreshTarget],
        flags: ExploreRefreshFlags,
        requested_by: str | None,
        now: datetime,
    ) -> str:
        selected = targets[: flags.max_items]
        run_id = self._store.create_run(
            {
                "mode": "manual",
                "scope": "selected",
                "status": "queued",
                "flags": flags.__dict__,
                "requested_by": requested_by,
                "target_count": len(selected),
            }
        )
        self._store.create_run_items(run_id, selected)
        await self._execute_targets(run_id=run_id, targets=selected, flags=flags, now=now)
        return run_id

    async def _execute_targets(
        self,
        *,
        run_id: str,
        targets: list[RefreshTarget],
        flags: ExploreRefreshFlags,
        now: datetime,
    ) -> None:
        self._store.mark_run_running(run_id)
        success_count = 0
        failure_count = 0

        for target in targets:
            try:
                result = await self._market.score(
                    ScoreRequest(
                        niche=target.niche_keyword,
                        city=city_for_scoring(target.cbsa_name, target.state),
                        state=target.state,
                        strategy_profile=flags.strategy_profile,
                        dry_run=flags.dry_run,
                    )
                )
                new_report_id = result.report_id
                self._store.mark_item_succeeded(
                    {
                        "run_id": run_id,
                        "target_id": target.id,
                        "old_report_id": target.latest_report_id,
                        "new_report_id": new_report_id,
                        "opportunity_before": None,
                        "opportunity_after": result.opportunity_score,
                    }
                )
                if new_report_id:
                    self._store.upsert_target_after_success(
                        target_id=target.id,
                        latest_report_id=new_report_id,
                        latest_scored_at=now,
                        next_refresh_at=now + timedelta(days=DEFAULT_REFRESH_CADENCE_DAYS),
                    )
                    self._store.record_snapshot_from_report(
                        run_id=run_id,
                        target_id=target.id,
                        report_id=new_report_id,
                        report=result.report,
                        scored_at=now,
                    )
                success_count += 1
            except Exception as exc:
                self._store.mark_item_failed(
                    {
                        "run_id": run_id,
                        "target_id": target.id,
                        "old_report_id": target.latest_report_id,
                        "error_message": str(exc)[:2000],
                    }
                )
                failure_count += 1

        self._store.mark_run_complete(
            run_id,
            success_count=success_count,
            failure_count=failure_count,
        )
```

- [ ] **Step 4: Run service tests**

Run:

```bash
pytest tests/unit/test_explore_refresh_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit service**

```bash
git add src/domain/services/explore_refresh_service.py tests/unit/test_explore_refresh_service.py
git commit -m "feat: add explore refresh service"
```

---

## Task 4: Supabase Refresh Store Adapter

**Files:**
- Modify: `src/clients/supabase_persistence.py`
- Test: `tests/unit/test_explore_refresh_service.py`

- [ ] **Step 1: Add adapter unit coverage**

Add this fake-client test to `tests/unit/test_explore_refresh_service.py`:

```python
def test_refresh_store_filters_due_targets() -> None:
    from src.clients.supabase_persistence import SupabaseExploreRefreshStore

    class FakeTable:
        def __init__(self) -> None:
            self.calls: list[tuple[str, tuple[object, ...]]] = []

        def select(self, value: str) -> "FakeTable":
            self.calls.append(("select", (value,)))
            return self

        def eq(self, key: str, value: object) -> "FakeTable":
            self.calls.append(("eq", (key, value)))
            return self

        def lte(self, key: str, value: object) -> "FakeTable":
            self.calls.append(("lte", (key, value)))
            return self

        def order(self, key: str, **kwargs: object) -> "FakeTable":
            self.calls.append(("order", (key, kwargs)))
            return self

        def limit(self, value: int) -> object:
            self.calls.append(("limit", (value,)))
            return type("Result", (), {"data": [], "error": None})()

    class FakeClient:
        def __init__(self) -> None:
            self.table = FakeTable()

        def table(self, name: str) -> FakeTable:  # type: ignore[no-redef]
            assert name == "explore_refresh_targets"
            return self.table

    fake = FakeClient()
    store = SupabaseExploreRefreshStore(fake)  # type: ignore[arg-type]
    now = datetime(2026, 5, 13, tzinfo=timezone.utc)

    assert store.list_due_targets(now=now, limit=10) == []
    assert ("eq", ("active", True)) in fake.table.calls
    assert any(call[0] == "lte" and call[1][0] == "next_refresh_at" for call in fake.table.calls)
```

- [ ] **Step 2: Run failing adapter test**

Run:

```bash
pytest tests/unit/test_explore_refresh_service.py::test_refresh_store_filters_due_targets -v
```

Expected: FAIL because `SupabaseExploreRefreshStore` does not exist.

- [ ] **Step 3: Add store adapter**

Add this class to `src/clients/supabase_persistence.py` or a nearby adapter if the file is too broad:

```python
from datetime import datetime
from typing import Any

from src.domain.services.explore_refresh_service import RefreshTarget


class SupabaseExploreRefreshStore:
    def __init__(self, client: Any) -> None:
        self._client = client

    def list_due_targets(self, *, now: datetime, limit: int) -> list[RefreshTarget]:
        result = (
            self._client.table("explore_refresh_targets")
            .select(
                "id, policy_id, niche_keyword, niche_normalized, cbsa_code, cbsa_name, "
                "state, latest_report_id, latest_scored_at, next_refresh_at"
            )
            .eq("active", True)
            .lte("next_refresh_at", now.isoformat())
            .order("priority", desc=False)
            .limit(limit)
        )
        if result.error:
            raise RuntimeError(result.error.message)
        return [
            RefreshTarget(
                id=row["id"],
                policy_id=row["policy_id"],
                niche_keyword=row["niche_keyword"],
                niche_normalized=row["niche_normalized"],
                cbsa_code=row["cbsa_code"],
                cbsa_name=row["cbsa_name"],
                state=row.get("state"),
                latest_report_id=row.get("latest_report_id"),
                latest_scored_at=row.get("latest_scored_at"),
                next_refresh_at=row["next_refresh_at"],
            )
            for row in result.data or []
        ]
```

Then add concrete methods for `create_run`, `create_run_items`, `mark_run_running`, `mark_item_succeeded`, `mark_item_failed`, `mark_run_complete`, `upsert_target_after_success`, and `record_snapshot_from_report` using the table names from Task 2. Each method should raise `RuntimeError(error.message)` on Supabase errors.

- [ ] **Step 4: Run adapter/service tests**

Run:

```bash
pytest tests/unit/test_explore_refresh_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit adapter**

```bash
git add src/clients/supabase_persistence.py tests/unit/test_explore_refresh_service.py
git commit -m "feat: persist explore refresh runs"
```

---

## Task 5: FastAPI Refresh Endpoints

**Files:**
- Modify: `src/research_agent/api.py`
- Test: `tests/unit/test_api_explore_refresh.py`

- [ ] **Step 1: Add endpoint tests**

Create `tests/unit/test_api_explore_refresh.py`:

```python
from fastapi.testclient import TestClient

from src.research_agent.api import app


def test_refresh_due_requires_cron_secret(monkeypatch) -> None:
    monkeypatch.setenv("EXPLORE_REFRESH_CRON_SECRET", "secret")
    client = TestClient(app)

    response = client.post("/api/explore/refresh/due")

    assert response.status_code == 401


def test_manual_refresh_accepts_flags(monkeypatch) -> None:
    class FakeService:
        async def refresh_selected_targets(self, **kwargs):
            return "run-123"

    monkeypatch.setattr("src.research_agent.api._get_explore_refresh_service", lambda: FakeService())
    client = TestClient(app)

    response = client.post(
        "/api/explore/refresh/runs",
        json={
            "scope": "selected",
            "target_ids": ["target-1"],
            "flags": {"force": True, "max_items": 1, "strategy_profile": "balanced"},
        },
    )

    assert response.status_code == 200
    assert response.json() == {"run_id": "run-123", "status": "queued"}
```

- [ ] **Step 2: Run failing endpoint tests**

Run:

```bash
pytest tests/unit/test_api_explore_refresh.py -v
```

Expected: FAIL because endpoints are missing.

- [ ] **Step 3: Add Pydantic models and endpoints**

Add to `src/research_agent/api.py`:

```python
class ExploreRefreshFlagsPayload(BaseModel):
    force: bool = False
    dry_run: bool = False
    strategy_profile: str = "balanced"
    max_items: int = Field(default=50, ge=1, le=500)
    concurrency: int = Field(default=2, ge=1, le=5)


class ExploreRefreshRunRequest(BaseModel):
    scope: str = Field(pattern="^(selected|visible|stale|all)$")
    target_ids: list[str] = Field(default_factory=list)
    report_ids: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    flags: ExploreRefreshFlagsPayload = Field(default_factory=ExploreRefreshFlagsPayload)


@app.post("/api/explore/refresh/runs")
async def create_explore_refresh_run(payload: ExploreRefreshRunRequest) -> dict[str, str]:
    service = _get_explore_refresh_service()
    flags = ExploreRefreshFlags(**payload.flags.model_dump())
    targets = service.resolve_manual_targets(
        scope=payload.scope,
        target_ids=payload.target_ids,
        report_ids=payload.report_ids,
        filters=payload.filters,
        force=flags.force,
    )
    run_id = await service.refresh_selected_targets(
        targets=targets,
        flags=flags,
        requested_by=None,
        now=datetime.now(timezone.utc),
    )
    return {"run_id": run_id, "status": "queued"}


@app.post("/api/explore/refresh/due")
async def refresh_due_explore_targets(request: Request) -> dict[str, str]:
    expected = os.environ.get("EXPLORE_REFRESH_CRON_SECRET")
    supplied = request.headers.get("x-cron-secret")
    if expected and supplied != expected:
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    service = _get_explore_refresh_service()
    run_id = await service.refresh_due_targets(
        now=datetime.now(timezone.utc),
        flags=ExploreRefreshFlags(),
    )
    return {"run_id": run_id, "status": "queued"}


@app.get("/api/explore/refresh/runs/{run_id}")
def get_explore_refresh_run(run_id: str) -> dict[str, Any]:
    return _get_explore_refresh_service().get_run_status(run_id)
```

Add `_get_explore_refresh_service()` near existing service dependency helpers. It should construct `SupabaseExploreRefreshStore` with service-role Supabase credentials and reuse `_market_service()` or the same MarketService dependency path used by `/api/niches/score`.

- [ ] **Step 4: Run endpoint tests**

Run:

```bash
pytest tests/unit/test_api_explore_refresh.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit API endpoints**

```bash
git add src/research_agent/api.py tests/unit/test_api_explore_refresh.py
git commit -m "feat: expose explore refresh API"
```

---

## Task 6: Consumer App API Proxies And Cron Route

**Files:**
- Create: `apps/app/src/lib/explore-refresh/types.ts`
- Create: `apps/app/src/app/api/explore/refresh/runs/route.ts`
- Create: `apps/app/src/app/api/explore/refresh/runs/[runId]/route.ts`
- Create: `apps/app/src/app/api/explore/refresh/due/route.ts`
- Modify/Create: `vercel.json`
- Test: `apps/app/src/app/api/explore/refresh/runs/route.test.ts`

- [ ] **Step 1: Add route test**

Create `apps/app/src/app/api/explore/refresh/runs/route.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { POST } from "./route";

describe("POST /api/explore/refresh/runs", () => {
  it("proxies refresh flags to FastAPI", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ run_id: "run-1", status: "queued" }), { status: 200 }),
    );
    global.fetch = fetchMock;

    const request = new Request("http://localhost/api/explore/refresh/runs", {
      method: "POST",
      body: JSON.stringify({
        scope: "selected",
        target_ids: ["target-1"],
        flags: { force: true, max_items: 1, strategy_profile: "balanced" },
      }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ run_id: "run-1", status: "queued" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/explore/refresh/runs",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
```

- [ ] **Step 2: Run failing route test**

Run:

```bash
cd apps/app && npx vitest run src/app/api/explore/refresh/runs/route.test.ts
```

Expected: FAIL because route does not exist.

- [ ] **Step 3: Add types**

Create `apps/app/src/lib/explore-refresh/types.ts`:

```ts
export interface ExploreRefreshFlags {
  force: boolean;
  dry_run: boolean;
  strategy_profile: "balanced" | "growth" | "defensive";
  max_items: number;
  concurrency: number;
}

export interface ExploreRefreshRunRequest {
  scope: "selected" | "visible" | "stale" | "all";
  target_ids?: string[];
  report_ids?: string[];
  filters?: Record<string, unknown>;
  flags: Partial<ExploreRefreshFlags>;
}

export interface ExploreRefreshRunResponse {
  run_id: string;
  status: "queued" | "running" | "succeeded" | "partial_failed" | "failed" | "canceled";
}
```

- [ ] **Step 4: Add manual-run proxy route**

Create `apps/app/src/app/api/explore/refresh/runs/route.ts`:

```ts
import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(request: Request) {
  const body = await request.json();
  const upstream = await fetch(`${API_BASE}/api/explore/refresh/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const payload = await upstream.json().catch(() => null);
  if (!upstream.ok) {
    return NextResponse.json(
      {
        status: "unavailable",
        message: payload?.detail ?? "Explore refresh run could not be created.",
        upstream_status: upstream.status,
      },
      { status: 502 },
    );
  }

  return NextResponse.json(payload);
}
```

- [ ] **Step 5: Add status route and cron route**

Create `apps/app/src/app/api/explore/refresh/runs/[runId]/route.ts`:

```ts
import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  const upstream = await fetch(`${API_BASE}/api/explore/refresh/runs/${encodeURIComponent(runId)}`);
  const payload = await upstream.json().catch(() => null);
  return NextResponse.json(payload, { status: upstream.ok ? 200 : 502 });
}
```

Create `apps/app/src/app/api/explore/refresh/due/route.ts`:

```ts
import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(request: Request) {
  const expected = process.env.EXPLORE_REFRESH_CRON_SECRET;
  const supplied = request.headers.get("x-cron-secret");
  if (expected && supplied !== expected) {
    return NextResponse.json({ status: "unauthorized" }, { status: 401 });
  }

  const upstream = await fetch(`${API_BASE}/api/explore/refresh/due`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(expected ? { "x-cron-secret": expected } : {}),
    },
  });
  const payload = await upstream.json().catch(() => null);
  return NextResponse.json(payload, { status: upstream.ok ? 200 : 502 });
}
```

Modify/create `vercel.json`:

```json
{
  "crons": [
    {
      "path": "/api/explore/refresh/due",
      "schedule": "0 9 * * *"
    }
  ]
}
```

The cron runs daily. The 30-day refresh rate is not in `vercel.json`; it is in `explore_refresh_policies.cadence_days`.

- [ ] **Step 6: Run route tests**

Run:

```bash
cd apps/app && npx vitest run src/app/api/explore/refresh/runs/route.test.ts
```

Expected: PASS.

- [ ] **Step 7: Commit app API routes**

```bash
git add apps/app/src/lib/explore-refresh/types.ts apps/app/src/app/api/explore/refresh vercel.json
git commit -m "feat: proxy explore refresh runs"
```

---

## Task 7: Explore Loader Freshness And Trend Fields

**Files:**
- Modify: `apps/app/src/lib/explore/types.ts`
- Modify: `apps/app/src/lib/explore/load-explore-data.ts`
- Test: `apps/app/src/lib/explore/load-explore-data.test.ts`

- [ ] **Step 1: Add failing loader test**

Add to `apps/app/src/lib/explore/load-explore-data.test.ts`:

```ts
it("maps latest refresh snapshot freshness onto cached scores", async () => {
  const { client } = makeClient({
    metros: [result([{ cbsa_code: "12420", cbsa_name: "Austin, TX", state: "TX", population: 1, population_class: "large_300k_1m", owner_occupancy_rate: null, median_household_income_usd: null, median_age_years: null }])],
    reports: [result([{ id: "report-1", created_at: "2026-04-01T00:00:00Z", niche_keyword: "roofing" }])],
    metro_scores: [result([{ report_id: "report-1", cbsa_code: "12420", opportunity_score: 70, serp_archetype: null, ai_exposure: null, difficulty_tier: null }])],
    explore_latest_target_scores: [result([{ report_id: "report-1", target_id: "target-1", scored_at: "2026-04-01T00:00:00Z", opportunity_score: 70 }])],
  });

  const data = await loadExploreData(client as never);

  expect(data.cities[0].cached_scores[0].refresh_target_id).toBe("target-1");
  expect(data.cities[0].cached_scores[0].last_refreshed_at).toBe("2026-04-01T00:00:00Z");
});
```

- [ ] **Step 2: Run failing loader test**

Run:

```bash
cd apps/app && npx vitest run src/lib/explore/load-explore-data.test.ts
```

Expected: FAIL because fields and view load are missing.

- [ ] **Step 3: Add types**

Modify `ExploreCachedScore` in `apps/app/src/lib/explore/types.ts`:

```ts
  refresh_target_id?: string;
  last_refreshed_at?: string;
  next_refresh_at?: string;
  stale_after_days?: number;
  is_stale?: boolean;
  opportunity_delta?: number | null;
```

- [ ] **Step 4: Load latest refresh view**

Modify `loadExploreData` to query `explore_latest_target_scores` by `report_id` and `cbsa_code`, then merge matching fields onto cached scores. Use the same fallback style as current loader: if the view does not exist, return cached scores without freshness fields rather than failing the entire Explore page during migration rollout.

- [ ] **Step 5: Run loader tests**

Run:

```bash
cd apps/app && npx vitest run src/lib/explore/load-explore-data.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit loader freshness fields**

```bash
git add apps/app/src/lib/explore/types.ts apps/app/src/lib/explore/load-explore-data.ts apps/app/src/lib/explore/load-explore-data.test.ts
git commit -m "feat: surface explore refresh freshness"
```

---

## Task 8: Refresh Control UI

**Files:**
- Create: `apps/app/src/components/explore/RefreshControlPanel.tsx`
- Create: `apps/app/src/components/explore/RefreshRunStatus.tsx`
- Modify: `apps/app/src/components/explore/ExplorePageClient.tsx`
- Modify: `apps/app/src/components/explore/ExploreTable.tsx`
- Modify: `apps/app/src/components/explore/CityDrawer.tsx`
- Test: `apps/app/src/components/explore/ExplorePageClient.test.tsx`

- [ ] **Step 1: Add failing UI test**

Add to `ExplorePageClient.test.tsx`:

```ts
it("starts a selected refresh run with force and max item flags", async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ run_id: "run-1", status: "queued" }), { status: 200 }),
  );
  global.fetch = fetchMock;

  render(<ExplorePageClient data={fixtureData} />);
  fireEvent.click(screen.getByRole("row", { name: /open austin/i }));
  fireEvent.click(screen.getByLabelText("Select roofing for fresh scan"));
  fireEvent.click(screen.getByRole("button", { name: /refresh selected/i }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    "/api/explore/refresh/runs",
    expect.objectContaining({ method: "POST" }),
  ));

  const body = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string);
  expect(body.scope).toBe("selected");
  expect(body.flags).toMatchObject({ force: false, max_items: 1, strategy_profile: "balanced" });
});
```

- [ ] **Step 2: Run failing UI test**

Run:

```bash
cd apps/app && npx vitest run src/components/explore/ExplorePageClient.test.tsx
```

Expected: FAIL because refresh selected UI does not exist.

- [ ] **Step 3: Create `RefreshControlPanel`**

Create `apps/app/src/components/explore/RefreshControlPanel.tsx`:

```tsx
"use client";

import { Icon, I } from "@/lib/icons";

interface RefreshControlPanelProps {
  selectedCount: number;
  staleCount: number;
  cadenceDays: number;
  disabled?: boolean;
  onRefreshSelected: () => void;
  onRefreshStale: () => void;
  onRefreshAllVisible: () => void;
}

export default function RefreshControlPanel({
  selectedCount,
  staleCount,
  cadenceDays,
  disabled = false,
  onRefreshSelected,
  onRefreshStale,
  onRefreshAllVisible,
}: RefreshControlPanelProps) {
  return (
    <section aria-label="Explore refresh controls" className="surface" style={{ padding: 14 }}>
      <div className="kicker">Refresh control</div>
      <p className="page-sub" style={{ margin: "4px 0 12px" }}>
        Base reporting refreshes every {cadenceDays} days.
      </p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button type="button" className="btn-primary" disabled={disabled || selectedCount === 0} onClick={onRefreshSelected}>
          <Icon d={I.refresh ?? I.sparkle} /> Refresh selected
        </button>
        <button type="button" className="btn-ghost" disabled={disabled || staleCount === 0} onClick={onRefreshStale}>
          Refresh stale ({staleCount})
        </button>
        <button type="button" className="btn-ghost" disabled={disabled} onClick={onRefreshAllVisible}>
          Refresh all visible
        </button>
      </div>
    </section>
  );
}
```

If `I.refresh` does not exist, add it to `apps/app/src/lib/icons.tsx`; otherwise use the existing closest icon.

- [ ] **Step 4: Create run status component**

Create `apps/app/src/components/explore/RefreshRunStatus.tsx`:

```tsx
import Link from "next/link";
import type { ExploreRefreshRunResponse } from "@/lib/explore-refresh/types";

interface RefreshRunStatusProps {
  run: ExploreRefreshRunResponse | null;
  error: string | null;
}

export default function RefreshRunStatus({ run, error }: RefreshRunStatusProps) {
  if (!run && !error) return null;
  if (error) {
    return <div role="alert" className="surface" style={{ padding: 12 }}>{error}</div>;
  }
  return (
    <div role="status" className="surface" style={{ padding: 12 }}>
      Refresh run {run?.run_id} is {run?.status}.{" "}
      {run ? <Link href={`/explore?refresh_run=${encodeURIComponent(run.run_id)}`}>View status</Link> : null}
    </div>
  );
}
```

- [ ] **Step 5: Wire panel into ExplorePageClient**

Add a `startRefreshRun` helper:

```ts
async function startRefreshRun(scope: "selected" | "visible" | "stale" | "all") {
  setRefreshError(null);
  setRefreshSubmitting(true);
  try {
    const response = await fetch("/api/explore/refresh/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scope,
        target_ids: selectedScores.map((score) => score.refresh_target_id).filter(Boolean),
        filters,
        flags: {
          force: false,
          dry_run: false,
          strategy_profile: "balanced",
          max_items: scope === "selected" ? selectedScores.length : 50,
          concurrency: 2,
        },
      }),
    });
    const json = await response.json();
    if (!response.ok) {
      throw new Error(json?.message ?? "Refresh run could not be started.");
    }
    setRefreshRun(json);
  } catch (error) {
    setRefreshError(error instanceof Error ? error.message : "Refresh run failed.");
  } finally {
    setRefreshSubmitting(false);
  }
}
```

Render `RefreshControlPanel` above the table and `RefreshRunStatus` below it.

- [ ] **Step 6: Add stale badges**

In `ExploreTable.tsx`, add a compact "Stale" chip when any cached score in the city has `is_stale === true`.

In `CityDrawer.tsx`, show `Last refreshed` and `Next refresh` for each service when fields exist.

- [ ] **Step 7: Run UI tests**

Run:

```bash
cd apps/app && npx vitest run src/components/explore/ExplorePageClient.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Commit UI**

```bash
git add apps/app/src/components/explore apps/app/src/lib/explore-refresh/types.ts
git commit -m "feat: add explore refresh controls"
```

---

## Task 9: Scheduled Due Refresh

**Files:**
- Modify: `apps/app/src/app/api/explore/refresh/due/route.ts`
- Modify/Create: `vercel.json`
- Test: `apps/app/src/app/api/explore/refresh/due/route.test.ts`

- [ ] **Step 1: Add cron auth tests**

Create `apps/app/src/app/api/explore/refresh/due/route.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { POST } from "./route";

describe("POST /api/explore/refresh/due", () => {
  it("rejects requests without cron secret when configured", async () => {
    vi.stubEnv("EXPLORE_REFRESH_CRON_SECRET", "secret");
    const response = await POST(new Request("http://localhost/api/explore/refresh/due"));
    expect(response.status).toBe(401);
  });

  it("proxies due refresh with cron secret", async () => {
    vi.stubEnv("EXPLORE_REFRESH_CRON_SECRET", "secret");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ run_id: "run-1", status: "queued" }), { status: 200 }),
    );
    global.fetch = fetchMock;

    const response = await POST(
      new Request("http://localhost/api/explore/refresh/due", {
        method: "POST",
        headers: { "x-cron-secret": "secret" },
      }),
    );

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run cron tests**

Run:

```bash
cd apps/app && npx vitest run src/app/api/explore/refresh/due/route.test.ts
```

Expected: PASS after Task 6 route exists.

- [ ] **Step 3: Confirm cron config**

Ensure `vercel.json` contains only this new cron if it did not already exist:

```json
{
  "crons": [
    {
      "path": "/api/explore/refresh/due",
      "schedule": "0 9 * * *"
    }
  ]
}
```

- [ ] **Step 4: Commit scheduler**

```bash
git add apps/app/src/app/api/explore/refresh/due/route.test.ts apps/app/src/app/api/explore/refresh/due/route.ts vercel.json
git commit -m "feat: schedule explore refresh due check"
```

---

## Task 10: Trend Analysis Read Model

**Files:**
- Modify: `apps/app/src/lib/explore/load-explore-data.ts`
- Create: `apps/app/src/lib/explore/load-score-trends.ts`
- Test: `apps/app/src/lib/explore/load-score-trends.test.ts`

- [ ] **Step 1: Add trend loader test**

Create `apps/app/src/lib/explore/load-score-trends.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { loadScoreTrends } from "./load-score-trends";

function makeClient(rows: Array<Record<string, unknown>>) {
  const limit = vi.fn().mockResolvedValue({ data: rows, error: null });
  const order = vi.fn().mockReturnValue({ limit });
  const eq = vi.fn().mockReturnValue({ order });
  const select = vi.fn().mockReturnValue({ eq });
  const from = vi.fn().mockReturnValue({ select });
  return { from, calls: { from, select, eq, order, limit } };
}

describe("loadScoreTrends", () => {
  it("loads trend rows for one refresh target", async () => {
    const { from } = makeClient([
      { scored_at: "2026-04-01T00:00:00Z", opportunity_score: 70, opportunity_delta: null },
      { scored_at: "2026-05-01T00:00:00Z", opportunity_score: 82, opportunity_delta: 12 },
    ]);

    const rows = await loadScoreTrends({ from } as never, "target-1");

    expect(rows).toHaveLength(2);
    expect(rows[1].opportunity_delta).toBe(12);
  });
});
```

- [ ] **Step 2: Run failing trend test**

Run:

```bash
cd apps/app && npx vitest run src/lib/explore/load-score-trends.test.ts
```

Expected: FAIL because loader is missing.

- [ ] **Step 3: Add trend loader**

Create `apps/app/src/lib/explore/load-score-trends.ts`:

```ts
import type { SupabaseClient } from "@supabase/supabase-js";

export interface ExploreScoreTrendRow {
  scored_at: string;
  opportunity_score: number | null;
  opportunity_delta: number | null;
}

export async function loadScoreTrends(
  client: SupabaseClient,
  refreshTargetId: string,
): Promise<ExploreScoreTrendRow[]> {
  const { data, error } = await client
    .from("explore_target_trends")
    .select("scored_at, opportunity_score, opportunity_delta")
    .eq("target_id", refreshTargetId)
    .order("scored_at", { ascending: true })
    .limit(24);

  if (error) {
    throw new Error(`loadScoreTrends: ${error.message}`);
  }

  return (data ?? []) as ExploreScoreTrendRow[];
}
```

- [ ] **Step 4: Run trend tests**

Run:

```bash
cd apps/app && npx vitest run src/lib/explore/load-score-trends.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit trend loader**

```bash
git add apps/app/src/lib/explore/load-score-trends.ts apps/app/src/lib/explore/load-score-trends.test.ts
git commit -m "feat: add explore trend loader"
```

---

## Task 11: Verification And Documentation Closeout

**Files:**
- Modify: `.codex/project_context.md`
- Modify: `docs-canonical/ARCHITECTURE.md`
- Modify: `docs-canonical/DATA-MODEL.md`
- Modify: `docs-canonical/TEST-SPEC.md`

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
pytest tests/unit/test_explore_refresh_schema.py tests/unit/test_explore_refresh_service.py tests/unit/test_api_explore_refresh.py -v
```

Expected: PASS.

- [ ] **Step 2: Run focused app tests**

Run:

```bash
cd apps/app && npx vitest run \
  src/lib/explore \
  src/components/explore \
  src/app/api/explore/refresh
```

Expected: PASS.

- [ ] **Step 3: Run typecheck and lint**

Run:

```bash
cd apps/app && npx tsc --noEmit
npm run lint
```

Expected: Existing unrelated baseline failures may remain from older jest-dom matcher typing and admin lint. New refresh files should be absent from failure output.

- [ ] **Step 4: Run DocGuard**

Run:

```bash
npx docguard-cli guard
```

Expected: PASS or existing repo-wide WARN only. New data-model and architecture sections should not produce new high-severity failures.

- [ ] **Step 5: Update project context**

Add to `.codex/project_context.md`:

```markdown
## Explore Refresh Control

Explore refresh control stores a 30-day default freshness policy in `explore_refresh_policies`, queues manual/scheduled refresh runs through the FastAPI scoring bridge, and records `explore_report_snapshots` so every refreshed report can be analyzed as a score trend over time.
```

- [ ] **Step 6: Commit closeout docs**

```bash
git add .codex/project_context.md docs-canonical/ARCHITECTURE.md docs-canonical/DATA-MODEL.md docs-canonical/TEST-SPEC.md
git commit -m "docs: record explore refresh control"
```

---

## Acceptance Criteria

- The default refresh cadence is 30 days and is stored in `explore_refresh_policies.cadence_days`.
- Manual refresh supports selected, visible, stale, and all scopes.
- Refresh flags include `force`, `dry_run`, `strategy_profile`, `max_items`, and `concurrency`.
- The scheduler can run daily while only refreshing due targets.
- Every successful refresh links old report -> new report in `explore_refresh_run_items`.
- Every successful score writes an `explore_report_snapshots` row for trend analysis.
- `/explore` can display stale state and last/next refresh times without running paid scans.
- Fresh scans still use the existing scoring pipeline through FastAPI.
- No fake quota or mock production data is introduced.

## Self-Review

Spec coverage:
- Refresh parameters: Tasks 1, 2, 3, 6, 8, 9.
- Some/all refresh scopes: Tasks 5, 6, 8.
- 30-day default: Tasks 1, 2, 3, 9.
- Pipeline trigger: Tasks 3, 5, 6.
- Historical report trend model: Tasks 1, 2, 10.
- Docs and verification: Task 11.

Placeholder scan:
- No `TBD`, `TODO`, "implement later", or empty "add tests" instructions remain.

Type consistency:
- `ExploreRefreshFlags`, `RefreshTarget`, `ExploreRefreshRunRequest`, and database field names match across tasks.

---

Plan complete and saved to `docs/superpowers/plans/2026-05-13-explore-refresh-control.md`. Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
