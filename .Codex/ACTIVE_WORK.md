# Active Work

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

## Explore Cities Backend Design

Status: local data-model/backfill/read-model slice implemented; live backfill blocked by missing/invalid Supabase env; backend API route and pagination still pending.

Completed: canonical Explore Cities architecture now defines the backend read model, source tables, metric formulas, server-side filtering boundary, run-report control, and refresh-target separation.

Latest audit slice: added `scripts/explore/audit_explore_sources.py`, a read-only PostgREST audit for Explore source table visibility and sparse `metros` demographic fields. Focused test `./.venv/bin/pytest tests/scripts/test_audit_explore_sources.py -v` passes. Live publishable-key and service-role audit commands currently report missing Supabase env in this worktree: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`.

Latest backfill slice: added and hardened `scripts/explore/backfill_metros.py`, which builds `public.metros` payloads from `src/data/seed/cbsa_seed.json` plus ACS demographics, derives `population_class`, includes `cbsa_type`, renter units, median age, and ACS load metadata, and only performs PostgREST upserts when `--apply` is explicitly passed with `NEXT_PUBLIC_SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` present. Default and `--dry-run` mode are non-mutating previews. Focused tests `./.venv/bin/pytest tests/scripts/test_backfill_metros.py -v` and `./.venv/bin/pytest tests/clients/census/test_client.py -v` pass. Required dry-run command `python scripts/explore/backfill_metros.py --dry-run` still cannot complete in this worktree because Census fetch is blocked/missing credentials, but it now exits nonzero with sanitized output only: `ACS fetch failed: ConnectError: ACS demographic request failed`. No live mutation ran; this worktree has no root `.env`, `NEXT_PUBLIC_SUPABASE_URL` is unset, and `SUPABASE_SERVICE_ROLE_KEY` is unset.

Latest CBP establishment slice: added `scripts/explore/backfill_cbp_establishments.py` and `tests/scripts/test_backfill_cbp_establishments.py` for import-file payload preparation targeting `public.census_cbp_establishments`. The CLI accepts already-fetched `.json` or `.csv` CBP rows, defaults to dry-run preview, and only performs PostgREST upserts when `--apply` is passed with Supabase URL/service-role env present. No live CBP fetch/write ran. Fetch-path blocker: `src/clients/census/cbp_client.py` currently verifies only a narrow `ESTAB`, `EMP`, `PAYANN`, `NAICS2017` MSA cache path and does not provide the size-bucket, `empflag`, `naics_label`, or suppression contract required for the Explore CBP table.

Latest benchmark readiness slice: added `scripts/explore/recompute_benchmark_readiness.py` and `tests/scripts/test_recompute_benchmark_readiness.py` as a read-only preflight before running the existing benchmark recompute path. The helper blocks recompute when `metros_with_population`, `seo_fact_count`, or `cbp_count` are zero or missing. No benchmark recompute ran in this worktree because live source checks/env were not part of this slice.

Latest read-model slice: added `src/domain/explore/metrics.py`, `src/domain/explore/entities.py`, and `src/domain/services/explore_city_service.py`. The service combines metros, score rows, and service-scoped CBP metric inputs through a repository protocol with no direct Supabase I/O; canonical service normalization, latest unique cached service collapse, V2-over-legacy preference, coherent latest-score freshness, business density, and annualized growth are covered by focused unit tests.

Latest consumer loader slice: `apps/app/src/lib/explore/load-explore-data.ts` now selects optional `public.metros.business_density_per_1k` and `establishment_growth_yoy` metrics when the backend/read-model exposes them, maps them into Explore city summaries, and falls back to the base metros select if PostgREST reports either optional metric column missing from the schema cache. Focused Vitest coverage verifies metric mapping and the missing-column fallback. `METRO_LIMIT` remains in place; final backend pagination/API route work is still required before removing the 100-metro loader limit.

Current implementation slice:

- Add `src/clients/explore_repository.py` so `ExploreCityService` reads from Supabase through a concrete adapter.
- Add backend/API routes for `GET /api/explore/cities`, city detail, run report for any city + service, and refresh runs for cached city + service targets.
- Update `/explore` to consume backend DTOs instead of loading the first 100 metros and filtering in React.
- Add readiness checks for `public.metros`, `public.census_cbp_establishments`, `public.niche_naics_mapping`, `public.metro_score_v2`, PostgREST schema visibility, and null density/growth coverage.

Verified locally:

- `./.venv/bin/pytest tests/scripts/test_audit_explore_sources.py tests/scripts/test_backfill_metros.py tests/scripts/test_backfill_cbp_establishments.py tests/scripts/test_recompute_benchmark_readiness.py tests/unit/test_explore_metrics.py tests/unit/test_explore_city_service.py tests/clients/census/test_client.py -v`
- `npm --workspace apps/app test -- load-explore-data`
- `git diff --check`
- `npx docguard-cli guard` ran with network approval and completed at `119/188 passed` with warning-only MEDIUM findings; HIGH categories passed.

Not verified live:

- `scripts/explore/backfill_metros.py --apply`
- `scripts/explore/backfill_cbp_establishments.py --apply`
- benchmark recompute after fresh source data
- `python scripts/explore/audit_explore_sources.py` against a valid Supabase service-role environment

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
