# Project Context

## Consumer User Management and Billing

Consumer user management now has a first implementation slice in code and schema. Supabase migration `014_user_management_billing.sql` defines profiles, accounts, memberships, subscriptions, billing customer mappings, usage counters, report ownership columns, cached/account report visibility, account-scoped report RLS, account bootstrap RPCs, and atomic report quota RPCs. Existing ownerless reports are treated as shared cached reports; fresh generated reports should persist with `owner_account_id`, `created_by_user_id`, and `access_scope = account`.

The consumer app scoring proxy now resolves the Supabase user/account entitlement before calling FastAPI, enforces PostHog-backed fresh-report and quota flags with secure defaults, denies free users fresh reports, consumes/refunds quota around upstream failures, and forwards report ownership context to the Render/FastAPI bridge. Stripe Checkout, Customer Portal, and webhook routes exist for Plus/Pro billing state, backed by `stripe` and `posthog-node` dependencies in `apps/app`.

## Consumer Explore

Consumer `/explore` is implemented as an authenticated Supabase-backed discovery surface in `apps/app`. It loads cached metro/service opportunities from `metros`, `reports`, and score tables, renders filterable city rows and city-level cached service scores, and sends fresh scans through the existing `/api/agent/scoring` proxy to the FastAPI scoring bridge.

Explore refresh control is implemented for cached report upkeep. Migration `015_explore_refresh_control.sql` adds policy, target, run, run-item, and snapshot tables with a default 30-day cadence; `ExploreRefreshService` and `SupabaseExploreRefreshStore` resolve due/manual targets, queue FastAPI scoring runs, update target freshness, and preserve `explore_report_snapshots` for trends. FastAPI exposes manual run, due-run, and run-status endpoints under `/api/explore/refresh/*`; the consumer app proxies those through bounded Next route handlers, displays refresh controls/status plus freshness fields on `/explore`, reads deltas from `explore_latest_target_scores`/`explore_target_trends`, and schedules due checks from app-scoped `apps/app/vercel.json`.

Explore data-model population now has a local, non-mutating implementation slice. Read-only audit and readiness helpers identify sparse `metros`, CBP, SEO fact, and benchmark prerequisites; ACS and CBP backfill scripts prepare payloads but require explicit `--apply` plus valid Supabase service-role env before writing. Pure Explore metric formulas and `ExploreCityService` build backend DTOs from repository inputs with canonical service normalization, latest unique cached service rows, V2-over-legacy score preference, coherent latest-score freshness, CBP density, and annualized growth. The current consumer loader surfaces optional density/growth fields when a backend/read-model row exposes them and falls back safely when those columns are absent. No live Supabase backfill or benchmark recompute was run in this slice.

## Phase 7 Benchmark and Sonar Slice-Lite

Phase 7 now has a staging-first benchmark recompute path. `public.recompute_seo_benchmarks(p_window_days integer)` rebuilds `seo_benchmarks` from `seo_facts`, ACS-backed `metros`, CBP-backed `census_cbp_establishments`, and weighted `niche_naics_mapping`; `scripts/benchmarks/recompute_benchmarks.py` calls that RPC through benchmark-specific Supabase env vars.

Benchmark collection is safer but not complete: `scripts/benchmarks/run_pilot.py` can run pilot or full-sample batches, rejects unknown niches/population classes before paid API calls, and captures top-three local-pack review metrics into `seo_facts`. Existing staging facts still need a paid rerun before review-floor benchmarks become populated.

Sonar slice-lite is implemented in staging through `sonar.cells`, `sonar.cell_runs`, `sonar.scoring_weights`, and the service-role-only `public.persist_sonar_slice_lite(p_record jsonb)` RPC. `scripts/sonar/build_slice_lite.py` builds the LA plumbing cell (`238220__msa__31080__2023`) from current Widby data and persists it with `score_version = sonar-lite-0.1` plus warnings for missing NES, BDS, Trends, geo crosswalk, and residual model inputs.
