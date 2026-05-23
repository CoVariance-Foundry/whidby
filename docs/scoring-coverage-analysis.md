# Scoring Coverage Analysis

Linear: `WHI-103`

Source artifacts:

- `reports/scoring_audit/coverage_micro.jsonl`
- `reports/scoring_audit/coverage_small.jsonl`
- `reports/scoring_audit/coverage_medium.jsonl`
- `reports/scoring_audit/coverage_large.jsonl`
- `reports/scoring_audit/coverage_metro.jsonl`
- `reports/scoring_audit/coverage_mega.jsonl`
- `reports/scoring_audit/scoring_audit_20260523T154926Z.json`
- `reports/scoring_audit/scoring_audit_20260523T154926Z.md`

The artifacts above are generated audit outputs and remain ignored by git. This document records the durable analysis that should travel with the repo.

## Executive Summary

The coverage pilot proved the guarded production scoring path, but it did not prove that the current data is ready for broader seed expansion or benchmark recompute.

The bounded 12 metro x 8 service pilot completed with 96 successful API and persistence outcomes, 0 partial failures, and 0 failures. Every pilot row persisted through the V2 scoring path, and every row used the production project guard, DFS-ready metro targeting, V2 persistence checks, and the production API.

The follow-up scoring audit still failed. The failure is not API/runtime health; it is evidence sufficiency. Benchmark cells are not usable at the canonical `sample_size_metros >= 8` threshold, top-5 DA and Lighthouse telemetry are absent, local difficulty inputs are missing, and app-surface V2 visibility is too sparse for a scale-out seed.

The next work should stay on the smallest data-acquisition and benchmark-sufficiency path. Do not run benchmark recompute or broader paid expansion until a reviewed acquisition batch produces usable benchmark cells and the read-only audits pass.

## Methodology

### Sample Frame

| Dimension | Value |
| --- | --- |
| Production Supabase project | `eoajvifhbmqmoluiokcj` |
| Production scoring API | `https://whidby-1.onrender.com` |
| Pilot size | 12 metros x 8 services = 96 market pairs |
| Intended audit universe | 935 metros x 8 services = 7,480 market pairs |
| Metro eligibility | Verified native DataForSEO location code required |
| Services | `roofing`, `plumbing`, `hvac`, `tree service`, `auto repair`, `water damage restoration`, `electrician`, `locksmith` |
| Population classes | `micro_under_50k`, `small_50_100k`, `medium_100_300k`, `large_300k_1m`, `metro_1m_5m`, `mega_5m_plus` |
| Benchmark usability threshold | `seo_benchmarks.sample_size_metros >= 8` |

### Pilot Markets

| Population class | Metros | Pairs |
| --- | --- | ---: |
| `micro_under_50k` | Winona, MN (`49100`) | 8 |
| `small_50_100k` | Rome, GA (`40660`); Dubuque, IA (`20220`); Adrian, MI (`10300`) | 24 |
| `medium_100_300k` | Waco, TX (`47380`); Sioux Falls, SD (`43620`); Longview, TX (`30980`) | 24 |
| `large_300k_1m` | Omaha, NE (`36540`); Greenville, SC (`24860`); Knoxville, TN (`28940`) | 24 |
| `metro_1m_5m` | Phoenix, AZ (`38060`) | 8 |
| `mega_5m_plus` | New York, NY (`35620`) | 8 |

### Command History And Dates

| Date | Action | Result |
| --- | --- | --- |
| 2026-05-22 | Six read-only preview buckets generated `preview_*.json` | Planned the exact 12 x 8 sample without paid scoring |
| 2026-05-22 | Original Waco, TX x roofing canary | API returned HTTP 200, but persistence was partial because production metro identity fell back to `fallback:waco` |
| 2026-05-23 | PR #78 merged | Explicit production metro identity propagated through `bulk_score.py`, `/api/niches/score`, `MarketService`, and `score_niche_for_metro` |
| 2026-05-23 | Post-PR #78 Waco, TX x roofing canary | Passed required `reports`, `metro_scores`, `metro_score_v2`, `seo_facts`, and `explore_market_cells` persistence |
| 2026-05-23 14:27-15:48 UTC | Six apply buckets generated `coverage_*.jsonl` | 96 successes, 0 partials, 0 failures |
| 2026-05-23 15:49 UTC | `audit_scoring_strategy` generated the final scoring audit | Exited `fail` because benchmark, organic telemetry, local difficulty, and app-surface gates remain below threshold |

### Environment And Stop Conditions

All apply runs used:

- `--require-dfs`
- `--require-v2-persistence`
- `--expected-project-ref eoajvifhbmqmoluiokcj`
- `--api-url https://whidby-1.onrender.com`
- concurrency `2` for pilot buckets and concurrency `1` for the canary

The governing stop conditions remain the canonical `docs-canonical/TEST-SPEC.md` contract:

- Abort on expected-project mismatch before production reads or writes.
- Abort if target identity does not use production `cbsa_code`, `cbsa_name`, `population`, and verified DataForSEO location code.
- Abort the pilot unless the canary persists `reports`, `metro_scores`, `metro_score_v2`, `seo_facts`, and a report-backed Explore row.
- Stop a bucket when API success drops below 80 percent after at least four attempts.
- Stop immediately on schema failure, missing required table/column, V2 persistence failure, or Explore refresh failure.
- Keep `--collect-organic-telemetry` and `--collect-review-velocity` as explicit bounded acquisition flags only.

## Coverage Matrix

Cell format: `scored; Explore visible; benchmark status`.

| Service | `micro_under_50k` | `small_50_100k` | `medium_100_300k` | `large_300k_1m` | `metro_1m_5m` | `mega_5m_plus` |
| --- | --- | --- | --- | --- | --- | --- |
| `roofing` | 1/1; 0/1; missing | 3/3; 0/3; missing | 3/3; 1/3; missing | 3/3; 1/3; missing | 1/1; 0/1; missing | 1/1; 1/1; missing |
| `plumbing` | 1/1; 0/1; missing | 3/3; 0/3; missing | 3/3; 0/3; missing | 3/3; 0/3; missing | 1/1; 1/1; missing | 1/1; 1/1; missing |
| `hvac` | 1/1; 0/1; missing | 3/3; 0/3; missing | 3/3; 0/3; missing | 3/3; 0/3; missing | 1/1; 1/1; missing | 1/1; 1/1; missing |
| `tree service` | 1/1; 0/1; missing | 3/3; 0/3; missing | 3/3; 0/3; missing | 3/3; 0/3; missing | 1/1; 0/1; missing | 1/1; 0/1; missing |
| `auto repair` | 1/1; 0/1; undersampled | 3/3; 0/3; undersampled | 3/3; 0/3; undersampled | 3/3; 0/3; undersampled | 1/1; 0/1; undersampled | 1/1; 0/1; undersampled |
| `water damage restoration` | 1/1; 0/1; undersampled | 3/3; 0/3; undersampled | 3/3; 0/3; undersampled | 3/3; 0/3; missing | 1/1; 0/1; undersampled | 1/1; 0/1; undersampled |
| `electrician` | 1/1; 0/1; missing | 3/3; 0/3; missing | 3/3; 0/3; missing | 3/3; 0/3; missing | 1/1; 1/1; missing | 1/1; 1/1; missing |
| `locksmith` | 1/1; 0/1; missing | 3/3; 0/3; undersampled | 3/3; 0/3; undersampled | 3/3; 0/3; undersampled | 1/1; 0/1; undersampled | 1/1; 1/1; undersampled |

### Pilot Outcome By Population Class

| Population class | API success | Persistence success | V2 score rows | Explore-visible pilot rows | Benchmark status |
| --- | ---: | ---: | ---: | ---: | --- |
| `micro_under_50k` | 8/8 | 8/8 | 8/8 | 0/8 | 6 missing, 2 undersampled |
| `small_50_100k` | 24/24 | 24/24 | 24/24 | 0/24 | 15 missing, 9 undersampled |
| `medium_100_300k` | 24/24 | 24/24 | 24/24 | 1/24 | 15 missing, 9 undersampled |
| `large_300k_1m` | 24/24 | 24/24 | 24/24 | 1/24 | 18 missing, 6 undersampled |
| `metro_1m_5m` | 8/8 | 8/8 | 8/8 | 3/8 | 5 missing, 3 undersampled |
| `mega_5m_plus` | 8/8 | 8/8 | 8/8 | 5/8 | 5 missing, 3 undersampled |

## Coverage By Scoring Component

| Component | Average coverage | Status | Recommendation |
| --- | ---: | --- | --- |
| `demand` | 0.2523 | undersampled | Keep scored, but acquire benchmark data and warn on low confidence |
| `monetization` | 0.2041 | undersampled | Acquire benchmark data and warn on low confidence |
| `app_surface` | 0.0152 | undersampled | Acquire data before scale-out seed |
| `ai_resilience` | 0.0113 | sparse | Score with warning |
| `organic` | 0.0064 | missing | Keep aggregator/local-business counts as warning signals; DA/Lighthouse remain telemetry-only |
| `local` | 0.0064 | missing | Acquire local difficulty and benchmark data before scale-out seed |

### Critical Metric Gaps

| Component | Metric | Overall coverage | Minimum city-size slice | Status | Recommendation |
| --- | --- | ---: | ---: | --- | --- |
| `demand` | `demand_benchmark` | 0.0000 | 0.0000 | undersampled | Requires data acquisition |
| `local` | `local_benchmark` | 0.0000 | 0.0000 | undersampled | Requires data acquisition |
| `local` | `local_difficulty_inputs` | 0.0000 | 0.0000 | missing | Requires data acquisition |
| `monetization` | `monetization_benchmark` | 0.0000 | 0.0000 | undersampled | Requires data acquisition |
| `organic` | `top5_da_measurement` | 0.0000 | 0.0000 | missing | Telemetry-only |
| `organic` | `top5_da_value` | 0.0000 | 0.0000 | missing | Telemetry-only |
| `organic` | `top5_lighthouse_measurement` | 0.0000 | 0.0000 | missing | Telemetry-only |
| `organic` | `top5_lighthouse_value` | 0.0000 | 0.0000 | missing | Telemetry-only |
| `demand` | `cpc` | 0.0035 | 0.0000 | sparse | Score with warning |
| `app_surface` | `explore_visible` | 0.0184 | 0.0031 | sparse | Requires data acquisition |

Population is the only demand input that is fully reliable in this audit: overall coverage `1.0000` with every city-size slice at `1.0000`.

## Benchmark Sufficiency

The benchmark gate remains closed.

| Measure | Result |
| --- | ---: |
| Required service x population benchmark cells | 48 |
| Usable benchmark cells at `sample_size_metros >= 8` | 0 |
| Existing `seo_benchmarks` cells in audit inventory | 55 |
| Pilot rows with missing benchmark cell | 64 |
| Pilot rows with undersampled benchmark cell | 32 |

The current benchmark shape is enough to explain why scores are low-confidence, but not enough to recompute benchmark-backed V2 scoring or expand production seeding. The next acquisition run should target the smallest missing service x population cells needed to lift benchmark sample sizes to at least 8 metros per cell.

## Benchmark-Cell Sufficiency Appendix

Linear: `WHI-104`

Schema source checked before querying:

- `.Codex/databricks-context/` is not present in this repo checkout.
- Supabase schema source is `supabase/migrations/010_v2_benchmarks.sql` and `supabase/migrations/012_recompute_seo_benchmarks.sql`.
- The live read-only query selected the documented `seo_benchmarks` columns: `niche_normalized`, `naics_code`, `population_class`, benchmark percentile fields, `sample_size_metros`, `sample_size_observations`, `confidence_label`, `last_recomputed_at`, `fact_window_start`, and `fact_window_end`.

Live query snapshot:

| Measure | Result |
| --- | ---: |
| Query time | 2026-05-23 |
| Production project | `eoajvifhbmqmoluiokcj` |
| `seo_benchmarks` rows | 55 |
| Distinct benchmark niches | 10 |
| Core-service cells present | 28/48 |
| Core-service cells usable at `sample_size_metros >= 8` | 0/48 |
| Core-service cells missing | 20/48 |
| Present core-service cells below sample threshold | 28/28 |
| Present core-service low-confidence cells | 6 |
| Present core-service insufficient cells | 22 |
| Latest benchmark recompute timestamp | 2026-05-17T19:44:17.682542+00:00 |

All present cells are below the production usability floor. Sample sizes across all 55 benchmark rows are: 21 cells at `n=1`, 22 cells at `n=2`, 11 cells at `n=3`, and 1 cell at `n=4`. There are no `medium` or `high` confidence cells.

### Core-Service Cell Matrix

Cell format: `sample_size_metros / confidence`. `missing` means no benchmark row exists for the core service alias and population class.

| Service | `micro_under_50k` | `small_50_100k` | `medium_100_300k` | `large_300k_1m` | `metro_1m_5m` | `mega_5m_plus` |
| --- | --- | --- | --- | --- | --- | --- |
| `roofing` | 1 / insufficient | 2 / insufficient | 2 / insufficient | 1 / insufficient | 2 / insufficient | 1 / insufficient |
| `plumbing` | 1 / insufficient | 1 / insufficient | 1 / insufficient | 1 / insufficient | 3 / low | 2 / insufficient |
| `hvac` | missing | missing | missing | missing | missing | missing |
| `tree service` | missing | missing | missing | missing | missing | missing |
| `auto repair` | 1 / insufficient | 2 / insufficient | 4 / low | 3 / low | 3 / low | 2 / insufficient |
| `water damage restoration` | 1 / insufficient | 2 / insufficient | 3 / low | missing | 1 / insufficient | 1 / insufficient |
| `electrician` | missing | missing | missing | missing | missing | missing |
| `locksmith` | missing | 2 / insufficient | 2 / insufficient | 3 / low | 2 / insufficient | 1 / insufficient |

### Metric-Level Usability

| Metric group | Current state | Production policy |
| --- | --- | --- |
| Demand volume/CPC | Values exist in many present cells, but every cell is below `sample_size_metros >= 8`. | Warning-only until each target cell or approved pooled cell reaches the sample floor. |
| Organic aggregator/local-business counts | Values exist in present cells, but every cell is below the sample floor. | Warning-only; do not treat as benchmark-reliable. |
| Local review count and review velocity | `median_top3_review_count_min` and `median_top3_review_velocity` are null in all 28 present core-service cells. | Requires acquisition/backfill before local difficulty benchmarking. |
| Monetization density/ads/LSA | Values exist in present cells, but every cell is below the sample floor. | Warning-only until sample sizes pass; do not recompute scale-out scores from these cells. |
| AI resilience AIO rate | Values exist in present cells, but every cell is below the sample floor. | Warning-only; defer formula decisions to post-acquisition audit. |

### Pooling And Seed Recommendations

Per-class scoring is not production-usable for any core service. If the product accepts pooled city-size classes as a temporary fallback, only one limited grouping clears the sample floor today: `auto repair` across small + medium + large (`n=9`). Everything else remains below threshold and should stay warning-only or receive more benchmark metros.

| Service | Small+medium+large n | Recommendation | Metro+mega n | Recommendation |
| --- | ---: | --- | ---: | --- |
| `roofing` | 5 | Add 3 class-pooled metros or keep warning-only | 3 | Add 5 metro/mega metros or keep warning-only |
| `plumbing` | 3 | Add 5 class-pooled metros or keep warning-only | 5 | Add 3 metro/mega metros or keep warning-only |
| `hvac` | 0 | Add 8 class-pooled metros or keep warning-only | 0 | Add 8 metro/mega metros or keep warning-only |
| `tree service` | 0 | Add 8 class-pooled metros or keep warning-only | 0 | Add 8 metro/mega metros or keep warning-only |
| `auto repair` | 9 | Pooled small/medium/large cell is usable if pooling is approved | 5 | Add 3 metro/mega metros or keep warning-only |
| `water damage restoration` | 5 | Add 3 class-pooled metros or keep warning-only | 2 | Add 6 metro/mega metros or keep warning-only |
| `electrician` | 0 | Add 8 class-pooled metros or keep warning-only | 0 | Add 8 metro/mega metros or keep warning-only |
| `locksmith` | 7 | Add 1 class-pooled metro or keep warning-only | 3 | Add 5 metro/mega metros or keep warning-only |

Concrete routing:

1. Add more metros for missing core services first: `hvac`, `tree service`, and `electrician` have 0/6 benchmark cells.
2. Backfill missing cells for `water damage restoration` large and `locksmith` micro before treating those services as class-complete.
3. Keep metro and mega buckets warning-only unless a follow-up explicitly approves pooling and adds at least 3 to 8 more metro/mega benchmark metros per service.
4. Keep local difficulty benchmark-gated until review count and review velocity medians are populated; sample size alone will not fix local difficulty because the current median fields are null.
5. Do not mark any benchmark cell usable in app or scoring logic until `sample_size_metros >= 8`; current `low` cells remain non-production.

## App Surface Visibility

| Measure | Result |
| --- | ---: |
| `explore_market_cells` rows in inventory | 131,835 |
| `metro_score_v2` rows in inventory | 114 |
| `seo_facts` rows in inventory | 8,315 |
| Pilot rows visible in Explore | 10/96 |
| Audit universe pairs missing V2 score | 7,368 |
| Audit universe legacy Explore fallback pairs | 7,388 |
| Audit universe missing Explore rows | 0 |
| Legacy-only pairs | 93 |

Explore has broad catalog/read-model coverage, but not enough V2-backed visibility for the scoring-hardening goal. The app can show many city-service rows through legacy or fallback paths, yet only a narrow slice has the V2 score and benchmark confidence metadata needed for the new scoring surface.

## Recommendations

1. Keep the scoring runner path accepted. The 96/96 pilot validates API health, production project guardrails, target identity, and V2 persistence checks.
2. Do not run benchmark recompute yet. The benchmark usability gate is 0/48 at `sample_size_metros >= 8`.
3. Run only the smallest approved acquisition/backfill batch for missing DA/Lighthouse telemetry, local review velocity, and benchmark cells. Use the WHI-102 opt-in flags added in PR #81; keep preflight free of those paid add-ons.
4. Route WHI-104 to benchmark-cell sufficiency. The first question is which service x population cells can reach sample size 8 with the least paid work.
5. Route WHI-105 to app visibility. After benchmark and V2 facts improve, verify Explore/report surfaces prefer V2 rows and expose benchmark confidence without legacy-only fallbacks hiding the gap.
6. Defer scoring-framework changes to WHI-106. Formula changes should be based on a rerun of the read-only audits after data acquisition, not on this failing audit alone.
