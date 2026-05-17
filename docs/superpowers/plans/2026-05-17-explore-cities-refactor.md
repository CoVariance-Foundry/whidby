# Explore Cities Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `/explore` into a prototype-aligned city-first market discovery surface backed by service-aware, backend-owned Explore data.

**Architecture:** Keep the proto's city-first browsing shape, but treat density and growth as service-aware city-service metrics, not city-only facts. Add a precomputed `explore_market_cells` read model for latency-sensitive sorting/filtering while keeping `src/domain/explore/metrics.py` and `ExploreCityService` as the source of truth for formulas and fallback composition. Strategies should consume the same market-cell read model as guided ranking lenses, not become a duplicate Explore table.

**Tech Stack:** Next.js App Router, React, TypeScript, Supabase/Postgres/PostgREST, FastAPI, Python domain services, pytest, Vitest, DocGuard.

---

## Current Findings

- Prototype source: `/Users/antwoineflowers/Desktop/development/covariance/whidby-ux-proto/src/app/explore/ExploreClient.tsx`.
- Current app route: `apps/app/src/app/(protected)/explore/page.tsx`.
- Current loader: `apps/app/src/lib/explore/load-explore-data.ts` directly reads Supabase, limits metros with `METRO_LIMIT`, stitches reports and legacy `metro_scores`, and maps optional `public.metros.business_density_per_1k` / `establishment_growth_yoy` if present.
- Current client filtering: `apps/app/src/components/explore/ExplorePageClient.tsx` filters the loaded first page in React. Growth uses `city.establishment_growth_yoy < 3`, but canonical growth is a decimal fraction such as `0.03`.
- Current backend domain service: `src/domain/services/explore_city_service.py` computes service-aware density and growth only when a `service_filter` is supplied.
- Canonical docs already require backend Explore filtering, cursor pagination, service-aware density/growth, V2-over-legacy score preference, and no top-100 frontend universe.
- Production currently has only CBP 2023 in `public.census_cbp_establishments`; growth must stay `null` with `growth_available=false` until a prior CBP year is loaded.

## Product Decisions

- Default mode stays city-first like the prototype: browse metros, demographics, cached service counts, and best visible opportunity.
- Service-selected mode becomes the primary way to compare density and growth across cities. The table still lists cities, but score, density, growth, freshness, and best opportunity are for the selected service.
- When no service is selected, the table may show `representative_service` and metrics from the best cached service row, but labels must make that lineage clear. Do not imply city-level density/growth.
- Strategies page remains a guided lens experience over the same city-service read model. It should answer "which markets match this strategy?", while Explore answers "what is in this data layer and what can I inspect or scan?"
- Fresh scans must remain available for any city + service, including services that do not yet have cached rows. Refresh remains available only for cached targets with `refresh_target_id`.

## File Structure

### Source-of-truth docs

- Modify: `docs-canonical/ARCHITECTURE.md`
  - Clarify that `/explore` reads from `GET /api/explore/cities` and optionally `GET /api/explore/cities/{cbsa_code}`.
  - Add the `explore_market_cells` read model as a derived cache, not a source table.
  - Document Explore vs Strategies responsibility split.
- Modify: `docs-canonical/DATA-MODEL.md`
  - Add `ExploreMarketCell` fields and metric lineage.
  - Clarify density/growth display rules when service is not selected.
- Modify: `docs-canonical/TEST-SPEC.md`
  - Add tests for backend pagination, service-selected metrics, growth-disabled state, and no client-side top-100 truncation.
- Modify: `.Codex/ACTIVE_WORK.md`
  - Point current active work at this plan and note the implementation phases.

### Database read model

- Create: `supabase/migrations/018_explore_market_cells.sql`
  - Derived materialized view or refreshable table named `public.explore_market_cells`.
  - Index by `(niche_normalized, cbsa_code)`, `(cbsa_code)`, `presentation_score DESC`, and `latest_scored_at DESC`.
  - RLS or view exposure must allow authenticated read and service-role refresh.
- Create: `tests/unit/test_explore_market_cells_schema.py`
  - Structure tests for view/table name, metric columns, indexes, and non-duplicate source-table policy.

### Python backend

- Modify: `src/domain/explore/entities.py`
  - Add `ExploreServiceMetric` and `ExplorePageResult` typed shapes.
  - Add `representative_service` and `growth_available` fields where needed.
- Modify: `src/domain/services/explore_city_service.py`
  - Accept filters, sorting, cursor, and page size.
  - Prefer precomputed market cells when repository supports them.
  - Preserve existing pure metric fallback for tests and missing cache scenarios.
- Create: `src/clients/explore_repository.py`
  - Concrete Supabase repository implementing the domain protocol.
  - Reads `explore_market_cells` when present.
  - Falls back to canonical sources only in unit-tested local paths.
- Modify: `src/research_agent/api.py`
  - Add singleton `_get_explore_city_service()`.
  - Add `GET /api/explore/cities`.
  - Add `GET /api/explore/cities/{cbsa_code}`.
- Create: `tests/unit/test_explore_repository.py`
  - Fake Supabase client tests for query construction and row mapping.
- Create: `tests/unit/test_api_explore_cities.py`
  - FastAPI tests for filters, pagination, service mode, and growth-unavailable response.

### Next.js backend proxy and loader

- Create: `apps/app/src/app/api/explore/cities/route.ts`
  - Proxy query params to FastAPI.
  - Bound upstream errors using the same pattern as refresh routes.
- Create: `apps/app/src/app/api/explore/cities/[cbsaCode]/route.ts`
  - Proxy city detail reads to FastAPI.
- Create: `apps/app/src/app/api/explore/cities/route.test.ts`
  - Vitest coverage for query forwarding and bounded errors.
- Create: `apps/app/src/app/api/explore/cities/[cbsaCode]/route.test.ts`
  - Vitest coverage for city detail proxy.
- Modify: `apps/app/src/lib/explore/types.ts`
  - Align frontend types with backend DTOs.
- Modify: `apps/app/src/lib/explore/load-explore-data.ts`
  - Replace direct Supabase table stitching with backend route/client loading.
  - Remove `METRO_LIMIT` as the source universe.
  - Keep exported `loadExploreData` name if page/component tests already depend on it.
- Modify: `apps/app/src/app/(protected)/explore/page.tsx`
  - Build initial query from search params and call backend loader.

### React Explore surface

- Modify: `apps/app/src/components/explore/ExplorePageClient.tsx`
  - Move filters/sort/pagination to URL-backed server fetches instead of filtering first 100 rows.
  - Add city-first and service-selected behavior.
- Modify: `apps/app/src/components/explore/ExploreFilters.tsx`
  - Match prototype controls: population range, income range, service picker, growth toggle, states.
  - Disable growth toggle when `growth_available=false` for the selected service universe.
- Modify: `apps/app/src/components/explore/ExploreTable.tsx`
  - Keep prototype columns but use backend row fields.
  - Add lineage label when metrics come from representative service.
- Modify: `apps/app/src/components/explore/CityDrawer.tsx`
  - Show city stats and service rows from detail endpoint.
  - Add "scan another service" path for services without cached rows.
- Modify: `apps/app/src/components/explore/FreshScanConfirmation.tsx`
  - Allow selected cached services and typed/catalog services.
- Modify: `apps/app/src/components/explore/ServiceScoreRow.tsx`
  - Display V2/legacy score system, freshness, AI resilience, and metric lineage.
- Add tests near existing component tests if present; otherwise extend `apps/app/src/lib/explore/load-explore-data.test.ts` and route tests first, then add component tests when test harness supports rendered components.

## Implementation Tasks

### Task 1: Lock The Product Contract In Canonical Docs

**Files:**
- Modify: `docs-canonical/ARCHITECTURE.md`
- Modify: `docs-canonical/DATA-MODEL.md`
- Modify: `docs-canonical/TEST-SPEC.md`
- Modify: `.Codex/ACTIVE_WORK.md`

- [ ] **Step 1: Update architecture contract**

Add this responsibility split to `docs-canonical/ARCHITECTURE.md` under Explore Cities and Strategy Discovery:

```markdown
Explore is the flexible market data browser. It supports city-first browsing, service-selected city comparison, city detail inspection, cached target refresh, and fresh report starts.

Strategies are guided ranking lenses over the same city-service market-cell read model. They should not duplicate the Explore table; they package opinionated scoring, ordering, and explanation around strategy intent.
```

- [ ] **Step 2: Update data model contract**

Add `ExploreMarketCell` to `docs-canonical/DATA-MODEL.md`:

```markdown
### ExploreMarketCell (derived read model)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `cbsa_code` | text | Yes | Metro key from `public.metros` |
| `niche_normalized` | text | Yes | Service key from `public.niche_naics_mapping` or cached score row |
| `niche_keyword` | text | Yes | Display service label |
| `presentation_score` | integer | No | V2 lens projection when present, else legacy opportunity score |
| `score_system` | text | Yes | `v2`, `legacy`, or `none` |
| `business_density_per_1k` | numeric | No | Weighted CBP establishments per 1,000 residents for this service |
| `establishment_growth_yoy` | numeric | No | Annualized establishment growth for this service |
| `growth_available` | boolean | Yes | False when no historical CBP prior year is loaded |
| `latest_scored_at` | timestamptz | No | Latest cached score time |
| `refresh_target_id` | uuid | No | Refresh target for cached rows |
| `stale` | boolean | Yes | Freshness relative to active cadence |

This is a derived read model for Explore latency. Canonical source tables remain `metros`, `census_cbp_establishments`, `niche_naics_mapping`, `reports`, `metro_scores`, `metro_score_v2`, and Explore refresh tables.
```

- [ ] **Step 3: Update test obligations**

Add these rows to `docs-canonical/TEST-SPEC.md`:

```markdown
| Explore market-cell read model | Materialized read model over canonical tables | Exposes service-aware density/growth without creating duplicate source tables |
| Explore service-selected mode | `/api/explore/cities?service=roofing` | Returns rows where density, growth, score, and freshness belong to roofing |
| Explore default mode lineage | `/api/explore/cities` with no service | Does not present density/growth as city-only facts unless row includes `metric_service` lineage |
| Explore frontend pagination | Next loader and page controls | Does not filter or sort only the first 100 metros in React |
| Explore growth unavailable | CBP only has one year | API returns `growth_available=false`; UI disables growth-only filtering |
```

- [ ] **Step 4: Run docs validation**

Run:

```bash
git diff --check
npx docguard-cli guard
```

Expected:
- `git diff --check` passes.
- `docguard-cli guard` may return repo-wide warnings; record whether Explore-specific traceability or schema-contract checks failed.

- [ ] **Step 5: Commit**

```bash
git add docs-canonical/ARCHITECTURE.md docs-canonical/DATA-MODEL.md docs-canonical/TEST-SPEC.md .Codex/ACTIVE_WORK.md
git commit -m "docs: define explore cities refactor contract"
```

### Task 2: Add The Derived Explore Market-Cell Schema

**Files:**
- Create: `supabase/migrations/018_explore_market_cells.sql`
- Create: `tests/unit/test_explore_market_cells_schema.py`

- [ ] **Step 1: Write schema structure tests**

Create `tests/unit/test_explore_market_cells_schema.py`:

```python
from pathlib import Path


MIGRATION = Path("supabase/migrations/018_explore_market_cells.sql")


def _sql() -> str:
    assert MIGRATION.exists(), f"Missing migration: {MIGRATION}"
    return MIGRATION.read_text()


def test_explore_market_cells_is_derived_read_model() -> None:
    sql = _sql()

    assert "explore_market_cells" in sql
    assert "public.metros" in sql
    assert "public.census_cbp_establishments" in sql
    assert "public.niche_naics_mapping" in sql
    assert "public.metro_score_v2" in sql
    assert "public.metro_scores" in sql
    assert "CREATE TABLE public.cities" not in sql
    assert "_simplified" not in sql


def test_explore_market_cells_exposes_metric_contract() -> None:
    sql = _sql()

    for column in (
        "cbsa_code",
        "niche_normalized",
        "niche_keyword",
        "presentation_score",
        "score_system",
        "business_density_per_1k",
        "establishment_growth_yoy",
        "growth_available",
        "latest_scored_at",
        "refresh_target_id",
        "stale",
    ):
        assert column in sql


def test_explore_market_cells_has_lookup_indexes() -> None:
    sql = _sql()

    assert "idx_explore_market_cells_niche_cbsa" in sql
    assert "idx_explore_market_cells_cbsa" in sql
    assert "idx_explore_market_cells_score" in sql
```

- [ ] **Step 2: Run failing schema tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/unit/test_explore_market_cells_schema.py -q
```

Expected: fail because `supabase/migrations/018_explore_market_cells.sql` does not exist.

- [ ] **Step 3: Add the migration**

Create `supabase/migrations/018_explore_market_cells.sql` with these concrete requirements:

```sql
-- Derived Explore read model. Source tables remain canonical.

DROP MATERIALIZED VIEW IF EXISTS public.explore_market_cells;

CREATE MATERIALIZED VIEW public.explore_market_cells AS
WITH latest_cbp_year AS (
    SELECT max(year) AS year FROM public.census_cbp_establishments
),
prior_cbp_year AS (
    SELECT max(c.year) AS year
    FROM public.census_cbp_establishments c
    CROSS JOIN latest_cbp_year latest
    WHERE c.year < latest.year
),
service_weights AS (
    SELECT
        niche_normalized,
        max(niche_keyword) AS niche_keyword,
        naics_code,
        weight
    FROM public.niche_naics_mapping
    GROUP BY niche_normalized, naics_code, weight
),
weighted_cbp AS (
    SELECT
        c.cbsa_code,
        w.niche_normalized,
        w.niche_keyword,
        c.year,
        sum(coalesce(c.est, 0) * w.weight)::numeric AS weighted_establishments
    FROM public.census_cbp_establishments c
    JOIN service_weights w ON w.naics_code = c.naics_code
    GROUP BY c.cbsa_code, w.niche_normalized, w.niche_keyword, c.year
),
latest_metrics AS (
    SELECT
        m.cbsa_code,
        m.niche_normalized,
        m.niche_keyword,
        m.weighted_establishments AS latest_weighted_establishments
    FROM weighted_cbp m
    JOIN latest_cbp_year y ON y.year = m.year
),
prior_metrics AS (
    SELECT
        m.cbsa_code,
        m.niche_normalized,
        m.weighted_establishments AS prior_weighted_establishments,
        y.year AS prior_year
    FROM weighted_cbp m
    JOIN prior_cbp_year y ON y.year = m.year
),
latest_legacy_scores AS (
    SELECT DISTINCT ON (ms.cbsa_code, lower(r.niche_keyword))
        ms.cbsa_code,
        lower(replace(r.niche_keyword, ' ', '_')) AS niche_normalized,
        r.niche_keyword,
        ms.report_id,
        ms.opportunity_score AS presentation_score,
        'legacy'::text AS score_system,
        r.created_at AS latest_scored_at,
        ms.serp_archetype,
        ms.ai_exposure,
        ms.difficulty_tier,
        ms.confidence_score,
        ms.ai_resilience_score
    FROM public.metro_scores ms
    JOIN public.reports r ON r.id = ms.report_id
    ORDER BY ms.cbsa_code, lower(r.niche_keyword), r.created_at DESC
),
latest_v2_scores AS (
    SELECT DISTINCT ON (v2.cbsa_code, v2.niche_normalized)
        v2.cbsa_code,
        v2.niche_normalized,
        v2.niche_normalized AS niche_keyword,
        NULL::uuid AS report_id,
        greatest(
            coalesce(v2.demand_strength, 0) / 2,
            0
        )::integer AS presentation_score,
        'v2'::text AS score_system,
        NULL::timestamptz AS latest_scored_at,
        v2.benchmark_confidence,
        v2.demand_strength,
        v2.organic_difficulty,
        v2.local_difficulty,
        v2.monetization_signal,
        v2.ai_resilience
    FROM public.metro_score_v2 v2
    ORDER BY v2.cbsa_code, v2.niche_normalized
),
score_union AS (
    SELECT
        coalesce(v2.cbsa_code, legacy.cbsa_code) AS cbsa_code,
        coalesce(v2.niche_normalized, legacy.niche_normalized) AS niche_normalized,
        coalesce(v2.niche_keyword, legacy.niche_keyword) AS niche_keyword,
        coalesce(v2.report_id, legacy.report_id) AS report_id,
        coalesce(v2.presentation_score, legacy.presentation_score) AS presentation_score,
        CASE WHEN v2.cbsa_code IS NOT NULL THEN 'v2' ELSE legacy.score_system END AS score_system,
        coalesce(v2.latest_scored_at, legacy.latest_scored_at) AS latest_scored_at,
        legacy.serp_archetype,
        legacy.ai_exposure,
        legacy.difficulty_tier,
        legacy.confidence_score,
        coalesce(v2.ai_resilience, legacy.ai_resilience_score) AS ai_resilience_score,
        v2.benchmark_confidence,
        v2.demand_strength,
        v2.organic_difficulty,
        v2.local_difficulty,
        v2.monetization_signal
    FROM latest_legacy_scores legacy
    FULL OUTER JOIN latest_v2_scores v2
      ON v2.cbsa_code = legacy.cbsa_code
     AND v2.niche_normalized = legacy.niche_normalized
),
refresh AS (
    SELECT
        t.id AS refresh_target_id,
        t.cbsa_code,
        t.niche_normalized,
        t.next_refresh_at,
        t.latest_scored_at AS refresh_scored_at
    FROM public.explore_refresh_targets t
)
SELECT
    metro.cbsa_code,
    metro.cbsa_name,
    metro.state,
    metro.population,
    metro.population_class,
    metro.median_household_income_usd,
    metro.owner_occupancy_rate,
    metro.median_age_years,
    score.niche_normalized,
    score.niche_keyword,
    score.report_id,
    score.presentation_score,
    score.score_system,
    score.latest_scored_at,
    latest.latest_weighted_establishments,
    prior.prior_weighted_establishments,
    CASE
        WHEN metro.population IS NULL OR metro.population <= 0 OR latest.latest_weighted_establishments IS NULL
        THEN NULL
        ELSE round((latest.latest_weighted_establishments / metro.population) * 1000, 10)
    END AS business_density_per_1k,
    CASE
        WHEN prior.prior_weighted_establishments IS NULL
          OR prior.prior_weighted_establishments <= 0
          OR latest.latest_weighted_establishments IS NULL
          OR prior.prior_year IS NULL
        THEN NULL
        ELSE round(
            power(
                latest.latest_weighted_establishments / prior.prior_weighted_establishments,
                1.0 / ((SELECT year FROM latest_cbp_year) - prior.prior_year)
            ) - 1,
            10
        )
    END AS establishment_growth_yoy,
    prior.prior_weighted_establishments IS NOT NULL AS growth_available,
    refresh.refresh_target_id,
    refresh.next_refresh_at,
    CASE
        WHEN score.latest_scored_at IS NULL THEN false
        ELSE score.latest_scored_at < now() - interval '30 days'
    END AS stale,
    score.serp_archetype,
    score.ai_exposure,
    score.difficulty_tier,
    score.confidence_score,
    score.ai_resilience_score,
    score.benchmark_confidence,
    score.demand_strength,
    score.organic_difficulty,
    score.local_difficulty,
    score.monetization_signal
FROM public.metros metro
JOIN score_union score ON score.cbsa_code = metro.cbsa_code
LEFT JOIN latest_metrics latest
  ON latest.cbsa_code = score.cbsa_code
 AND latest.niche_normalized = score.niche_normalized
LEFT JOIN prior_metrics prior
  ON prior.cbsa_code = score.cbsa_code
 AND prior.niche_normalized = score.niche_normalized
LEFT JOIN refresh
  ON refresh.cbsa_code = score.cbsa_code
 AND refresh.niche_normalized = score.niche_normalized
WHERE metro.population IS NOT NULL;

CREATE UNIQUE INDEX idx_explore_market_cells_niche_cbsa
    ON public.explore_market_cells(niche_normalized, cbsa_code);
CREATE INDEX idx_explore_market_cells_cbsa
    ON public.explore_market_cells(cbsa_code);
CREATE INDEX idx_explore_market_cells_score
    ON public.explore_market_cells(presentation_score DESC NULLS LAST);
CREATE INDEX idx_explore_market_cells_scored_at
    ON public.explore_market_cells(latest_scored_at DESC NULLS LAST);

GRANT SELECT ON public.explore_market_cells TO authenticated;
GRANT SELECT ON public.explore_market_cells TO service_role;
```

Implementation note: if `metro_score_v2` does not have a scored timestamp in the current schema, leave `latest_scored_at` null for V2-only rows and use legacy report timestamps when a legacy row exists for the same city-service pair.

- [ ] **Step 4: Run schema tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/unit/test_explore_market_cells_schema.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/018_explore_market_cells.sql tests/unit/test_explore_market_cells_schema.py
git commit -m "feat: add explore market cell read model"
```

### Task 3: Add SupabaseExploreRepository

**Files:**
- Modify: `src/domain/explore/entities.py`
- Modify: `src/domain/services/explore_city_service.py`
- Create: `src/clients/explore_repository.py`
- Create: `tests/unit/test_explore_repository.py`
- Modify: `tests/unit/test_explore_city_service.py`

- [ ] **Step 1: Write repository mapping tests**

Create tests that assert:

```python
def test_repository_filters_market_cells_by_service_state_and_population() -> None:
    client = FakeSupabaseClient({"explore_market_cells": []})
    repo = SupabaseExploreRepository(client)

    repo.list_city_rows(
        service="roofing",
        states=["AZ", "CO"],
        population_min=50_000,
        population_max=300_000,
        income_min=50_000,
        sort="presentation_score",
        direction="desc",
        limit=25,
        cursor=None,
    )

    table = client.table_calls["explore_market_cells"][0]
    assert table.filters == [
        ("eq", "niche_normalized", "roofing"),
        ("in", "state", ["AZ", "CO"]),
        ("gte", "population", 50_000),
        ("lte", "population", 300_000),
        ("gte", "median_household_income_usd", 50_000),
    ]
    assert table.orders[0] == ("presentation_score", False)
    assert table.limit_value == 26
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/unit/test_explore_repository.py -q
```

Expected: fail because `src/clients/explore_repository.py` does not exist.

- [ ] **Step 3: Implement repository**

Implement `SupabaseExploreRepository` with:

```python
class SupabaseExploreRepository:
    def __init__(self, supabase_client: Any) -> None:
        self._client = supabase_client

    def list_city_rows(
        self,
        *,
        service: str | None,
        states: list[str],
        population_min: int | None,
        population_max: int | None,
        income_min: int | None,
        income_max: int | None,
        growing_only: bool,
        sort: str,
        direction: str,
        limit: int,
        cursor: str | None,
    ) -> list[dict[str, Any]]:
        ...

    def load_city_detail(self, cbsa_code: str) -> dict[str, Any] | None:
        ...
```

Rules:
- Normalize service using `src.pipeline.canonical_key.normalize_niche`.
- Fetch `limit + 1` rows to determine `next_cursor`.
- If `growing_only` is true and growth is unavailable, return no filtered rows only when the API request explicitly asked for growth filtering. Otherwise keep rows and set `growth_available=false`.
- Raise `RuntimeError("Supabase request failed: ...")` on Supabase errors, matching `StrategyRepository` style.

- [ ] **Step 4: Extend domain service**

Update `ExploreCityService` so:

```python
result = service.list_cities(
    service_filter="roofing",
    states=["AZ"],
    population_min=50_000,
    population_max=300_000,
    income_min=None,
    income_max=None,
    growing_only=False,
    sort="presentation_score",
    direction="desc",
    limit=25,
    cursor=None,
)
```

returns:

```python
{
    "cities": [...],
    "next_cursor": None,
    "growth_available": False,
    "service_filter": "roofing",
}
```

- [ ] **Step 5: Run focused backend tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/unit/test_explore_city_service.py tests/unit/test_explore_repository.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/domain/explore/entities.py src/domain/services/explore_city_service.py src/clients/explore_repository.py tests/unit/test_explore_city_service.py tests/unit/test_explore_repository.py
git commit -m "feat: add explore repository boundary"
```

### Task 4: Add FastAPI Explore Cities Endpoints

**Files:**
- Modify: `src/research_agent/api.py`
- Create: `tests/unit/test_api_explore_cities.py`

- [ ] **Step 1: Write API tests**

Create tests for:

```python
def test_get_explore_cities_forwards_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    service = FakeExploreCityService()
    monkeypatch.setattr(api_module, "_get_explore_city_service", lambda: service)
    client = TestClient(app)

    response = client.get(
        "/api/explore/cities",
        params={
            "service": "Roofing",
            "state": ["AZ", "CO"],
            "population_min": "50000",
            "income_min": "60000",
            "sort": "presentation_score",
            "direction": "desc",
            "limit": "25",
        },
    )

    assert response.status_code == 200
    assert service.calls[0]["service_filter"] == "Roofing"
    assert service.calls[0]["states"] == ["AZ", "CO"]
    assert service.calls[0]["population_min"] == 50000
```

Also test:
- invalid `limit=500` returns 400.
- `GET /api/explore/cities/38060` returns city detail.
- service unavailable returns 503 with sanitized detail.

- [ ] **Step 2: Run failing tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/unit/test_api_explore_cities.py -q
```

Expected: fail because endpoints do not exist.

- [ ] **Step 3: Implement FastAPI models and endpoints**

Add a singleton near existing `_get_strategy_repository()`:

```python
_EXPLORE_CITY_SERVICE: ExploreCityService | None = None


def _get_explore_city_service() -> ExploreCityService:
    global _EXPLORE_CITY_SERVICE
    if _EXPLORE_CITY_SERVICE is None:
        persistence = SupabasePersistence()
        repository = SupabaseExploreRepository(persistence._client)
        _EXPLORE_CITY_SERVICE = ExploreCityService(repository)
    return _EXPLORE_CITY_SERVICE
```

Endpoint behavior:
- `GET /api/explore/cities`
  - Query params: `service`, repeated `state`, `population_min`, `population_max`, `income_min`, `income_max`, `growing_only`, `sort`, `direction`, `limit`, `cursor`.
  - Limit range: 1 to 100.
  - Sort allowlist: `city`, `population`, `income`, `business_density`, `growth`, `cached_services`, `presentation_score`, `latest_scored_at`.
- `GET /api/explore/cities/{cbsa_code}`
  - Returns city demographics and cached service rows.
  - 404 when no city exists.

- [ ] **Step 4: Run API tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/unit/test_api_explore_cities.py tests/unit/test_explore_city_service.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/research_agent/api.py tests/unit/test_api_explore_cities.py
git commit -m "feat: expose explore cities api"
```

### Task 5: Replace Direct Supabase Explore Loading With Backend Proxy

**Files:**
- Create: `apps/app/src/app/api/explore/cities/route.ts`
- Create: `apps/app/src/app/api/explore/cities/[cbsaCode]/route.ts`
- Create: `apps/app/src/app/api/explore/cities/route.test.ts`
- Create: `apps/app/src/app/api/explore/cities/[cbsaCode]/route.test.ts`
- Modify: `apps/app/src/lib/explore/load-explore-data.ts`
- Modify: `apps/app/src/lib/explore/load-explore-data.test.ts`
- Modify: `apps/app/src/lib/explore/types.ts`
- Modify: `apps/app/src/app/(protected)/explore/page.tsx`

- [ ] **Step 1: Write route proxy tests**

Test success:

```ts
it("forwards explore city filters to FastAPI", async () => {
  process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
  global.fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ cities: [], next_cursor: null, growth_available: false }), {
      status: 200,
    }),
  );

  const req = new Request(
    "http://localhost/api/explore/cities?service=roofing&state=AZ&limit=25",
  );
  const res = await GET(req as never);

  expect(res.status).toBe(200);
  expect(global.fetch).toHaveBeenCalledWith(
    "https://api.example.test/api/explore/cities?service=roofing&state=AZ&limit=25",
    expect.objectContaining({ cache: "no-store" }),
  );
});
```

- [ ] **Step 2: Run failing route tests**

Run:

```bash
npm --workspace apps/app test -- api/explore/cities
```

Expected: fail because route files do not exist.

- [ ] **Step 3: Implement route proxies**

Use the bounded upstream error pattern from `apps/app/src/app/api/explore/refresh/runs/route.ts`. Keep:

```ts
const DEFAULT_API_BASE = "http://localhost:8000";
const MAX_UPSTREAM_ERROR_CHARS = 500;
```

Rules:
- Preserve repeated `state` query params.
- Do not pass Supabase service role keys through Next routes.
- Return `{ status: "unavailable", message, upstream_status }` with status 502 for upstream failures.

- [ ] **Step 4: Update frontend types**

Update `apps/app/src/lib/explore/types.ts` so `ExploreCitySummary` includes:

```ts
growth_available: boolean;
score_system: "v2" | "legacy" | "none";
presentation_score: number | null;
representative_service?: string | null;
metric_service?: string | null;
last_scored_at?: string | null;
stale?: boolean | null;
```

Keep compatibility aliases only if required by existing components:

```ts
best_opportunity_score: number | null;
```

- [ ] **Step 5: Replace loader implementation**

Change `loadExploreData` to accept URL/search params instead of a Supabase client:

```ts
export async function loadExploreData(params: ExploreQueryParams = {}): Promise<ExploreData> {
  const query = toExploreSearchParams(params);
  const response = await fetch(`${getBaseUrl()}/api/explore/cities?${query}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`loadExploreData explore cities: HTTP ${response.status}`);
  }

  return (await response.json()) as ExploreData;
}
```

- [ ] **Step 6: Update page search params**

Change `apps/app/src/app/(protected)/explore/page.tsx` to:

```ts
export default async function ExplorePage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const resolvedParams = searchParams ? await searchParams : {};
  const data = await loadExploreData(fromSearchParams(resolvedParams));
  ...
}
```

- [ ] **Step 7: Run focused app tests**

Run:

```bash
npm --workspace apps/app test -- load-explore-data api/explore/cities
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add apps/app/src/app/api/explore/cities apps/app/src/lib/explore apps/app/src/app/'(protected)'/explore/page.tsx
git commit -m "feat: load explore cities through backend api"
```

### Task 6: Refactor The Explore UI Around Prototype-Aligned City Browsing

**Files:**
- Modify: `apps/app/src/components/explore/ExplorePageClient.tsx`
- Modify: `apps/app/src/components/explore/ExploreFilters.tsx`
- Modify: `apps/app/src/components/explore/ExploreTable.tsx`
- Modify: `apps/app/src/components/explore/format.ts`

- [ ] **Step 1: Update growth formatting**

Ensure canonical decimal growth formats as percent:

```ts
expect(formatPercent(0.032)).toBe("3.2%");
expect(formatPercent(null)).toBe("-");
```

If `formatPercent` already behaves this way, add the regression test in the closest existing formatter test file or `load-explore-data.test.ts`.

- [ ] **Step 2: Move filters to URL state**

In `ExplorePageClient`, replace local-only filtering with URL updates:

```ts
function applyFilters(nextFilters: ExploreFilterState) {
  const params = new URLSearchParams(window.location.search);
  writeExploreFilters(params, nextFilters);
  router.replace(`/explore?${params.toString()}`, { scroll: false });
}
```

Rules:
- Use repeated `state=AZ&state=CO` params.
- Use `service=roofing` for selected service.
- Use `growing_only=1` only when enabled.
- Keep `sort` and `direction` in URL.

- [ ] **Step 3: Match prototype page frame**

Update header copy and controls to match the prototype intent:

```text
Explore
Cities & service data
Browse the data layer for free. Narrow down by demographics, then spend scans on the markets that need fresh numbers.
```

Do not add explanatory instructional blocks in the page body.

- [ ] **Step 4: Disable growth filter when unavailable**

In `ExploreFilters`, accept `growthAvailable: boolean` and render:

```tsx
<input
  type="checkbox"
  checked={filters.growingOnly}
  disabled={!growthAvailable}
  aria-label="Show growing markets only"
/>
```

Button/label copy:

```text
Growing markets only
```

When disabled, the UI should visually dim the control and omit rows being filtered out by absent data.

- [ ] **Step 5: Update table labels**

Use prototype column names:

```ts
const COLUMNS = [
  { key: "city", label: "City" },
  { key: "population", label: "Pop." },
  { key: "income", label: "Median HH income" },
  { key: "business_density", label: "Biz density" },
  { key: "growth", label: "Growth YoY" },
  { key: "cached_services", label: "Services cached" },
  { key: "best_opportunity", label: "Best opportunity" },
];
```

- [ ] **Step 6: Add metric lineage display**

When `city.metric_service` exists and no active service is selected, show a compact secondary line under density/growth:

```tsx
<span className="metric-lineage">{city.metric_service}</span>
```

If there is an active service, do not show lineage because the service picker already explains it.

- [ ] **Step 7: Run focused app tests and lint**

Run:

```bash
npm --workspace apps/app test -- load-explore-data
npm --workspace apps/app run lint
```

Expected: pass. If lint has existing unrelated failures, capture the exact failures and keep Explore files clean.

- [ ] **Step 8: Commit**

```bash
git add apps/app/src/components/explore apps/app/src/lib/explore
git commit -m "feat: refactor explore cities browsing ui"
```

### Task 7: Update City Drawer, Scans, And Refresh Semantics

**Files:**
- Modify: `apps/app/src/components/explore/CityDrawer.tsx`
- Modify: `apps/app/src/components/explore/ServiceScoreRow.tsx`
- Modify: `apps/app/src/components/explore/FreshScanConfirmation.tsx`
- Modify: `apps/app/src/components/explore/ExplorePageClient.tsx`
- Modify: `apps/app/src/app/api/agent/scoring/route.test.ts`

- [ ] **Step 1: Support cached and uncached service scan selections**

Define a scan target type:

```ts
export type ExploreScanTarget = {
  service: string;
  service_label: string;
  source: "cached" | "catalog";
  report_id?: string;
  refresh_target_id?: string;
};
```

- [ ] **Step 2: Keep refresh selected limited to cached targets**

Refresh button enablement:

```ts
const selectedRefreshableCount = selectedTargets.filter(
  (target) => target.source === "cached" && target.refresh_target_id,
).length;
```

Fresh scan button enablement:

```ts
const selectedScanCount = selectedTargets.length;
```

- [ ] **Step 3: Add drawer service rows**

Drawer should render:
- cached services from city detail first.
- catalog services not cached under a compact "Other services" group.
- selected count and scan cost in confirmation.

- [ ] **Step 4: Preserve entitlement enforcement**

Do not bypass `apps/app/src/app/api/agent/scoring/route.ts`; fresh scans must still go through quota and feature-flag checks.

- [ ] **Step 5: Add tests for scan payload**

Extend route/component-level tests so a fresh scan from Explore sends:

```json
{
  "city": "Phoenix-Mesa-Chandler",
  "state": "AZ",
  "service": "roofing",
  "metadata_source": "fallback_cbsa"
}
```

Expected: quota enforcement remains in the scoring route.

- [ ] **Step 6: Run focused tests**

Run:

```bash
npm --workspace apps/app test -- agent/scoring explore
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add apps/app/src/components/explore apps/app/src/app/api/agent/scoring/route.test.ts
git commit -m "feat: support explore scan and refresh semantics"
```

### Task 8: Wire Data Readiness And Growth Availability

**Files:**
- Modify: `scripts/explore/audit_explore_sources.py`
- Modify: `tests/scripts/test_audit_explore_sources.py`
- Modify: `scripts/explore/backfill_cbp_establishments.py`
- Modify: `tests/scripts/test_backfill_cbp_establishments.py`

- [ ] **Step 1: Extend audit expectations**

Add checks for:

```python
{
    "explore_market_cells_count": int,
    "market_cells_with_density": int,
    "cbp_years": [2023],
    "growth_available": False,
}
```

Current production expectation is `growth_available=False` until a second CBP year is loaded.

- [ ] **Step 2: Keep one-year CBP behavior explicit**

Audit output should say:

```text
growth unavailable: census_cbp_establishments has 1 year loaded
```

Do not mark this as failure unless the user asked for growth filtering to be launch-blocking.

- [ ] **Step 3: Add backfill support for prior CBP year**

Update `scripts/explore/backfill_cbp_establishments.py` so `--year 2022` and `--year 2023` can be run independently from import files:

```bash
python scripts/explore/backfill_cbp_establishments.py --input /path/to/cbp-2022.csv --year 2022 --dry-run
python scripts/explore/backfill_cbp_establishments.py --input /path/to/cbp-2022.csv --year 2022 --apply
```

- [ ] **Step 4: Run focused Python tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/scripts/test_audit_explore_sources.py tests/scripts/test_backfill_cbp_establishments.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/explore/audit_explore_sources.py tests/scripts/test_audit_explore_sources.py scripts/explore/backfill_cbp_establishments.py tests/scripts/test_backfill_cbp_establishments.py
git commit -m "feat: audit explore market-cell readiness"
```

### Task 9: End-To-End Verification And Linear Closeout

**Files:**
- Modify: `.Codex/project_context.md`
- Modify: `.Codex/ACTIVE_WORK.md`

- [ ] **Step 1: Run backend unit tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/unit/test_explore_metrics.py tests/unit/test_explore_city_service.py tests/unit/test_explore_repository.py tests/unit/test_api_explore_cities.py tests/unit/test_explore_market_cells_schema.py -q
```

Expected: pass.

- [ ] **Step 2: Run frontend unit tests**

Run:

```bash
npm --workspace apps/app test -- load-explore-data api/explore/cities explore
```

Expected: pass.

- [ ] **Step 3: Run static checks**

Run:

```bash
npm --workspace apps/app run lint
git diff --check
npx docguard-cli guard
```

Expected:
- `git diff --check` passes.
- lint passes or reports existing unrelated files only.
- DocGuard result is recorded with exact pass/fail categories.

- [ ] **Step 4: Run local visual smoke**

Start local services:

```bash
npm run dev:app
```

Open `/explore` and verify:
- table loads from backend API.
- service filter changes URL and refetches.
- growth toggle is disabled when `growth_available=false`.
- drawer opens and shows cached service rows.
- fresh scan button reaches the existing scoring route.
- refresh selected only enables for cached rows with refresh targets.

- [ ] **Step 5: Update project docs**

Update `.Codex/project_context.md` with a concise "what was built" note only after implementation is verified. Update `.Codex/ACTIVE_WORK.md` with remaining follow-up, especially historical CBP-year loading if still absent.

- [ ] **Step 6: Update Linear**

Add a Linear comment or closeout note with:
- shipped files.
- verification commands.
- known data gaps.
- whether growth is still unavailable because only one CBP year is loaded.

- [ ] **Step 7: Commit docs closeout**

```bash
git add .Codex/project_context.md .Codex/ACTIVE_WORK.md
git commit -m "docs: close out explore cities refactor"
```

## Rollout Notes

- Apply migration `018_explore_market_cells.sql` to staging first.
- Refresh `public.explore_market_cells` after hydration:

```sql
REFRESH MATERIALIZED VIEW public.explore_market_cells;
```

- Verify staging before production:

```bash
python scripts/explore/audit_explore_sources.py --json
```

- Production rollout should not enable growth filtering until the audit reports at least two CBP years.

## Linear Issue Body

Created Linear issue: `WHI-1` - Refactor Explore Cities into city-first market discovery surface.

Use this summary when updating Linear:

```markdown
## Goal

Refactor `/explore` into the prototype-aligned city-first Explore Cities surface, backed by backend-owned service-aware market-cell data.

## Product direction

- Keep Explore city-first by default.
- Add service-selected mode for comparing one service across cities.
- Treat density and growth as service-aware metrics, never unlabelled city-only facts.
- Keep Strategies as guided ranking lenses over the same market-cell read model.
- Fresh scan works for any city + service; refresh only works for cached targets.

## Implementation phases

1. Update canonical docs and test obligations.
2. Add `explore_market_cells` derived read model.
3. Add `SupabaseExploreRepository` and FastAPI Explore endpoints.
4. Switch Next `/explore` loader to backend API and remove top-100 client universe.
5. Refactor filters/table/drawer to match the prototype and backend contracts.
6. Add readiness audit for density/growth and historical CBP-year availability.

## Acceptance criteria

- `/explore` no longer direct-loads and filters only the first 100 `metros`.
- Service-selected mode returns service-specific score, density, growth, freshness, and cached rows.
- Default mode makes metric lineage clear when no service is selected.
- Growth filtering is disabled when only one CBP year is loaded.
- City drawer supports cached refresh and fresh scan semantics without bypassing entitlements.
- Backend/frontend tests and `git diff --check` pass; DocGuard result is recorded.

## Plan

Repo plan: `docs/superpowers/plans/2026-05-17-explore-cities-refactor.md`
```

## Self-Review

- Spec coverage: Covers prototype comparison, backend read model, density/growth correctness, service-aware design, Explore vs Strategies responsibility, frontend refactor, and Linear handoff.
- Placeholder scan: No placeholder red flags remain.
- Type consistency: Uses `niche_normalized`, `presentation_score`, `growth_available`, `business_density_per_1k`, and `establishment_growth_yoy` consistently across SQL, Python, and TypeScript tasks.
