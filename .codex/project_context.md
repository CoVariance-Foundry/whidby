# Project Context

## Strategy Discovery System

Strategy Discovery is implemented as a consumer product surface on branch `codex/strategy-discovery-system`. The system treats strategies as ranking and explanation lenses over existing Whidby market intelligence instead of creating a second scoring engine. Launch strategies are `easy_win`, `gbp_blitz`, `keyword_hijack`, and `expand_conquer`; `cash_cow` is cataloged as phase 2, and AI resilience is a warning/modifier rather than a standalone route.

Migration `016_strategy_discovery_system.sql` adds `strategy_runs`, `strategy_run_items`, `local_pack_listing_facts`, `metro_feature_vectors`, and `strategy_score_cache`. Domain projection logic lives in `src/domain/strategy_projection.py`, cached market access and run lineage live in `src/clients/strategy_repository.py`, and FastAPI now serves `/api/strategies`, strategy-aware `/api/discover`, and `/api/strategy-runs`. The consumer app adds protected `/strategies` gallery/detail screens, shared strategy types/API helpers, and proxy routes under `apps/app/src/app/api/strategies/*` with existing entitlement/quota checks for fresh runs.

Fresh strategy run creation is validated and lineage-backed: free users remain cached-only via the app proxy, fresh runs are capped at 100 targets, backend write failures return non-success responses so quota can be refunded, and queued runs persist `quota_consumed = 1`. Full async report fanout and run-status/report detail endpoints are still follow-up work.

## Consumer User Management and Billing

Consumer user management now has a first implementation slice in code and schema. Supabase migration `014_user_management_billing.sql` defines profiles, accounts, memberships, subscriptions, billing customer mappings, usage counters, report ownership columns, cached/account report visibility, account-scoped report RLS, account bootstrap RPCs, and atomic report quota RPCs. Existing ownerless reports are treated as shared cached reports; fresh generated reports should persist with `owner_account_id`, `created_by_user_id`, and `access_scope = account`.

The consumer app scoring proxy now resolves the Supabase user/account entitlement before calling FastAPI, enforces PostHog-backed fresh-report and quota flags with secure defaults, denies free users fresh reports, consumes/refunds quota around upstream failures, and forwards report ownership context to the Render/FastAPI bridge. Stripe Checkout, Customer Portal, and webhook routes exist for Plus/Pro billing state, backed by `stripe` and `posthog-node` dependencies in `apps/app`.

## Consumer Explore

Consumer `/explore` is implemented as an authenticated Supabase-backed discovery surface in `apps/app`. It loads cached metro/service opportunities from `metros`, `reports`, and score tables, renders filterable city rows and city-level cached service scores, and sends fresh scans through the existing `/api/agent/scoring` proxy to the FastAPI scoring bridge.

Explore refresh control is implemented for cached report upkeep. Migration `015_explore_refresh_control.sql` adds policy, target, run, run-item, and snapshot tables with a default 30-day cadence; `ExploreRefreshService` and `SupabaseExploreRefreshStore` resolve due/manual targets, queue FastAPI scoring runs, update target freshness, and preserve `explore_report_snapshots` for trends. FastAPI exposes manual run, due-run, and run-status endpoints under `/api/explore/refresh/*`; the consumer app proxies those through bounded Next route handlers, displays refresh controls/status plus freshness fields on `/explore`, reads deltas from `explore_latest_target_scores`/`explore_target_trends`, and schedules due checks from app-scoped `apps/app/vercel.json`.

## Phase 7 Benchmark and Sonar Slice-Lite

Phase 7 now has a staging-first benchmark recompute path. `public.recompute_seo_benchmarks(p_window_days integer)` rebuilds `seo_benchmarks` from `seo_facts`, ACS-backed `metros`, CBP-backed `census_cbp_establishments`, and weighted `niche_naics_mapping`; `scripts/benchmarks/recompute_benchmarks.py` calls that RPC through benchmark-specific Supabase env vars.

Benchmark collection is safer but not complete: `scripts/benchmarks/run_pilot.py` can run pilot or full-sample batches, rejects unknown niches/population classes before paid API calls, and captures top-three local-pack review metrics into `seo_facts`. Existing staging facts still need a paid rerun before review-floor benchmarks become populated.

Sonar slice-lite is implemented in staging through `sonar.cells`, `sonar.cell_runs`, `sonar.scoring_weights`, and the service-role-only `public.persist_sonar_slice_lite(p_record jsonb)` RPC. `scripts/sonar/build_slice_lite.py` builds the LA plumbing cell (`238220__msa__31080__2023`) from current Widby data and persists it with `score_version = sonar-lite-0.1` plus warnings for missing NES, BDS, Trends, geo crosswalk, and residual model inputs.
