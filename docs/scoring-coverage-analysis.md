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
