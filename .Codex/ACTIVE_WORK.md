# Active Work

## Scoring Coverage & Benchmark Hardening

Status: `WHI-99`, `WHI-100`, `WHI-101`, and `WHI-102` are done in Linear. PR #82 is open and green for `WHI-103`; the current branch is `WHI-104`, extending the coverage analysis with benchmark-cell sufficiency details.

Linear: project `Scoring Coverage & Benchmark Hardening` is In Progress. Current issue is `WHI-104`.

Goal: define the guarded production scoring coverage experiment before any paid sample run, so V2 scoring and benchmark seed decisions are based on measured signal availability by metro size and service.

Current contract:

- Production project guard is `eoajvifhbmqmoluiokcj`.
- Pilot scope is 12 metros x 8 services: 1 micro, 3 small, 3 medium, 3 large, 1 metro, and 1 mega, using DFS-ready metros only.
- Core services are roofing, plumbing, hvac, tree service, auto repair, water damage restoration, electrician, and locksmith.
- Apply commands require `--require-dfs`, `--require-v2-persistence`, and `--expected-project-ref eoajvifhbmqmoluiokcj`.
- No broader paid expansion or benchmark recompute should run until the read-only audit gates pass.
- `scripts/explore/bulk_score.py` now emits WHI-100 stable JSONL fields plus aggregate preview/apply JSON under ignored `reports/scoring_audit/` by default.
- `scripts/explore/audit_metro_dfs_readiness.py` review CSVs now include WHI-101 residual review classification, production seed policy, approval-artifact requirement, and population context.
- `bulk_score.py --require-dfs` excludes rows whose DFS match confidence is marked `ambiguous`, `invalid_existing_code`, or `no_match`.
- WHI-102 previews passed for all six buckets using `uv run python -m scripts.explore.bulk_score --preview` and wrote ignored summary files under `reports/scoring_audit/preview_*.json`.
- WHI-102 original one-pair production canary ran Waco, TX x roofing against `https://whidby-1.onrender.com` with `--require-dfs`, `--require-v2-persistence`, and project guard `eoajvifhbmqmoluiokcj`. It returned API HTTP 200 and created report `69d8dccf-b1c9-453d-9ff7-7dffaf0c9850`, but stopped as `partial_failure` because `metro_scores`, `metro_score_v2`, and `seo_facts` were missing. Follow-up inspection showed target identity drift: the API persisted legacy child rows under synthetic `cbsa_code=fallback:waco`, so V2 upserts could not satisfy production metro lineage.
- PR #78 fixed explicit production metro identity propagation through `bulk_score.py` -> `/api/niches/score` -> `score_niche_for_metro`. After merge, `npm run runtime:check` passed and the post-merge canary reran Waco, TX x roofing against `https://whidby-1.onrender.com`; it returned API HTTP 200, created report `d440f723-4f6f-43a3-a4c4-65fc786cee9e`, and passed required persistence checks for `reports`, `metro_scores`, `metro_score_v2`, `seo_facts`, and report-backed `explore_market_cells` under CBSA `47380`.
- The bounded 12x8 WHI-102 pilot passed: 96 successes, 0 partials, 0 failures. Bucket outputs are ignored artifacts under `reports/scoring_audit/coverage_*.jsonl`: micro Winona, MN (8); small Rome, GA / Dubuque, IA / Adrian, MI (24); medium Waco, TX / Sioux Falls, SD / Longview, TX (24); large Omaha, NE / Greenville, SC / Knoxville, TN (24); metro Phoenix, AZ (8); mega New York, NY (8). Each apply run used `--require-dfs`, `--require-v2-persistence`, project guard `eoajvifhbmqmoluiokcj`, and refreshed `explore_market_cells`.
- `audit_scoring_strategy` wrote `reports/scoring_audit/scoring_audit_20260523T154926Z.json` and exited fail despite the 96/96 pilot success. Critical gaps remain: demand benchmark undersampled; organic top-5 DA/Lighthouse values and measurements missing; local difficulty inputs missing; local and monetization benchmarks undersampled; and app-surface benchmark confidence undersampled. Inventory snapshot: 7,480 intended market pairs, 114 `metro_score_v2` rows, 8,315 `seo_facts` rows, 55 `seo_benchmark` cells, and 131,835 `explore_market_cells` rows.
- `audit_signal_coverage --coverage-threshold 0.6 --min-benchmark-cells 48 --min-benchmark-sample-size 8` exited fail. Overall DA/Lighthouse value and measurement coverage are 0.0; usable benchmark cells at sample size 8 are 0/48; 32 fact-backed niche/population cells lack benchmark cells; 55 benchmark cells are undersampled; and 89 fact pairs are missing Explore cache rows.
- Current acquisition slice adds explicit, paid opt-in flags to `scripts/benchmarks/run_pilot.py`: `--collect-organic-telemetry` enriches top non-aggregator organic targets with DataForSEO Backlinks Summary and Lighthouse into nullable top-5 telemetry fields, while `--collect-review-velocity` enriches top local-pack listings through Google Reviews using `cid`/`place_id` when available. Preflight still skips both add-ons, and no broader paid acquisition has run in this slice.
- PR #81 reviewer follow-up fixed acquisition edge cases: review velocity now propagates to every keyword fact row, malformed local-pack rows without title/CID/place ID are skipped, Backlinks Summary requests the `one_hundred` rank scale before persisting DA telemetry, and DA parsing prefers explicit domain-rank keys before any generic nested `rank`.
- WHI-103 records the durable analysis in `docs/scoring-coverage-analysis.md`, using the ignored `reports/scoring_audit/coverage_*.jsonl` and `scoring_audit_20260523T154926Z.*` artifacts. The conclusion is that the 96/96 pilot validates the guarded scoring and persistence path, but benchmark usability remains 0/48 at `sample_size_metros >= 8`, DA/Lighthouse telemetry is absent, local difficulty inputs are missing, and only 10/96 pilot rows are visible through V2-backed Explore rows.
- WHI-104 read live production `seo_benchmarks` after checking the Supabase schema in `supabase/migrations/010_v2_benchmarks.sql` and `012_recompute_seo_benchmarks.sql` because `.Codex/databricks-context/` is not present. The benchmark appendix in `docs/scoring-coverage-analysis.md` records 55 benchmark rows, 28/48 core-service cells present, 0/48 core-service cells usable at `sample_size_metros >= 8`, 20/48 core cells missing, all present core cells capped at sample size 4, and null local review-count/velocity medians across all present core cells.
- The benchmark-development research plan is logged in Linear at `https://linear.app/covariancestudio/document/benchmark-development-research-plan-32e613154242` and linked from `WHI-104`. Phase 1 mapped the current plan in `docs/scoring-coverage-analysis.md`. Phase 2 added comparable benchmark research across Ahrefs, Semrush, Moz, SISTRIX, Google local ranking guidance, and Whitespark local factors. Phase 3 cataloged active SEO data APIs, centered on DataForSEO endpoint coverage, current Whidby wrappers, identifier stability, local cost estimates, and the metric-level sample counts each endpoint should support. Stage 4 converted those findings into a platform gap analysis that also accounts for Strategy Discovery needs: Easy Win, GBP Blitz, Keyword Hijack, Expand & Conquer, `/agency`, strategy cache rows, and fresh strategy runs all depend on metric-level sufficiency, benchmark lineage, local-place identifiers, raw evidence retention, agent tool parity, structured warning semantics, feature-vector readiness, and guarded paid acquisition. Stage 5 recommends the implementation sequence: schema/data-model lineage first, metric-level audits second, runner and agent-tool parity third, then a small paid metric canary before any broader cell backfill or benchmark recompute.

Verified:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/scripts/test_bulk_score.py -q` passed 32 tests with the existing `asyncio_mode` warning.
- `ruff check scripts/explore/bulk_score.py tests/scripts/test_bulk_score.py` passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p asyncio tests/scripts/test_metro_dfs_readiness.py tests/scripts/test_enrich_metro_dfs_codes.py tests/scripts/test_bulk_score.py -q` passed 58 tests.
- `ruff check scripts/explore/metro_dfs_readiness.py scripts/explore/audit_metro_dfs_readiness.py scripts/explore/enrich_metro_dfs_codes.py scripts/explore/bulk_score.py tests/scripts/test_metro_dfs_readiness.py tests/scripts/test_enrich_metro_dfs_codes.py tests/scripts/test_bulk_score.py` passed.
- `git diff --check` passed.
- `npm run env:sync:local` synced ignored env files from the main checkout.
- `npm run runtime:check` passed with network access: production service role, staging service role, production publishable key, staging publishable key, and Python 3.13 Supabase client all worked.
- `uv run python -m scripts.explore.audit_scoring_strategy --read-only --expected-project-ref eoajvifhbmqmoluiokcj --service-name roofing --population-class medium_100_300k --pilot-results reports/scoring_audit/coverage_canary.jsonl --stdout-only` exited fail because the canary was a persistence partial failure.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p asyncio tests/unit/test_pipeline_orchestrator.py tests/unit/test_api_niches.py tests/scripts/test_bulk_score.py -q` passed 50 tests after the explicit-target fix.
- `ruff check src/pipeline/orchestrator.py src/domain/services/market_service.py src/research_agent/api.py scripts/explore/bulk_score.py tests/unit/test_pipeline_orchestrator.py tests/unit/test_api_niches.py tests/scripts/test_bulk_score.py` passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p asyncio tests/scripts/test_benchmark_serp_parsing.py tests/scripts/test_benchmark_sampling.py tests/scripts/test_signal_coverage_audit.py tests/scripts/test_scoring_strategy_audit.py -q` passed 47 tests for the acquisition/backfill support.
- `pytest tests/unit/test_dataforseo_client.py -q` passed 18 tests.
- `ruff check scripts/benchmarks/run_pilot.py src/clients/dataforseo/client.py tests/scripts/test_benchmark_serp_parsing.py tests/unit/test_dataforseo_client.py` passed.
- `git diff --check` passed.
- `npx docguard-cli guard` ran with network escalation and exited warn-only with the existing repository warnings around docs-sync, traceability, TODO tracking, Spec-Kit, and unrelated doc quality.

Next:

- Convert the Stage 5 recommendations into implementation slices: benchmark run lineage and metric-sufficiency schema, local identifier/raw evidence persistence, metric-level audit readiness, DataForSEO wrapper parity, then a cost-capped paid metric canary. Do not run broad paid expansion or benchmark recompute before those gates exist.
- Open and merge the WHI-104 benchmark-sufficiency PR after WHI-103 PR #82 lands. Then move to `WHI-105` for Explore/report visibility. Keep paid work bounded to the smallest reviewed acquisition/backfill batch needed to populate DA/Lighthouse telemetry, top-3 review velocity, and benchmark cells with `sample_size_metros >= 8`; do not run benchmark recompute or broader paid expansion until the read-only audits pass.

## Billing Hardening And Admin Issue Visibility

Status: merge conflicts with `origin/main` resolved on `codex/billing-hardening-admin-visibility`; implementation and final checkout reservation race fix are already pushed.

Goal: harden Stripe Checkout/Portal/Webhook behavior after the account billing rollout and give admins an in-app view of billing issues.

Completed in this slice:

- Added migration `023_billing_operations_hardening.sql` with checkout session reservations, billing operation event logging, webhook event ledgering, subscription event-order columns, RLS/service-role policies, and admin RPCs for listing/resolving billing events.
- Added fail-open billing issue logging, checkout session reservation/reuse helpers, webhook event ledger helpers, and stale-event-aware subscription sync.
- Hardened consumer Checkout, Portal, and Webhook routes with stable public error codes/messages, Stripe idempotency keys, same-plan checkout reservation race recovery, abandoned reservation cleanup, duplicate webhook handling, stale/same-second webhook skipping, and admin-visible issue records.
- Added admin billing issue list/resolve API routes, `/billing` dashboard, severity/status filters, expandable issue detail, resolve action, and Billing sidebar navigation.
- Updated canonical architecture, data-model, test-spec, and project context docs for the billing operations contract.

Verified:

- `npm --workspace apps/app test -- billing flags AccountSettingsClient` passed 36 tests.
- `npm --workspace apps/admin test -- billing Sidebar` passed 8 tests after using the local dependency bridge in this worktree.
- Targeted `npm --workspace apps/app run lint -- ...billing files...` passed.
- Targeted `npm --workspace apps/admin run lint -- ...billing files... Sidebar...` passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/unit/test_supabase_schema.py -q` passed 2 tests with the existing `asyncio_mode` warning.
- `git diff --check` passed.
- `npx docguard-cli guard` ran with network escalation and exited warn-only with existing repository warnings around docs-sync, traceability, TODO tracking, Spec-Kit, and unrelated doc quality.

Noted but not fixed in this slice:

- `npx --no-install tsc --noEmit` in `apps/app` now fails only on existing `src/lib/explore/load-explore-data.test.ts` `NODE_ENV` assignment errors.
- `npx --no-install tsc --noEmit` in `apps/admin` still fails on existing `src/__tests__/proxy.test.ts` string pathname assertions.

## WHI-10 Design System Alignment

Status: PR open at `https://github.com/CoVariance-Foundry/whidby/pull/64` on `codex/whi-10-design-system-alignment`; local implementation, review gates, merge-conflict repair, and review-nit fixes passed. GitHub CI/review is still pending and WHI-10 should not be marked Done until the PR merges.

Completed in this slice:

- Adopted DM Serif Display as the consumer display serif while keeping numeric displays on mono and display tracking at `0`.
- Added shared score tone thresholds/components across report breakdowns, report detail modal scores, strategy discovery result scores, Explore score text, service score rows, and report table score text.
- Added shared `NextMoveCard`, `ScoreCircle`, and `ScoreBar` primitives with focused tests.
- Removed local report `scoreColor` / `scoreBarBg` helpers from `BreakdownPanel` and `ReportDetailModal`.
- Repaired the post-`main` merge Reports table conflict by preserving the new card-list layout and applying WHI-10 shared score tones/labels to it.
- Removed synthetic serif weights in login/dashboard inline headings now that DM Serif Display is loaded at weight `400`.
- Removed the redundant `strategyAccentForId` call in `withStrategyAccent`.
- Reused `NextMoveCard` for the dashboard Explore/Multi-market destination cards where it matched the existing next-move pattern.
- Updated canonical design-system architecture/test obligations for shared score visuals.

Verified:

- `npm --workspace apps/app test -- src/lib/design-tokens.test.ts src/lib/strategies/catalog.test.ts src/lib/explore/load-explore-data.test.ts src/components/NextMoveCard.test.tsx src/components/ScoreVisuals.test.tsx src/components/StateMultiselect.test.tsx src/components/reports/ScoreInfoHover.test.tsx src/components/reports/ReportsTable.test.tsx src/components/reports/ScoreBreakdownTabs.test.tsx src/components/explore/ExplorePageClient.test.tsx 'src/app/(protected)/strategies/[id]/StrategyPageClient.test.tsx'` passed 84 tests before the `main` merge; rerun the focused reports tests after any further conflict repair.
- `npx --no-install tsc --noEmit` passed from `apps/app`.
- `npm --workspace apps/app run lint` passed with two pre-existing warnings.
- `git diff --check origin/main...HEAD` passed before merging latest `main`.
- `npm run runtime:check` passed service-role checks, but local Supabase publishable keys are invalid.
- Playwright smoke rendered `/login`; protected routes redirected to `/login?next=...`.

Next:

- Push the merge-conflict repair, wait for GitHub checks/review, then merge PR #64.
- Mark `WHI-10` Done only after the PR merges.
- Authenticated visual QA of protected routes remains blocked locally until publishable Supabase keys are refreshed.

## WHI-9 Competitor Intel

Status: implemented locally on `codex/whi-9-competitor-intel`; focused verification complete, browser/auth QA pending.

Linear: `WHI-9`.

Completed in this slice:

- Added protected `/competitor-intel` as a direct-link Plus/Pro dossier route with upgrade, ready, running, aggregate-only, dossier, and error states.
- Added Next BFF routes and FastAPI routes for `GET /api/competitor-intel` and `POST /api/competitor-intel/runs`.
- Added `organic_competitor_facts` and `competitor_intel_runs`, reused `local_pack_listing_facts`, and persisted competitor-level facts when report payloads carry them.
- Added atomic multi-unit quota RPCs so Competitor Intel consumes/refunds two `fresh_report` units without two separate one-scan calls; refunds are service-role-only.
- Updated canonical docs and focused tests for persistence, schema, API gates, and frontend states.

Next:

- Add the live DataForSEO collector/worker that turns a `ready_to_run` target into newly persisted competitor facts. This slice refuses and refunds runs when no durable aggregate/dossier can be materialized.
- Run browser/visual QA once local auth/API wiring is available.
- Add strategy/report entrypoint CTAs after the route is validated behind rollout controls.
## Proto -> Production Convergence: Epic 6 Reports Page

Status: merged to `main` through PR #59. Follow-up visual QA with authenticated report data remains useful.

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
