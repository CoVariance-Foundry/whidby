# Implementation Plan: Data Persistence Layer

**Branch**: `010-data-persistence-layer` | **Date**: 2026-04-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-data-persistence-layer/spec.md`

## Summary

Add three persistence layers to the Widby scoring engine: (1) an observation store that caches every DataForSEO API response with TTL-aware freshness, (2) canonical reference tables for metro demographics, industry benchmarks, and niche taxonomies, and (3) an anchor search system for automated longitudinal data collection. The primary integration point is the M0 DataForSEO client, which is refactored from pass-through to write-through without changing its public interface.

## Technical Context

**Language/Version**: Python 3.11+ (existing codebase)
**Primary Dependencies**: `httpx`, `pydantic>=2`, existing `DataForSEOClient` (`src/clients/dataforseo/`), Supabase Python client
**Storage**: Supabase PostgreSQL (observation index, canonical tables, anchor config) + Supabase Storage (observation payloads as gzipped JSON)
**Testing**: `pytest` + `pytest-asyncio` + `pytest-mock`
**Target Platform**: Linux server (same as existing pipeline)
**Project Type**: Library/pipeline (Python async functions, no agent framework)
**Performance Goals**: Cache lookup < 100ms, cache hit returns data 50%+ faster than API call, 365-day time-series query < 2s
**Constraints**: DataForSEO rate limit 2000 calls/min (existing), Supabase Storage 50MB file limit, 24-month retention on payloads
**Scale/Scope**: V1 = 200 anchors (~$420/month), cold start = 100 simulated reports (~$250 one-time)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-Driven, TDD | PASS | Spec artifact complete. Tests written before implementation per constitution. |
| II. Module-First Architecture | PASS | Observation store is a new component within M0's module boundary. Canonical and anchor are new modules with clear I/O contracts. No module boundary violations. |
| III. No Framework for V1 | PASS | Plain Python + asyncio + Supabase client. No new frameworks introduced. Anchor runner uses Supabase Edge Function as scheduler only. |
| IV. Code Quality Standards | PASS | All new code will follow ruff, type annotations, Google docstrings. |
| V. Documentation as Code | PASS | `docs-canonical/DATA-MODEL.md` already updated (v1.1.0) with persistence layer entities. Plan artifacts generated. |
| VI. Simplicity and Determinism | PASS | Phase 1 is additive-only (no scoring changes). Benchmark integration deferred to Phase 2 with explicit opt-in. YAGNI respected. |

**Post-Phase 1 re-check**: All gates still pass. Benchmark-blended scoring (Phase 2) will modify M7 output and requires recalibration — this is documented and explicitly flagged as a breaking scoring change.

## Project Structure

### Documentation (this feature)

```text
specs/010-data-persistence-layer/
├── plan.md                                # This file
├── spec.md                                # Feature specification
├── research.md                            # Phase 0: research decisions
├── data-model.md                          # Phase 1: entity schemas
├── quickstart.md                          # Phase 1: setup guide
├── contracts/
│   └── observation-store.schema.json      # Phase 1: I/O contracts
└── tasks.md                               # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── clients/dataforseo/
│   ├── client.py                 # MODIFIED: inject ObservationStore, add force_refresh/run_id
│   ├── cache.py                  # MODIFIED: delegate to ObservationStore, keep as in-memory fallback
│   ├── cost_tracker.py           # MODIFIED: write cost to observations.cost_usd
│   ├── endpoints.py              # MODIFIED: add ttl_category field to Endpoint dataclass
│   ├── types.py                  # UNCHANGED
│   ├── observation_store.py      # NEW: Supabase-backed observation persistence + cache
│   └── query_hash.py             # NEW: deterministic query hash computation
├── canonical/
│   ├── __init__.py               # NEW
│   ├── benchmark_resolver.py     # NEW: get_benchmark() priority chain
│   ├── benchmark_compute.py      # NEW: weekly benchmark computation from observations
│   ├── metro_store.py            # NEW: canonical_metros read/write
│   └── niche_store.py            # NEW: canonical_niches read/write
├── anchor/
│   ├── __init__.py               # NEW
│   ├── runner.py                 # NEW: anchor data collection executor
│   ├── snapshot_extractor.py     # NEW: signal snapshot derivation (reuses M6 extractors)
│   └── config_manager.py         # NEW: anchor CRUD + auto-config from M4 output
├── scripts/
│   ├── cold_start.py             # NEW: batch pipeline executor for bootstrapping
│   ├── compute_benchmarks.py     # NEW: benchmark computation CLI
│   ├── seed_canonical_metros.py  # NEW: census data seeder
│   ├── seed_canonical_niches.py  # NEW: niche taxonomy seeder
│   └── seed_external_benchmarks.py # NEW: external benchmark seeder
├── data/metro_db.py              # MODIFIED: read from canonical_metros, fallback to seed JSON
├── scoring/demand_score.py       # MODIFIED (Phase 2 only): blend percentile_rank with benchmark
└── config/constants.py           # MODIFIED: add TTL_DURATIONS dict, benchmark config constants

supabase/migrations/
├── 005_observation_store.sql     # NEW: observations table + indexes
├── 006_canonical_reference.sql   # NEW: canonical_metros, canonical_benchmarks, canonical_niches
├── 007_anchor_system.sql         # NEW: anchor_configs, anchor_runs, signal_snapshots
└── 008_persistence_rls.sql       # NEW: RLS policies for all new tables

tests/
├── unit/
│   ├── test_observation_store.py     # NEW: cache hit/miss, TTL, hash, storage path
│   ├── test_query_hash.py            # NEW: deterministic hashing, excluded keys
│   ├── test_benchmark_resolver.py    # NEW: priority chain, stale fallback, sample size
│   ├── test_benchmark_compute.py     # NEW: aggregation, minimum sample size
│   ├── test_anchor_runner.py         # NEW: budget check, partial failure, status lifecycle
│   ├── test_snapshot_extractor.py    # NEW: signal extraction from observation payloads
│   └── test_cold_start.py           # NEW: matrix validation, batch execution
├── integration/
│   ├── test_m0_write_through.py      # NEW: end-to-end cache with real Supabase
│   └── test_pipeline_regression.py   # NEW: M5→M9 output identity check
└── fixtures/
    ├── observation_fixtures.py       # NEW: sample observations, payloads
    └── benchmark_fixtures.py         # NEW: sample benchmarks, metro data
```

**Structure Decision**: Follows the existing single-project layout. New `src/canonical/` and `src/anchor/` packages are peer modules alongside `src/scoring/`, `src/pipeline/`, and `src/clients/`. Migration files continue the sequential numbering in `supabase/migrations/`. Test files mirror source paths per constitution.

## Implementation Phases

### Phase 1: Observation Store (refactor M0 + migrations)

The M0 client gains write-through persistence. Existing M5-M9 pipeline code is unchanged — it calls M0 the same way, but M0 now persists behind the scenes.

| # | Task | Files | Effort | Risk | Depends On |
|---|------|-------|--------|------|------------|
| 1.1 | Create `observations` table migration | `005_observation_store.sql` | S | Low | — |
| 1.2 | Create Supabase Storage bucket config | Dashboard / CLI | S | Low | — |
| 1.3 | Extract `query_hash.py` from `cache.py` | `query_hash.py`, `cache.py` | S | Low | — |
| 1.4 | Add `ttl_category` to `Endpoint` dataclass | `endpoints.py`, `constants.py` | S | Low | — |
| 1.5 | Build `ObservationStore` class | `observation_store.py` | M | Low | 1.1, 1.3, 1.4 |
| 1.6 | Refactor `client.py` to inject `ObservationStore` as optional kwarg | `client.py` | M | Low | 1.5 |
| 1.7 | Update `cache.py` as in-memory fallback for Storage outages | `cache.py` | S | Low | 1.6 |
| 1.8 | Migrate `cost_tracker.py` writes to observation rows; deprecate `api_usage_log` | `cost_tracker.py`, docs | S | Low | 1.6 |
| 1.9 | Add `force_refresh` + `run_id` params to all public methods | `client.py` | S | Low | 1.6 |
| 1.10 | RLS policies for `observations` | `008_persistence_rls.sql` | S | Low | 1.1 |
| 1.11 | Unit tests: hash, cache hit/miss, TTL, force refresh, Storage failure fallback | `test_query_hash.py`, `test_observation_store.py` | M | Low | 1.5 |
| 1.12 | Integration test: M5 pipeline with observation store | `test_m0_write_through.py`, `test_pipeline_regression.py` | M | Low-Med | 1.6 |
| 1.13 | Update `test_supabase_schema.py` assertions for new tables | `test_supabase_schema.py` | S | Low | 1.1, 1.10 |

**Validation gate**: Run existing M5→M9 pipeline with refactored M0. Confirm identical scoring output (FR-012, SC-006).

**Risk clarification (1.6)**: Analysis confirms 4 constructor call sites exist (1 production in `api_tools.py`, 3 in tests). All use keyword args. Adding `observation_store: ObservationStore | None = None` as an optional keyword-only parameter breaks zero call sites. Two standalone `FakeDataForSEOClient` classes in test fixtures are duck-typed fakes (not subclasses) and are unaffected. No production code outside `client.py` accesses `_cache`, `cost_log`, or `total_cost`.

**Storage failure mode (1.5, 1.7)**: When Supabase Storage is unavailable for payload upload, the `ObservationStore` must: (a) write the observation index row with `storage_path = None` and `status = 'partial'`, (b) fall through to the in-memory `ResponseCache` so the current pipeline run is unaffected, (c) log the failure for alerting. On subsequent cache lookups, observations with `status = 'partial'` are skipped — the pipeline re-fetches from the API and retries the full write.

**`api_usage_log` deprecation (1.8)**: The existing `api_usage_log` table (from `003_shared_tables.sql`) is fully redundant with `observations` — both record endpoint, cost, parameters, and report linkage. Currently `CostTracker` has never been wired to write to `api_usage_log` (the flush is a TODO in the docstring). Task 1.8 wires cost tracking to `observations.cost_usd` instead. The `api_usage_log` table is NOT dropped (existing RLS policies and schema tests reference it) but is marked deprecated in `docs-canonical/DATA-MODEL.md` for removal in a future cleanup migration.

### Phase 2: Canonical Reference Store + Cold Start

Benchmarks, metro enrichment, and the cold start simulation. Can start in parallel with Phase 1 tasks 1.1-1.4 (table creation is independent).

| # | Task | Files | Effort | Risk | Depends On |
|---|------|-------|--------|------|------------|
| 2.1 | Create canonical tables migration | `006_canonical_reference.sql` | S | Low | — |
| 2.2 | Build `metro_store.py` CRUD | `canonical/metro_store.py` | S | Low | 2.1 |
| 2.3 | Build `niche_store.py` CRUD | `canonical/niche_store.py` | S | Low | 2.1 |
| 2.4 | Migrate `metro_db.py` to read from `canonical_metros` | `data/metro_db.py` | S | Low | 2.2 |
| 2.5 | Build `benchmark_resolver.py` (get_benchmark priority chain) | `canonical/benchmark_resolver.py` | M | Low | 2.1 |
| 2.6 | Build `benchmark_compute.py` (weekly aggregation) | `canonical/benchmark_compute.py` | M | Low | 2.1, Phase 1 |
| 2.7 | Seed scripts: metros, niches, external benchmarks | `scripts/seed_*.py` | M | Low | 2.1 |
| 2.8 | Build cold start runner | `scripts/cold_start.py` | M | Med | Phase 1, 2.7 |
| 2.9 | Unit tests: benchmark resolver, compute, metro store | `test_benchmark_*.py` | M | Low | 2.5, 2.6 |
| 2.10 | RLS policies for canonical tables | `008_persistence_rls.sql` | S | Low | 2.1 |
| 2.11 | Define benchmark integration feature flag in `constants.py` | `config/constants.py` | S | Low | — |
| 2.12 | Recalibrate `M7_*` normalization boundaries from cold start data | `config/constants.py`, analysis script | M | Med | 2.8 |
| 2.13 | Integrate benchmarks into M7 demand scoring (gated by feature flag) | `scoring/demand_score.py` | M | **Med-High** | 2.5, 2.8, 2.11, 2.12 |

**Validation gate**: After cold start, computed benchmarks exist for >=80% of niche×tier combos (SC-002). Computed benchmarks within 50% of external seeds.

**Benchmark scoring integration (2.11–2.13)**: This is the riskiest change in the entire plan — it modifies M7 scoring output, which is a breaking change per constitution. The safeguard is a three-task sequence: (a) task 2.11 adds a `BENCHMARK_SCORING_ENABLED = False` flag in `constants.py` so the change is off by default, (b) task 2.12 uses cold start observation data to recalibrate the hardcoded `M7_*` normalization ceilings/floors (e.g. `M7_DA_CEILING = 60.0`, `MEDIAN_LOCAL_SERVICE_CPC = 5.00`) against real distributions, and (c) task 2.13 implements the blended absolute+relative demand scoring, gated behind the flag. The 60/40 blend ratio (relative/absolute) is an initial estimate — task 2.12 should produce a data-driven recommendation for the ratio based on the cold start distribution analysis.

### Phase 3: Anchor Search System

Automated longitudinal data collection. Depends on Phases 1 and 2 being stable.

| # | Task | Files | Effort | Risk | Depends On |
|---|------|-------|--------|------|------------|
| 3.1 | Create anchor tables migration | `007_anchor_system.sql` | S | Low | — |
| 3.2 | Build `config_manager.py` (CRUD + auto-config from M4) | `anchor/config_manager.py` | M | Low | 3.1 |
| 3.3 | Build `runner.py` (anchor data collection) | `anchor/runner.py` | M | Med | 3.1, Phase 1 |
| 3.4 | Build `snapshot_extractor.py` (reuses M6 extractors) | `anchor/snapshot_extractor.py` | M | Low | 3.3 |
| 3.5 | Build anchor runner Edge Function | `supabase/functions/anchor-runner/` | M | Med | 3.3 |
| 3.6 | Set up pg_cron schedule | Supabase dashboard / migration | S | Low | 3.5 |
| 3.7 | Seed initial anchors for cold-start niches | `scripts/seed_anchors.py` | S | Low | 3.2, Phase 2 |
| 3.8 | Unit tests: runner, snapshot extractor, config manager | `test_anchor_*.py`, `test_snapshot_*.py` | M | Low | 3.2-3.4 |
| 3.9 | RLS policies for anchor tables | `008_persistence_rls.sql` | S | Low | 3.1 |

**Validation gate**: Anchors run 7 consecutive days with >95% completion rate (SC-004). Signal snapshots queryable for time-series.

## Impact on Existing Modules

| Module | Change | Phase | Breaking? |
|--------|--------|-------|-----------|
| **M0** (`src/clients/dataforseo/`) | Major: `ObservationStore` injected, write-through cache, new params | 1 | No — public interface shape unchanged |
| **M1** (`src/data/metro_db.py`) | Minor: reads from `canonical_metros` table, seed file as fallback. `canonical_metros` coexists with `metro_location_cache` — no DROP in this migration set. | 2 | No |
| **M2** (`supabase/migrations/`) | Medium: 4 new migration files. `api_usage_log` deprecated (not dropped). `metro_location_cache` retained alongside `canonical_metros`. | 1-3 | No — additive tables only |
| **M4** (`src/pipeline/keyword_expansion.py`) | None (output consumed by anchor auto-config) | 3 | No |
| **M5** (`src/pipeline/`) | None (benefits from M0 caching automatically) | 1 | No |
| **M6** (`src/pipeline/signal_extraction.py`) | Minor: extraction functions reused by snapshot extractor | 3 | No |
| **M7** (`src/scoring/`) | Medium: benchmark-blended demand scoring (gated by `BENCHMARK_SCORING_ENABLED` flag) | 2 | **Yes — scoring output changes when flag is enabled** |
| **M9** | Minor: report can include benchmark context in guidance | 2 | No |

## Migration Coexistence Notes

**`api_usage_log` (003_shared_tables)**: Fully redundant with the `observations` table — both record endpoint, cost, parameters, and report linkage. `CostTracker` has never been wired to write to it (the flush is still a TODO in the docstring). This table is deprecated-in-place: not dropped (existing RLS policies in 004 and assertions in `test_supabase_schema.py` reference it), not written to going forward. Cost tracking writes go to `observations.cost_usd` instead. Removal deferred to a future cleanup migration.

**`metro_location_cache` (003_shared_tables)**: Coexists with the new `canonical_metros` table. No Python code reads or writes `metro_location_cache` — `MetroDB` reads from a JSON seed file (`cbsa_seed.json`). The table was created in migrations but never connected to application code. Not dropped in this migration set (existing RLS policies and test assertions reference it). `canonical_metros` becomes the active table; `metro_location_cache` remains as a dead artifact.

**`rentability_signals` UNIQUE constraint**: The plan to drop `UNIQUE(niche_keyword, cbsa_code)` via ALTER TABLE in a new migration is safe — no Python code currently writes to this table. The schema test reads raw SQL from `002_experiment_schema.sql` (which retains the original UNIQUE), so it won't break from an ALTER TABLE in 005+.

## Complexity Tracking

No constitution violations. All gates pass.
