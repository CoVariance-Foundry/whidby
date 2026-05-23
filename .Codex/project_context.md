# Project Context

## Consumer Visual System

The consumer app now has shared WHI-10 score primitives in `apps/app/src/lib/design-tokens.ts` and `apps/app/src/components/ScoreVisuals.tsx`. Use `scoreToneForValue` for 80/60/40 score tone decisions and `ScoreCircle` / `ScoreBar` for visible score displays before adding route-local threshold helpers. Numeric score displays should stay on `var(--mono)` with no negative letter spacing.

Report breakdowns, the report detail modal, strategy discovery result cards, Explore score cells, service score rows, and Reports table scores now consume the shared score tone/visual path. Dashboard destination cards use `NextMoveCard` where the pattern is a simple next action rather than a bespoke content card.

## Consumer App Frame

The protected consumer app frame now lives in `apps/app/src/app/(protected)/layout.tsx`. It renders a sticky `Navbar`, a minimal `Footer`, and the route content for authenticated app pages. The navbar resolves the Supabase user, attempts account entitlement and usage loading, and falls back to `Free` with `0/0 scans` if account summary data is unavailable.

Primary authenticated nav is Home, Strategies, Explore, Multi-market, and Reports. `/niche-finder` and `/recommendations` remain valid routes/deep links but are no longer primary nav items. Account settings, password, admin dashboard, and sign-out live in the navbar profile dropdown. Do not reintroduce page-local `Sidebar`/`Topbar` shells; protected pages should render route content and put actions in page headers or client surfaces.

## Consumer Auth Entry

`apps/app/src/app/login/page.tsx` is the canonical email/password login surface. It uses the white Widby card design, preserves the client-side progressive lockout/timeout behavior, honors safe `next` redirects, and defaults successful sign-in to `/reports`.

`apps/web/src/app/login/page.tsx` no longer authenticates users directly. It redirects to the consumer app `/login`, preserving a safe `next` value, so users do not create a marketing-origin session and then bounce into the product app's auth gate.

## Consumer Dashboard

The authenticated `/` home route is now the Phase 2 strategy-first dashboard. `apps/app/src/lib/home/load-dashboard.ts` aggregates the report dashboard BFF, account entitlement/usage summary, onboarding profile/target context, and the strategy catalog into one internal dashboard data shape. Report fetch and onboarding failures are soft dashboard notices; entitlement/auth failures render an actionable blocking account card.

Dashboard starter and shortcut strategies are launch-safe only: `easy_win`, `gbp_blitz`, `keyword_hijack`, and `expand_conquer`. Deprecated or future onboarding recommendations such as `cash_cow`, `blue_ocean`, `portfolio_builder`, and `seasonal_arbitrage` fall back to `easy_win`, so dashboard links do not point users into unavailable strategy routes.

The new dashboard component surface lives in `apps/app/src/components/home/DashboardHome.tsx` and includes the first-run banner, usage strip, recommended strategy hero, Explore/Multi-market cards, strategy shortcuts, and recent reports. Free/no-quota users are routed to cached Explore/settings CTAs; paid or quota-exempt users are routed to the launch-safe starter strategy. Recent report rows link to `/reports?open=<report_id>` so they reuse the existing report modal behavior. The old home widget components were removed; shared dashboard report item types now live in `apps/app/src/lib/home/types.ts`.

## Consumer Reports

Epic 6 reports convergence is in progress on `codex/whi-7-reports-proto-layout`. The protected `/reports` page now uses the prototype history framing, summary stats, search, sort, empty state, and card-list rows. Rows from the reports list link to `/reports/[reportId]`; existing dashboard, Explore, and Niche Finder deep links to `/reports?open=<report_id>` still open the legacy modal for compatibility.

`apps/app/src/app/(protected)/reports/[reportId]/page.tsx` is the new detail-page surface for the remaining Epic 6 work. It loads the existing `/api/agent/reports/[reportId]` BFF with the active cookies, renders headline score bands, score tabs, strategy guidance when report guidance exists, safe Next Moves, and keyword expansion. Continue `WHI-33` through `WHI-35` against this page rather than expanding the modal.
## Consumer Multi-market

The protected `/agency` route is now the Epic 5 Multi-market batch configuration flow instead of a placeholder. It uses the shared protected app frame, exposes a batch-cost indicator, and moves users through configure, confirm, and complete states. Configuration includes launch-safe strategy lenses, state/population filters, service selection, and a 100 target cap.

Target review resolves cached city-service pairs through `apps/app /api/strategies/discover`; queueing sends explicit targets to `apps/app /api/strategies/runs` in fresh mode. The current quota model is one fresh-report scan per queued batch, using the existing strategy-run account/user injection, quota consume/refund behavior, and `strategy_runs` lineage. Target-level execution progress and report fanout remain the backend follow-up for WHI-30.

`apps/app/src/components/StateMultiselect.tsx` is the shared state selector for Multi-market and Explore filters. Do not reintroduce route-local state dropdown copies unless a page needs behavior the shared selector cannot express.

## Account and Billing Settings

Consumer `/settings` now implements the Account and Billing surface for authenticated users. The protected page resolves the Supabase user, account entitlement, fresh-report usage counter, Stripe customer presence, billing-management flag, Stripe scheduled-cancellation state, Supabase auth metadata, and the latest account-visible reports. It renders profile metadata, plan status, cycle reset dates, usage remaining, saved reports preview, plan change actions, payment/invoice rows, password reset controls, and session sign-out.

Saved reports on `/settings` are loaded server-side through the existing `/api/agent/reports?limit=5` route with cookie forwarding, so cached/account-owned visibility stays aligned with the Reports surface. Rows open through `/reports?open=<report_id>`.

The navbar profile menu links Account settings to `/settings`, shows the signed-in email plus live plan label, exposes `/settings/password`, and preserves Supabase sign-out. The external Admin dashboard link is shown only when the resolved account entitlement has `member_role === "admin"`; fallback or non-admin account loading states do not show it. Free users start Plus/Pro upgrades through Stripe Checkout; existing paid plan changes, payment method updates, invoices, and cancellation route through the Stripe Customer Portal. Billing return URLs land on `/settings?billing=success|cancelled`. Password reset emails redirect through `/auth/callback?next=/settings/password`, where an authenticated completion form updates the Supabase password and returns to `/settings?password=updated`.

## AI Review and Visual QA CI/CD

Added CI/CD review scaffolding for Greptile PR review policy, Playwright visual QA, optional Codex/Claude artifact critique, preview URL resolution, and environment manifest checks. The workflow keeps `dev -> main` as the release spine, uses preview/staging/production environment separation, and avoids printing or committing secret values.

Greptile review execution remains owned by the Greptile GitHub App and local Greptile MCP use in Cursor/Codex/Claude Code. PR `visual-qa` labels now create a no-secret request summary; the secret-bearing Visual QA run is maintainer-dispatched from `dev` or `main` with `workflow_dispatch`, validates the preview URL against the allowed HTTPS host list, and uses trusted checkout code so PR-controlled code does not receive Vercel, auth, GitHub, or agent credentials. Visual QA can post review JSON back to a PR when `pr_number` is supplied, and agent critique is capped by workflow and subprocess timeouts. Supabase preview branches require external Supabase GitHub/Vercel integration setup before manual Visual QA should be dispatched for schema-changing previews.

The env sync scripts are intentionally planning-only at this stage. Use the `env:plan:*` package scripts to audit required provider names; do not treat them as live sync/apply commands until provider write implementations are added.

## Consumer Onboarding Flow

Consumer onboarding now has a first production implementation in the consumer app. Supabase migration `016_consumer_onboarding.sql` defines `onboarding_profiles` and `onboarding_targets` for durable signup intent, starter strategy recommendation, selected service/geography target, resume state, and first-report handoff. The tables are account-scoped through existing account membership checks and preserve Mapbox/DataForSEO metadata when a city target is selected.

The consumer app now owns deterministic strategy routing in `apps/app/src/lib/onboarding/`, plus `/api/onboarding/profile`, `/api/onboarding/target`, and `/api/onboarding/start-report` route handlers. Onboarding does not create a separate scoring path: city fresh-report starts delegate to the existing `/api/agent/scoring` route so entitlement, quota, request metadata, and report persistence behavior stay centralized. Free users and broad geography targets are routed toward cached Explore/report experiences instead of fresh generation.

The `/onboarding` page is implemented as a production flow with starter intent capture, service selection, city/state target capture, and confirmation. It reuses the consumer `CityAutocomplete` and now passes a stable input id so labels bind correctly. The auth callback now routes new or incomplete users into onboarding, keeps selected-target users in onboarding so they can start the report, preserves explicit safe `next` redirects, and sends terminal onboarding states to `/reports`.

## Strategy Discovery System

Strategy Discovery is implemented as a consumer product surface on branch `codex/strategy-discovery-system`. The system treats strategies as ranking and explanation lenses over existing Whidby market intelligence instead of creating a second scoring engine. Launch strategies are `easy_win`, `gbp_blitz`, `keyword_hijack`, and `expand_conquer`; `cash_cow` is cataloged as phase 2, and AI resilience is a warning/modifier rather than a standalone route.

Migration `016_strategy_discovery_system.sql` adds `strategy_runs`, `strategy_run_items`, `local_pack_listing_facts`, `metro_feature_vectors`, and `strategy_score_cache`. Domain projection logic lives in `src/domain/strategy_projection.py`, cached market access and run lineage live in `src/clients/strategy_repository.py`, and FastAPI now serves `/api/strategies`, strategy-aware `/api/discover`, and `/api/strategy-runs`. The consumer app adds protected `/strategies` gallery/detail screens, shared strategy types/API helpers, and proxy routes under `apps/app/src/app/api/strategies/*` with existing entitlement/quota checks for fresh runs.

Fresh strategy run creation is validated and lineage-backed: free users remain cached-only via the app proxy, fresh runs are capped at 100 targets, backend write failures return non-success responses so quota can be refunded, and queued runs persist `quota_consumed = 1`. Full async report fanout and run-status/report detail endpoints are still follow-up work.

## Competitor Intel

WHI-9 adds a protected `/competitor-intel` route as a paid Plus/Pro dossier surface. Free users receive an upgrade state; paid users can view durable dossier data or create a two-scan run record when durable aggregate/dossier facts already exist. Until the live DataForSEO collector is wired, `ready_to_run` targets refuse and refund instead of charging for a dead queued job. The UI renders upgrade, ready, running, aggregate-only, dossier, and error states using the existing Widby warm paper design system.

Migration `20260522184933_whi9_competitor_intel_schema_quota.sql` adds `organic_competitor_facts`, `competitor_intel_runs`, and generic multi-unit `consume_usage_quota` / `refund_usage_quota` RPCs while preserving one-unit consume wrappers and moving refund wrappers to service-role-only access. `SupabasePersistence` now writes durable organic and local-pack competitor facts when report payloads contain those rows; `api_response_cache` remains cache/cost infrastructure only. `CompetitorIntelService` reads `organic_competitor_facts`, `local_pack_listing_facts`, `seo_facts`, `metro_score_v2`, and `reports` to assemble ready, aggregate-only, or dossier states, and service-role reads drop competitor fact rows without visible report lineage.

## Consumer User Management and Billing

Consumer user management now has a first implementation slice in code and schema. Supabase migration `014_user_management_billing.sql` defines profiles, accounts, memberships, subscriptions, billing customer mappings, usage counters, report ownership columns, cached/account report visibility, account-scoped report RLS, account bootstrap RPCs, and atomic report quota RPCs. Existing ownerless reports are treated as shared cached reports; fresh generated reports should persist with `owner_account_id`, `created_by_user_id`, and `access_scope = account`.

The consumer app scoring proxy now resolves the Supabase user/account entitlement before calling FastAPI, enforces PostHog-backed fresh-report and quota flags with secure defaults, denies free users fresh reports, consumes/refunds quota around upstream failures, and forwards report ownership context to the Render/FastAPI bridge. Stripe Checkout, Customer Portal, and webhook routes exist for Plus/Pro billing state, backed by `stripe` and `posthog-node` dependencies in `apps/app`.

Billing hardening adds service-role operational tables in `023_billing_operations_hardening.sql`: `billing_checkout_sessions` for one active pending Checkout reservation per account, `billing_webhook_events` for Stripe event dedupe/retry state, and `billing_operation_events` for admin-visible issue logging. Subscription sync persists `last_stripe_event_id` and `last_stripe_event_created_at` so stale or same-second Stripe webhook deliveries are ignored instead of rolling account plans backward.

Consumer billing routes now return stable public `code`/`message` responses and write raw operational details only to `billing_operation_events`. Checkout reuses unexpired pending sessions, recovers same-plan reservation insert races, expires abandoned reservations after failed Stripe setup, and sends Stripe idempotency keys for customer/session creation; portal and webhook failures are logged for admins. The admin dashboard has `/billing`, `/api/billing/issues`, and `/api/billing/issues/:id/resolve` for listing, filtering, expanding, and resolving billing issues through Supabase RPCs gated by `internal_user_entitlements.billing_operations_admin`.

Internal test/admin entitlements are now modeled separately from paid plan state. Migration `018_internal_user_entitlements.sql` adds service-role-only quota exemptions plus `ensure_account_for_user_admin(...)`; app fresh-report gates use `fresh_report_quota_exempt` to let trusted admins test fresh report flows while remaining on `free`. Staging Supabase project `whidby-staging` has migrations `014` through `018` applied, and Auth/account personas are seeded for `admin-test@widby.dev`, `user-test@widby.dev`, `henock@covariance.studio`, `antwoine@covariance.studio`, and `lm13vand@gmail.com`.

Operational sync is migration-first, not Terraform-first: schema/RLS/RPCs live in `supabase/migrations`, curated Auth test users are handled by `scripts/supabase/seed_test_accounts.py`, and ignored `.env` plus GitHub/Vercel environment secrets carry environment-specific credentials. Seed passwords were stored locally in the repo-root `.env`; GitHub `staging` Environment secrets were not uploaded because the escalation reviewer rejected transmitting service-role and account-password secrets without explicit user approval. The local staging service-role credentials work for seeded password auth; the local staging publishable key still needs refresh before browser/client login smoke can pass.

## Consumer Explore

Consumer `/explore` is now a backend-backed, city-first market discovery surface. Migration `020_explore_market_cells.sql` defines `public.explore_market_cells` as a derived materialized read model over `metros`, CBP establishments, service mappings, V2/legacy score rows, and refresh targets. `src/clients/explore_repository.py` and `ExploreCityService` provide the repository/domain boundary, and FastAPI exposes `GET /api/explore/cities` plus `GET /api/explore/cities/{cbsa_code}` for paginated list/detail reads.

WHI-5 / Epic 4 updated the Explore header copy to match the prototype subheader and added the `/strategies` jump link from the Explore subheader. Keep the cross-link as header-level navigation; do not move it into the filter or table controls.

Explore refresh control is implemented for cached report upkeep. Migration `015_explore_refresh_control.sql` adds policy, target, run, run-item, and snapshot tables with a default 30-day cadence; `ExploreRefreshService` and `SupabaseExploreRefreshStore` resolve due/manual targets, queue FastAPI scoring runs, update target freshness, and preserve `explore_report_snapshots` for trends. FastAPI exposes manual run, due-run, and run-status endpoints under `/api/explore/refresh/*`; the consumer app proxies those through bounded Next route handlers, displays refresh controls/status plus freshness fields on `/explore`, reads deltas from `explore_latest_target_scores`/`explore_target_trends`, and schedules due checks from app-scoped `apps/app/vercel.json`.

The app route now loads Explore through bounded Next proxy routes instead of direct Supabase table stitching. Filters and sorts are URL-driven server fetches, table labels match the prototype city browsing model, growth-only filtering is disabled/cleared when `growth_available=false`, and representative density/growth values show metric-service lineage when no service is selected. The city drawer separates cached refresh targets from fresh scan targets: refresh only applies to cached rows with `refresh_target_id`, catalog-only market cells stay reachable without appearing as cached scores, and cached, catalog, and custom services all start fresh scans through the existing entitlement-protected `/api/agent/scoring` route.

Explore data readiness remains staging/live-data dependent. `scripts/explore/audit_explore_sources.py` now reports `explore_market_cells_count`, `market_cells_with_density`, loaded CBP years, and `growth_available`; one CBP year is a warning, not a launch-blocking failure. `scripts/explore/backfill_cbp_establishments.py --year <year>` can import 2022/2023 CBP files independently and still requires explicit `--apply` plus valid Supabase service-role env before writing.

## Phase 7 Benchmark and Sonar Slice-Lite

Phase 7 now has a staging-first benchmark recompute path. `public.recompute_seo_benchmarks(p_window_days integer)` rebuilds `seo_benchmarks` from `seo_facts`, ACS-backed `metros`, CBP-backed `census_cbp_establishments`, and weighted `niche_naics_mapping`; `scripts/benchmarks/recompute_benchmarks.py` calls that RPC through benchmark-specific Supabase env vars.

Benchmark collection is safer but not complete: `scripts/benchmarks/run_pilot.py` can run pilot or full-sample batches, rejects unknown niches/population classes before paid API calls, and captures top-three local-pack review metrics into `seo_facts`. Existing staging facts still need a paid rerun before review-floor benchmarks become populated.

Sonar slice-lite is implemented in staging through `sonar.cells`, `sonar.cell_runs`, `sonar.scoring_weights`, and the service-role-only `public.persist_sonar_slice_lite(p_record jsonb)` RPC. `scripts/sonar/build_slice_lite.py` builds the LA plumbing cell (`238220__msa__31080__2023`) from current Widby data and persists it with `score_version = sonar-lite-0.1` plus warnings for missing NES, BDS, Trends, geo crosswalk, and residual model inputs.
