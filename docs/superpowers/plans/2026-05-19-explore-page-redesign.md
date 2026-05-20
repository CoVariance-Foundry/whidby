# Explore Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the explore page so it only shows scored city/service pairs, with expandable city rows that cleanly separate city-level from service-level metrics, then populate ~2,080 scored pairs across 130 cities and 16 services.

**Architecture:** Backend filters to scored-only rows via `report_id IS NOT NULL`. Frontend replaces the flat table with expandable city rows (parent = demographics, child = per-service scores). Bulk scoring runs via the existing `scripts/explore/bulk_score.py` against the local FastAPI server.

**Tech Stack:** Python (FastAPI + supabase-py 2.x), TypeScript/React (Next.js 16), PostgreSQL materialized view, Playwright MCP for UI verification.

---

### Task 1: Backend — Add scored-only filter to explore repository

**Files:**
- Modify: `src/clients/explore_repository.py:10-52`
- Modify: `tests/unit/test_explore_repository.py`

- [ ] **Step 1: Update FakeTable to support `not_` property and `is_` method**

In `tests/unit/test_explore_repository.py`, add `not_` and `is_` to `FakeTable`:

```python
class _FakeNot:
    """Handles `.not_.is_(col, val)` chaining."""
    def __init__(self, parent: "FakeTable"):
        self._parent = parent

    def is_(self, key: str, value: str) -> "FakeTable":
        self._parent.calls.append(("not_.is_", key, value))
        self._parent.filters.append(("not_.is_", key, value))
        return self._parent
```

Add this property to the existing `FakeTable` class:

```python
@property
def not_(self):
    return _FakeNot(self)
```

Update the filter logic inside `FakeTable.execute()` — add after the `"gt"` case:

```python
if operator == "not_.is_":
    if value == "null":
        rows = [row for row in rows if row.get(key) is not None]
```

- [ ] **Step 2: Write failing test for scored-only filter (no service)**

Add to `tests/unit/test_explore_repository.py`:

```python
def test_list_city_rows_without_service_excludes_unscored() -> None:
    rows = [
        {"cbsa_code": "11111", "cbsa_name": "Scored City", "state": "TX",
         "representative_service_rank": 1, "report_id": "r-1",
         "presentation_score": 82, "niche_normalized": "roofing"},
        {"cbsa_code": "22222", "cbsa_name": "Unscored City", "state": "CA",
         "representative_service_rank": 1, "report_id": None,
         "presentation_score": None, "niche_normalized": "air_conditioning"},
    ]
    client = FakeClient(rows_by_table={"explore_market_cells": rows})
    repo = SupabaseExploreRepository(client)

    result = repo.list_city_rows(
        service=None, states=[], population_min=None, population_max=None,
        income_min=None, income_max=None, growing_only=False,
        sort="score", direction="desc", limit=50, cursor=None,
    )

    assert len(result) == 1
    assert result[0]["cbsa_code"] == "11111"
    calls = client.tables["explore_market_cells"].calls
    assert ("not_.is_", "report_id", "null") in calls
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_explore_repository.py::test_list_city_rows_without_service_excludes_unscored -v`
Expected: FAIL — no `not_.is_` call in the current code.

- [ ] **Step 4: Add scored-only filter and sort alias to repository**

In `src/clients/explore_repository.py`, add `"best_opportunity"` to `SORT_COLUMNS`:

```python
SORT_COLUMNS = {
    "score": "presentation_score",
    "best_score": "presentation_score",
    "best_opportunity": "presentation_score",
    "presentation_score": "presentation_score",
    # ... rest unchanged
}
```

In `list_city_rows()`, change lines 48-52 from:

```python
normalized_service = _normalize_service(service)
if normalized_service:
    query = query.eq("niche_normalized", normalized_service)
else:
    query = query.eq("representative_service_rank", 1)
```

to:

```python
normalized_service = _normalize_service(service)
if normalized_service:
    query = query.eq("niche_normalized", normalized_service)
else:
    query = query.eq("representative_service_rank", 1)
query = query.not_.is_("report_id", "null")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_explore_repository.py -v`
Expected: All tests PASS (including the new one). The existing `test_list_city_rows_without_service_filters_representative_rows` will need an update — add `("not_.is_", "report_id", "null")` to its assertions:

Update that test's assertion block to add:

```python
assert ("not_.is_", "report_id", "null") in calls
```

- [ ] **Step 6: Write test for scored-only filter (with service)**

```python
def test_list_city_rows_with_service_excludes_unscored() -> None:
    rows = [
        {"cbsa_code": "11111", "cbsa_name": "Dallas", "state": "TX",
         "niche_normalized": "roofing", "report_id": "r-1",
         "presentation_score": 82},
        {"cbsa_code": "22222", "cbsa_name": "Phoenix", "state": "AZ",
         "niche_normalized": "roofing", "report_id": None,
         "presentation_score": None},
    ]
    client = FakeClient(rows_by_table={"explore_market_cells": rows})
    repo = SupabaseExploreRepository(client)

    result = repo.list_city_rows(
        service="roofing", states=[], population_min=None, population_max=None,
        income_min=None, income_max=None, growing_only=False,
        sort="score", direction="desc", limit=50, cursor=None,
    )

    assert len(result) == 1
    assert result[0]["cbsa_code"] == "11111"
    calls = client.tables["explore_market_cells"].calls
    assert ("eq", "niche_normalized", "roofing") in calls
    assert ("not_.is_", "report_id", "null") in calls
```

- [ ] **Step 7: Run all explore repository tests**

Run: `pytest tests/unit/test_explore_repository.py -v`
Expected: All PASS.

- [ ] **Step 8: Add difficulty_tier and serp_archetype to _cached_score pass-through**

In `src/clients/explore_repository.py`, update `_cached_score()` to include fields from the matview that the frontend needs:

```python
def _cached_score(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "niche_normalized": row.get("niche_normalized"),
        "niche_keyword": row.get("niche_keyword"),
        "report_id": row.get("report_id"),
        "presentation_score": row.get("presentation_score"),
        "score_system": row.get("score_system"),
        "latest_scored_at": row.get("latest_scored_at"),
        "last_refreshed_at": row.get("last_refreshed_at") or row.get("latest_scored_at"),
        "refresh_target_id": row.get("refresh_target_id"),
        "next_refresh_at": row.get("next_refresh_at"),
        "stale": row.get("stale"),
        "business_density_per_1k": row.get("business_density_per_1k"),
        "establishment_growth_yoy": row.get("establishment_growth_yoy"),
        "growth_available": row.get("growth_available"),
        "serp_archetype": row.get("serp_archetype"),
        "difficulty_tier": row.get("difficulty_tier"),
        "confidence_score": row.get("confidence_score"),
        "ai_resilience_score": row.get("ai_resilience_score"),
        "ai_exposure": row.get("ai_exposure"),
    }
```

- [ ] **Step 9: Commit**

```bash
git add src/clients/explore_repository.py tests/unit/test_explore_repository.py
git commit -m "fix(explore): filter to scored-only rows, add sort alias and matview fields"
```

---

### Task 2: Migration — Codify matview refresh RPC

**Files:**
- Create: `supabase/migrations/021_explore_refresh_rpc.sql`

- [ ] **Step 1: Create migration file**

```sql
-- RPC to refresh the explore_market_cells materialized view.
-- Called by scripts/explore/bulk_score.py and can be invoked manually.

CREATE OR REPLACE FUNCTION public._refresh_explore_market_cells()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY public.explore_market_cells;
END;
$$;

REVOKE ALL ON FUNCTION public._refresh_explore_market_cells() FROM public;
GRANT EXECUTE ON FUNCTION public._refresh_explore_market_cells() TO service_role;
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/021_explore_refresh_rpc.sql
git commit -m "feat(explore): add matview refresh RPC migration"
```

---

### Task 3: Frontend — Remove hardcoded service catalog

**Files:**
- Modify: `apps/app/src/components/explore/ExplorePageClient.tsx:47-54,103-110,308-320,617-619`

- [ ] **Step 1: Remove DEFAULT_CATALOG_SERVICES and uniqueServiceCatalog**

In `apps/app/src/components/explore/ExplorePageClient.tsx`:

Delete lines 47-54 (the `DEFAULT_CATALOG_SERVICES` constant):

```typescript
const DEFAULT_CATALOG_SERVICES = [
  "Plumbing",
  "HVAC",
  "Roofing",
  "Tree service",
  "Pest control",
  "Water damage",
];
```

Delete lines 103-110 (the `uniqueServiceCatalog` function):

```typescript
function uniqueServiceCatalog(services: string[]): string[] {
  const byKey = new Map<string, string>();
  [...DEFAULT_CATALOG_SERVICES, ...services].forEach((service) => {
    const key = normalizedServiceLabel(service);
    if (!byKey.has(key)) byKey.set(key, service);
  });
  return [...byKey.values()].sort((a, b) => a.localeCompare(b));
}
```

Replace the `catalogServices` memo (around line 317-320):

```typescript
const catalogServices = useMemo(
  () => uniqueServiceCatalog(services),
  [services],
);
```

with:

```typescript
const catalogServices = services;
```

- [ ] **Step 2: Update ExploreFilters to use services directly**

In the `<ExploreFilters>` usage (around line 619), it already receives `services={services}`. No change needed — the `services` array now comes purely from scored data.

- [ ] **Step 3: Commit**

```bash
git add apps/app/src/components/explore/ExplorePageClient.tsx
git commit -m "fix(explore): remove hardcoded service catalog, populate from scored data only"
```

---

### Task 4: Frontend — Rewrite ExploreTable with expandable city rows

**Files:**
- Modify: `apps/app/src/components/explore/ExploreTable.tsx`

- [ ] **Step 1: Rewrite ExploreTable with expandable rows**

Replace the entire content of `apps/app/src/components/explore/ExploreTable.tsx`:

```typescript
"use client";

import { useState } from "react";
import type { ExploreCachedScore, ExploreCitySummary } from "@/lib/explore/types";
import { Icon, I } from "@/lib/icons";
import {
  formatCurrency,
  formatDecimal,
  formatInteger,
  formatPercent,
} from "./format";

export type ExploreSortKey =
  | "city"
  | "population"
  | "income"
  | "business_density"
  | "growth"
  | "cached_services"
  | "best_opportunity";

export type SortDirection = "asc" | "desc";

interface ExploreTableProps {
  cities: ExploreCitySummary[];
  sortKey: ExploreSortKey;
  sortDirection: SortDirection;
  activeService?: string;
  onSortChange: (key: ExploreSortKey) => void;
  onCityOpen: (city: ExploreCitySummary) => void;
  onReset: () => void;
}

const COLUMNS: Array<{ key: ExploreSortKey; label: string; align?: "right" }> = [
  { key: "city", label: "City" },
  { key: "population", label: "Pop.", align: "right" },
  { key: "income", label: "Median HH income", align: "right" },
  { key: "business_density", label: "Biz density", align: "right" },
  { key: "growth", label: "Growth YoY", align: "right" },
  { key: "best_opportunity", label: "Best score", align: "right" },
  { key: "cached_services", label: "Services", align: "right" },
];

function scoreColor(score: number | null | undefined): string {
  if (score == null) return "var(--ink-3)";
  if (score >= 70) return "var(--green, #4ade80)";
  if (score >= 40) return "var(--yellow, #facc15)";
  return "var(--red, #f87171)";
}

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "-";
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 1) return "Today";
  if (diffDays === 1) return "1 day ago";
  if (diffDays < 30) return `${diffDays} days ago`;
  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths === 1) return "1 month ago";
  return `${diffMonths} months ago`;
}

function displayScore(city: ExploreCitySummary, activeService: string): number | null {
  if (!activeService) return city.best_opportunity_score;
  const match = city.cached_scores.find(
    (s) =>
      (s.niche_normalized ?? "").toLowerCase().replace(/[_-]+/g, " ") ===
      activeService.toLowerCase().replace(/[_-]+/g, " "),
  );
  return match?.opportunity_score ?? null;
}

function SortIcon({ active, direction }: { active: boolean; direction: SortDirection }) {
  if (!active) return <Icon d={I.chevronDown} size={12} style={{ opacity: 0.35 }} />;
  return <Icon d={direction === "asc" ? I.arrowUp : I.arrowDown} size={12} />;
}

function HeaderCell({
  column,
  sortKey,
  sortDirection,
  onSortChange,
}: {
  column: (typeof COLUMNS)[number];
  sortKey: ExploreSortKey;
  sortDirection: SortDirection;
  onSortChange: (key: ExploreSortKey) => void;
}) {
  const active = sortKey === column.key;
  return (
    <span role="columnheader" aria-sort={active ? (sortDirection === "asc" ? "ascending" : "descending") : "none"} style={{ textAlign: column.align, minWidth: 0 }}>
      <button
        type="button"
        aria-label={`Sort by ${column.label}`}
        onClick={() => onSortChange(column.key)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: column.align === "right" ? "flex-end" : "flex-start",
          gap: 5,
          width: "100%",
          minHeight: 24,
          color: active ? "var(--ink)" : "var(--ink-3)",
          fontFamily: "var(--sans)",
          fontSize: 11.5,
          fontWeight: 650,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
        }}
      >
        {column.label}
        <SortIcon active={active} direction={sortDirection} />
      </button>
    </span>
  );
}

function ServiceDetailRow({
  score,
  highlighted,
}: {
  score: ExploreCachedScore;
  highlighted: boolean;
}) {
  const serviceName = score.niche_keyword ?? score.niche_normalized ?? score.service ?? "-";
  const opportunityScore = score.opportunity_score;
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1.5fr 0.7fr 1fr 0.8fr 1fr",
        gap: 10,
        padding: "7px 16px 7px 44px",
        borderBottom: "1px solid var(--rule)",
        background: highlighted ? "color-mix(in srgb, var(--accent) 6%, transparent)" : "var(--paper-alt)",
        borderLeft: highlighted ? "3px solid var(--accent)" : "3px solid transparent",
        fontFamily: "var(--sans)",
        fontSize: 12.5,
        color: "var(--ink-2)",
      }}
    >
      <span style={{ fontWeight: highlighted ? 700 : 500, color: highlighted ? "var(--accent-ink)" : "var(--ink)" }}>
        {serviceName}
      </span>
      <span style={{ textAlign: "right", fontFamily: "var(--mono)", fontWeight: 700, color: scoreColor(opportunityScore) }}>
        {opportunityScore ?? "-"}
      </span>
      <span style={{ textAlign: "right" }}>
        {score.archetype_label ?? "-"}
      </span>
      <span style={{ textAlign: "right" }}>
        {score.difficulty_tier ? score.difficulty_tier.replace(/_/g, " ") : "-"}
      </span>
      <span style={{ textAlign: "right", color: "var(--ink-3)", fontSize: 11.5 }}>
        {relativeTime(score.latest_scored_at ?? score.last_scored_at)}
      </span>
    </div>
  );
}

function CityRow({
  city,
  activeService,
  expanded,
  onToggle,
  onCityOpen,
}: {
  city: ExploreCitySummary;
  activeService: string;
  expanded: boolean;
  onToggle: () => void;
  onCityOpen: () => void;
}) {
  const score = displayScore(city, activeService);
  return (
    <>
      <div
        role="row"
        tabIndex={0}
        className="report-row-clickable"
        aria-label={`${expanded ? "Collapse" : "Expand"} ${city.cbsa_name}`}
        onClick={onToggle}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onToggle();
          }
        }}
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(220px, 1.8fr) repeat(6, minmax(80px, 0.8fr))",
          gap: 12,
          alignItems: "center",
          padding: "13px 16px",
          borderBottom: expanded ? "none" : "1px solid var(--rule)",
          cursor: "pointer",
          fontFamily: "var(--sans)",
          fontSize: 13.5,
          color: "var(--ink)",
          background: expanded ? "var(--paper-alt)" : undefined,
        }}
      >
        <span role="cell" style={{ minWidth: 0 }}>
          <span style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
            <Icon
              d={expanded ? I.chevronDown : I.chevronRight}
              size={14}
              style={{ flex: "0 0 auto", opacity: 0.5 }}
            />
            <span
              style={{
                minWidth: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                fontWeight: 650,
                cursor: "pointer",
              }}
              role="link"
              tabIndex={0}
              onClick={(e) => {
                e.stopPropagation();
                onCityOpen();
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.stopPropagation();
                  onCityOpen();
                }
              }}
            >
              {city.cbsa_name}
            </span>
          </span>
          <span style={{ display: "block", marginTop: 2, marginLeft: 22, fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 12, color: "var(--ink-3)" }}>
            {city.state}
          </span>
        </span>
        <span role="cell" style={{ textAlign: "right", fontFamily: "var(--mono)" }}>
          {formatInteger(city.population)}
        </span>
        <span role="cell" style={{ textAlign: "right", fontFamily: "var(--mono)" }}>
          {formatCurrency(city.median_household_income_usd)}
        </span>
        <span role="cell" style={{ textAlign: "right", fontFamily: "var(--mono)" }}>
          {formatDecimal(city.business_density_per_1k)}
        </span>
        <span role="cell" style={{ textAlign: "right", fontFamily: "var(--mono)" }}>
          {formatPercent(city.establishment_growth_yoy)}
        </span>
        <span role="cell" style={{ textAlign: "right", fontFamily: "var(--mono)", fontWeight: 700, color: scoreColor(score) }}>
          {score ?? "-"}
        </span>
        <span role="cell" style={{ textAlign: "right", fontFamily: "var(--mono)" }}>
          {city.cached_services_count}
        </span>
      </div>

      {expanded && city.cached_scores.length > 0 && (
        <div style={{ borderBottom: "1px solid var(--rule)" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1.5fr 0.7fr 1fr 0.8fr 1fr",
              gap: 10,
              padding: "6px 16px 6px 44px",
              borderBottom: "1px solid var(--rule)",
              background: "var(--paper-alt)",
              fontFamily: "var(--sans)",
              fontSize: 10.5,
              fontWeight: 650,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--ink-3)",
            }}
          >
            <span>Service</span>
            <span style={{ textAlign: "right" }}>Score</span>
            <span style={{ textAlign: "right" }}>Archetype</span>
            <span style={{ textAlign: "right" }}>Difficulty</span>
            <span style={{ textAlign: "right" }}>Last scored</span>
          </div>
          {city.cached_scores.map((score) => (
            <ServiceDetailRow
              key={score.niche_normalized ?? score.service}
              score={score}
              highlighted={
                !!activeService &&
                (score.niche_normalized ?? "").toLowerCase().replace(/[_-]+/g, " ") ===
                  activeService.toLowerCase().replace(/[_-]+/g, " ")
              }
            />
          ))}
        </div>
      )}
    </>
  );
}

export default function ExploreTable({
  cities,
  sortKey,
  sortDirection,
  activeService = "",
  onSortChange,
  onCityOpen,
  onReset,
}: ExploreTableProps) {
  const [expandedCities, setExpandedCities] = useState<Set<string>>(new Set());

  function toggleCity(cbsaCode: string) {
    setExpandedCities((prev) => {
      const next = new Set(prev);
      if (next.has(cbsaCode)) {
        next.delete(cbsaCode);
      } else {
        next.add(cbsaCode);
      }
      return next;
    });
  }

  if (cities.length === 0) {
    return (
      <div
        role="status"
        style={{
          background: "var(--card)",
          border: "1px solid var(--rule)",
          borderRadius: 12,
          padding: "28px 20px",
          display: "grid",
          justifyItems: "center",
          gap: 12,
          textAlign: "center",
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 999,
            display: "grid",
            placeItems: "center",
            color: "var(--accent-ink)",
            background: "var(--accent-soft)",
          }}
        >
          <Icon d={I.search} size={17} />
        </div>
        <p style={{ margin: 0, fontFamily: "var(--sans)", fontSize: 14, color: "var(--ink-2)" }}>
          No scored cities match the current filters.
        </p>
        <button type="button" className="btn-ghost" aria-label="Reset filters" onClick={onReset}>
          Reset filters
        </button>
      </div>
    );
  }

  return (
    <div
      role="table"
      aria-label="Explore cities"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        overflowX: "auto",
      }}
    >
      <div style={{ minWidth: 920 }}>
        <div
          role="row"
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(220px, 1.8fr) repeat(6, minmax(80px, 0.8fr))",
            gap: 12,
            alignItems: "center",
            padding: "10px 16px",
            background: "var(--paper-alt)",
            borderBottom: "1px solid var(--rule)",
          }}
        >
          {COLUMNS.map((column) => (
            <HeaderCell
              key={column.key}
              column={column}
              sortKey={sortKey}
              sortDirection={sortDirection}
              onSortChange={onSortChange}
            />
          ))}
        </div>

        {cities.map((city) => (
          <CityRow
            key={city.cbsa_code}
            city={city}
            activeService={activeService}
            expanded={expandedCities.has(city.cbsa_code)}
            onToggle={() => toggleCity(city.cbsa_code)}
            onCityOpen={() => onCityOpen(city)}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run TypeScript check**

Run: `cd apps/app && npx tsc --noEmit`
Expected: No type errors.

- [ ] **Step 3: Commit**

```bash
git add apps/app/src/components/explore/ExploreTable.tsx
git commit -m "feat(explore): rewrite table with expandable city rows and service detail"
```

---

### Task 5: Verify frontend with Playwright MCP

**Files:** None (manual verification)

- [ ] **Step 1: Verify the explore page renders correctly**

Use Playwright MCP to navigate to `http://localhost:3002/explore`. Verify:
- The page loads without errors
- The table shows only cities that have scored data (not all 935)
- The service dropdown lists only scored services (not all 141)
- Clicking a city row expands to show per-service detail with score, archetype, difficulty, last scored columns
- The service filter highlights the filtered service in expanded rows

- [ ] **Step 2: Take screenshot for visual verification**

Use Playwright MCP `browser_take_screenshot` to capture the page state.

- [ ] **Step 3: Commit any fixes from visual testing**

---

### Task 6: Bulk scoring — expand dataset

**Files:**
- Modify: `scripts/explore/bulk_score.py` (already exists — expand city count)

- [ ] **Step 1: Update bulk_score.py to support 130 cities**

The script already defaults to 50 cities. Update the `--cities` default from 50 to 130 in the argparse section. No other code change — the script already reads top N metros by population from Supabase.

In `scripts/explore/bulk_score.py`, change the `--cities` default:

```python
parser.add_argument(
    "--cities",
    type=int,
    default=130,
    help="Number of top metros by population (default: 130).",
)
```

And change the `--services` default from 12 to 16:

```python
parser.add_argument(
    "--services",
    type=int,
    default=16,
    help="Number of services from the catalog (default: 16).",
)
```

- [ ] **Step 2: Run preview to verify scope**

Run: `set -a && source .env && set +a && arch -arm64 python3 -m scripts.explore.bulk_score --preview --resume`
Expected: Shows ~2,080 pairs (130 cities x 16 services) minus any already-scored pairs.

- [ ] **Step 3: Start bulk scoring in background**

Run: `set -a && source .env && set +a && arch -arm64 python3 -m scripts.explore.bulk_score --apply --resume`

This runs for ~5.5 hours. Use `--resume` to skip already-scored pairs. Monitor progress via the log output. Results are written to `scripts/explore/bulk_score_results.jsonl`.

- [ ] **Step 4: After scoring completes, refresh matview**

Run: `set -a && source .env && set +a && arch -arm64 python3 -m scripts.explore.bulk_score --refresh-only`

Or via Supabase MCP: `SELECT _refresh_explore_market_cells();`

- [ ] **Step 5: Commit the updated script defaults**

```bash
git add scripts/explore/bulk_score.py
git commit -m "feat(explore): expand bulk scoring defaults to 130 cities x 16 services"
```

---

### Task 7: Final integration test with Playwright MCP

**Files:** None (manual verification)

- [ ] **Step 1: Verify explore page with real scored data**

After some scoring data has populated (even a partial batch), use Playwright MCP to verify:
- Multiple cities appear in the table with real scores
- Multiple services appear in the dropdown
- Expanding a city shows multiple scored services with real archetype/difficulty data
- Service filter correctly highlights and re-sorts
- Sorting by score, population, income all work correctly
- "Last scored" column shows realistic relative times

- [ ] **Step 2: Verify the matview refresh updated correctly**

Run via Supabase MCP:
```sql
SELECT COUNT(*) as scored_pairs,
  COUNT(DISTINCT cbsa_code) as cities,
  COUNT(DISTINCT niche_normalized) as services
FROM explore_market_cells
WHERE report_id IS NOT NULL;
```
Expected: Counts should match or exceed the number of successful bulk scoring runs.
