# Explore Page Redesign — Scored Pairs, Expandable Rows, Bulk Data

**Date:** 2026-05-19
**Status:** Design approved, pending implementation

## Problem Statement

The explore page (`/explore`) has three interconnected issues:

1. **Service visibility bug**: The backend returns only one service per city ("air conditioning") because the materialized view's `representative_service_rank` window function falls back to alphabetical ordering when no scores exist. The service dropdown shows only this one service.
2. **Mixed-metric table design**: The current flat table mixes city-level metrics (population, income) with service-level metrics (opportunity score, services cached) in one row, which is confusing when the "representative service" is meaningless.
3. **Sparse data**: Only 5 scored city×service cells exist across 33 reports. The explore page needs hundreds of scored pairs to be useful.

## Design Decisions

| Question | Answer |
|----------|--------|
| Primary use case | See the full (city, service) matrix ranked by opportunity |
| Unscored pairs | Hide them — only show scored pairs |
| Table layout | Expandable city rows (Layout C) |
| Service filter behavior | Show all scored cities, highlight the filtered service |
| Default sort | Best opportunity score DESC |
| Data expansion budget | Up to $50 in API costs |
| Report freshness | Show `last_scored_at` in service detail sub-rows |

## Phase 1: Backend — Fix Service Visibility Bug

### Root Cause

`SupabaseExploreRepository.list_city_rows()` (`src/clients/explore_repository.py:52`) applies `.eq("representative_service_rank", 1)` when no service filter is set. The matview window function ranks by `presentation_score DESC NULLS LAST, latest_scored_at DESC NULLS LAST, niche_normalized ASC`. With no scores, all presentation_scores are NULL, so `niche_normalized ASC` determines rank — "air_conditioning" wins for every city.

### Fix

**`src/clients/explore_repository.py`:**
- When no service filter is set: change the query to filter `representative_service_rank = 1` AND `report_id IS NOT NULL`. This excludes cities with no scored services entirely.
- When a service filter IS set: keep `.eq("niche_normalized", normalized_service)` but add `.not_.is_("report_id", "null")` to only return cities that have a score for that service.

**Frontend service dropdown:**
- Remove the `DEFAULT_CATALOG_SERVICES` hardcoded list from `ExplorePageClient.tsx` (line 47-54).
- The dropdown should populate from `data.cities.cached_scores` — which, with the scored-only filter, will naturally contain only services that have actual scores.

**Migration `021_explore_refresh_rpc.sql`:**
- Codify the `_refresh_explore_market_cells()` RPC function already created in Supabase into a migration file for version control.

### Files Changed
- `src/clients/explore_repository.py` — add `report_id IS NOT NULL` filter
- `apps/app/src/components/explore/ExplorePageClient.tsx` — remove `DEFAULT_CATALOG_SERVICES`
- `supabase/migrations/021_explore_refresh_rpc.sql` — new migration

## Phase 2: Frontend — Expandable City Rows

### Table Structure

**Parent rows** (one per city with any scored service):
| Column | Source | Sortable |
|--------|--------|----------|
| City, State | `cbsa_name`, `state` | Yes (alphabetical) |
| Population | `population` | Yes |
| Median Income | `median_household_income_usd` | Yes |
| Business Density | `business_density_per_1k` | Yes |
| Growth YoY | `establishment_growth_yoy` | Yes |
| Best Score | max `presentation_score` across cached_scores | Yes (default DESC) |
| Services | count of `cached_scores` | Yes |
| Expand toggle | chevron icon | No |

**Expandable detail sub-table** (per scored service within that city):
| Column | Source |
|--------|--------|
| Service | `cached_scores[].service` |
| Opportunity Score | `cached_scores[].opportunity_score` (color-coded: green >=70, yellow 40-69, red <40) |
| SERP Archetype | `cached_scores[].archetype_label` |
| Difficulty | `cached_scores[].difficulty_tier` from matview (passed through API; add to `normalizeCachedScore` if missing) |
| Last Scored | `cached_scores[].latest_scored_at` (relative time: "3 days ago") |

### Service Filter Behavior

When a service is selected from the dropdown:
- All scored cities still appear (not just those scored for the filtered service)
- The "Best Score" parent column switches to show that specific service's score (or "—" if the city lacks it)
- Sort by the filtered service's score so best-opportunity cities for that service rise to top
- In the expanded detail, the filtered service row is visually highlighted (accent border/bold)

### Component Changes

| Component | Change |
|-----------|--------|
| `ExploreTable.tsx` | Rewrite: parent rows with expand/collapse, sub-table for services |
| `ExplorePageClient.tsx` | Remove `DEFAULT_CATALOG_SERVICES`, update service list derivation |
| `ExploreFilters.tsx` | No structural change — service dropdown populates from scored data only |
| `ServiceScoreRow.tsx` | New or repurposed: renders one service row in the sub-table |

### Data Shape

No API contract change needed. The API already returns `cached_scores[]` per city. The current frontend flattens this — the redesign uses it directly for sub-rows.

## Phase 3: API — Fix Default Sorting

### Changes

1. **Sort column alias**: Add `"best_opportunity": "presentation_score"` to the `SORT_COLUMNS` dict in `explore_repository.py` so the frontend sort key maps correctly.

2. **Default direction**: Verify the API defaults to `direction=desc` for score-based sorts. Currently true — make it explicit in the code.

3. **No aggregation change needed**: The matview already computes `representative_service_rank` via a window function. With the `report_id IS NOT NULL` filter from Phase 1, the rank-1 row is always the city's highest-scored service. The sorting bug is resolved by excluding unscored rows.

### Files Changed
- `src/clients/explore_repository.py` — add sort alias

## Phase 4: Data — Bulk Scoring Expansion

### Scope

- **Cities**: All metros with population >= 500,000 (~130 cities)
- **Services** (16): roofing, plumbing, hvac, tree service, pest control, water damage restoration, landscaping, electrician, concrete, fence installation, pressure washing, garage door repair, painting, carpet cleaning, junk removal, locksmith
- **Total pairs**: ~2,080
- **Estimated cost**: $20-40 (within $50 budget)
- **Estimated runtime**: ~5.5 hours

### Execution

The `scripts/explore/bulk_score.py` script calls `POST /api/niches/score` for each (city, service) pair:
- Sequential execution with 2s delay between calls (rate limiting)
- `--resume` flag skips pairs already scored in `metro_scores` (preserves existing 33 reports)
- Results logged to `scripts/explore/bulk_score_results.jsonl`
- Run against local FastAPI server on port 8001

### Matview Refresh

After scoring completes, the script calls `_refresh_explore_market_cells()` RPC to update the materialized view. Can also be triggered manually:
```sql
SELECT _refresh_explore_market_cells();
```

### Incremental Expansion

The `--resume` flag enables incremental expansion:
1. Run initial batch: `python -m scripts.explore.bulk_score --apply --cities 130 --services 16`
2. If interrupted, resume: `python -m scripts.explore.bulk_score --apply --cities 130 --services 16 --resume`
3. Add more services later by extending the `SERVICES` list and running with `--resume`

## Implementation Order

1. **Phase 1** (backend fix) — unblocks all other phases
2. **Phase 3** (sort fix) — small, closely related to Phase 1, do together
3. **Phase 4** (data expansion) — start bulk scoring in background
4. **Phase 2** (frontend redesign) — implement while scoring runs, test with real data as it populates

## Out of Scope

- V2 scoring integration (separate feature)
- Explore refresh automation (existing refresh targets system handles this)
- Service catalog management (adding/removing services from `niche_naics_mapping`)
- Mobile-responsive table layout (desktop-first for now)
