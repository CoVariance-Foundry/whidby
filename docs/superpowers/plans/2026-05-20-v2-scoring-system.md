# V2 Scoring System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make V2 scoring production-real: benchmark-backed, census/CBP-aware, top-3/top-5 correct, persisted, and surfaced through domain/application APIs instead of frontend infra reads.
**Architecture:** Next.js BFF owns auth/quota/UI policy; FastAPI application services orchestrate scoring/report reads; pure domain scoring owns formulas; infrastructure adapters own Supabase/DataForSEO/Census access.
**Tech Stack:** Python FastAPI, Supabase/Postgres, DataForSEO, Next.js app router, Vitest, Pytest.

---

### Task Group 1: Canonical Docs and Worktree Guardrails

**Files:**
- Modify: `docs-canonical/ARCHITECTURE.md`
- Modify: `docs-canonical/DATA-MODEL.md`
- Modify: `docs-canonical/TEST-SPEC.md`
- Modify: `.Codex/ACTIVE_WORK.md`

- [x] Confirm this branch is `codex/v2-scoring-system` inside `.worktrees/codex-v2-scoring-system`.
- [x] Keep implementation changes out of canonical docs except where contracts, tables, or boundaries change.
- [x] Update canonical docs before code when V2 APIs or persistence semantics change.
- [x] Run `git diff --check` after each implementation task group.

### Task Group 2: V2 Dependency Wiring

**Files:**
- Modify: `src/research_agent/api.py`
- Modify: `src/pipeline/orchestrator.py`
- Modify: `src/clients/supabase_persistence.py`
- Modify: `src/scoring/benchmark_repository.py`
- Modify: `src/clients/seo_benchmark_repository.py`
- Test: `tests/unit/test_api_niches.py`
- Test: `tests/unit/test_pipeline_orchestrator.py`
- Test: `tests/unit/test_supabase_persistence.py`

- [x] Wire FastAPI service factories so scoring receives a `SeoBenchmarkRepository` instead of constructing Supabase reads inside formulas.
- [x] Pass the shared `SupabasePersistence.client` into repository adapters; do not reach into private persistence internals.
- [x] Keep Next.js scoring routes as BFF proxies for auth/quota/UI policy only.
- [x] Add tests proving benchmark repository injection works with fixtures and no network.

### Task Group 3: V2 Signal Semantics

**Files:**
- Modify: `src/scoring/v2.py`
- Modify: `src/domain/services/discovery_service.py`
- Modify: `src/clients/explore_repository.py`
- Test: `tests/scoring/test_v2_scoring.py`
- Test: `tests/unit/test_strategy_projection.py`
- Test: `tests/unit/test_explore_repository.py`

- [x] Define V2 runtime facts from `seo_facts`, `seo_benchmarks`, `metros`, and `census_cbp_establishments`.
- [x] Compute `top3_review_count_min` as the minimum review count among ranked local top-3 listings with review data.
- [x] Compute `top3_review_velocity_avg` as the average monthly review velocity among ranked local top-3 listings with velocity data.
- [x] Treat missing top-3 review data as lower confidence, not as zero competition.
- [x] Preserve CBP business density and growth as service-aware signals joined through `niche_naics_mapping`.

### Task Group 4: Top-5 Backlinks and Lighthouse

**Files:**
- Modify: `src/pipeline/batch_executor.py`
- Modify: `src/pipeline/extractors/organic_competition.py`
- Modify: `src/scoring/v2.py`
- Test: `tests/unit/test_batch_executor.py`
- Test: `tests/unit/test_signal_extraction.py`
- Test: `tests/unit/test_signal_extractors.py`
- Test: `tests/scoring/test_v2_scoring.py`

- [x] Extract top-5 organic competitors from the canonical SERP response order.
- [x] Compute `avg_top5_da` from available domain authority values across top-5 organic competitors.
- [x] Compute `avg_top5_lighthouse` from available Lighthouse/site scan scores across top-5 organic competitors.
- [x] Exclude aggregators and missing URLs according to existing SERP classification rules.
- [x] Add confidence penalties when fewer than three top-5 competitors have usable DA or Lighthouse data.

### Task Group 5: V2 Score and Fact Persistence

**Files:**
- Modify: `src/clients/supabase_persistence.py`
- Modify: `supabase/migrations/*.sql` only if schema is missing required columns
- Test: `tests/unit/test_supabase_persistence.py`

- [x] Persist keyword-grain observations into `seo_facts` with stable niche, CBSA, keyword, and observation date keys.
- [x] Persist V2 score vectors into `metro_score_v2` with report lineage and benchmark confidence.
- [x] Preserve legacy `metro_scores` writes until all reads are V2-safe.
- [x] Upsert instead of creating duplicate `_v2`, `_simplified`, or side tables when schema already exists.
- [x] Add schema and persistence tests for `top3_review_count_min`, `top3_review_velocity_avg`, `avg_top5_da`, and `avg_top5_lighthouse`.

### Task Group 6: Report and Read-Model API Cleanup

**Files:**
- Modify: `src/domain/services/explore_city_service.py`
- Modify: `src/clients/explore_repository.py`
- Modify: `src/research_agent/api.py`
- Modify: `apps/app/src/app/api/explore/cities/route.ts`
- Modify: `apps/app/src/app/api/reports/**`
- Test: `tests/unit/test_explore_city_service.py`
- Test: `tests/unit/test_api_explore_cities.py`
- Test: `apps/app/src/app/api/explore/cities/route.test.ts`

- [x] Serve report and Explore reads through BFF/API boundaries instead of direct frontend Supabase stitching.
- [x] Prefer `metro_score_v2` for report-list read-model detection and retain legacy fallback.
- [x] Return V2 benchmark/fact lineage through persisted `metro_score_v2` and `seo_facts` rows for backend DTOs to consume.
- [x] Keep account entitlement and report ownership checks in `apps/app` route handlers before proxying.
- [x] Remove frontend-only score joins from report/dashboard page loaders once BFF DTO coverage was verified.

### Task Group 7: Verification Commands

- [x] Run targeted Python scoring, signal, persistence, and service suites.
- [x] Run targeted app Vitest suites for Explore/report/dashboard route and loader changes.
- [x] Run targeted Python ruff and app ESLint checks.
- [x] Run `git diff --check`.
- [x] Run DocGuard; warning-only noisy baseline remains.
- [ ] Full app build remains blocked in this worktree by dependency-resolution/typecheck noise around `vitest/config`.
