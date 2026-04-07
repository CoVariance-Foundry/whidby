# Tasks: Data Persistence Layer

**Input**: Design documents from `/specs/010-data-persistence-layer/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required per constitution (Principle I: TDD is non-negotiable). Tests written before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)

## Story Mapping

| Story | Priority | Plan Phase | Description |
|-------|----------|------------|-------------|
| US1 | P1 | Phase 1 | Repeated niche queries use cached data (observation store) |
| US2 | P2 | Phase 2 | Scoring anchored against industry baselines (canonical reference + cold start) |
| US3 | P3 | Phase 3 | Temporal trend analysis for key markets (anchor search system) |
| US4 | P2 | Phase 2 | Cold start bootstraps benchmarks from day one |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Migrations, shared utilities, and project scaffolding that all user stories depend on.

- [x] T001 Create `observations` table migration in `supabase/migrations/005_observation_store.sql` per data-model.md schema (id, endpoint, query_params, query_hash, observed_at, source, run_id, cost_usd, api_queue_mode, storage_path, payload_size_bytes, ttl_category, expires_at, status, error_message, payload_purged columns; 4 indexes on query_hash+expires_at, query_hash+observed_at, source+observed_at, expires_at)
- [x] T002 [P] Create `canonical_metros`, `canonical_benchmarks`, `canonical_niches` tables migration in `supabase/migrations/006_canonical_reference.sql` per data-model.md schemas
- [x] T003 [P] Create `anchor_configs`, `anchor_runs`, `signal_snapshots` tables migration in `supabase/migrations/007_anchor_system.sql` per data-model.md schemas (includes UNIQUE constraints and indexes)
- [x] T004 [P] Create RLS policies for all 7 new tables in `supabase/migrations/008_persistence_rls.sql` (same service_role pattern as 004_rls_policies.sql)
- [x] T005 Update `test_supabase_schema.py` assertions to include all 7 new tables in RLS checks and add structural assertions for `observations`, `canonical_benchmarks`, `anchor_configs`, and `signal_snapshots` in `tests/unit/test_supabase_schema.py`
- [x] T006 [P] Add `TTL_DURATIONS` dict and `BENCHMARK_SCORING_ENABLED = False` flag to `src/config/constants.py` (TTL values: serp=24h, keyword=30d, business=7d, review=7d, technical=14d, reference=90d)
- [x] T007 [P] Add `ttl_category: str` field to the frozen `Endpoint` dataclass in `src/clients/dataforseo/endpoints.py` and assign a category to each of the 10 existing endpoint constants (SERP_ORGANIC→serp, KEYWORD_VOLUME→keyword, BUSINESS_LISTINGS→business, etc.)
- [x] T008 [P] Create `src/clients/dataforseo/query_hash.py` — extract hash logic from `cache.py`'s `_key()` method into a standalone `compute_query_hash(endpoint: str, params: dict) -> str` function with EXCLUDED_KEYS set for non-semantic fields
- [x] T009 [P] Create test fixtures in `tests/fixtures/observation_fixtures.py` (sample observation records, gzipped payloads, TTL category mappings, cache-hit/miss scenarios) and `tests/fixtures/benchmark_fixtures.py` (sample benchmarks, canonical metro data, niche taxonomy entries)

**Checkpoint**: All migrations pass `supabase db push`. Schema tests pass. Shared constants and utilities ready.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `ObservationStore` class and M0 client refactor. MUST be complete before any user story work.

### Tests (write first, expect red)

- [x] T010 [P] Write unit tests for `compute_query_hash` in `tests/unit/test_query_hash.py` — deterministic hashing, excluded keys, sorted params, empty params, same endpoint+params always produces same hash
- [x] T011 [P] Write unit tests for `ObservationStore` in `tests/unit/test_observation_store.py` — cache hit (fresh), cache miss (expired), cache miss (no entry), force refresh bypass, error observations never served, `status='partial'` observations skipped, Storage failure fallback (index row written with status=partial), gzip payload round-trip, storage path convention validation

### Implementation

- [x] T012 Build `ObservationStore` class in `src/clients/dataforseo/observation_store.py` — constructor takes Supabase client + storage bucket name; methods: `check_cache(query_hash) -> CacheCheckResult | None`, `store(endpoint, params, query_hash, ttl_category, data, cost_usd, source, run_id, queue_mode) -> ObservationRecord`, `download_payload(storage_path) -> dict`; on Storage upload failure: write index row with `storage_path=None, status='partial'`, log warning, return None so caller falls through to in-memory cache
- [x] T013 Refactor `src/clients/dataforseo/client.py` — add `observation_store: ObservationStore | None = None` as optional keyword-only constructor param; in `_queued_request` and `_live_request`: before `self._cache.get()`, check `self._observation_store.check_cache()` if available; after successful API response, call `self._observation_store.store()` alongside `self._cache.put()`; add `force_refresh: bool = False` and `run_id: str | None = None` keyword params to all 10 public methods, threading them through to the internal request methods
- [x] T014 Update `src/clients/dataforseo/cache.py` — `ResponseCache` remains as in-memory fallback; when `ObservationStore` is present and returns a cache hit, skip in-memory lookup; when Storage is unavailable (observation status=partial), `ResponseCache` serves as warm fallback for the current process
- [x] T015 Update `src/clients/dataforseo/cost_tracker.py` — when `ObservationStore` is present, cost is recorded on the observation row (`cost_usd` field) instead of only in-memory; add deprecation note for `api_usage_log` in docstring; keep in-memory `CostRecord` list for backward compatibility with `client.cost_log` and `client.total_cost` properties

### Integration Validation

- [x] T016 Write integration test in `tests/integration/test_m0_write_through.py` — with a real Supabase instance: make an API call, verify observation row exists, make same call again, verify cache hit (cost=0), verify payload downloadable from Storage
- [x] T017 Write regression test in `tests/integration/test_pipeline_regression.py` — run M5→M9 pipeline with and without ObservationStore injected, assert identical scoring output (FR-012, SC-006)

**Checkpoint**: Foundation ready. `pytest tests/unit/test_query_hash.py tests/unit/test_observation_store.py -v` passes. M0 client accepts optional ObservationStore. Existing pipeline behavior unchanged.

---

## Phase 3: User Story 1 — Repeated Niche Queries Use Cached Data (Priority: P1) — MVP

**Goal**: Two identical pipeline runs within the freshness window: second run makes zero paid API calls and completes 50%+ faster.

**Independent Test**: Run `collect_data("plumber", phoenix_metro, "balanced", client)` twice within an hour. Assert second run has zero API cost and equivalent output.

### Tests for User Story 1

- [ ] T018 [P] [US1] Write unit test for TTL-aware freshness in `tests/unit/test_observation_store.py` — observation with `expires_at > now()` is a hit; observation with `expires_at < now()` is a miss; SERP data (24h TTL) expires while keyword data (30d TTL) is still fresh in the same run
- [ ] T019 [P] [US1] Write unit test for force-refresh in `tests/unit/test_observation_store.py` — `force_refresh=True` bypasses cache, new observation appended (not overwriting old), old observation still queryable for temporal analysis

### Implementation for User Story 1

- [ ] T020 [US1] Create Supabase Storage bucket `observations/` (via CLI or dashboard config script)
- [ ] T021 [US1] Wire `ObservationStore` into the pipeline entry point — wherever `DataForSEOClient` is instantiated for pipeline runs (currently `src/research_agent/tools/api_tools.py` and test helpers), create `ObservationStore` with Supabase client and pass it to the constructor; ensure the pipeline's `data_collection.collect_data()` call path gets a client with observation persistence enabled
- [ ] T022 [US1] Verify partial-TTL expiry: write an end-to-end test showing that within a mixed-TTL run (SERP expired at 25h, keyword still fresh at 25h), only SERP endpoints are re-fetched while keyword data is served from cache — in `tests/unit/test_observation_store.py`
- [ ] T023 [US1] Add cache-hit/miss metrics logging — when `ObservationStore.check_cache()` returns a hit, log at INFO level with endpoint, query_hash, and time-to-expiry; on miss, log the TTL category and reason (expired vs. not found)

**Checkpoint**: US1 complete. `pytest tests/unit/test_observation_store.py tests/unit/test_query_hash.py -v` all green. A second pipeline run for the same niche+metro within TTL windows makes zero paid API calls.

---

## Phase 4: User Story 4 — Cold Start Bootstraps Benchmarks (Priority: P2)

**Goal**: Batch-execute 100 pipeline runs across 20 niches × 25 metros to populate the observation store and compute initial benchmarks.

**Independent Test**: Run cold start for a 3-niche × 3-metro subset. Verify observations are stored and benchmarks are computed within minutes.

> **Note**: US4 is sequenced before US2 because US2 (benchmark-anchored scoring) depends on the cold start having populated the observation store and benchmark tables.

### Tests for User Story 4

- [ ] T024 [P] [US4] Write unit tests for metro store CRUD in `tests/unit/test_canonical_metro_store.py` — insert, read by cbsa_code, read by size tier, read all
- [ ] T025 [P] [US4] Write unit tests for niche store CRUD in `tests/unit/test_canonical_niche_store.py` — insert, read by keyword, read by vertical
- [ ] T026 [P] [US4] Write unit tests for benchmark computation in `tests/unit/test_benchmark_compute.py` — median aggregation, minimum sample size (>=5) gate, 90-day observation window, upsert on recompute
- [ ] T027 [P] [US4] Write unit test for cold start matrix validation in `tests/unit/test_cold_start.py` — every niche in >=3 metros (one per tier), every metro in >=2 niches, total pairs = 100

### Implementation for User Story 4

- [ ] T028 [P] [US4] Build `src/canonical/metro_store.py` — CRUD for `canonical_metros` table; `get_by_cbsa(code) -> CanonicalMetro | None`, `get_by_tier(tier) -> list[CanonicalMetro]`, `upsert(metro) -> CanonicalMetro`
- [ ] T029 [P] [US4] Build `src/canonical/niche_store.py` — CRUD for `canonical_niches` table; `get(keyword) -> CanonicalNiche | None`, `get_by_vertical(vertical) -> list[CanonicalNiche]`, `upsert(niche) -> CanonicalNiche`
- [ ] T030 [US4] Build `src/canonical/benchmark_compute.py` — `compute_benchmark(niche, metric, metro_tier) -> BenchmarkResult | None`; queries observations from last 90 days, requires sample_size >= 5, computes median, upserts to `canonical_benchmarks` with `source='computed'` and `valid_until = now() + 7 days`
- [ ] T031 [US4] Migrate `src/data/metro_db.py` to read from `canonical_metros` table with fallback to `src/data/seed/cbsa_seed.json` — `MetroDB.from_canonical(supabase_client)` class method alongside existing `from_seed()`
- [ ] T032 [P] [US4] Build seed script `src/scripts/seed_canonical_metros.py` — reads census CBSA data, classifies metro_size_tier (major/mid/small), inserts into `canonical_metros`
- [ ] T033 [P] [US4] Build seed script `src/scripts/seed_canonical_niches.py` — seeds 20 target niches across 5 verticals (home_services, automotive, legal, medical, specialty_services) with category mappings and modifier patterns
- [ ] T034 [P] [US4] Build seed script `src/scripts/seed_external_benchmarks.py` — loads published benchmark data (median CPC, avg review count, avg DA) into `canonical_benchmarks` with `source='external'` and `valid_until = now() + 90 days`
- [ ] T035 [US4] Build cold start runner `src/scripts/cold_start.py` — reads niche×metro matrix from a JSON config, executes full M4→M9 pipeline per pair using the M0 client with ObservationStore enabled, rate-limited by existing `_RateLimiter`, configurable `--batch-size` and `--concurrency`, progress logging per completed pair
- [ ] T036 [US4] Build benchmark computation CLI `src/scripts/compute_benchmarks.py` — iterates all (niche, metro_tier, metric) combos, calls `compute_benchmark()` for each, logs computed count vs. skipped (insufficient data)
- [ ] T037 [US4] Create cold start matrix config `configs/cold_start_matrix.json` — 100 niche×metro pairs per spec §10.2 selection criteria

**Checkpoint**: US4 complete. Seed scripts populate canonical tables. Cold start runner can execute pipeline batches. Benchmarks are computed from observation data. `pytest tests/unit/test_benchmark_compute.py tests/unit/test_cold_start.py -v` all green.

---

## Phase 5: User Story 2 — Scoring Anchored Against Industry Baselines (Priority: P2)

**Goal**: Scoring reports blend relative (within-report) and absolute (vs. benchmark) components when benchmarks are available, with graceful fallback to relative-only when they are not.

**Independent Test**: Generate a report for a niche+metro with existing benchmarks. Verify demand score incorporates benchmark comparison. Generate for a niche without benchmarks. Verify fallback to relative-only with no errors.

### Tests for User Story 2

- [ ] T038 [P] [US2] Write unit tests for benchmark resolver in `tests/unit/test_benchmark_resolver.py` — priority chain: fresh computed > fresh external > stale computed > None; expired benchmarks marked `is_stale=True`; `sample_size < 5` computed benchmarks rejected; NULL `metro_size_tier` returns national benchmark
- [ ] T039 [P] [US2] Write unit test for benchmark-blended demand scoring in `tests/unit/test_demand_score.py` — when `BENCHMARK_SCORING_ENABLED=True` and benchmark exists: score blends percentile_rank (relative) with scaled absolute value; when benchmark missing: falls back to pure percentile_rank; when flag is False: always relative-only regardless of benchmark availability

### Implementation for User Story 2

- [ ] T040 [US2] Build `src/canonical/benchmark_resolver.py` — `get_benchmark(niche, metric, metro_tier) -> BenchmarkResult | None`; implements priority chain: fresh computed > fresh external > stale computed > None; returns `BenchmarkResult` with `is_stale` flag
- [ ] T041 [US2] Add recalibration analysis script `src/scripts/recalibrate_m7.py` — reads cold start observations, computes p5/p25/p50/p75/p95 distributions for each M7 normalization metric (DA, CPC, review count, etc.), outputs recommended ceiling/floor values and blend ratio, compares against current `M7_*` constants in `constants.py`
- [ ] T042 [US2] Update `M7_*` normalization boundaries in `src/config/constants.py` based on recalibration output — update `MEDIAN_LOCAL_SERVICE_CPC`, `M7_DA_CEILING`, and other normalization ceilings/floors with data-driven values; document the data source and sample size in comments
- [ ] T043 [US2] Integrate benchmarks into `src/scoring/demand_score.py` — when `BENCHMARK_SCORING_ENABLED` is True, `compute_demand_score()` calls `get_benchmark(niche, "median_search_volume", metro_tier)` and blends `percentile_rank * relative_weight + scale(volume, 0, benchmark * 3) * absolute_weight`; blend ratio configurable via constants; when flag is False or benchmark is None, pure `percentile_rank` (current behavior)
- [ ] T044 [US2] Update `docs-canonical/DATA-MODEL.md` to add `api_usage_log` deprecation note and `canonical_benchmarks` integration with M7 scoring

**Checkpoint**: US2 complete. `pytest tests/unit/test_benchmark_resolver.py tests/unit/test_demand_score.py -v` all green. With `BENCHMARK_SCORING_ENABLED=False` (default), scoring output is identical to pre-persistence baseline. With flag enabled, demand scores incorporate benchmark anchoring.

---

## Phase 6: User Story 3 — Temporal Trend Analysis for Key Markets (Priority: P3)

**Goal**: Automated daily data collection for configured niche×metro pairs, producing queryable signal snapshot time series.

**Independent Test**: Configure an anchor for "pest control in Atlanta", run it for 7 days, query `signal_snapshots` for a 7-day time series, verify 7 daily records with expected signal fields.

### Tests for User Story 3

- [ ] T045 [P] [US3] Write unit tests for anchor config manager in `tests/unit/test_anchor_config_manager.py` — CRUD operations, auto-config from M4 keyword expansion output (selects top Tier 1+2 transactional/commercial keywords), UNIQUE(niche_keyword, cbsa_code) enforcement, frequency validation
- [ ] T046 [P] [US3] Write unit tests for anchor runner in `tests/unit/test_anchor_runner.py` — budget check (cumulative_cost + estimated > max_daily_cost → status=budget_exceeded), partial failure (one data type fails, others succeed, failure logged), status lifecycle (running → completed/failed), observation count tracking
- [ ] T047 [P] [US3] Write unit tests for signal snapshot extraction in `tests/unit/test_snapshot_extractor.py` — extracts serp_avg_da_top5, serp_aggregator_count, local_pack_review_avg, keyword_volume_total, keyword_cpc_avg from raw observation payloads; handles missing data types gracefully (nullable fields); links observation_ids

### Implementation for User Story 3

- [ ] T048 [US3] Build `src/anchor/config_manager.py` — `create_anchor(niche, cbsa_code, keywords, frequency) -> AnchorConfig`, `auto_config_from_expansion(keyword_expansion, cbsa_code) -> AnchorConfig` (filters to Tier 1+2 transactional/commercial), `list_due_anchors() -> list[AnchorConfig]` (WHERE enabled AND next_run_at <= now()), `update_schedule(config_id, last_run_at, next_run_at)`
- [ ] T049 [US3] Build `src/anchor/runner.py` — `run_anchor(config, client) -> AnchorRun`; checks budget (skip if exceeded), calls M0 client methods based on config flags (collect_serp, collect_keyword_volume, collect_reviews, collect_gbp, collect_lighthouse), updates cumulative_cost, inserts anchor_runs log row; on partial failure: log error, continue collecting remaining data types, set status='completed' with error details in error_message
- [ ] T050 [US3] Build `src/anchor/snapshot_extractor.py` — `extract_snapshot(anchor_config, observation_ids, raw_payloads) -> SignalSnapshot`; reuses signal extraction functions from `src/pipeline/extractors/` (demand_signals, organic_signals, local_signals) to derive denormalized snapshot fields from raw observation payloads
- [ ] T051 [US3] Build anchor runner API endpoint — thin FastAPI endpoint at `/api/anchor/run` that the Supabase Edge Function calls; queries due anchors via `config_manager.list_due_anchors()`, runs each via `runner.run_anchor()`, extracts snapshot via `snapshot_extractor`, inserts `signal_snapshots` row
- [ ] T052 [P] [US3] Build seed script `src/scripts/seed_anchors.py` — auto-configures anchors for the 20 cold-start niches in their respective metros using M4 keyword expansion output from cold start runs
- [ ] T053 [US3] Build Supabase Edge Function `supabase/functions/anchor-runner/index.ts` — triggered by pg_cron, invokes the Python anchor runner API endpoint via HTTP, handles timeout and retry

**Checkpoint**: US3 complete. `pytest tests/unit/test_anchor_runner.py tests/unit/test_snapshot_extractor.py tests/unit/test_anchor_config_manager.py -v` all green. Anchors can be configured, run, and produce daily signal snapshots.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and validation across all stories.

- [ ] T054 [P] Update `docs-canonical/DATA-MODEL.md` with observation store entities, anchor system entities, and deprecation notes for `api_usage_log` and `metro_location_cache`
- [ ] T055 [P] Update `docs-canonical/ARCHITECTURE.md` with persistence layer overview (3 layers, module map additions for `src/canonical/` and `src/anchor/`)
- [ ] T056 [P] Update `docs-canonical/ENVIRONMENT.md` with new env vars (Supabase Storage bucket config) and new CLI scripts (cold start, seed, benchmark compute)
- [ ] T057 Run `ruff check src tests` and fix any lint issues across all new files
- [ ] T058 Run quickstart.md validation — execute the setup steps in `specs/010-data-persistence-layer/quickstart.md` and verify all commands succeed
- [ ] T059 Run full regression suite — `pytest tests/unit/ -v` (all unit tests pass) and `pytest tests/integration/ -v -m integration` (pipeline regression, write-through cache)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on T001, T006, T007, T008 from Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion — no dependencies on other stories
- **US4 (Phase 4)**: Depends on Phase 2 (needs ObservationStore) + T002 from Setup (canonical tables) — no dependencies on US1
- **US2 (Phase 5)**: Depends on US4 completion (needs cold start data + computed benchmarks)
- **US3 (Phase 6)**: Depends on Phase 2 (needs ObservationStore) — can run in parallel with US4/US2
- **Polish (Phase 7)**: Depends on all desired stories being complete

### User Story Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational: ObservationStore + M0 refactor)
    │
    ├──────────────────────┬──────────────────────┐
    ▼                      ▼                      ▼
Phase 3 (US1: Cache)   Phase 4 (US4: Cold Start)  Phase 6 (US3: Anchors)
                           │                        [can run in parallel
                           ▼                         with US4/US2]
                       Phase 5 (US2: Benchmarks)
                           │
                           ▼
                       Phase 7 (Polish)
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation (constitution Principle I)
- Models/stores before services
- Services before integration points
- Core implementation before cross-cutting concerns

### Parallel Opportunities

**Phase 1 (Setup)**: T002, T003, T004 can run in parallel with each other. T006, T007, T008, T009 can all run in parallel.

**Phase 2 (Foundational)**: T010 and T011 (tests) run in parallel. T012 depends on both tests passing (red→green).

**Phase 4 (US4)**: T024-T027 (tests) all run in parallel. T028, T029 (stores) run in parallel. T032, T033, T034 (seed scripts) all run in parallel.

**Phase 5 (US2)**: T038 and T039 (tests) run in parallel.

**Phase 6 (US3)**: T045, T046, T047 (tests) all run in parallel. T052 (seed script) can run in parallel with T051 (API endpoint).

---

## Parallel Example: Phase 1 Setup

```bash
# These can all run in parallel (different files, no dependencies):
T002: Create canonical tables migration in 006_canonical_reference.sql
T003: Create anchor system migration in 007_anchor_system.sql
T004: Create RLS policies in 008_persistence_rls.sql
T006: Add TTL_DURATIONS and feature flag to constants.py
T007: Add ttl_category to Endpoint dataclass in endpoints.py
T008: Create query_hash.py module
T009: Create test fixtures
```

## Parallel Example: Phase 4 Cold Start

```bash
# Tests first (parallel):
T024: Unit tests for metro store
T025: Unit tests for niche store
T026: Unit tests for benchmark compute
T027: Unit tests for cold start matrix

# Then stores (parallel):
T028: Build metro_store.py
T029: Build niche_store.py

# Then seed scripts (parallel, after stores):
T032: Seed canonical metros
T033: Seed canonical niches
T034: Seed external benchmarks
```

---

## Implementation Strategy

### MVP First (US1 Only: Cached Pipeline Runs)

1. Complete Phase 1: Setup (migrations + shared utilities)
2. Complete Phase 2: Foundational (ObservationStore + M0 refactor)
3. Complete Phase 3: US1 (cache integration + Storage bucket)
4. **STOP and VALIDATE**: Run two identical pipeline executions, verify second has zero API cost
5. This alone delivers SC-001 (50%+ faster) and SC-003 (30%+ cost reduction)

### Incremental Delivery

1. Setup + Foundational → ObservationStore ready
2. Add US1 → Cache works → **Deploy** (immediate cost savings)
3. Add US4 → Cold start populates data → Benchmarks computed
4. Add US2 → Benchmark scoring available (behind feature flag) → **Deploy**
5. Add US3 → Anchors collecting daily → Time series building → **Deploy**
6. Each story adds value without breaking previous stories

### Task Count Summary

| Phase | Tasks | Parallel Opportunities |
|-------|-------|----------------------|
| Phase 1: Setup | 9 | 7 parallelizable |
| Phase 2: Foundational | 8 | 2 test tasks parallel |
| Phase 3: US1 (Cache) | 6 | 2 test tasks parallel |
| Phase 4: US4 (Cold Start) | 14 | 8 parallelizable |
| Phase 5: US2 (Benchmarks) | 7 | 2 test tasks parallel |
| Phase 6: US3 (Anchors) | 9 | 4 parallelizable |
| Phase 7: Polish | 6 | 3 parallelizable |
| **Total** | **59** | **28 parallelizable** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Tests must fail before implementation (red→green per constitution)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- `BENCHMARK_SCORING_ENABLED` flag defaults to False — scoring output unchanged until explicitly enabled
- `api_usage_log` and `metro_location_cache` are deprecated-in-place, not dropped
