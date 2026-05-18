# Active Work

## Consumer Onboarding Flow

Status: implementation complete; unauthenticated browser smoke verified.

Completed:

- Added Supabase onboarding persistence in `016_consumer_onboarding.sql` for `onboarding_profiles` and `onboarding_targets`, with account-scoped RLS, service-role policies, idempotent policy creation, and `updated_at` triggers.
- Added deterministic strategy routing in `apps/app/src/lib/onboarding/`, using snake_case API response contracts.
- Added `/api/onboarding/profile`, `/api/onboarding/target`, and `/api/onboarding/start-report` route handlers. Fresh city report starts delegate to the existing entitlement-protected `/api/agent/scoring` route; broad/free routes return cached Explore/report handoffs.
- Added the production `/onboarding` flow with starter intent capture, service selection, city/state target selection, summary/confirmation, and accessible `CityAutocomplete` labeling.
- Updated auth callback resume routing so new/incomplete users land on `/onboarding`, users with selected targets resume onboarding, explicit safe `next` values still win, and terminal onboarding states route to `/reports`.
- Updated canonical onboarding architecture, data model, and test obligations.

Verified:

- `npm --workspace apps/app test -- src/lib/onboarding/strategy-routing.test.ts src/app/api/onboarding/profile/route.test.ts src/app/api/onboarding/target/route.test.ts src/app/api/onboarding/start-report/route.test.ts src/app/onboarding/OnboardingClient.test.tsx src/components/niche-finder/CityAutocomplete.test.tsx src/app/auth/callback/route.test.ts src/app/api/agent/scoring/route.test.ts` passed 58 tests.
- `pytest tests/unit/test_supabase_schema.py -v`
- `npm --workspace apps/app run lint` exits 0 with two pre-existing warnings outside this onboarding slice.
- `git diff --check`
- Local preview `http://localhost:3012/onboarding` redirects unauthenticated users to `/login` without a runtime crash.

Known constraint:

- `npx docguard-cli guard` is blocked in the sandbox by `ENOTFOUND registry.npmjs.org`; escalation to fetch/execute npm code was rejected by the safety reviewer.

## Strategy Discovery System

Status: implementation complete on `codex/strategy-discovery-system`; ready for integration review and live-environment validation.

Completed:

- Canonical architecture, data model, and test-spec updates define strategies as lenses over existing market intelligence, not separate scoring engines.
- Supabase migration `016_strategy_discovery_system.sql` adds strategy run lineage, local-pack listing facts, metro feature vectors, and optional strategy score cache tables.
- Python domain logic projects launch strategies `easy_win`, `gbp_blitz`, `keyword_hijack`, and `expand_conquer`; `cash_cow` remains phase-2/catalog-only.
- `StrategyRepository` reads cached market rows, local-pack facts, feature vectors, and persists strategy run lineage.
- FastAPI exposes `/api/strategies`, strategy-aware `/api/discover`, and `/api/strategy-runs` with validation, fresh-run caps, and storage-failure handling.
- The consumer app exposes protected `/strategies` gallery/detail screens plus Next.js proxy routes for catalog, discovery, and run creation with existing entitlement/quota behavior.

Known follow-ups:

- Expand & Conquer requests now pass `reference_city_id`; high-quality scoring still depends on populated feature-vector/reference competition inputs.
- Fresh strategy runs currently persist queued run lineage; full async report fanout/status detail endpoints remain the next implementation slice.
- Live Supabase/PostgREST validation is still required before production rollout.

## Consumer User Management, Billing, and Report Quotas

Status: implementation in progress.

Target behavior:

- `free` users can browse cached reports but cannot generate fresh reports.
- `plus` users pay $49/month and can generate 10 fresh reports per billing month.
- `pro` users pay $100/month and can generate 50 fresh reports per billing month.
- Fresh generated reports are owned by the user's account; existing ownerless reports remain shared cached reports.
- PostHog flags control rollout and kill switches only; Supabase RLS remains the hard data-isolation boundary.

Implementation path:

- Add account, membership, subscription, usage, billing customer, and report ownership schema in Supabase.
- Replace broad authenticated report read policies with cached-or-account-member policies.
- Add consumer app entitlement checks before `/api/agent/scoring` calls the Render/FastAPI bridge.
- Add Stripe Checkout, Customer Portal, and webhook endpoints.
- Thread `owner_account_id` and `created_by_user_id` through FastAPI and Supabase report persistence.

## Explore Cities Refactor

Status: implementation complete locally; staging/live rollout still requires migration, materialized-view refresh, and data readiness audit.

Current plan: `docs/superpowers/plans/2026-05-17-explore-cities-refactor.md`.
Linear: `WHI-1` Refactor Explore Cities into city-first market discovery surface.

Product direction: keep `/explore` city-first like the UX prototype, add service-selected comparison for city-service metrics, and keep Strategies as guided ranking lenses over the same market-cell read model. Density and growth remain service-aware metrics; do not present them as unlabelled city-only facts.

Completed:

- Updated canonical docs for the Explore vs. Strategies responsibility split, the `ExploreMarketCell` derived read model, service-aware metric lineage, backend filtering/pagination, and growth-unavailable behavior.
- Added `supabase/migrations/018_explore_market_cells.sql` as a derived materialized read model over `public.metros`, `public.census_cbp_establishments`, `public.niche_naics_mapping`, `public.metro_score_v2`, `public.metro_scores`, reports, and refresh targets.
- Added `src/clients/explore_repository.py` and wired `ExploreCityService` to backend list/detail reads with cursor pagination, service filters, sort mapping, representative-service defaults, V2-over-legacy score preference, freshness fields, density, growth, and `growth_available`.
- Added FastAPI `GET /api/explore/cities` and `GET /api/explore/cities/{cbsa_code}` plus bounded Next proxy routes under `apps/app/src/app/api/explore/cities`.
- Replaced the app Explore loader's direct Supabase stitching/top-100 React filtering with backend-backed query loading from URL search params.
- Refactored the Explore UI to city-first prototype copy/labels, URL-driven filters/sorts, growth-disabled/cleared state, representative metric lineage, and stale-refresh guards during URL transitions.
- Updated the city drawer and fresh-scan flow so cached rows, catalog defaults, and custom services can start fresh scans through `/api/agent/scoring`; refresh remains limited to cached targets with `refresh_target_id`.
- Extended `scripts/explore/audit_explore_sources.py` to report `explore_market_cells_count`, `market_cells_with_density`, loaded CBP years, and `growth_available`.
- Extended `scripts/explore/backfill_cbp_establishments.py --year <year>` so 2022/2023 CBP import files can be prepared/applied independently.

Verified locally:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/unit/test_explore_metrics.py tests/unit/test_explore_city_service.py tests/unit/test_explore_repository.py tests/unit/test_api_explore_cities.py tests/unit/test_explore_market_cells_schema.py -q` passed 43 tests with one pre-existing pytest config warning.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/scripts/test_audit_explore_sources.py tests/scripts/test_backfill_cbp_establishments.py -q` passed 20 tests with one pre-existing pytest config warning.
- `npm --workspace apps/app test -- load-explore-data api/explore/cities explore` passed 54 tests.
- `npx tsc --noEmit` from `apps/app` passed.
- `npm --workspace apps/app run lint` exited 0 with two pre-existing unrelated warnings in `apps/app/e2e/autocomplete-scoring-flow.spec.ts` and `apps/app/src/app/(protected)/niche-finder/page.test.tsx`.
- `git diff --check` passed.
- Local app server started on `http://localhost:3004`; `/explore` redirected to `/login`, so protected-page visual smoke was auth-blocked rather than compile/runtime blocked.

Not verified:

- `npx docguard-cli guard` could not complete in this sandbox because `npx` could not resolve `registry.npmjs.org` (`ENOTFOUND`).
- Live Supabase migration application, `REFRESH MATERIALIZED VIEW public.explore_market_cells`, and `python scripts/explore/audit_explore_sources.py --service-role` against staging/prod.
- Historical CBP backfill for a second year. Until at least two CBP years exist, Explore should keep `growth_available=false` and the UI should disable/clear growth-only filters.

Known constraints:

- Do not create duplicate `cities`, `business_patterns`, `_simplified`, or `_v2` tables; use `public.metros`, `public.census_cbp_establishments`, `public.niche_naics_mapping`, score tables, and optional read-only views only.
- If historical CBP years are absent, return `growth_available=false` and hide/disable growth filters rather than filtering all rows out.
- `Run report` must be available for a city even when it has no cached services; `Refresh cached score` only applies to existing cached city + service targets.

## Phase 7 Benchmark Completion

Status: closeout validation.

Completed: staging benchmark recompute path, benchmark runner controls, Sonar slice-lite persistence, and LA plumbing slice-lite staging record.

Latest update: paid benchmark sampling is pruned to DFS-native, keyword-volume-capable metros by default. Filtered full-sample launch scope is 60 metros (9 mega, 37 metro, 12 large, 2 medium); small/micro metros stay census-only unless `--include-low-signal` is used for diagnostics. A 2026-05-12 live preflight for plumber + concrete contractor succeeded 10/10 with zero Supabase writes; New York now keeps separate validated `keyword_volume_location_codes` to avoid a known invalid volume code.

Current blockers before production:

- Paid DataForSEO full-sample collection has not been run with the new review-floor fields.
- Staging benchmark confidence remains below usable coverage: 43 insufficient cells, 12 low cells, 0 medium/high cells after the latest recompute.
- Production promotion requires explicit approval and a staging health review.

Next implementation slice after Explore backend: V2 scoring should read `seo_benchmarks` through a repository boundary instead of ad hoc Supabase queries, unless Explore implementation needs that repository first.
