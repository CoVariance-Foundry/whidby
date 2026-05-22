# Active Work

## Proto -> Production Convergence: Epic 6 Reports Page

Status: in progress on `codex/whi-7-reports-proto-layout`.

Linear: `WHI-7` with first child `WHI-32` in progress. Remaining child issues are `WHI-33` strategy guidance refinement, `WHI-34` Next Moves refinement, and `WHI-35` report detail header/export/delete polish.

Completed in the first slice:

- Opened Epic 6 and `WHI-32` in Linear.
- Updated `/reports` header copy to match the prototype history framing.
- Reworked the reports list into prototype-style summary stats, search, sort, empty state, and card-list rows.
- Kept existing `/reports?open=<report_id>` modal behavior for dashboard/explore deep links.
- Added `/reports/[reportId]` as the page-based report detail entry point used by list rows, including headline score band, score tabs, strategy guidance when present, safe Next Moves, and keyword expansion.

Verified:

- `npm ci` completed for this worktree.
- `npm --workspace apps/app test -- ReportsTable` passed.
- `cd apps/app && npx --no-install tsc --noEmit` passed.
- `cd apps/app && npx --no-install eslint 'src/app/(protected)/reports/ReportsPageClient.tsx' 'src/components/reports/ReportsTable.tsx' 'src/app/(protected)/reports/[reportId]/page.tsx'` passed.
- `npm --workspace apps/app run lint` passed with two pre-existing warnings in `apps/app/e2e/autocomplete-scoring-flow.spec.ts` and `apps/app/src/app/(protected)/niche-finder/page.test.tsx`.
- `git diff --check` passed.
- `npx docguard-cli guard` ran after network escalation; it exited warn-only with existing repository warnings around traceability, freshness, TODO tracking, and unrelated config/doc drift.
- Local app server is running at `http://localhost:3002`; Playwright navigation to `/reports` redirected to `/login` as expected for the protected route. The browser console only showed the existing missing `/favicon.ico`; server logs also reported missing Supabase env vars, so authenticated report-page visual QA is still blocked in this worktree.

Next:

- Use an authenticated local session or preview to visually verify `/reports` and `/reports/[reportId]` with real report data.
- Continue `WHI-33`/`WHI-34`/`WHI-35` polish on the new detail page rather than the legacy modal.
## Proto -> Production Convergence: Epic 7 Account & Settings

Status: implemented on `codex/whi-8-account-settings-epic`; ready for PR/review closeout.

Linear: `WHI-8` with children `WHI-36`, `WHI-37`, and `WHI-38`.

Goal: align `/settings` with the account proto while preserving existing Stripe Checkout/Portal billing actions, Supabase password reset/update flow, navbar profile dropdown behavior, admin dashboard link, and sign-out.

Completed in this slice:

- Reconciled the already-merged Account & Billing implementation with the newer Navbar app frame.
- Added profile metadata, saved reports preview, password-management entry, and session/sign-out sections to `/settings` without changing billing semantics.
- Server-loads the saved reports preview through the existing `/api/agent/reports?limit=5` route with cookie forwarding, then opens rows through `/reports?open=<report_id>`.
- Added explicit navbar admin visibility from `entitlement.member_role === "admin"`; fallback/non-admin users no longer see the external Admin dashboard link.
- Preserved Stripe Checkout/Portal actions, billing return banners, Supabase password reset/update, and Supabase sign-out behavior.

Verified:

- `npm --workspace apps/app test -- AccountSettingsClient settings/page Navbar` passed 21 tests.
- `npx --no-install tsc --noEmit` passed from `apps/app`.
- `npm --workspace apps/app run lint` passed with two pre-existing warnings in `apps/app/e2e/autocomplete-scoring-flow.spec.ts` and `apps/app/src/app/(protected)/niche-finder/page.test.tsx`.

## Proto -> Production Convergence: Epic 5 Multi-market

Status: started on `codex/whi-6-multi-market-page`.

Linear: `WHI-6` with child issues `WHI-27` through `WHI-31`. `WHI-6`, `WHI-27`, `WHI-28`, `WHI-29`, and `WHI-31` are in progress; `WHI-30` remains the deeper backend follow-up.

Completed in this slice:

- Replaced the protected `/agency` placeholder with a configure → confirm → complete Multi-market batch flow.
- Added launch-safe strategy lens selection, population/state criteria, service selection, target caps, target preview, and completion state.
- Ported a shared `StateMultiselect` component and wired Explore filters to use it.
- Connected target review to `apps/app /api/strategies/discover` and queued batches to `apps/app /api/strategies/runs` fresh mode with explicit targets.
- Documented the current quota assumption: one fresh-report scan per queued batch through the existing strategy-run quota boundary.

Next:

- Implement WHI-30 backend depth beyond queue creation: target-level processing progress, run item/report linkage, and surfaced run status once FastAPI has durable fanout semantics.
- Decide whether batch cost should remain one fresh-report scan per batch or become target-scaled before changing schema/RPCs.

## Bulk Scoring Data Buildout

Status: implemented on `codex/bulk-scoring-followups`; draft PR open.

Goal: turn `scripts/explore/bulk_score.py` into a trustworthy Explore data-build runner rather than a loose cached-report seeder.

Completed in this slice:

- Default metro selection now follows rank-and-rent population-class ordering, requires DataForSEO-ready metros by default, and caps `mega_5m_plus` markets.
- Bulk scoring audit output now records every attempted pair with status, request metadata, score summary, persistence counts, warnings, timing, and rerun-friendly error details.
- Successful pairs now require verified Supabase persistence across `reports`, legacy `metro_scores`, and V2 `metro_score_v2` / `seo_facts` rows.
- Resume state prefers `explore_market_cells` and falls back to legacy report/score tables with normalized service keys.
- V2 `seo_facts` row building now requires a valid `generated_at` snapshot date and validates rows before report persistence writes begin.

Next:

- Review diff and decide whether to extend the runner with a live dry-run/preflight mode before paid scoring.

## Proto -> Production Convergence: Epic 1 App Frame

Status: implemented locally on `codex/whi-2-app-frame-navbar`; PR publication pending.

Linear: `WHI-2` with `WHI-11`, `WHI-12`, and sub-issues `WHI-44` through `WHI-51`.

Completed:

- Replaced the protected consumer app sidebar/topbar shell with a single sticky `Navbar` from `(protected)/layout.tsx`.
- Added authenticated primary navigation for Home, Strategies, Explore, Multi-market, and Reports.
- Moved plan usage, account settings, password, admin dashboard, and sign-out into the navbar profile area.
- Added a minimal app footer to the protected layout.
- Removed page-local app chrome wrappers from protected pages; route actions now live in page headers or client surfaces.
- Preserved the existing `/niche-finder` and `/recommendations` routes for deep links while removing them from primary authenticated navigation.

Verification:

- `npm --workspace apps/app test -- Navbar layout settings/page explore/page` passed 8 tests.
- `npx --no-install tsc --noEmit` passed from `apps/app`.
- `npm --workspace apps/app run lint` exited 0 with two pre-existing warnings in `apps/app/e2e/autocomplete-scoring-flow.spec.ts` and `apps/app/src/app/(protected)/niche-finder/page.test.tsx`.

Notes:

- Linear `WHI-2` has the implementation assumptions for quota wording, hidden nav routes, onboarding suppression, and epic-level testing scope.
- Project-level Linear status updates are disabled in the workspace, so progress notes live on the epic and sub-issue statuses.

## V2 Scoring System

Status: implemented and under final verification on `codex/v2-scoring-system`.

Current plan: `docs/superpowers/plans/2026-05-20-v2-scoring-system.md`.

Completed:

- Wired `MarketService` and FastAPI construction to inject `SeoBenchmarkRepository` and Supabase-backed CBP city density into the orchestrator.
- Corrected V2 top-3 local review semantics with nullable missing facts, coverage, and confidence so missing data no longer becomes zero competition.
- Expanded M5 backlinks and Lighthouse dependent collection to top-5 non-aggregator organic competitors with dedupe/cost controls.
- Persisted `metro_score_v2` rows and V2-only `seo_facts` rows with idempotent upsert and nullable top-5 organic fact fields.
- Moved Explore/report/dashboard reads behind Next BFF routes; report detail fallback now happens server-side after access checks.

Verification notes:

- Python targeted suites, app route/loader Vitest suites, targeted ruff, targeted ESLint, and `git diff --check` pass locally.
- `npx docguard-cli guard` runs with warning-only status from existing traceability/freshness/TODO/doc-drift issues.
- `next build` compiles past app code after network access, but full build remains blocked in this worktree by dependency-resolution/typecheck noise around `vitest/config`.

## Supabase Staging Auth and Entitlements

Status: staging schema and seeded personas verified; GitHub Environment secret upload still requires explicit user approval.

Completed:

- Added `018_internal_user_entitlements.sql` for service-role-managed quota exemptions, `ensure_account_for_user_admin(...)`, and `get_account_entitlement()` with `fresh_report_quota_exempt`.
- App fresh-report gates now allow internal quota-exempt admins to run fresh scoring/strategy/onboarding city reports without consuming monthly report quota.
- Added migration parity and seed scripts under `scripts/supabase/`.
- Added GitHub Actions workflows for staging migration deploys and manual test-account seeding from the `staging` Environment.
- Applied staging migrations `014_user_management_billing` through `018_internal_user_entitlements` to Supabase project `whidby-staging` (`wuybidpvqhhgkukpyyhq`).
- Seeded staging Auth/account entitlements for `admin-test@widby.dev`, `user-test@widby.dev`, `henock@covariance.studio`, `antwoine@covariance.studio`, and `lm13vand@gmail.com`.
- Stored seed passwords locally in the repo-root `.env`; do not commit or print them.

Verified:

- Staging migration ledger includes `014_user_management_billing`, `015_explore_refresh_control`, `016_consumer_onboarding`, `017_strategy_discovery_system`, and `018_internal_user_entitlements`.
- Staging SQL verification shows `admin-test`, Henock, and Antwoine are `admin`/`free`/quota-exempt; Luke is `owner`/`pro`/non-exempt; normal test user is `owner`/`free`/non-exempt.
- Password-auth smoke passes for all five seeded users when using the valid staging service-role API key.

Current blockers:

- GitHub `staging` Environment secrets were not uploaded from Codex because the escalation reviewer rejected transmitting service-role and password secrets to GitHub without explicit user approval.
- Local `.env` value `STAGING_NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` appears invalid for `whidby-staging`; browser/client login will fail until the staging publishable key is refreshed in local env and Vercel Preview env.

## CI/CD AI Review and Visual QA

- Account & Billing screen implementation exists on `main`; Epic 7 is now reconciling it with the proto and the Navbar app frame.
- Spec: `specs/015-account-billing-screen/spec.md`
- Account/settings is implemented; future app-frame work should use the navbar profile dropdown instead of the removed bottom-sidebar user menu.

## Prior/Archived Context

## AI Review and Visual QA CI/CD

Status: closeout review.

Plan: `docs/superpowers/plans/2026-05-17-ai-review-visual-qa-cicd.md`

Next: dispatch Visual QA from `dev` or `main` with `preview_url` and `pr_number` when a trusted preview is ready.

## Account and Billing Settings

Status: implementation merged into local `dev`; awaiting final integrated verification.

Completed:

- Added protected `/settings` and `/settings/password` consumer settings screens.
- Routed billing checkout, portal return URLs, plan actions, invoices, payment methods, cancellation entry points, and scheduled-cancellation display through the settings surface.
- Added account summary loading, fresh-report usage display, account entry points, and password reset completion controls.
- Preserved canonical `free` / `plus` / `pro` plan behavior and existing Stripe Checkout/Portal boundaries.

## Explore Cities Refactor

Status: implementation complete locally; staging/live rollout still requires migration, materialized-view refresh, and data readiness audit.

Current plan: `docs/superpowers/plans/2026-05-17-explore-cities-refactor.md`.
Linear: `WHI-1` Refactor Explore Cities into city-first market discovery surface.

Product direction: keep `/explore` city-first like the UX prototype, add service-selected comparison for city-service metrics, and keep Strategies as guided ranking lenses over the same market-cell read model. Density and growth remain service-aware metrics; do not present them as unlabelled city-only facts.

Completed:

- Updated canonical docs for the Explore vs. Strategies responsibility split, the `ExploreMarketCell` derived read model, service-aware metric lineage, backend filtering/pagination, and growth-unavailable behavior.
- Added `supabase/migrations/020_explore_market_cells.sql` as a derived materialized read model over `public.metros`, `public.census_cbp_establishments`, `public.niche_naics_mapping`, `public.metro_score_v2`, `public.metro_scores`, reports, and refresh targets.
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

Next implementation slice: V2 scoring should read `seo_benchmarks` through a repository boundary instead of ad hoc Supabase queries.
