# Test Specification

<!-- docguard:version 1.6.0 -->
<!-- docguard:status approved -->
<!-- docguard:last-reviewed 2026-05-17 -->
<!-- docguard:owner @widby-team -->

> **Canonical document** — Design intent. This file declares what tests MUST exist.

---

## Test Categories

| Category | Required | Applies To | Tools |
|----------|----------|-----------|-------|
| Unit | Yes | All pipeline/scoring/client modules | pytest, pytest-asyncio, pytest-mock |
| Integration | Yes (advisory, not CI-blocking) | Live API calls | pytest with `@pytest.mark.integration` |
| E2E | Optional | Full pipeline runs | Custom scripts |
| Contract | Yes | Module I/O boundaries | pytest (schema validation) |

## Coverage Rules

| Source Pattern | Required Test Pattern | Category |
|---------------|----------------------|----------|
| `src/clients/**/*.py` | `tests/unit/test_*.py` | Unit |
| `src/pipeline/**/*.py` | `tests/unit/test_*.py` | Unit |
| `src/scoring/**/*.py` | `tests/unit/test_*.py` | Unit |
| `src/classification/**/*.py` | `tests/unit/test_*.py` | Unit |
| `src/experiment/**/*.py` | `tests/unit/test_*.py` | Unit |
| `src/research_agent/**/*.py` | `tests/unit/test_*.py` | Unit |
| `src/domain/explore/**/*.py` | `tests/unit/test_explore_*.py` | Unit |
| `src/domain/services/explore_city_service.py` | `tests/unit/test_explore_city_service.py` | Unit |
| `apps/app/src/app/api/onboarding/**/*.ts` | colocated `*.test.ts` | Unit/contract |
| `apps/app/src/lib/onboarding/**/*.ts` | colocated `*.test.ts` | Unit/contract |
| `apps/app/src/app/onboarding/**/*.tsx` | colocated `*.test.tsx` | Component |
| `scripts/supabase/**/*.py` | `tests/scripts/test_*.py` | Unit/contract |

## Test Rules (Constitution-Mandated)

1. Unit tests run without API keys or network access (use fixtures/mocks).
2. Integration tests are tagged `@pytest.mark.integration` and skipped in CI by default.
3. Every public function has at least one unit test.
4. Every I/O contract from the spec has a corresponding test.
5. Use `pytest` with `pytest-asyncio` for async code.
6. Use `pytest-mock` for mocking external dependencies.
7. Fixtures live alongside tests in `tests/fixtures/`, not in `conftest.py`.

## Test Structure

```
tests/
  unit/
    test_{module}.py              # No external calls, use fixtures/mocks
  integration/
    test_{module}_integration.py  # Real API calls, tagged @pytest.mark.integration
  fixtures/
    {module}_fixtures.py          # Shared test data, mock responses
```

## Service-to-Test Map

| Source File | Unit Test | Integration Test | Status |
|------------|-----------|-----------------|--------|
| `src/clients/dataforseo/client.py` | `tests/unit/test_dataforseo_client.py` | — | ✅ |
| `src/clients/llm/client.py` | `tests/unit/test_llm_client.py` | — | ✅ |
| `src/data/metro_db.py` | `tests/unit/test_metro_db.py` | — | ✅ |
| `supabase/migrations/` | `tests/unit/test_supabase_schema.py` | — | ✅ |
| `src/pipeline/keyword_expansion.py` | `tests/unit/test_keyword_expansion.py` | `tests/integration/test_keyword_expansion_integration.py` | ✅ |
| `src/pipeline/intent_classifier.py` | `tests/unit/test_intent_classifier.py` | — | ✅ |
| `src/pipeline/keyword_deduplication.py` | `tests/unit/test_keyword_deduplication.py` | — | ✅ |
| `src/research_agent/` | `tests/unit/test_research_agent_loop.py` | — | ✅ |
| `src/research_agent/places.py` | `tests/unit/test_places_bridge.py`, `tests/unit/test_api_places_suggest.py` | — | ✅ |
| `src/pipeline/orchestrator.py` | `tests/unit/test_pipeline_orchestrator.py` | — | ✅ |

## Explore Cities Test Obligations

| Test | Scope | Expected |
|------|-------|----------|
| Business density formula | Weighted CBP rows + population | Returns establishments per 1,000 residents using `niche_naics_mapping.weight`; missing population returns null with a quality flag |
| Establishment growth formula | Prior/latest weighted CBP rows | Returns annualized growth; missing historical CBP year returns `growth_available=false` |
| Freshness calculation | Latest score timestamp + cadence | Marks stale when older than cadence; null score timestamp is stale only for cached-service targets |
| V2 score preference | V2 and legacy rows for same city/service | Uses `metro_score_v2` for presentation score and marks `score_system=v2` |
| Legacy fallback | Legacy row with no V2 row | Returns legacy opportunity with `score_system=legacy` |
| Server-side filters | State, population, income, service, density, growth, stale | Repository receives filters; frontend does not filter the first 100 rows as the source universe |
| Run report availability | City with no cached services | API accepts city + service and returns queued/started report response through scoring bridge |
| Refresh target resolution | Selected, visible, stale, all scopes | Resolves existing cached city + service targets without browser-side scoring loops |
| Readiness audit | `metros`, CBP, NAICS mapping, scores | Fails clearly when canonical tables are missing, empty, or hidden from PostgREST schema cache |
| Explore E2E smoke | Explore table, filters, drawer, run-report control | Loads from backend API and exposes run report even when a city has no cached services |

## E2E Scoring Tests (Playwright)

| Spec File | Scope | Requires Backend? |
|-----------|-------|-------------------|
| `apps/app/e2e/scoring-regression.spec.ts` | Huntsville regression, city normalization, input validation, duplicate submit, UI error display | Yes (FastAPI) |
| `apps/app/e2e/autocomplete-scoring-flow.spec.ts` | Autocomplete → select → submit metadata propagation, DFS bridge diagnosis | Yes (FastAPI + Mapbox) |
| `apps/app/e2e/scoring-matrix.spec.ts` | 10-combo parameterized matrix (5 Tier 1 + 5 Tier 2), JSONL metrics output | Yes (FastAPI + DFS) |
| `apps/app/e2e/scoring-lifecycle.spec.ts` | Full UI lifecycle: submit → result → reports list → recent searches | Yes (FastAPI) |
| `apps/app/e2e/scoring-quality-gates.spec.ts` | Pass rate, flake rate, latency, cost gates (reads matrix JSONL) | No (post-run analysis) |

Additional contract checks for scoring/autocomplete:
- `apps/app/src/app/api/agent/scoring/route.test.ts`: verifies `metadata_source` passthrough, `fallback_path` derivation, and `request_id` propagation.
- `tests/unit/test_api_niches.py`: validates `metadata_source` request contract on FastAPI boundary.
- `tests/unit/test_api_places_suggest.py`: verifies `enrichment_status` semantics for `enriched`, `mapbox_only`, and `not_configured`.

## Explore Refresh Control Tests

| Scope | Required Coverage | Required Tests |
|-------|-------------------|----------------|
| Explore refresh control | 30-day refresh policy defaults, loader freshness mapping, refresh store persistence, stale target selection, run status transitions, snapshot lineage, score/trend deltas, API behavior, bounded Next proxy behavior, and cron auth enforcement | `tests/unit/test_explore_refresh_service.py`, `tests/unit/test_explore_refresh_schema.py`, `tests/unit/test_api_explore_refresh.py`, `apps/app/src/lib/explore/load-explore-data.test.ts`, `apps/app/src/lib/explore/load-score-trends.test.ts`, `apps/app/src/app/api/explore/refresh/runs/route.test.ts`, `apps/app/src/app/api/explore/refresh/runs/[runId]/route.test.ts`, `apps/app/src/app/api/explore/refresh/due/route.test.ts`, `apps/app/src/components/explore/ExplorePageClient.test.tsx`, `apps/app/e2e/reports-smoke.spec.ts` |

## Consumer Onboarding Tests

| Scope | Required Coverage | Required Tests |
|-------|-------------------|----------------|
| Onboarding schema | Profile/target table creation, status/geo checks, RLS enablement, account membership policies, service-role policies, and timestamp triggers | `tests/unit/test_supabase_schema.py` |
| Strategy routing | Deterministic mapping from intent/focus/coach-or-agency answers to starter strategy, available strategy ids, and snake_case next route | `apps/app/src/lib/onboarding/strategy-routing.test.ts` |
| Profile API | Auth requirement, account entitlement resolution, profile upsert validation, existing profile reads, latest target reads, and entitlement error mapping | `apps/app/src/app/api/onboarding/profile/route.test.ts` |
| Target API | Target validation, strategy id validation, city metadata preservation, broad geography persistence, and profile status transition to `target_selected` | `apps/app/src/app/api/onboarding/target/route.test.ts` |
| First-report handoff | Saved target lookup, free-tier cached-route handling, city target delegation to `/api/agent/scoring`, broad target cached Explore routing, and quota/upgrade responses | `apps/app/src/app/api/onboarding/start-report/route.test.ts`, `apps/app/src/app/api/agent/scoring/route.test.ts` |
| Onboarding UI | Resume load, profile defaults, service selection, city/state target selection, confirmation state, CTA behavior, and accessible production location input labels | `apps/app/src/app/onboarding/OnboardingClient.test.tsx`, `apps/app/src/components/niche-finder/CityAutocomplete.test.tsx` |
| Auth resume | Supabase auth callback redirects new/incomplete users to onboarding, respects safe explicit `next`, ignores unsafe `next`, and routes terminal onboarding states to reports | `apps/app/src/app/auth/callback/route.test.ts` |

## Strategy Discovery Tests

| Scope | Required Coverage | Required Tests |
| --- | --- | --- |
| Strategy catalog | Launch strategies, phase-2 status, AI modifier behavior | `tests/unit/test_strategy_projection.py` |
| Easy Win | Weak organic/local competition projection from V2 vector and facts | `tests/unit/test_strategy_projection.py` |
| GBP Blitz | Review barrier, review velocity, profile completeness, map-pack presence | `tests/unit/test_strategy_projection.py` |
| Keyword Hijack | Primary keyword volume floor, map-pack presence, exact-match GBP name availability | `tests/unit/test_strategy_projection.py`, `tests/unit/test_api_strategy_discovery.py` |
| Expand & Conquer | Feature-vector similarity plus equal-or-lower competition filter | `tests/unit/test_discovery_service_strategies.py` |
| Consumer entitlements | Free cached-only, plus/pro fresh strategy run allowed, internal quota-exempt admins allowed, batch cap enforced | `apps/app/src/app/api/strategies/runs/route.test.ts` |

## Internal Entitlement and Staging Account Tests

| Scope | Required Coverage | Required Tests |
| --- | --- | --- |
| Internal entitlement schema | `internal_user_entitlements` table, service-role-only policy, active exemption index, `get_account_entitlement()` return shape, and admin bootstrap RPC permissions | `tests/unit/test_supabase_schema.py` |
| Fresh-report gates | Free users blocked from fresh reports, plus/pro allowed through quota, internal quota-exempt admins bypass quota without consuming usage, and non-city onboarding targets remain cached-route only | `apps/app/src/app/api/agent/scoring/route.test.ts`, `apps/app/src/app/api/strategies/runs/route.test.ts`, `apps/app/src/app/api/onboarding/start-report/route.test.ts` |
| Staging seed script | Creates/updates Auth users without returning passwords, preserves existing metadata, assigns member role/plan/quota exemption, and supports admin-test, user-test, Henock, Antwoine, and Luke personas | `tests/scripts/test_seed_test_accounts.py` |
| Migration parity audit | Fails closed on missing/empty local migration directories and reports local migrations absent from staging history | `tests/scripts/test_audit_migration_parity.py` |

## Unit Test Obligations (Algo Spec §12.1)

| Test | Input | Expected |
|------|-------|----------|
| Keyword expansion produces Tier 1 terms | "plumber" | Contains "plumber near me" |
| Intent classification: transactional | "emergency plumber near me" | intent = "transactional" |
| Intent classification: informational | "how to fix a leaky faucet" | intent = "informational", excluded from SERP |
| AIO volume discount (transactional) | volume=1000, intent=transactional | effective ≈ 988 |
| AIO volume discount (informational) | volume=1000, intent=informational | effective ≈ 743 |
| Aggregator detection | SERP with yelp.com at #1 | `aggregator_count >= 1` |
| Cross-metro dedup | Same domain in 10/20 metros | Domain in `DETECTED_NATIONAL` |
| Review velocity calculation | 12 reviews in 6 months | velocity = 2.0 reviews/month |
| GBP completeness: full | All 7 signals present | score = 1.0 |
| GBP completeness: minimal | Only phone + category | score = 0.29 |
| Confidence penalty: missing review data | Metro with 0 review results | Confidence <= 90 |
| Confidence penalty: high AIO | aio_trigger_rate = 0.35 | Confidence <= 90 |
| Opportunity cap: weak component | Any score < 5 | Opportunity <= 20 |
| AI resilience hard floor | ai_resilience < 20 | Opportunity <= 50 |
| Feedback log created | Any report generation | Non-null log_id in meta |

## Integration Tests (Known Markets, Algo Spec §12.2)

| Test Case | Niche | Metro | Expected Outcome |
|-----------|-------|-------|------------------|
| Known easy market | "plumber" | Small city with weak SERPs | Opportunity > 70, Difficulty EASY |
| Known hard market | "plumber" | NYC/LA | Opportunity < 40, Difficulty HARD/VERY_HARD |
| Known aggregator market | "lawyer" | Any major metro | Archetype = AGGREGATOR_DOMINATED |
| Niche niche | "septic tank pumping" | Rural MSA | Low volume but low competition |
| AI-exposed niche | "how to" heavy niche | Any metro | AI exposure = AI_MODERATE or AI_EXPOSED |
| Review fortress | Niche with 200+ review incumbents | Major metro | Local competition score < 30 |
| GBP desert | Niche with incomplete GBP profiles | Smaller metro | Local competition score > 70 |

## Quality Gates (CI)

| Gate | Scope | Blocks Merge? |
|------|-------|---------------|
| `ruff check` | All Python files | Yes |
| `pytest tests/unit/` | All unit tests pass | Yes |
| `npm run lint` | All TypeScript/JS in affected workspaces | Yes |
| Spec artifact presence | Feature branch touches module scope | Yes |
| Docs-sync validation | Architecture docs updated when interfaces change | Yes |
| Integration tests | Real API calls (`@pytest.mark.integration`) | No (advisory) |

## Validation Commands

```bash
ruff check src tests
python -m pytest tests/unit/ -v
python -m pytest tests/unit/ --cov=src --cov-report=term-missing
python -m pytest tests/integration/ -v -m integration
npm run lint
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-04-05 | DocGuard Init | Initial template |
| 1.0.0 | 2026-04-05 | Migration | Populated from `docs/algo_spec_v1_1.md` §12, `docs/product_breakdown.md`, `.specify/memory/constitution.md` |
| 1.1.0 | 2026-04-23 | E2E scoring suite | Added places bridge + orchestrator to service-test map, added E2E scoring tests section (regression, autocomplete flow, matrix, lifecycle, quality gates) |
| 1.2.0 | 2026-05-14 | Explore Cities system design | Added domain metric, service, repository, API, and E2E obligations for backend-backed Explore Cities |
| 1.3.0 | 2026-05-14 | Explore refresh control | Added refresh policy, target selection, run status, snapshot lineage, trend delta, and cron auth test obligations |
| 1.4.0 | 2026-05-16 | Consumer onboarding flow | Added schema, routing, API, UI, first-report handoff, and auth-resume test obligations |
| 1.5.0 | 2026-05-16 | Strategy Discovery system design | Added strategy projection, discovery service, API, and consumer entitlement test obligations |
| 1.6.0 | 2026-05-17 | Internal entitlements and staging accounts | Added quota-exempt admin, seed script, and migration parity test obligations |
