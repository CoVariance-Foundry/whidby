# Project Context

## Consumer Onboarding Flow

Consumer onboarding now has a first production implementation in the consumer app. Supabase migration `016_consumer_onboarding.sql` defines `onboarding_profiles` and `onboarding_targets` for durable signup intent, starter strategy recommendation, selected service/geography target, resume state, and first-report handoff. The tables are account-scoped through existing account membership checks and preserve Mapbox/DataForSEO metadata when a city target is selected.

The consumer app now owns deterministic strategy routing in `apps/app/src/lib/onboarding/`, plus `/api/onboarding/profile`, `/api/onboarding/target`, and `/api/onboarding/start-report` route handlers. Onboarding does not create a separate scoring path: city fresh-report starts delegate to the existing `/api/agent/scoring` route so entitlement, quota, request metadata, and report persistence behavior stay centralized. Free users and broad geography targets are routed toward cached Explore/report experiences instead of fresh generation.

The `/onboarding` page is implemented as a production flow with starter intent capture, service selection, city/state target capture, and confirmation. It reuses the consumer `CityAutocomplete` and now passes a stable input id so labels bind correctly. The auth callback now routes new or incomplete users into onboarding, keeps selected-target users in onboarding so they can start the report, preserves explicit safe `next` redirects, and sends terminal onboarding states to `/reports`.

## Strategy Discovery System

Strategy Discovery is implemented as a consumer product surface on branch `codex/strategy-discovery-system`. The system treats strategies as ranking and explanation lenses over existing Whidby market intelligence instead of creating a second scoring engine. Launch strategies are `easy_win`, `gbp_blitz`, `keyword_hijack`, and `expand_conquer`; `cash_cow` is cataloged as phase 2, and AI resilience is a warning/modifier rather than a standalone route.

Migration `016_strategy_discovery_system.sql` adds `strategy_runs`, `strategy_run_items`, `local_pack_listing_facts`, `metro_feature_vectors`, and `strategy_score_cache`. Domain projection logic lives in `src/domain/strategy_projection.py`, cached market access and run lineage live in `src/clients/strategy_repository.py`, and FastAPI now serves `/api/strategies`, strategy-aware `/api/discover`, and `/api/strategy-runs`. The consumer app adds protected `/strategies` gallery/detail screens, shared strategy types/API helpers, and proxy routes under `apps/app/src/app/api/strategies/*` with existing entitlement/quota checks for fresh runs.

Fresh strategy run creation is validated and lineage-backed: free users remain cached-only via the app proxy, fresh runs are capped at 100 targets, backend write failures return non-success responses so quota can be refunded, and queued runs persist `quota_consumed = 1`. Full async report fanout and run-status/report detail endpoints are still follow-up work.

## Consumer User Management and Billing

Consumer user management now has a first implementation slice in code and schema. Supabase migration `014_user_management_billing.sql` defines profiles, accounts, memberships, subscriptions, billing customer mappings, usage counters, report ownership columns, cached/account report visibility, account-scoped report RLS, account bootstrap RPCs, and atomic report quota RPCs. Existing ownerless reports are treated as shared cached reports; fresh generated reports should persist with `owner_account_id`, `created_by_user_id`, and `access_scope = account`.

The consumer app scoring proxy now resolves the Supabase user/account entitlement before calling FastAPI, enforces PostHog-backed fresh-report and quota flags with secure defaults, denies free users fresh reports, consumes/refunds quota around upstream failures, and forwards report ownership context to the Render/FastAPI bridge. Stripe Checkout, Customer Portal, and webhook routes exist for Plus/Pro billing state, backed by `stripe` and `posthog-node` dependencies in `apps/app`.

## Consumer Explore

Consumer `/explore` is now a backend-backed, city-first market discovery surface. Migration `020_explore_market_cells.sql` defines `public.explore_market_cells` as a derived materialized read model over `metros`, CBP establishments, service mappings, V2/legacy score rows, and refresh targets. `src/clients/explore_repository.py` and `ExploreCityService` provide the repository/domain boundary, and FastAPI exposes `GET /api/explore/cities` plus `GET /api/explore/cities/{cbsa_code}` for paginated list/detail reads.

Explore refresh control is implemented for cached report upkeep. Migration `015_explore_refresh_control.sql` adds policy, target, run, run-item, and snapshot tables with a default 30-day cadence; `ExploreRefreshService` and `SupabaseExploreRefreshStore` resolve due/manual targets, queue FastAPI scoring runs, update target freshness, and preserve `explore_report_snapshots` for trends. FastAPI exposes manual run, due-run, and run-status endpoints under `/api/explore/refresh/*`; the consumer app proxies those through bounded Next route handlers, displays refresh controls/status plus freshness fields on `/explore`, reads deltas from `explore_latest_target_scores`/`explore_target_trends`, and schedules due checks from app-scoped `apps/app/vercel.json`.

The app route now loads Explore through bounded Next proxy routes instead of direct Supabase table stitching. Filters and sorts are URL-driven server fetches, table labels match the prototype city browsing model, growth-only filtering is disabled/cleared when `growth_available=false`, and representative density/growth values show metric-service lineage when no service is selected. The city drawer separates cached refresh targets from fresh scan targets: refresh only applies to cached rows with `refresh_target_id`, while cached, catalog, and custom services all start fresh scans through the existing entitlement-protected `/api/agent/scoring` route.

Explore data readiness remains staging/live-data dependent. `scripts/explore/audit_explore_sources.py` now reports `explore_market_cells_count`, `market_cells_with_density`, loaded CBP years, and `growth_available`; one CBP year is a warning, not a launch-blocking failure. `scripts/explore/backfill_cbp_establishments.py --year <year>` can import 2022/2023 CBP files independently and still requires explicit `--apply` plus valid Supabase service-role env before writing.

## Phase 7 Benchmark and Sonar Slice-Lite

Phase 7 now has a staging-first benchmark recompute path. `public.recompute_seo_benchmarks(p_window_days integer)` rebuilds `seo_benchmarks` from `seo_facts`, ACS-backed `metros`, CBP-backed `census_cbp_establishments`, and weighted `niche_naics_mapping`; `scripts/benchmarks/recompute_benchmarks.py` calls that RPC through benchmark-specific Supabase env vars.

Benchmark collection is safer but not complete: `scripts/benchmarks/run_pilot.py` can run pilot or full-sample batches, rejects unknown niches/population classes before paid API calls, and captures top-three local-pack review metrics into `seo_facts`. Existing staging facts still need a paid rerun before review-floor benchmarks become populated.

Sonar slice-lite is implemented in staging through `sonar.cells`, `sonar.cell_runs`, `sonar.scoring_weights`, and the service-role-only `public.persist_sonar_slice_lite(p_record jsonb)` RPC. `scripts/sonar/build_slice_lite.py` builds the LA plumbing cell (`238220__msa__31080__2023`) from current Widby data and persists it with `score_version = sonar-lite-0.1` plus warnings for missing NES, BDS, Trends, geo crosswalk, and residual model inputs.
