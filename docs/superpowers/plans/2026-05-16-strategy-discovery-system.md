# Strategy Discovery System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the product strategy system from the v2 playbook so users can browse cached strategy opportunities and paid users can generate fresh strategy-backed reports.

**Architecture:** Treat strategies as presentation and ranking lenses over the existing Whidby market intelligence data, not as separate scoring engines. Reuse canonical source tables (`metros`, `census_cbp_establishments`, `niche_naics_mapping`, `seo_facts`, `seo_benchmarks`, `metro_score_v2`, `reports`) and extend the existing `DiscoveryService` boundary with a Supabase-backed market store, strategy run lineage, and consumer API routes.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, Supabase/Postgres migrations, pytest, Next.js App Router, TypeScript, Vitest, Supabase SSR, existing consumer entitlement helpers.

---

## Scope Check

This plan intentionally ships in testable vertical slices:

1. Document the accepted architecture in canonical docs first.
2. Add schema for strategy run lineage and strategy-only evidence.
3. Add pure strategy catalog/projection logic.
4. Back `DiscoveryService` with Supabase market data.
5. Add FastAPI discovery/run contracts.
6. Add consumer Next.js proxy routes with entitlement behavior.
7. Wire strategy gallery/detail screens to real APIs.
8. Add queued fresh-report fanout for paid multi-market runs.

Phase 2 concepts from the playbook (`cash_cow`) are represented behind flags/catalog status. Removed concepts from the old prototype (`blue_ocean`, `portfolio_builder`, `seasonal_arbitrage` as standalone strategies) must not be reintroduced as launch strategy routes.

## File Structure

### Canonical Docs

- Modify: `docs-canonical/ARCHITECTURE.md`
  - Add "Strategy Discovery System" under Consumer Product and Component Map.
- Modify: `docs-canonical/DATA-MODEL.md`
  - Add strategy DTOs, `strategy_runs`, `strategy_run_items`, `local_pack_listing_facts`, `metro_feature_vectors`, and optional `strategy_score_cache`.
- Modify: `docs-canonical/TEST-SPEC.md`
  - Add strategy discovery, Keyword Hijack, entitlement, queue, and frontend obligations.
- Modify: `.Codex/ACTIVE_WORK.md`
  - Add this feature as the next implementation slice only when the user confirms it is active work.

### Database

- Create: `supabase/migrations/017_strategy_discovery_system.sql`
  - Adds run lineage, local pack facts, feature vectors, optional cache projection, RLS.
- Modify: `tests/unit/test_supabase_schema.py`
  - Add schema assertions for strategy tables and policy-sensitive columns.

### Backend Domain

- Modify: `src/domain/lenses.py`
  - Replace old prototype-only strategy set with launch catalog: `balanced`, `easy_win`, `gbp_blitz`, `keyword_hijack`, `expand_conquer`, `cash_cow`, `ai_resilience`.
- Create: `src/domain/strategy_projection.py`
  - Pure formulas for strategy scores and warnings.
- Create: `src/domain/strategy_entities.py`
  - Typed dataclasses for strategy inputs, results, evidence, run status.
- Modify: `src/domain/queries.py`
  - Add `primary_keyword`, `reference_city_id`, `strategy_mode`, and `ai_resilience_filter`.
- Modify: `src/domain/services/discovery_service.py`
  - Route lens-specific scoring, reference-city expansion, and Keyword Hijack triples.
- Test: `tests/unit/test_strategy_projection.py`
- Test: `tests/unit/test_discovery_service_strategies.py`

### Backend Repository/API

- Create: `src/clients/strategy_repository.py`
  - Supabase adapter for cached market rows, local-pack facts, feature vectors, run lineage.
- Modify: `src/research_agent/api.py`
  - Extend `/api/discover`.
  - Add `/api/strategies`.
  - Add `/api/strategy-runs`.
  - Add `/api/strategy-runs/{run_id}`.
  - Add `/api/strategy-runs/{run_id}/reports`.
- Test: `tests/unit/test_strategy_repository.py`
- Test: `tests/unit/test_api_strategy_discovery.py`

### Consumer App

- Create: `apps/app/src/lib/strategies/types.ts`
- Create: `apps/app/src/lib/strategies/api.ts`
- Create: `apps/app/src/app/api/strategies/route.ts`
- Create: `apps/app/src/app/api/strategies/discover/route.ts`
- Create: `apps/app/src/app/api/strategies/runs/route.ts`
- Create: `apps/app/src/app/api/strategies/runs/[runId]/route.ts`
- Modify: `apps/app/src/app/(protected)/strategies/page.tsx`
- Create: `apps/app/src/app/(protected)/strategies/StrategiesGalleryClient.tsx`
- Modify/Create: `apps/app/src/app/(protected)/strategies/[id]/page.tsx`
- Create: `apps/app/src/app/(protected)/strategies/[id]/StrategyPageClient.tsx`
- Test: route tests under matching `route.test.ts`
- Test: strategy client tests under matching `.test.tsx`

---

## Task 1: Canonical Design Update

**Files:**
- Modify: `docs-canonical/ARCHITECTURE.md`
- Modify: `docs-canonical/DATA-MODEL.md`
- Modify: `docs-canonical/TEST-SPEC.md`

- [ ] **Step 1: Update architecture doc**

Add a "Strategy Discovery System" subsection under the consumer product area:

````markdown
### Strategy Discovery System

The consumer strategy system applies strategy-specific ranking lenses over the existing cached market intelligence read model. Launch strategies are `easy_win`, `gbp_blitz`, `keyword_hijack`, and `expand_conquer`; `cash_cow` is a phase-2/flagged strategy; AI resilience is a global modifier and warning, not a standalone strategy route.

The backend boundary is `DiscoveryService` plus a Supabase-backed `StrategyRepository`. Cached discovery reads from `metros`, `census_cbp_establishments`, `niche_naics_mapping`, `seo_facts`, `seo_benchmarks`, `metro_score_v2`, `reports`, `explore_report_snapshots`, `local_pack_listing_facts`, and `metro_feature_vectors`. Fresh report generation remains gated by consumer entitlements and routes through the existing FastAPI scoring bridge.

Data flow:

```text
DataForSEO / Census / CBP / BLS
  -> canonical facts and benchmarks
  -> strategy repository read model
  -> DiscoveryService strategy projection
  -> FastAPI /api/discover and /api/strategy-runs
  -> apps/app strategy gallery and detail screens
```
````

- [ ] **Step 2: Update data model doc**

Add entities for:

```markdown
| StrategyRun | Supabase `strategy_runs` table | id (UUID) | Cached/fresh strategy run envelope for account-scoped lineage |
| StrategyRunItem | Supabase `strategy_run_items` table | id (UUID) | Ranked strategy result row for a city/service/keyword |
| LocalPackListingFact | Supabase `local_pack_listing_facts` table | id (UUID) | Keyword + CBSA local pack listing evidence used by GBP Blitz and Keyword Hijack |
| MetroFeatureVector | Supabase `metro_feature_vectors` table | cbsa_code + feature_version | Derived metro similarity vector used by Expand & Conquer |
| StrategyScoreCache | Supabase `strategy_score_cache` table | strategy_id + cbsa_code + niche + keyword | Optional read-optimized strategy projection cache |
```

Add a DTO section for `StrategyResult`:

```markdown
| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `strategy_id` | string | Yes | `easy_win`, `gbp_blitz`, `keyword_hijack`, `expand_conquer`, or `cash_cow` |
| `rank` | integer | Yes | Rank within the returned result set |
| `score` | number | Yes | Strategy projection score, 0-100 |
| `cbsa_code` | string | Yes | Metro key |
| `niche_normalized` | string | Yes | Stable service key |
| `primary_keyword` | string | No | Required for Keyword Hijack rows |
| `evidence` | object | Yes | Strategy-specific signal facts used to explain the score |
| `warnings` | array | Yes | AI resilience, benchmark confidence, stale data, missing local pack, and entitlement warnings |
```

- [ ] **Step 3: Update test spec**

Add a "Strategy Discovery Tests" section:

```markdown
| Scope | Required Coverage | Required Tests |
| --- | --- | --- |
| Strategy catalog | Launch strategies, phase-2 status, AI modifier behavior | `tests/unit/test_strategy_projection.py` |
| Easy Win | Weak organic/local competition projection from V2 vector and facts | `tests/unit/test_strategy_projection.py` |
| GBP Blitz | Review barrier, review velocity, profile completeness, map-pack presence | `tests/unit/test_strategy_projection.py` |
| Keyword Hijack | Primary keyword volume floor, map-pack presence, exact-match GBP name availability | `tests/unit/test_strategy_projection.py`, `tests/unit/test_api_strategy_discovery.py` |
| Expand & Conquer | Feature-vector similarity plus equal-or-lower competition filter | `tests/unit/test_discovery_service_strategies.py` |
| Consumer entitlements | Free cached-only, plus/pro fresh strategy run allowed, batch cap enforced | `apps/app/src/app/api/strategies/runs/route.test.ts` |
```

- [ ] **Step 4: Run doc validation**

Run:

```bash
npx docguard-cli guard
git diff --check docs-canonical/ARCHITECTURE.md docs-canonical/DATA-MODEL.md docs-canonical/TEST-SPEC.md
```

Expected:

- `git diff --check` passes.
- `docguard-cli guard` either passes or reports only known repo-wide warnings. If npm registry/network blocks the command, record the exact failure in the final implementation report.

- [ ] **Step 5: Commit**

```bash
git add docs-canonical/ARCHITECTURE.md docs-canonical/DATA-MODEL.md docs-canonical/TEST-SPEC.md
git commit -m "docs: design strategy discovery system"
```

---

## Task 2: Strategy Schema Migration

**Files:**
- Create: `supabase/migrations/017_strategy_discovery_system.sql`
- Modify: `tests/unit/test_supabase_schema.py`

- [ ] **Step 1: Write failing schema tests**

Add tests that load migration SQL text and assert the expected tables/columns exist:

```python
from pathlib import Path


def test_strategy_discovery_migration_defines_run_tables() -> None:
    sql = Path("supabase/migrations/017_strategy_discovery_system.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS public.strategy_runs" in sql
    assert "CREATE TABLE IF NOT EXISTS public.strategy_run_items" in sql
    assert "account_id UUID" in sql
    assert "strategy_id TEXT NOT NULL" in sql
    assert "result_count INTEGER NOT NULL DEFAULT 0" in sql


def test_strategy_discovery_migration_defines_evidence_tables() -> None:
    sql = Path("supabase/migrations/017_strategy_discovery_system.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS public.local_pack_listing_facts" in sql
    assert "CREATE TABLE IF NOT EXISTS public.metro_feature_vectors" in sql
    assert "exact_match_name BOOLEAN NOT NULL DEFAULT FALSE" in sql
    assert "feature_vector JSONB NOT NULL" in sql
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest tests/unit/test_supabase_schema.py -k strategy_discovery -v
```

Expected: FAIL because `017_strategy_discovery_system.sql` does not exist.

- [ ] **Step 3: Create migration**

Create `supabase/migrations/017_strategy_discovery_system.sql`:

```sql
-- 017_strategy_discovery_system.sql
-- Strategy run lineage and strategy-specific evidence tables.

CREATE TABLE IF NOT EXISTS public.strategy_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES public.accounts(account_id) ON DELETE SET NULL,
    created_by_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    strategy_id TEXT NOT NULL CHECK (strategy_id IN (
        'easy_win', 'gbp_blitz', 'keyword_hijack', 'expand_conquer', 'cash_cow'
    )),
    mode TEXT NOT NULL DEFAULT 'cached' CHECK (mode IN ('cached', 'fresh')),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN (
        'queued', 'running', 'succeeded', 'partial_failed', 'failed', 'canceled'
    )),
    input_payload JSONB NOT NULL DEFAULT '{}',
    result_count INTEGER NOT NULL DEFAULT 0 CHECK (result_count >= 0),
    quota_consumed INTEGER NOT NULL DEFAULT 0 CHECK (quota_consumed >= 0),
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_strategy_runs_account_created
    ON public.strategy_runs(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.strategy_run_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES public.strategy_runs(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL CHECK (rank > 0),
    strategy_id TEXT NOT NULL,
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code),
    niche_normalized TEXT NOT NULL,
    niche_keyword TEXT NOT NULL,
    primary_keyword TEXT,
    report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    score NUMERIC(5,2) NOT NULL CHECK (score >= 0 AND score <= 100),
    evidence JSONB NOT NULL DEFAULT '{}',
    warnings JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_strategy_run_items_run_rank
    ON public.strategy_run_items(run_id, rank);

CREATE TABLE IF NOT EXISTS public.local_pack_listing_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code),
    niche_normalized TEXT NOT NULL,
    keyword TEXT NOT NULL,
    listing_rank INTEGER NOT NULL CHECK (listing_rank > 0),
    business_name TEXT NOT NULL,
    exact_match_name BOOLEAN NOT NULL DEFAULT FALSE,
    review_count INTEGER,
    review_velocity_monthly NUMERIC(8,2),
    rating NUMERIC(3,2),
    gbp_completeness NUMERIC(5,4),
    photo_count INTEGER,
    has_recent_post BOOLEAN,
    categories TEXT[] NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'dataforseo',
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (cbsa_code, niche_normalized, keyword, listing_rank, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_local_pack_facts_lookup
    ON public.local_pack_listing_facts(cbsa_code, niche_normalized, keyword, snapshot_date DESC);

CREATE TABLE IF NOT EXISTS public.metro_feature_vectors (
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code) ON DELETE CASCADE,
    feature_version TEXT NOT NULL DEFAULT 'strategy_v1',
    feature_vector JSONB NOT NULL,
    archetype TEXT,
    source_tables JSONB NOT NULL DEFAULT '[]',
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (cbsa_code, feature_version)
);

CREATE TABLE IF NOT EXISTS public.strategy_score_cache (
    strategy_id TEXT NOT NULL,
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code) ON DELETE CASCADE,
    niche_normalized TEXT NOT NULL,
    primary_keyword TEXT NOT NULL DEFAULT '',
    score NUMERIC(5,2) NOT NULL CHECK (score >= 0 AND score <= 100),
    evidence JSONB NOT NULL DEFAULT '{}',
    warnings JSONB NOT NULL DEFAULT '[]',
    source_report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    scored_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (strategy_id, cbsa_code, niche_normalized, primary_keyword)
);

ALTER TABLE public.strategy_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategy_run_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.local_pack_listing_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.metro_feature_vectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategy_score_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY strategy_runs_service_role_all
    ON public.strategy_runs FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY strategy_run_items_service_role_all
    ON public.strategy_run_items FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY local_pack_listing_facts_read_all
    ON public.local_pack_listing_facts FOR SELECT
    USING (true);

CREATE POLICY metro_feature_vectors_read_all
    ON public.metro_feature_vectors FOR SELECT
    USING (true);

CREATE POLICY strategy_score_cache_read_all
    ON public.strategy_score_cache FOR SELECT
    USING (true);
```

- [ ] **Step 4: Run schema tests**

Run:

```bash
python -m pytest tests/unit/test_supabase_schema.py -k strategy_discovery -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/017_strategy_discovery_system.sql tests/unit/test_supabase_schema.py
git commit -m "feat: add strategy discovery schema"
```

---

## Task 3: Pure Strategy Projection

**Files:**
- Create: `src/domain/strategy_entities.py`
- Create: `src/domain/strategy_projection.py`
- Modify: `src/domain/lenses.py`
- Test: `tests/unit/test_strategy_projection.py`

- [ ] **Step 1: Write failing projection tests**

Create `tests/unit/test_strategy_projection.py`:

```python
from src.domain.strategy_projection import (
    project_easy_win,
    project_gbp_blitz,
    project_keyword_hijack,
    project_ai_resilience_warning,
)


def test_easy_win_rewards_demand_and_low_difficulty() -> None:
    row = {
        "demand_strength": 140,
        "organic_difficulty": 22,
        "local_difficulty": 35,
        "ai_resilience": 88,
        "benchmark_confidence": "high",
    }
    result = project_easy_win(row)
    assert result.score >= 80
    assert result.evidence["organic_difficulty"] == 22


def test_gbp_blitz_rewards_low_review_barrier() -> None:
    result = project_gbp_blitz({
        "demand_strength": 120,
        "local_pack_present": True,
        "top3_review_count_min": 12,
        "top3_review_velocity_avg": 0.8,
        "gbp_completeness_avg": 0.42,
    })
    assert result.score >= 75
    assert result.evidence["top3_review_count_min"] == 12


def test_keyword_hijack_requires_volume_pack_and_available_name() -> None:
    result = project_keyword_hijack({
        "search_volume_monthly": 260,
        "cpc_usd": 38.5,
        "local_pack_present": True,
        "exact_match_name_taken": False,
        "commercial_intent_score": 0.9,
    })
    assert result.score >= 80
    assert "exact_match_name_available" in result.evidence


def test_keyword_hijack_blocks_low_volume() -> None:
    result = project_keyword_hijack({
        "search_volume_monthly": 90,
        "cpc_usd": 38.5,
        "local_pack_present": True,
        "exact_match_name_taken": False,
        "commercial_intent_score": 0.9,
    })
    assert result.score == 0
    assert "primary_keyword_volume_below_200" in result.warnings


def test_ai_resilience_warning_flags_not_hides() -> None:
    warning = project_ai_resilience_warning({"aio_trigger_rate": 0.22, "ai_resilience": 52})
    assert warning["code"] == "ai_resilience_risk"
    assert warning["severity"] == "warning"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest tests/unit/test_strategy_projection.py -v
```

Expected: FAIL because `src.domain.strategy_projection` does not exist.

- [ ] **Step 3: Add strategy entity dataclasses**

Create `src/domain/strategy_entities.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StrategyProjection:
    strategy_id: str
    score: float
    evidence: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Add projection formulas**

Create `src/domain/strategy_projection.py`:

```python
from __future__ import annotations

from typing import Any

from src.domain.strategy_entities import StrategyProjection


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def project_easy_win(row: dict[str, Any]) -> StrategyProjection:
    demand = min(float(row.get("demand_strength") or 0), 200.0) / 2.0
    organic_ease = 100.0 - float(row.get("organic_difficulty") or 100)
    local_raw = row.get("local_difficulty")
    local_ease = 65.0 if local_raw is None else 100.0 - float(local_raw)
    ai = float(row.get("ai_resilience") or 50)
    score = _clamp((demand * 0.25) + (organic_ease * 0.45) + (local_ease * 0.20) + (ai * 0.10))
    warnings: list[str] = []
    if row.get("benchmark_confidence") in {"low", "insufficient"}:
        warnings.append("benchmark_confidence_low")
    return StrategyProjection(
        strategy_id="easy_win",
        score=round(score, 2),
        evidence={
            "demand_strength": row.get("demand_strength"),
            "organic_difficulty": row.get("organic_difficulty"),
            "local_difficulty": row.get("local_difficulty"),
            "ai_resilience": row.get("ai_resilience"),
        },
        warnings=warnings,
    )


def project_gbp_blitz(row: dict[str, Any]) -> StrategyProjection:
    if not row.get("local_pack_present", True):
        return StrategyProjection(
            strategy_id="gbp_blitz",
            score=0.0,
            evidence={"local_pack_present": False},
            warnings=["no_local_pack_detected"],
        )
    demand = min(float(row.get("demand_strength") or 0), 200.0) / 2.0
    review_floor = float(row.get("top3_review_count_min") or 100)
    velocity = float(row.get("top3_review_velocity_avg") or 5)
    completeness = float(row.get("gbp_completeness_avg") or 1.0)
    review_ease = 100.0 - min(review_floor, 100.0)
    velocity_ease = 100.0 - min(velocity * 25.0, 100.0)
    completeness_gap = (1.0 - min(completeness, 1.0)) * 100.0
    score = _clamp((demand * 0.20) + (review_ease * 0.40) + (velocity_ease * 0.20) + (completeness_gap * 0.20))
    return StrategyProjection(
        strategy_id="gbp_blitz",
        score=round(score, 2),
        evidence={
            "top3_review_count_min": row.get("top3_review_count_min"),
            "top3_review_velocity_avg": row.get("top3_review_velocity_avg"),
            "gbp_completeness_avg": row.get("gbp_completeness_avg"),
        },
    )


def project_keyword_hijack(row: dict[str, Any]) -> StrategyProjection:
    volume = float(row.get("search_volume_monthly") or 0)
    if volume < 200:
        return StrategyProjection(
            strategy_id="keyword_hijack",
            score=0.0,
            evidence={"search_volume_monthly": volume},
            warnings=["primary_keyword_volume_below_200"],
        )
    if not row.get("local_pack_present", False):
        return StrategyProjection(
            strategy_id="keyword_hijack",
            score=0.0,
            evidence={"local_pack_present": False},
            warnings=["no_local_pack_detected"],
        )
    if row.get("exact_match_name_taken", False):
        return StrategyProjection(
            strategy_id="keyword_hijack",
            score=0.0,
            evidence={"exact_match_name_available": False},
            warnings=["exact_match_gbp_name_taken"],
        )
    volume_score = min(volume / 500.0, 1.0) * 45.0
    cpc_score = min(float(row.get("cpc_usd") or 0) / 50.0, 1.0) * 30.0
    intent_score = min(float(row.get("commercial_intent_score") or 0.5), 1.0) * 25.0
    return StrategyProjection(
        strategy_id="keyword_hijack",
        score=round(_clamp(volume_score + cpc_score + intent_score), 2),
        evidence={
            "search_volume_monthly": volume,
            "cpc_usd": row.get("cpc_usd"),
            "local_pack_present": True,
            "exact_match_name_available": True,
        },
    )


def project_ai_resilience_warning(row: dict[str, Any]) -> dict[str, str] | None:
    aio_rate = float(row.get("aio_trigger_rate") or 0)
    score = float(row.get("ai_resilience") or 100)
    if aio_rate >= 0.15 or score < 65:
        return {
            "code": "ai_resilience_risk",
            "severity": "warning",
            "message": "AI Overview exposure is elevated for this market.",
        }
    return None
```

- [ ] **Step 5: Update lens catalog**

Modify `src/domain/lenses.py` so `LENS_REGISTRY` includes `keyword_hijack` and removes launch-ineligible standalone routes from default user-facing output. Keep `cash_cow` but mark as phase 2 via metadata if you add metadata; otherwise leave it registered for API compatibility.

- [ ] **Step 6: Run tests**

Run:

```bash
python -m pytest tests/unit/test_strategy_projection.py -v
python -m pytest tests/unit/test_api_discover.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/domain/strategy_entities.py src/domain/strategy_projection.py src/domain/lenses.py tests/unit/test_strategy_projection.py
git commit -m "feat: add strategy projection formulas"
```

---

## Task 4: Supabase Strategy Repository

**Files:**
- Create: `src/clients/strategy_repository.py`
- Test: `tests/unit/test_strategy_repository.py`

- [ ] **Step 1: Write failing repository tests**

Create `tests/unit/test_strategy_repository.py`:

```python
from src.clients.strategy_repository import StrategyRepository


class FakeTable:
    def __init__(self):
        self.calls = []

    def select(self, value):
        self.calls.append(("select", value))
        return self

    def eq(self, key, value):
        self.calls.append(("eq", key, value))
        return self

    def limit(self, value):
        self.calls.append(("limit", value))
        return self

    def execute(self):
        return type("Response", (), {"data": []})()


class FakeClient:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        self.tables[name] = FakeTable()
        return self.tables[name]


def test_fetch_cached_markets_reads_canonical_tables() -> None:
    client = FakeClient()
    repo = StrategyRepository(client)
    repo.fetch_cached_markets(strategy_id="easy_win", limit=25)
    assert "metro_score_v2" in client.tables
    assert ("limit", 25) in client.tables["metro_score_v2"].calls


def test_fetch_local_pack_facts_filters_keyword_and_niche() -> None:
    client = FakeClient()
    repo = StrategyRepository(client)
    repo.fetch_local_pack_facts(cbsa_code="13820", niche_normalized="roofing", keyword="boise roofing")
    calls = client.tables["local_pack_listing_facts"].calls
    assert ("eq", "cbsa_code", "13820") in calls
    assert ("eq", "niche_normalized", "roofing") in calls
    assert ("eq", "keyword", "boise roofing") in calls
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest tests/unit/test_strategy_repository.py -v
```

Expected: FAIL because `StrategyRepository` does not exist.

- [ ] **Step 3: Implement repository adapter**

Create `src/clients/strategy_repository.py`:

```python
from __future__ import annotations

from typing import Any


class StrategyRepository:
    """Supabase adapter for strategy discovery read models and run lineage."""

    def __init__(self, supabase_client: Any):
        self._client = supabase_client

    def fetch_cached_markets(
        self,
        *,
        strategy_id: str,
        niche_normalized: str | None = None,
        cbsa_code: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = self._client.table("metro_score_v2").select("*")
        if niche_normalized:
            query = query.eq("niche_normalized", niche_normalized)
        if cbsa_code:
            query = query.eq("cbsa_code", cbsa_code)
        response = query.limit(limit).execute()
        return list(response.data or [])

    def fetch_local_pack_facts(
        self,
        *,
        cbsa_code: str,
        niche_normalized: str,
        keyword: str,
    ) -> list[dict[str, Any]]:
        response = (
            self._client.table("local_pack_listing_facts")
            .select("*")
            .eq("cbsa_code", cbsa_code)
            .eq("niche_normalized", niche_normalized)
            .eq("keyword", keyword)
            .limit(10)
            .execute()
        )
        return list(response.data or [])

    def fetch_feature_vector(self, *, cbsa_code: str, feature_version: str = "strategy_v1") -> dict[str, Any] | None:
        response = (
            self._client.table("metro_feature_vectors")
            .select("*")
            .eq("cbsa_code", cbsa_code)
            .eq("feature_version", feature_version)
            .limit(1)
            .execute()
        )
        rows = list(response.data or [])
        return rows[0] if rows else None
```

- [ ] **Step 4: Run tests**

Run:

```bash
python -m pytest tests/unit/test_strategy_repository.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/clients/strategy_repository.py tests/unit/test_strategy_repository.py
git commit -m "feat: add strategy repository adapter"
```

---

## Task 5: Strategy Discovery Service Behavior

**Files:**
- Modify: `src/domain/services/discovery_service.py`
- Modify: `src/domain/queries.py`
- Test: `tests/unit/test_discovery_service_strategies.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/unit/test_discovery_service_strategies.py`:

```python
from src.domain.entities import City, Market, Service
from src.domain.lenses import get_lens
from src.domain.queries import MarketQuery
from src.domain.services.discovery_service import DiscoveryService


class FakeStore:
    def query_markets(self, query):
        return [
            Market(
                city=City(city_id="boise-id", name="Boise", state="ID", population=235000, cbsa_code="14260"),
                service=Service(service_id="roofing", name="Roofing"),
                signals={
                    "strategy_row": {
                        "demand_strength": 140,
                        "organic_difficulty": 20,
                        "local_difficulty": 30,
                        "ai_resilience": 90,
                        "benchmark_confidence": "high",
                    }
                },
            )
        ]


def test_easy_win_uses_strategy_projection() -> None:
    service = DiscoveryService(market_store=FakeStore())
    results = service.discover_sync_for_test(MarketQuery(lens=get_lens("easy_win"), limit=10))
    assert results[0].lens_id == "easy_win"
    assert results[0].opportunity_score >= 80
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python -m pytest tests/unit/test_discovery_service_strategies.py -v
```

Expected: FAIL because `discover_sync_for_test` does not exist or the service does not use `strategy_row`.

- [ ] **Step 3: Implement a pure strategy scoring helper in service**

Modify `src/domain/services/discovery_service.py`:

```python
from src.domain.strategy_projection import (
    project_easy_win,
    project_gbp_blitz,
    project_keyword_hijack,
)


def _project_strategy_market(market: Market, lens_id: str) -> ScoredMarket:
    row = market.signals.get("strategy_row", {})
    if lens_id == "easy_win":
        projection = project_easy_win(row)
    elif lens_id == "gbp_blitz":
        projection = project_gbp_blitz(row)
    elif lens_id == "keyword_hijack":
        projection = project_keyword_hijack(row)
    else:
        return score_market(market, get_lens(lens_id))
    return ScoredMarket(
        market=market,
        opportunity_score=projection.score,
        lens_id=projection.strategy_id,
        score_breakdown=projection.evidence,
    )
```

Then update `discover()` to call `_project_strategy_market()` for launch strategy IDs before sorting.

- [ ] **Step 4: Add sync test helper only if needed**

If the service remains async-only, replace the test with:

```python
import pytest


@pytest.mark.asyncio
async def test_easy_win_uses_strategy_projection() -> None:
    service = DiscoveryService(market_store=FakeStore())
    results = await service.discover(MarketQuery(lens=get_lens("easy_win"), limit=10))
    assert results[0].lens_id == "easy_win"
    assert results[0].opportunity_score >= 80
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m pytest tests/unit/test_discovery_service_strategies.py tests/unit/test_api_discover.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/domain/services/discovery_service.py src/domain/queries.py tests/unit/test_discovery_service_strategies.py
git commit -m "feat: apply strategy projections in discovery"
```

---

## Task 6: FastAPI Strategy Contracts

**Files:**
- Modify: `src/research_agent/api.py`
- Test: `tests/unit/test_api_strategy_discovery.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/unit/test_api_strategy_discovery.py`:

```python
from fastapi.testclient import TestClient

from src.research_agent.api import app


def test_get_strategies_returns_launch_catalog() -> None:
    client = TestClient(app)
    resp = client.get("/api/strategies")
    assert resp.status_code == 200
    ids = [s["strategy_id"] for s in resp.json()["strategies"]]
    assert ids[:4] == ["easy_win", "gbp_blitz", "keyword_hijack", "expand_conquer"]
    assert "blue_ocean" not in ids


def test_discover_accepts_keyword_hijack_primary_keyword() -> None:
    client = TestClient(app)
    resp = client.post(
        "/api/discover",
        json={
            "lens_id": "keyword_hijack",
            "primary_keyword": "okc roof repair",
            "limit": 10,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["lens"]["lens_id"] == "keyword_hijack"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest tests/unit/test_api_strategy_discovery.py -v
```

Expected: FAIL because `/api/strategies` does not exist and `DiscoverRequest` lacks `primary_keyword`.

- [ ] **Step 3: Add request fields**

Modify `DiscoverRequest` in `src/research_agent/api.py`:

```python
class DiscoverRequest(BaseModel):
    lens_id: str = "balanced"
    city_filters: list[dict[str, Any]] = Field(default_factory=list)
    service_filters: list[dict[str, Any]] = Field(default_factory=list)
    primary_keyword: str | None = None
    reference_city_id: str | None = None
    ai_resilience_filter: bool = False
    portfolio_market_ids: list[str] | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
```

- [ ] **Step 4: Add strategy catalog endpoint**

Add to `src/research_agent/api.py`:

```python
@app.get("/api/strategies")
async def list_strategies() -> dict[str, Any]:
    return {
        "strategies": [
            {
                "strategy_id": "easy_win",
                "name": "Easy Win",
                "status": "launch",
                "input_shape": "city_service",
            },
            {
                "strategy_id": "gbp_blitz",
                "name": "GBP Blitz",
                "status": "launch",
                "input_shape": "city_service",
            },
            {
                "strategy_id": "keyword_hijack",
                "name": "Keyword Hijack",
                "status": "launch",
                "input_shape": "city_service_keyword",
            },
            {
                "strategy_id": "expand_conquer",
                "name": "Expand & Conquer",
                "status": "launch",
                "input_shape": "reference_city_service",
            },
            {
                "strategy_id": "cash_cow",
                "name": "Cash Cow",
                "status": "phase_2",
                "input_shape": "cached_scan",
            },
        ],
        "global_modifiers": [
            {
                "modifier_id": "ai_resilience",
                "name": "AI Resilience",
                "behavior": "warn_not_hide",
            }
        ],
    }
```

- [ ] **Step 5: Include new fields in response query echo**

Update `/api/discover` response:

```python
"query": {
    "city_filters": req.city_filters,
    "service_filters": req.service_filters,
    "primary_keyword": req.primary_keyword,
    "reference_city_id": req.reference_city_id,
    "ai_resilience_filter": req.ai_resilience_filter,
    "limit": req.limit,
    "offset": req.offset,
}
```

- [ ] **Step 6: Run tests**

Run:

```bash
python -m pytest tests/unit/test_api_strategy_discovery.py tests/unit/test_api_discover.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/research_agent/api.py tests/unit/test_api_strategy_discovery.py
git commit -m "feat: expose strategy discovery api"
```

---

## Task 7: Consumer Strategy Proxy Routes

**Files:**
- Create: `apps/app/src/lib/strategies/types.ts`
- Create: `apps/app/src/lib/strategies/api.ts`
- Create: `apps/app/src/app/api/strategies/route.ts`
- Create: `apps/app/src/app/api/strategies/discover/route.ts`
- Create: `apps/app/src/app/api/strategies/runs/route.ts`
- Test: `apps/app/src/app/api/strategies/route.test.ts`
- Test: `apps/app/src/app/api/strategies/discover/route.test.ts`
- Test: `apps/app/src/app/api/strategies/runs/route.test.ts`

- [ ] **Step 1: Write route tests**

Create `apps/app/src/app/api/strategies/runs/route.test.ts` with this entitlement expectation:

```typescript
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/account/entitlements", () => ({
  resolveEntitlementContext: vi.fn().mockResolvedValue({
    user: { id: "user-1" },
    entitlement: {
      account_id: "acct-1",
      plan_key: "free",
      monthly_report_limit: 0,
      subscription_status: "active",
    },
  }),
}));

describe("POST /api/strategies/runs", () => {
  it("blocks free users from fresh strategy runs", async () => {
    const { POST } = await import("./route");
    const req = new Request("http://localhost/api/strategies/runs", {
      method: "POST",
      body: JSON.stringify({ strategy_id: "easy_win", mode: "fresh" }),
    });
    const res = await POST(req as never);
    expect(res.status).toBe(403);
    expect(await res.json()).toMatchObject({
      code: "fresh_strategy_runs_not_included",
    });
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
npm --workspace apps/app test -- strategies/runs/route.test.ts
```

Expected: FAIL because route files do not exist.

- [ ] **Step 3: Add shared strategy types**

Create `apps/app/src/lib/strategies/types.ts`:

```typescript
export type StrategyId =
  | "easy_win"
  | "gbp_blitz"
  | "keyword_hijack"
  | "expand_conquer"
  | "cash_cow";

export type StrategyRunMode = "cached" | "fresh";

export interface StrategyDefinition {
  strategy_id: StrategyId;
  name: string;
  status: "launch" | "phase_2";
  input_shape: string;
}

export interface StrategyRunRequest {
  strategy_id: StrategyId;
  mode: StrategyRunMode;
  city?: string;
  state?: string;
  service?: string;
  primary_keyword?: string;
  reference_city_id?: string;
  limit?: number;
}
```

- [ ] **Step 4: Add proxy helper**

Create `apps/app/src/lib/strategies/api.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function proxyToStrategyApi(path: string, init?: RequestInit) {
  return fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
}
```

- [ ] **Step 5: Add routes**

Create `apps/app/src/app/api/strategies/runs/route.ts`:

```typescript
import { NextResponse } from "next/server";
import { resolveEntitlementContext } from "@/lib/account/entitlements";
import { createClient } from "@/lib/supabase/server";
import { proxyToStrategyApi } from "@/lib/strategies/api";

export async function POST(req: Request) {
  const supabase = await createClient();
  const { user, entitlement } = await resolveEntitlementContext(supabase);
  const body = await req.json();
  const mode = body.mode ?? "cached";

  if (mode === "fresh" && entitlement.monthly_report_limit <= 0) {
    return NextResponse.json(
      {
        status: "tier_limit",
        code: "fresh_strategy_runs_not_included",
        message: "Your current plan can browse cached strategy results but cannot generate fresh strategy runs.",
        tier: entitlement.plan_key,
      },
      { status: 403 },
    );
  }

  const upstream = await proxyToStrategyApi("/api/strategy-runs", {
    method: "POST",
    body: JSON.stringify({
      ...body,
      account_id: entitlement.account_id,
      created_by_user_id: user.id,
    }),
  });

  return NextResponse.json(await upstream.json(), { status: upstream.status });
}
```

- [ ] **Step 6: Add list/discover routes**

Create simple pass-through routes:

```typescript
// apps/app/src/app/api/strategies/route.ts
import { NextResponse } from "next/server";
import { proxyToStrategyApi } from "@/lib/strategies/api";

export async function GET() {
  const upstream = await proxyToStrategyApi("/api/strategies");
  return NextResponse.json(await upstream.json(), { status: upstream.status });
}
```

```typescript
// apps/app/src/app/api/strategies/discover/route.ts
import { NextResponse } from "next/server";
import { proxyToStrategyApi } from "@/lib/strategies/api";

export async function POST(req: Request) {
  const body = await req.json();
  const upstream = await proxyToStrategyApi("/api/discover", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return NextResponse.json(await upstream.json(), { status: upstream.status });
}
```

- [ ] **Step 7: Run tests**

Run:

```bash
npm --workspace apps/app test -- strategies
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/app/src/lib/strategies apps/app/src/app/api/strategies
git commit -m "feat: add consumer strategy api routes"
```

---

## Task 8: Strategy UI Integration

**Files:**
- Create/Modify: `apps/app/src/app/(protected)/strategies/page.tsx`
- Create: `apps/app/src/app/(protected)/strategies/StrategiesGalleryClient.tsx`
- Create/Modify: `apps/app/src/app/(protected)/strategies/[id]/page.tsx`
- Create: `apps/app/src/app/(protected)/strategies/[id]/StrategyPageClient.tsx`
- Test: `apps/app/src/app/(protected)/strategies/StrategiesGalleryClient.test.tsx`
- Test: `apps/app/src/app/(protected)/strategies/[id]/StrategyPageClient.test.tsx`

- [ ] **Step 1: Write UI tests**

Create `StrategiesGalleryClient.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import StrategiesGalleryClient from "./StrategiesGalleryClient";

describe("StrategiesGalleryClient", () => {
  it("shows launch strategies and omits cut prototype strategies", () => {
    render(<StrategiesGalleryClient strategies={[
      { strategy_id: "easy_win", name: "Easy Win", status: "launch", input_shape: "city_service" },
      { strategy_id: "gbp_blitz", name: "GBP Blitz", status: "launch", input_shape: "city_service" },
      { strategy_id: "keyword_hijack", name: "Keyword Hijack", status: "launch", input_shape: "city_service_keyword" },
      { strategy_id: "expand_conquer", name: "Expand & Conquer", status: "launch", input_shape: "reference_city_service" },
      { strategy_id: "cash_cow", name: "Cash Cow", status: "phase_2", input_shape: "cached_scan" },
    ]} />);
    expect(screen.getByText("Easy Win")).toBeTruthy();
    expect(screen.getByText("Keyword Hijack")).toBeTruthy();
    expect(screen.queryByText("Blue Ocean")).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
npm --workspace apps/app test -- StrategiesGalleryClient.test.tsx
```

Expected: FAIL because component does not exist in `apps/app`.

- [ ] **Step 3: Implement gallery**

Create `apps/app/src/app/(protected)/strategies/StrategiesGalleryClient.tsx`:

```tsx
"use client";

import Link from "next/link";
import type { StrategyDefinition } from "@/lib/strategies/types";

export default function StrategiesGalleryClient({ strategies }: { strategies: StrategyDefinition[] }) {
  const launch = strategies.filter((strategy) => strategy.status === "launch");
  const phase2 = strategies.filter((strategy) => strategy.status === "phase_2");

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <h1 className="font-serif text-4xl text-gray-950">Strategies</h1>
        <p className="mt-3 max-w-2xl text-sm text-gray-600">
          Use the same Whidby market data through the strategy lens that matches the job.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {launch.map((strategy) => (
            <Link
              key={strategy.strategy_id}
              href={`/strategies/${strategy.strategy_id}`}
              className="rounded-lg border border-gray-200 bg-white p-5 hover:border-gray-400"
            >
              <div className="text-lg font-semibold text-gray-950">{strategy.name}</div>
              <div className="mt-2 text-xs uppercase tracking-wide text-gray-400">{strategy.input_shape}</div>
            </Link>
          ))}
        </div>
        {phase2.length > 0 && (
          <section className="mt-10">
            <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">Phase 2</div>
            <div className="mt-3 grid gap-4 md:grid-cols-2">
              {phase2.map((strategy) => (
                <div key={strategy.strategy_id} className="rounded-lg border border-gray-200 bg-white p-5 opacity-70">
                  <div className="text-lg font-semibold text-gray-950">{strategy.name}</div>
                  <div className="mt-2 text-sm text-gray-500">Coming after launch validation.</div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
```

- [ ] **Step 4: Implement page loader**

Create/modify `apps/app/src/app/(protected)/strategies/page.tsx`:

```tsx
import StrategiesGalleryClient from "./StrategiesGalleryClient";

export default async function StrategiesPage() {
  const res = await fetch(`${process.env.NEXT_PUBLIC_APP_FRONTEND_URL ?? ""}/api/strategies`, {
    cache: "no-store",
  });
  const data = res.ok ? await res.json() : { strategies: [] };
  return <StrategiesGalleryClient strategies={data.strategies} />;
}
```

- [ ] **Step 5: Implement strategy detail client**

Create `apps/app/src/app/(protected)/strategies/[id]/StrategyPageClient.tsx` with inputs for each launch strategy and submit to `/api/strategies/discover`.

Minimum behavior:

```tsx
"use client";

import { useState } from "react";
import type { StrategyId } from "@/lib/strategies/types";

export default function StrategyPageClient({ strategyId }: { strategyId: StrategyId }) {
  const [city, setCity] = useState("");
  const [service, setService] = useState("");
  const [primaryKeyword, setPrimaryKeyword] = useState("");
  const [results, setResults] = useState<unknown[]>([]);

  async function runCachedDiscovery() {
    const res = await fetch("/api/strategies/discover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lens_id: strategyId,
        primary_keyword: strategyId === "keyword_hijack" ? primaryKeyword : undefined,
        city_filters: city ? [{ field: "name", operator: "like", value: city }] : [],
        service_filters: service ? [{ field: "name", operator: "like", value: service }] : [],
        limit: 25,
      }),
    });
    const data = await res.json();
    setResults(data.markets ?? []);
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl text-gray-950">{strategyId.replaceAll("_", " ")}</h1>
      <div className="mt-6 grid gap-3 md:grid-cols-3">
        <input value={city} onChange={(e) => setCity(e.target.value)} placeholder="City" className="rounded border px-3 py-2" />
        <input value={service} onChange={(e) => setService(e.target.value)} placeholder="Service" className="rounded border px-3 py-2" />
        {strategyId === "keyword_hijack" && (
          <input value={primaryKeyword} onChange={(e) => setPrimaryKeyword(e.target.value)} placeholder="Primary keyword" className="rounded border px-3 py-2" />
        )}
      </div>
      <button onClick={runCachedDiscovery} className="mt-4 rounded bg-gray-950 px-4 py-2 text-white">
        Search cached opportunities
      </button>
      <div className="mt-8 space-y-3">
        {results.map((result, index) => (
          <pre key={index} className="overflow-auto rounded border bg-white p-3 text-xs">
            {JSON.stringify(result, null, 2)}
          </pre>
        ))}
      </div>
    </main>
  );
}
```

- [ ] **Step 6: Run tests**

Run:

```bash
npm --workspace apps/app test -- StrategiesGalleryClient.test.tsx StrategyPageClient.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add 'apps/app/src/app/(protected)/strategies'
git commit -m "feat: add strategy discovery UI"
```

---

## Task 9: Fresh Strategy Runs and Batch Report Fanout

**Files:**
- Modify: `src/research_agent/api.py`
- Modify: `src/clients/strategy_repository.py`
- Modify: `apps/app/src/app/api/strategies/runs/route.ts`
- Test: `tests/unit/test_api_strategy_runs.py`
- Test: `apps/app/src/app/api/strategies/runs/route.test.ts`

- [ ] **Step 1: Write backend tests for batch cap**

Create `tests/unit/test_api_strategy_runs.py`:

```python
from fastapi.testclient import TestClient

from src.research_agent.api import app


def test_strategy_runs_reject_over_100_pair_fresh_run() -> None:
    client = TestClient(app)
    resp = client.post(
        "/api/strategy-runs",
        json={
            "strategy_id": "easy_win",
            "mode": "fresh",
            "targets": [{"cbsa_code": str(i), "niche_normalized": "roofing"} for i in range(101)],
        },
    )
    assert resp.status_code == 400
    assert "100" in resp.json()["detail"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest tests/unit/test_api_strategy_runs.py -v
```

Expected: FAIL because `/api/strategy-runs` does not exist.

- [ ] **Step 3: Add request model and endpoint**

Modify `src/research_agent/api.py`:

```python
class StrategyRunTarget(BaseModel):
    cbsa_code: str
    niche_normalized: str
    niche_keyword: str | None = None
    primary_keyword: str | None = None


class StrategyRunRequest(BaseModel):
    strategy_id: str
    mode: str = "cached"
    targets: list[StrategyRunTarget] = Field(default_factory=list)
    account_id: str | None = None
    created_by_user_id: str | None = None


@app.post("/api/strategy-runs")
async def create_strategy_run(req: StrategyRunRequest) -> dict[str, Any]:
    if req.mode == "fresh" and len(req.targets) > 100:
        raise HTTPException(status_code=400, detail="Fresh strategy runs are capped at 100 city-service pairs.")
    return {
        "run_id": str(uuid.uuid4()),
        "strategy_id": req.strategy_id,
        "mode": req.mode,
        "status": "queued" if req.mode == "fresh" else "succeeded",
        "target_count": len(req.targets),
    }
```

Ensure `uuid` is imported.

- [ ] **Step 4: Add repository persistence methods**

Add to `src/clients/strategy_repository.py`:

```python
def create_run(self, payload: dict[str, Any]) -> dict[str, Any]:
    response = self._client.table("strategy_runs").insert(payload).execute()
    rows = list(response.data or [])
    return rows[0] if rows else {}


def insert_run_items(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    response = self._client.table("strategy_run_items").insert(rows).execute()
    return list(response.data or [])
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m pytest tests/unit/test_api_strategy_runs.py tests/unit/test_strategy_repository.py -v
npm --workspace apps/app test -- strategies/runs/route.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/research_agent/api.py src/clients/strategy_repository.py tests/unit/test_api_strategy_runs.py apps/app/src/app/api/strategies/runs/route.ts apps/app/src/app/api/strategies/runs/route.test.ts
git commit -m "feat: queue fresh strategy runs"
```

---

## Task 10: Final Verification and Active Work Closeout

**Files:**
- Modify: `.Codex/ACTIVE_WORK.md`
- Modify: `.Codex/project_context.md`

- [ ] **Step 1: Run backend verification**

Run:

```bash
ruff check src tests
python -m pytest tests/unit/test_strategy_projection.py tests/unit/test_strategy_repository.py tests/unit/test_discovery_service_strategies.py tests/unit/test_api_strategy_discovery.py tests/unit/test_api_strategy_runs.py -v
python -m pytest tests/unit/test_supabase_schema.py -k "strategy_discovery or existing_schema_checks" -v
```

Expected: PASS.

- [ ] **Step 2: Run frontend verification**

Run:

```bash
npm --workspace apps/app test -- strategies
npm run lint
```

Expected: PASS.

- [ ] **Step 3: Run docs verification**

Run:

```bash
npx docguard-cli guard
git diff --check
```

Expected: PASS or known DocGuard WARN-only state. Record exact failure if npm registry/network blocks DocGuard.

- [ ] **Step 4: Update project context**

Append concise completion context to `.Codex/project_context.md`:

```markdown
## Strategy Discovery System

Implemented strategy discovery as cached-first lenses over canonical market data. Launch strategies are Easy Win, GBP Blitz, Keyword Hijack, and Expand & Conquer; Cash Cow remains phase 2; AI resilience is a warning/modifier. Added strategy run lineage, local-pack facts, metro feature vectors, strategy projection formulas, FastAPI discovery/run contracts, and consumer strategy routes/UI.
```

- [ ] **Step 5: Update active work**

In `.Codex/ACTIVE_WORK.md`, mark this slice complete and list the next work:

```markdown
## Strategy Discovery System

Status: implemented; pending live data validation.

Next:
- Backfill `local_pack_listing_facts` from the next paid DataForSEO collection.
- Compute `metro_feature_vectors` for all benchmark-ready metros.
- Run a paid Keyword Hijack subset for 10 benchmark-ready city/service/keyword triples.
```

- [ ] **Step 6: Commit**

```bash
git add .Codex/ACTIVE_WORK.md .Codex/project_context.md
git commit -m "docs: close out strategy discovery implementation"
```

---

## Self-Review

Spec coverage:

- Launch strategies: covered by Tasks 3, 5, 6, 8.
- AI resilience as modifier: covered by Tasks 1, 3, 6.
- Data model: covered by Tasks 1, 2.
- Cached discovery: covered by Tasks 4, 5, 6, 7, 8.
- Fresh paid runs: covered by Tasks 7, 9.
- Entitlements: covered by Task 7.
- Canonical docs: covered by Tasks 1 and 10.

Known follow-up after this plan:

- The first implementation can return cached results from `metro_score_v2`; full high-quality GBP Blitz and Keyword Hijack ranking depends on populating `local_pack_listing_facts` in a paid/provider run.
- Expand & Conquer quality depends on `metro_feature_vectors`; first implementation can compute vectors from current `metros` data and improve as more ACS/CBP fields are populated.

Plan complete and saved to `docs/superpowers/plans/2026-05-16-strategy-discovery-system.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.
