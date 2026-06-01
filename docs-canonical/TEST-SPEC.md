# Test Specification

<!-- docguard:version 1.7.9 -->
<!-- docguard:status approved -->
<!-- docguard:last-reviewed 2026-05-31 -->
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
| `apps/app/src/app/api/billing/**/*.ts` | colocated `*.test.ts` | Unit/contract |
| `apps/app/src/lib/billing/**/*.ts` | colocated `*.test.ts` | Unit/contract |
| `apps/admin/src/app/api/billing/**/*.ts` | colocated `*.test.ts` | Unit/contract |
| `apps/admin/src/app/(protected)/billing/**/*.tsx` | colocated `*.test.tsx` | Component |
| `apps/app/src/app/api/onboarding/**/*.ts` | colocated `*.test.ts` | Unit/contract |
| `apps/app/src/lib/onboarding/**/*.ts` | colocated `*.test.ts` | Unit/contract |
| `apps/app/src/app/onboarding/**/*.tsx` | colocated `*.test.tsx` | Component |
| `apps/app/src/app/(protected)/layout.tsx` | colocated `layout.test.tsx` | Module/integration |
| `apps/app/src/components/Navbar.tsx` | colocated `Navbar.test.tsx` | Module |
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
| Explore market-cell read model | Materialized read model over canonical tables | Exposes service-aware density/growth without creating duplicate source tables |
| Explore service-selected mode | `/api/explore/cities?service=roofing` | Returns rows where density, growth, score, and freshness belong to roofing |
| Explore default mode lineage | `/api/explore/cities` with no service | Does not present density/growth as city-only facts unless row includes `metric_service` lineage |
| Explore frontend pagination | Next loader and page controls | Does not filter or sort only the first 100 metros in React |
| Explore growth unavailable | CBP only has one year | API returns `growth_available=false`; UI disables growth-only filtering |
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

## V2 Scoring Test Obligations

| Scope | Required Coverage | Required Tests |
|-------|-------------------|----------------|
| Dependency wiring | FastAPI/orchestrator scoring receives benchmark repositories by injection and never instantiates Supabase in formulas | `tests/unit/test_api_niches.py`, `tests/unit/test_pipeline_orchestrator.py`, `tests/scoring/test_benchmark_repository_contract.py` |
| Signal semantics | `top3_review_count_min`, `top3_review_velocity_avg`, CBP density/growth, missing-data confidence penalties, and benchmark confidence | `tests/scoring/test_v2_scoring.py`, `tests/unit/test_strategy_projection.py` |
| Top-5 organic facts | `avg_top5_da` and `avg_top5_lighthouse` use canonical top-5 organic competitors and exclude aggregators/missing URLs | `tests/unit/test_batch_executor.py`, `tests/unit/test_signal_extraction.py`, `tests/unit/test_signal_extractors.py`, `tests/scoring/test_v2_scoring.py` |
| V2 persistence | `seo_facts` and `metro_score_v2` upserts preserve report lineage and do not create duplicate side tables | `tests/unit/test_supabase_persistence.py` |
| Read-model APIs | Explore/report/strategy reads prefer `metro_score_v2`, expose benchmark confidence, and retain legacy fallback | `tests/unit/test_explore_city_service.py`, `tests/unit/test_api_explore_cities.py`, app route tests |
| Benchmark lineage | `seo_benchmarks` reads tolerate nullable lineage fields, benchmark modes are validated, and migration tests assert run plus metric-family sufficiency schema | `tests/scoring/test_benchmark_repository_contract.py`, `tests/clients/test_seo_benchmark_repository.py` |
| SEO evidence lineage | Local-pack rows preserve `cid`/`place_id` plus explicit provenance fields; raw SEO evidence artifact builders/upserts cover request/response hashes, cache status, cost, collection timestamp, collection context id, non-fatal side-channel write failures, RLS, and schema constraints | `tests/unit/test_supabase_persistence.py` |
| Competitor Intel persistence | Organic/local competitor facts are persisted as durable read-model rows without reading `api_response_cache`; run lineage records account/user/quota/status | `tests/unit/test_supabase_persistence.py`, `tests/unit/test_supabase_schema.py` |
| Competitor Intel APIs | Free users receive upgrade state; Plus/Pro users can read/run; run creation consumes/refunds two `fresh_report` units atomically; service-role reads enforce account visibility | `apps/app/src/app/api/competitor-intel/route.test.ts`, `apps/app/src/app/api/competitor-intel/runs/route.test.ts`, `tests/unit/test_api_competitor_intel.py`, `tests/unit/test_competitor_intel_service.py` |
| Competitor Intel UI | Locked, ready, running, aggregate-only, dossier, and error states render without leaking paid details or null-heavy cards | `apps/app/src/components/competitor-intel/CompetitorIntelClient.test.tsx` |

## Coverage-First Production Seed Acceptance

| Gate | Expected |
|------|----------|
| Schema parity | Local migrations and target Supabase schema agree before seed writes |
| Expected-project guard | Seed and recompute commands fail closed when pointed at the wrong project |
| Canary | One city/service pair persists report, V2 score, SEO facts, and readable Explore cache output |
| 12x8 coverage pilot | Pilot records success, partial, and failure audit rows without treating nullable top-5 DA/Lighthouse telemetry as blocking |
| Benchmark recompute | `seo_benchmarks` is rebuilt from accepted `seo_facts` after pilot coverage is reviewed; readiness checks include usable benchmark-cell and metric-family sufficiency gates, not source row counts alone |
| Explore cache validation | `/explore` read models surface the seeded city/service rows with V2 preference and legacy fallback intact; acceptance checks include V2 Explore row counts before claiming the refresh complete |
| 50x16 seed | Full seed proceeds only after the prior gates pass |

## Scoring Coverage Experiment Spec

Linear: `WHI-99`. This is the required source-of-truth experiment contract before any paid coverage run for the `Scoring Coverage & Benchmark Hardening` project. No broad paid scoring run is authorized until this section is satisfied and the preview/canary gates below pass.

### Sample Frame

| Dimension | Required Scope |
| --- | --- |
| Supabase project | Production only, guarded by expected project ref `eoajvifhbmqmoluiokcj` |
| Metro eligibility | `metros.dataforseo_location_codes` must contain a verified native DataForSEO location code; residual ambiguous/invalid/no-match rows are excluded unless a later Linear issue explicitly approves a comparison row |
| Population classes | `micro_under_50k`, `small_50_100k`, `medium_100_300k`, `large_300k_1m`, `metro_1m_5m`, `mega_5m_plus` |
| Core services | `roofing`, `plumbing`, `hvac`, `tree service`, `auto repair`, `water damage restoration`, `electrician`, `locksmith` |
| Minimum pilot size | 12 metros x 8 services: 1 micro, 3 small, 3 medium, 3 large, 1 metro, 1 mega |
| Benchmark usability | `seo_benchmarks.sample_size_metros >= 8` remains the aggregate sample-size threshold, but metric-family readiness is gated by `seo_benchmark_metric_sufficiency` non-null counts and confidence |

### Required Metrics

| Metric Family | Required Evidence |
| --- | --- |
| API outcome | Success, partial failure, failure, latency, and error class by service and population class |
| Persistence | Report-backed rows in `reports`, `metro_scores`, `metro_score_v2`, `seo_facts`, and `explore_market_cells` |
| Demand | Commercial volume, CPC, intent mix, and demand benchmark cell coverage |
| Organic difficulty | Aggregator/local-business counts plus top-5 DA and Lighthouse missingness; top-5 DA/Lighthouse remain telemetry and must not block scoring by themselves |
| Local difficulty | Local-pack known rate, `top3_review_count_min`, `top3_review_velocity_avg`, and local benchmark coverage |
| Monetization | CBP-backed business density, paid ads, LSA, CPC, and monetization benchmark coverage |
| AI resilience | AIO presence, PAA density, intent mix, and persisted V2 AI resilience coverage |
| App visibility | V2 score existence, benchmark confidence metadata, Explore visible row, and Explore V2 preference |

### Benchmark Data Acquisition

The post-pilot acquisition slice is explicit opt-in only. `scripts.benchmarks.run_pilot --collect-organic-telemetry` enriches the top non-aggregator organic SERP targets with DataForSEO Backlinks Summary using `rank_scale=one_hundred` plus Lighthouse data, writing nullable `avg_top5_da`, `avg_top5_lighthouse`, coverage, and confidence fields to `seo_facts`. `--collect-review-velocity` enriches the top local-pack listings through DataForSEO Google Reviews using `cid` or `place_id` when available, writing nullable `top3_review_velocity_avg`. Persistence tests must prove these identifiers and raw provider evidence artifacts survive without inferring unknown provenance.

Preflight mode must skip both acquisition add-ons even when their flags are present. Without `--paid-budget-usd`, preflight validates the selected sample and DFS target metadata only, then exits before paid DataForSEO calls; with `--paid-budget-usd`, it may validate live keyword-volume coverage after the budget and balance guard. These flags are for bounded backfill/acquisition runs after read-only audits identify missing DA/Lighthouse, review velocity, or undersampled benchmark cells; they do not authorize broader paid expansion or benchmark recompute until audit gates pass. Any paid benchmark acquisition run must pass `--paid-budget-usd`, preflight the live DataForSEO balance, and abort before paid calls when the estimated run cost exceeds the cap or the provider balance is not positive.

### CLI Commands

Run from the repo root after `npm run env:sync:local` and `npm run runtime:check`. All apply commands use `--require-dfs`, `--require-v2-persistence`, `--expected-project-ref eoajvifhbmqmoluiokcj`, and production API `https://whidby-1.onrender.com`.

Preview the exact sample before paid calls:

```bash
python -m scripts.explore.bulk_score --preview --cities 1 --population-class micro_under_50k --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --require-dfs --expected-project-ref eoajvifhbmqmoluiokcj
python -m scripts.explore.bulk_score --preview --cities 3 --population-class small_50_100k --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --require-dfs --expected-project-ref eoajvifhbmqmoluiokcj
python -m scripts.explore.bulk_score --preview --cities 3 --population-class medium_100_300k --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --require-dfs --expected-project-ref eoajvifhbmqmoluiokcj
python -m scripts.explore.bulk_score --preview --cities 3 --population-class large_300k_1m --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --require-dfs --expected-project-ref eoajvifhbmqmoluiokcj
python -m scripts.explore.bulk_score --preview --cities 1 --population-class metro_1m_5m --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --require-dfs --expected-project-ref eoajvifhbmqmoluiokcj
python -m scripts.explore.bulk_score --preview --cities 1 --population-class mega_5m_plus --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --require-dfs --expected-project-ref eoajvifhbmqmoluiokcj
```

Run a one-pair canary before the 12x8 pilot:

```bash
python -m scripts.explore.bulk_score --apply --cities 1 --population-class medium_100_300k --service-name roofing --concurrency 1 --api-url https://whidby-1.onrender.com --results-path reports/scoring_audit/coverage_canary.jsonl --require-dfs --require-v2-persistence --expected-project-ref eoajvifhbmqmoluiokcj
python -m scripts.explore.audit_scoring_strategy --read-only --expected-project-ref eoajvifhbmqmoluiokcj --service-name roofing --population-class medium_100_300k --pilot-results reports/scoring_audit/coverage_canary.jsonl --stdout-only
```

Run the bounded 12x8 pilot only after the canary passes:

```bash
python -m scripts.explore.bulk_score --apply --cities 1 --population-class micro_under_50k --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --concurrency 2 --api-url https://whidby-1.onrender.com --results-path reports/scoring_audit/coverage_micro.jsonl --require-dfs --require-v2-persistence --expected-project-ref eoajvifhbmqmoluiokcj
python -m scripts.explore.bulk_score --apply --cities 3 --population-class small_50_100k --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --concurrency 2 --api-url https://whidby-1.onrender.com --results-path reports/scoring_audit/coverage_small.jsonl --require-dfs --require-v2-persistence --expected-project-ref eoajvifhbmqmoluiokcj
python -m scripts.explore.bulk_score --apply --cities 3 --population-class medium_100_300k --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --concurrency 2 --api-url https://whidby-1.onrender.com --results-path reports/scoring_audit/coverage_medium.jsonl --require-dfs --require-v2-persistence --expected-project-ref eoajvifhbmqmoluiokcj
python -m scripts.explore.bulk_score --apply --cities 3 --population-class large_300k_1m --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --concurrency 2 --api-url https://whidby-1.onrender.com --results-path reports/scoring_audit/coverage_large.jsonl --require-dfs --require-v2-persistence --expected-project-ref eoajvifhbmqmoluiokcj
python -m scripts.explore.bulk_score --apply --cities 1 --population-class metro_1m_5m --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --concurrency 2 --api-url https://whidby-1.onrender.com --results-path reports/scoring_audit/coverage_metro.jsonl --require-dfs --require-v2-persistence --expected-project-ref eoajvifhbmqmoluiokcj
python -m scripts.explore.bulk_score --apply --cities 1 --population-class mega_5m_plus --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --concurrency 2 --api-url https://whidby-1.onrender.com --results-path reports/scoring_audit/coverage_mega.jsonl --require-dfs --require-v2-persistence --expected-project-ref eoajvifhbmqmoluiokcj
```

Analyze pilot output and benchmark readiness:

```bash
python -m scripts.explore.audit_scoring_strategy --read-only --expected-project-ref eoajvifhbmqmoluiokcj --service-name roofing --service-name plumbing --service-name hvac --service-name "tree service" --service-name "auto repair" --service-name "water damage restoration" --service-name electrician --service-name locksmith --population-class micro_under_50k --population-class small_50_100k --population-class medium_100_300k --population-class large_300k_1m --population-class metro_1m_5m --population-class mega_5m_plus --pilot-results reports/scoring_audit/coverage_micro.jsonl --pilot-results reports/scoring_audit/coverage_small.jsonl --pilot-results reports/scoring_audit/coverage_medium.jsonl --pilot-results reports/scoring_audit/coverage_large.jsonl --pilot-results reports/scoring_audit/coverage_metro.jsonl --pilot-results reports/scoring_audit/coverage_mega.jsonl
python -m scripts.explore.audit_signal_coverage --coverage-threshold 0.6 --min-benchmark-cells 48 --min-benchmark-sample-size 8 --min-metric-ready-cells 48 --min-explore-v2-rows 48 --acceptance-gates-only --expected-project-ref eoajvifhbmqmoluiokcj
BENCHMARK_SUPABASE_URL=https://eoajvifhbmqmoluiokcj.supabase.co python -m scripts.benchmarks.recompute_benchmarks 120 --expected-project-ref eoajvifhbmqmoluiokcj
python -m scripts.explore.bulk_score --refresh-only --expected-project-ref eoajvifhbmqmoluiokcj
```

Run bounded benchmark acquisition only after the read-only audits identify the smallest missing cells:

```bash
BENCHMARK_SUPABASE_URL=https://eoajvifhbmqmoluiokcj.supabase.co python -m scripts.benchmarks.run_pilot --sample-mode pilot --population-class medium_100_300k --limit-pairs 8 --niche "roofing contractor" --collect-organic-telemetry --collect-review-velocity --organic-telemetry-limit 5 --review-depth 10 --paid-budget-usd 200 --require-dfs --require-v2-persistence --expected-project-ref eoajvifhbmqmoluiokcj
```

### Cost And Stop Rules

| Rule | Stop Condition |
| --- | --- |
| Project guard | Any expected-project mismatch aborts before reads or writes |
| Target identity | Operational runners must send the production `cbsa_code`, `cbsa_name`, `population`, and verified DataForSEO location code into `/api/niches/score`; fallback/manual CBSA ids are not acceptable for coverage or Explore seed runs |
| Canary | Abort the pilot unless the canary returns one successful API result and persists `reports`, `metro_scores`, `metro_score_v2`, `seo_facts`, and a report-backed Explore row |
| Concurrency | Canary concurrency is `1`; pilot concurrency is `2`; raising above `3` requires explicit operator approval |
| API health | Stop the current bucket when API success for attempted rows drops below `80%` after at least four attempts |
| Persistence | Stop immediately on schema failure, missing required table/column, V2 persistence failure, or Explore refresh failure |
| Acquisition flags | `--collect-organic-telemetry` and `--collect-review-velocity` are bounded backfill tools only; preflight skips them, and any broad paid run still requires an approved sample frame |
| Paid budget | `scripts.benchmarks.run_pilot` requires a finite positive `--paid-budget-usd` for paid benchmark acquisition and aborts before paid calls if the estimated DataForSEO cost exceeds the cap or live balance is not positive; `--preflight-only` without a budget exits before paid DataForSEO calls |
| Paid spend | Do not continue to the next population class if the prior class produced more than `25%` `failed` or `partial_failure` rows |
| Residual DFS rows | Ambiguous, invalid, and no-match DFS residuals are excluded until `WHI-112`, `WHI-113`, or `WHI-114` explicitly approves a bounded batch |

### DFS Residual Review Path

Linear: `WHI-101`. The latest post-enrichment baseline is `already_ready=718`, `ambiguous=136`, `invalid_existing_code=52`, and `no_match=31`. Residual rows do not block the coverage experiment, but they are excluded from paid scoring samples until review produces an approval artifact.

| Residual Status | Review Classification | Required Action | Production Seed Policy |
| --- | --- | --- | --- |
| `ambiguous` | `approve` | Human reviewer selects one clear DFS city-level code in the review CSV, or leaves the row excluded | Excluded until approved CSV/equivalent artifact exists |
| `invalid_existing_code` | `correct` | Correct to a compatible DFS city-level code with provenance, or explicitly exclude | Excluded while marked invalid |
| `no_match` | `needs_alternate_target` | Decide whether to exclude, defer source work, or map an approved alternate city-level target | Excluded until alternate target policy is approved |

`scripts/explore/audit_metro_dfs_readiness.py` writes JSON plus candidates/review CSV under ignored `reports/metro_readiness/`. Review CSV rows include population, population class, residual review classification, production seed policy, approval-artifact requirement, and blank review notes. `scripts/explore/enrich_metro_dfs_codes.py` only applies exact rows automatically and only applies strong rows with an approved CSV. `scripts/explore/bulk_score.py --require-dfs` excludes rows whose DFS match confidence is already marked `ambiguous`, `invalid_existing_code`, or `no_match`; residual opt-in requires a dedicated follow-up issue.

### Classification Thresholds

| Classification | Threshold | Scoring Policy |
| --- | --- | --- |
| Reliable | Overall coverage `>= 0.80`, every required population slice `>= 0.60`, canonical required benchmark cells meet `sample_size_metros >= 8`, required metric families are `metric_ready`, and Explore rows are backed by V2 scores | Keep scored |
| Score-with-warning | Overall coverage `>= 0.40` but below reliable, or a required slice below `0.60` with nonzero evidence | Use in V2 scoring with warning/confidence penalty |
| Telemetry-only | Optional signal is present but below `0.40`, or top-5 DA/Lighthouse is sparse/missing | Record and display as evidence only; do not let missingness block scoring |
| Remove | Non-critical signal remains below `0.05` across all successful API rows and does not affect an accepted product requirement | Propose removal from formula in `WHI-106`; do not change formula inside the experiment |
| Acquire-more-data | Required scoring or benchmark input is missing, benchmark cells are undersampled, or app visibility is blocked | Open/route follow-up before scale-out seed |

## Scoring Strategy Audit Tests

| Coverage | Expected | Tests |
|----------|----------|-------|
| Component coverage | Demand, organic, local, monetization, AI resilience, and app-surface metrics summarize by service, population class, and benchmark cell | `tests/scripts/test_scoring_strategy_audit.py` |
| Metric sufficiency | Benchmark cells classify each metric family as `metric_missing`, `metric_undersampled`, or `metric_ready` using `seo_benchmark_metric_sufficiency` non-null evidence and confidence | `tests/scripts/test_scoring_strategy_audit.py`, `tests/scripts/test_signal_coverage_audit.py` |
| Strategy readiness | Easy Win, GBP Blitz, Keyword Hijack, Expand & Conquer, and `/agency` target review roll up required/warning metric families and emit paid canary guidance | `tests/scripts/test_scoring_strategy_audit.py`, `tests/scripts/test_signal_coverage_audit.py` |
| Benchmark usability | Legacy benchmark metrics still classify cells below `sample_size_metros >= 8` as undersampled for backward-compatible audit fields | `tests/scripts/test_scoring_strategy_audit.py` |
| Readiness gates | Signal coverage emits `readiness_gates` with canonical required-cell counts, all-family metric-ready counts, and V2 Explore row counts; `--acceptance-gates-only` sets pass/fail from those explicit gates while preserving broader coverage diagnostics; out-of-scope benchmark cells cannot satisfy the required 48-cell gate | `tests/scripts/test_signal_coverage_audit.py` |
| Acquisition plan | Signal coverage emits `required_acquisition_plan` for required cells below sample size or metric-family sufficiency, including bounded collection flags for organic telemetry, review velocity, and GBP profile gaps | `tests/scripts/test_signal_coverage_audit.py` |
| Pilot analysis | Bulk-score JSONL rows classify success, API failure, persistence partial failure, and schema failure | `tests/scripts/test_scoring_strategy_audit.py` |
| Project guard | Expected-project validation rejects mismatched and suffixed Supabase hosts | `tests/scripts/test_scoring_strategy_audit.py` |
| Production target identity | Bulk scoring requests preserve Supabase metro identity through `/api/niches/score` so `metro_scores`, `metro_score_v2`, `seo_facts`, and Explore rows share the same CBSA | `tests/scripts/test_bulk_score.py`, `tests/unit/test_api_niches.py`, `tests/unit/test_pipeline_orchestrator.py` |

## Benchmark Acquisition Tests

| Coverage | Expected | Tests |
|----------|----------|-------|
| Organic target extraction | SERP parsing excludes known aggregators and missing URLs before selecting organic telemetry targets | `tests/scripts/test_benchmark_serp_parsing.py` |
| DA/Lighthouse parsing | Backlinks Summary and Lighthouse response shapes produce nullable top-5 telemetry and coverage fields | `tests/scripts/test_benchmark_serp_parsing.py` |
| Review velocity acquisition | Google Reviews can target local-pack `cid` or `place_id` identifiers and request newest reviews for top-3 velocity | `tests/scripts/test_benchmark_serp_parsing.py`, `tests/unit/test_dataforseo_client.py` |
| Sampling guardrails | Benchmark pilot sampling still rejects invalid modes, population classes, and metro limits before paid calls | `tests/scripts/test_benchmark_sampling.py` |
| Metric sufficiency schema | Benchmark lineage migrations preserve existing reads while adding per-family evidence counts, source windows, confidence labels, and non-null-count constraints | `tests/scoring/test_benchmark_repository_contract.py` |

## Metro DFS Readiness Tests

| Coverage | Expected | Tests |
|----------|----------|-------|
| DFS match safety | Exact principal-city matches can be auto-selected, split-token CBSA matches are review-gated, ambiguous cities fail closed, and existing codes are compatible with the metro before being trusted | `tests/scripts/test_metro_dfs_readiness.py` |
| DFS enrichment apply guard | Production applies require the expected Supabase project, approved strong rows must match CBSA and location code, unsafe statuses never write, provenance schema misses abort, and updates must affect exactly one metro row | `tests/scripts/test_enrich_metro_dfs_codes.py` |
| Schema provenance | `metros` has DFS match provenance columns and confidence constraints before enrichment writes run | `tests/unit/test_supabase_schema.py` |

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

## Consumer App Frame Tests

| Scope | Required Coverage | Required Tests |
| --- | --- | --- |
| Protected app frame | Authenticated protected layout renders sticky Navbar, account usage pill, profile dropdown entry points, app footer, and child route content; entitlement-summary failures keep the frame usable with free-plan fallback | `apps/app/src/app/(protected)/layout.test.tsx`, `apps/app/src/components/Navbar.test.tsx` |
| Epic-level route shell | Protected route pages rely on `(protected)/layout.tsx` for app chrome and render route content without page-local sidebar/topbar shells | representative protected page tests such as `apps/app/src/app/(protected)/explore/page.test.tsx` and `apps/app/src/app/(protected)/settings/page.test.tsx` |

## Consumer Design System Tests

| Scope | Required Coverage | Required Tests |
| --- | --- | --- |
| Typography baseline | Root app layout exposes Inter, DM Serif Display, and JetBrains Mono font variables; shared CSS maps headings/italic metadata to the serif token and numeric displays to the mono token without negative display tracking | focused component/style tests when shared typography primitives are extracted; `apps/app` typecheck for font import regressions |
| Score visuals | Shared score tone thresholds remain 80/60/40; `ScoreCircle` and `ScoreBar` preserve accessible labels, meter/img semantics, clamped fills, mono numeric display, and hidden-label variants used by compact report surfaces | `apps/app/src/components/ScoreVisuals.test.tsx`; affected surface tests such as `StrategyPageClient.test.tsx`, report table/modal tests, and Explore component tests when markup changes |

## Multi-Market Tests

| Scope | Required Coverage | Required Tests |
| --- | --- | --- |
| Multi-market page flow | `/agency` renders the batch-cost indicator, configure/confirm/complete states, service and state filters, target discovery payloads, and fresh strategy-run queue payloads | `apps/app/src/app/(protected)/agency/page.test.tsx` |
| Shared state selector | State multiselect keeps Explore and Multi-market state filtering accessible and preserves selected-state query behavior | `apps/app/src/app/(protected)/agency/page.test.tsx`, `apps/app/src/components/explore/ExplorePageClient.test.tsx` |
| Backend queue boundary | Fresh strategy runs cap targets at 100, inject account/user ids, consume or refund one fresh-report quota, and forward explicit targets to FastAPI `/api/strategy-runs` | `apps/app/src/app/api/strategies/runs/route.test.ts`, `tests/unit/test_api_strategy_runs.py` |

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

## Billing Operations Tests

| Scope | Required Coverage | Required Tests |
| --- | --- | --- |
| Billing hardening schema | `billing_checkout_sessions`, `billing_operation_events`, `billing_webhook_events`, subscription Stripe event ordering columns, `internal_user_entitlements.billing_operations_admin`, RLS, service-role policies, admin RPCs, and supporting indexes | `tests/unit/test_supabase_schema.py` |
| Checkout route/helpers | Reuses unexpired pending sessions, recovers same-plan reservation insert races, creates customers/sessions with deterministic idempotency keys, logs failures, and returns stable public error codes/messages | `apps/app/src/app/api/billing/checkout/route.test.ts`, `apps/app/src/lib/billing/checkout-session.test.ts` |
| Portal route | Logs missing customer/config/Stripe failures and never returns raw exception text to users | `apps/app/src/app/api/billing/portal/route.test.ts` |
| Webhook route | Deduplicates processed Stripe events, retries failed events, fetches current subscription state when needed, skips stale subscription updates, marks checkout sessions complete/expired, and logs processing failures | `apps/app/src/app/api/billing/webhook/route.test.ts`, `apps/app/src/lib/billing/sync-subscription.test.ts` |
| Admin billing APIs | Requires authenticated admin access through Supabase RPCs, lists filtered billing events, and resolves events | `apps/admin/src/app/api/billing/issues/route.test.ts`, `apps/admin/src/app/api/billing/issues/[id]/resolve/route.test.ts` |
| Admin billing UI | Shows open issue counts, severity/status filters, detail rows, resolve actions, and a sidebar Billing link | `apps/admin/src/app/(protected)/billing/page.test.tsx`, `apps/admin/src/components/Sidebar.test.tsx` |

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
| 1.6.2 | 2026-05-22 | Billing operations hardening | Added checkout/session idempotency, webhook ledger, issue logging, admin API/UI, and schema test obligations |
| 1.6.0 | 2026-05-17 | Internal entitlements and staging accounts | Added quota-exempt admin, seed script, and migration parity test obligations |
| 1.6.2 | 2026-05-22 | Coverage-first production seed acceptance | Added schema parity, expected-project guard, canary, pilot, benchmark, Explore cache, and full-seed gates |
| 1.6.3 | 2026-05-22 | Scoring strategy audit | Added component coverage, benchmark usability, pilot-result, and project-guard test obligations |
| 1.7.0 | 2026-05-22 | Competitor Intel | Added paid dossier, durable competitor facts, two-scan quota, and UI/API test obligations |
| 1.7.1 | 2026-05-22 | Merge sync | Preserved coverage-first seed gates alongside Competitor Intel test obligations |
| 1.7.2 | 2026-05-22 | Merge sync | Preserved scoring strategy audit obligations alongside Competitor Intel and coverage-first seed gates |
| 1.7.3 | 2026-05-23 | WHI-99 scoring coverage experiment | Added source-of-truth sample frame, CLI commands, stop rules, and classification thresholds |
| 1.7.4 | 2026-05-23 | WHI-101 DFS residual review path | Added residual classification, approval, and seed-exclusion policy |
| 1.7.5 | 2026-05-23 | WHI-102 canary persistence gate | Added production target identity preservation as a canary/pilot test obligation |
| 1.7.6 | 2026-05-23 | WHI-102 acquisition backfill gate | Added explicit opt-in benchmark acquisition flags and tests for top-5 organic telemetry plus top-3 review velocity |
| 1.7.7 | 2026-05-24 | WHI-126 benchmark lineage schema | Added benchmark mode parsing and metric-family sufficiency migration test obligations |
| 1.7.8 | 2026-05-24 | WHI-127 evidence lineage schema | Added local-place identifier and raw SEO evidence artifact persistence test obligations |
| 1.7.9 | 2026-05-31 | WHI-127 review fix | Added collection context id and non-fatal evidence side-channel failure test obligations |
