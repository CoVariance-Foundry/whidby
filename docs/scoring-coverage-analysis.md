# Scoring Coverage Analysis

Linear: `WHI-103`, `WHI-104`, `WHI-105`

Source artifacts:

- `reports/scoring_audit/coverage_micro.jsonl`
- `reports/scoring_audit/coverage_small.jsonl`
- `reports/scoring_audit/coverage_medium.jsonl`
- `reports/scoring_audit/coverage_large.jsonl`
- `reports/scoring_audit/coverage_metro.jsonl`
- `reports/scoring_audit/coverage_mega.jsonl`
- `reports/scoring_audit/scoring_audit_20260523T154926Z.json`
- `reports/scoring_audit/scoring_audit_20260523T154926Z.md`
- `reports/scoring_audit/scoring_audit_20260524T040729Z.json`
- `reports/scoring_audit/scoring_audit_20260524T040729Z.md`

The artifacts above are generated audit outputs and remain ignored by git. This document records the durable analysis that should travel with the repo.

## Executive Summary

The coverage pilot proved the guarded production scoring path, but it did not prove that the current data is ready for broader seed expansion or benchmark recompute.

The bounded 12 metro x 8 service pilot completed with 96 successful API and persistence outcomes, 0 partial failures, and 0 failures. Every pilot row persisted through the V2 scoring path, and every row used the production project guard, DFS-ready metro targeting, V2 persistence checks, and the production API.

The follow-up scoring audit still failed. The failure is not API/runtime health; it is evidence sufficiency. Benchmark cells are not usable at the canonical `sample_size_metros >= 8` threshold, top-5 DA and Lighthouse telemetry are absent, local difficulty inputs are missing, and app-surface V2 visibility is too sparse for a scale-out seed.

The WHI-105 app-surface pass confirms the same shape from the product side. Explore has materialized catalog rows for all 3,208 current audit pairs, and sampled production report-detail API lookups resolve, but only 64 pairs are V2-preferred in Explore and only 110 pairs have any report-backed detail row. The hidden-row cause is coverage, not routing: most rows have no V2 score/report lineage yet, and legacy/catalog fallback rows can still mask that gap in the UI.

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
| 2026-05-24 04:07 UTC | `audit_scoring_strategy` reran the WHI-105 app-surface verification with the 96 pilot artifacts | Exited `fail` because V2/report-backed Explore visibility is still sparse despite 96/96 pilot success |

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

## Benchmark Development Research: Phase 1 Map

Linear research plan: `https://linear.app/covariancestudio/document/benchmark-development-research-plan-32e613154242`

Phase 1 maps the benchmark plan already encoded in the repo before comparing it with external SEO benchmark structures.

### Current Architecture

| Layer | Current contract |
| --- | --- |
| Collection input | DataForSEO-backed scoring and acquisition runners produce keyword, SERP, map-pack, review, backlink, and Lighthouse observations under guarded production project checks. |
| Fact grain | `seo_facts` stores keyword-grain observations by `niche_normalized`, `cbsa_code`, `keyword`, and `snapshot_date`. Missing local, organic, review, DA, and Lighthouse values remain nullable evidence gaps. |
| Metro context | `metros.population_class`, `metros.population`, and verified native `metros.dataforseo_location_codes` define eligible metro targeting and benchmark city-size buckets. |
| Business-density context | `census_cbp_establishments` joins through `niche_naics_mapping` to produce weighted establishments per 100,000 residents for monetization benchmarks. |
| Benchmark recompute | `recompute_seo_benchmarks(p_window_days)` reads recent transactional/commercial `seo_facts`, rolls them up by metro, computes percentile and median statistics by `niche_normalized` and `population_class`, then upserts `seo_benchmarks`. |
| Scoring read boundary | V2 scoring consumes benchmark cells through `SeoBenchmarkRepository`; formulas should not query Supabase directly. |
| Persisted scoring output | `metro_score_v2` records benchmark population class, confidence, sample size, warning flags, and score vectors for report and Explore surfaces. |
| App visibility | Explore/report read models should prefer V2 rows and expose benchmark confidence while preserving legacy fallback until V2 coverage is sufficient. |

### Current Benchmark Cell Contract

| Dimension | Contract |
| --- | --- |
| Cell key | `niche_normalized + population_class` |
| Core matrix | 8 services x 6 population classes = 48 required cells |
| Current usability threshold | `sample_size_metros >= 8` |
| Confidence labels | `<3` insufficient, `3-7` low, `8-19` medium, `20+` high |
| Fact window | Recompute defaults to a 90-day window unless the runner passes a different value |
| Demand metrics | Per-capita search volume and average CPC percentiles |
| Local metrics | Local-pack rate, median top-3 review-count floor, and median top-3 review velocity |
| Organic metrics | Median top-10 aggregator count and local-business count; top-5 DA/Lighthouse are still telemetry gaps in this snapshot |
| Monetization metrics | Weighted CBP establishments per 100,000 residents plus ads and LSA rates |
| AI resilience metrics | Median AIO trigger rate |

The current schema has cell-level `sample_size_metros` and `sample_size_observations`, but it does not expose metric-specific sample counts for review velocity, review count, DA, Lighthouse, organic target extraction, ads, LSA, or AIO. That means a cell can reach the metro-count threshold while still lacking the evidence needed for a specific score dimension.

### Current Gate Sequence

| Gate | Purpose | Current state |
| --- | --- | --- |
| Schema/project guard | Prevent writes to the wrong Supabase project or stale schema | Required for production runners |
| DFS readiness | Include only metros with verified native DataForSEO location codes | Required for paid scoring samples |
| Canary | Prove one city-service pair persists report, legacy score, V2 score, facts, and Explore row | Passed after PR #78 target-identity fix |
| 12x8 pilot | Prove guarded production scoring path across 12 metros and 8 services | Passed 96/96 with 0 partials and 0 failures |
| Read-only audits | Measure benchmark, component, and app-surface sufficiency | Still failing |
| Benchmark recompute | Rebuild `seo_benchmarks` from accepted facts | Not authorized until audit gates improve |
| Explore cache validation | Confirm seeded rows surface through V2-preferred app paths | Pending stronger V2/benchmark coverage |
| 50x16 seed | Broader production seed | Blocked by benchmark and app-surface sufficiency |

### Phase 1 Findings

| Finding | Implication for benchmark development |
| --- | --- |
| Core benchmark usability is 0/48. | The benchmark layer cannot yet support recompute-backed scale-out scoring for any core service/population cell. |
| 20/48 core cells are missing entirely. | Acquisition must first create cells for missing services/classes, especially `hvac`, `tree service`, and `electrician`. |
| 28/48 core cells exist but are below sample threshold. | Existing rows explain low confidence but are not production-usable. |
| Local review medians are null across present core cells. | Sample size alone cannot unlock local difficulty; review count and velocity acquisition are required. |
| DA/Lighthouse telemetry remains absent. | Organic authority/site-quality evidence should remain telemetry-only until acquisition populates coverage. |
| Pooling is not yet formalized. | Temporary pooled city-size fallbacks require an explicit policy before scoring or UI can rely on them. |
| Confidence is too coarse. | External benchmark research should focus on separating cell confidence from metric-specific confidence. |

Phase 2 should compare this plan against external SEO benchmark structures and return with concrete updates for metric-level sufficiency, pooling policy, source lineage, and acquisition priority.

## Benchmark Development Research: Phase 2 Comparables

Phase 2 researched comparable SEO benchmark structures on 2026-05-24. The goal was to identify how established tools define benchmark grain, combine evidence, express confidence or limitations, and turn raw data into product guidance.

### Comparable Benchmark Patterns

| Source | Benchmark structure | Useful pattern for Whidby |
| --- | --- | --- |
| [Ahrefs Keyword Difficulty](https://ahrefs.com/keyword-difficulty) | Keyword-level 0-100 difficulty score based on referring domains across the top 10 organic ranking pages. The score maps to an estimated referring-domain need, excludes on-page factors, and is recommended as a first filter before detailed SERP analysis. | Keep organic difficulty evidence SERP-relative. Do not represent top-5 DA, backlinks, or Lighthouse telemetry as complete competition truth; expose them as one dimension that still needs SERP/context review. |
| [Semrush Keyword Difficulty](https://www.semrush.com/kb/1158-what-is-kd) | Keyword-level 0-100 effort estimate using multiple top-10 SERP factors: median referring domains, dofollow/nofollow ratio, authority score, and SERP qualities. It converts score bands into guidance such as easy, possible, difficult, hard, and very hard. | Add metric-specific inputs before guidance. Whidby should separate raw evidence, normalized benchmark score, and user-facing effort label rather than letting one confidence label carry every dimension. |
| [Moz Authority Scoring Guide](https://moz-static.s3.amazonaws.com/products/landing-pages/announcements/Authority_Scoring_Guide.pdf) | Domain Authority is a 0-100 comparative score built from link-index evidence and a model that changes as Moz updates its link data and scoring calculation. Moz frames authority as comparative, not absolute. | Version benchmark recomputes and formulas. Treat benchmark scores as relative to the peer universe, not objective market quality, and preserve enough lineage to compare current values only against compatible benchmark versions. |
| [SISTRIX Visibility Index](https://www.sistrix.com/visibility-index/calculation) | Domain visibility benchmark built from a representative keyword set, organic rankings, search volume weighting, click-probability weighting, and summed visibility values. It emphasizes transparent, stable calculation and supports custom project indexes for narrow niches/local tracking. | Formalize Whidby's sample frame. Local service benchmarks need explicit service, metro, keyword, and population-class coverage rules so future recomputes compare like with like. Add weighting policy before any city-size pooling. |
| [Google local ranking guidance](https://support.google.com/business/answer/7091?hl=en) and [Whitespark local factors](https://whitespark.ca/blog/7-local-search-ranking-factors-that-may-challenge-your-current-thinking/) | Local visibility depends on relevance, distance, and prominence; review count/rating, review recency, business information completeness, hours, citations, and local-pack behavior are important local evidence. | Local difficulty must stay independent from organic difficulty. Review count and velocity are not optional for local-pack benchmarking, and `cid`/`place_id` lineage should be first-class for repeatable review acquisition. |

### Common Structure Across Benchmarks

| Pattern | Observed in comparables | Gap in current Whidby plan |
| --- | --- | --- |
| Defined grain | Ahrefs/Semrush use keyword + SERP; SISTRIX uses domain + keyword set + ranking; Moz uses domain/page authority; local search uses business + geography. | Whidby has a clear cell grain, but it still needs metric-grain sufficiency inside each cell. |
| Evidence-specific scoring | Semrush combines backlink, authority, and SERP qualities; SISTRIX weights rank by volume and click probability; local SEO separates reviews, prominence, and relevance. | `seo_benchmarks` has one cell confidence label even when local, organic, and demand evidence coverage differ sharply. |
| Comparative interpretation | Moz explicitly frames authority as comparative; SISTRIX recommends competitor comparison; Ahrefs recommends SERP analysis after KD filtering. | Whidby explanations should say "relative to this service/population benchmark version" instead of implying absolute market truth. |
| Transparent limitations | Ahrefs states KD excludes on-page factors; SISTRIX documents small-niche limitations and custom indexes; Google states local rank cannot be bought/requested. | Whidby needs product-visible warnings for sparse cells, missing metric evidence, pooled fallbacks, and unsupported local signals. |
| Stable/versioned calculation | Moz discusses score changes when link index or scoring models change; SISTRIX emphasizes calculation stability for historical comparison. | Whidby recomputes should carry formula version, source window, acquisition flags, and sample-frame version. |

### Phase 2 Findings

| Finding | Impact on Whidby benchmark development |
| --- | --- |
| Established SEO difficulty tools are SERP-relative, not market-cell-relative. | Whidby's market-cell benchmark is differentiated, but it needs clearer SERP evidence lineage so users can understand what part of difficulty is organic SERP competition versus local-market structure. |
| Multi-factor benchmarks still preserve dimension limits. | Whidby should not unlock a whole cell just because `sample_size_metros >= 8`; each score dimension needs its own sufficiency gate. |
| Comparable scores are best used as filters or comparative guides. | Whidby should keep low-confidence scores available with warnings, but block recompute-backed expansion and hard product claims until metric-specific gates pass. |
| Authority and visibility scores depend on data-version stability. | Benchmark recomputes need versioned lineage before they become durable customer-facing benchmarks. |
| Local SEO benchmarks require local-specific evidence. | Review velocity, review count, stable place identifiers, GBP/business completeness signals, and local-pack presence should be first-class local inputs, not optional add-ons hidden under a generic confidence label. |
| Narrow-niche/local indexes need custom sample frames. | Whidby should explicitly define a benchmark sample frame per service and population class, then document any pooled fallback as a separate benchmark type. |

### Phase 2 Recommendations

1. Add metric-specific sufficiency fields or a companion benchmark metric table before treating `seo_benchmarks` as production-complete.
2. Split benchmark confidence into at least demand, organic, local, monetization, and AI-resilience confidence; keep the current cell confidence as a rollup only.
3. Store benchmark lineage: formula version, source window, acquisition flags, sample-frame version, data source mix, and recompute timestamp.
4. Define pooling as an explicit benchmark mode with its own key and warnings, not an implicit fallback inside `niche_normalized + population_class`.
5. Add local-place lineage for review acquisition: preserve `cid`, `place_id`, source query, rank, and collected review window for top local-pack businesses.
6. Preserve raw SERP/local/review evidence separately from normalized benchmark scores so future formulas can be recalibrated without rerunning all paid collection.
7. Update product copy and scoring explanations to frame benchmarks as relative to a peer set and evidence window.

Phase 3 should catalog active SEO data APIs against these required evidence fields, with special attention to DataForSEO endpoint coverage, identifier stability, costs, and which fields can populate metric-level sample counts.

## Benchmark Development Research: Phase 3 SEO API Catalog

Phase 3 cataloged active SEO data APIs on 2026-05-24. The catalog combines the current Whidby client surface in `src/clients/dataforseo/endpoints.py`, `src/clients/dataforseo/client.py`, and `src/research_agent/tools/api_tools.py` with current DataForSEO documentation. Cost values below are local repo estimates; refresh live vendor pricing before any paid acquisition batch.

### Current Whidby API Surface

| Local endpoint constant | Local method/tool | DataForSEO path | Mode | Local estimated cost | Current benchmark role |
| --- | --- | --- | --- | ---: | --- |
| `SERP_ORGANIC` | `serp_organic`, `fetch_serp_organic` | `serp/google/organic/live/advanced` | Live | 0.002 | Organic SERP composition, top organic targets, ads/SERP-feature context, AIO presence where returned in SERP items. |
| `SERP_MAPS` | `serp_maps`, `fetch_serp_maps` | `serp/google/maps/live/advanced` | Live | 0.002 | Local-pack rank, rating, review count, `cid`, `place_id`, category, claimed/listing metadata. |
| `KEYWORD_VOLUME` | `keyword_volume`, `fetch_keyword_volume` | `keywords_data/google/search_volume/task_post` | Queued | 0.05 | Demand volume and CPC for selected keyword set. |
| `KEYWORD_SUGGESTIONS` | `keyword_suggestions`, `fetch_keyword_suggestions` | `dataforseo_labs/google/keyword_suggestions/live` | Live | 0.05 | Keyword expansion and long-tail discovery. |
| `BUSINESS_LISTINGS` | `business_listings`, `fetch_business_listings` | `business_data/business_listings/search/live` | Live | 0.01 | Supplemental local-business inventory, listing/domain/rating fields; not the canonical density source. |
| `GOOGLE_MY_BUSINESS_INFO` | `google_my_business_info` | `business_data/google/my_business_info/live` | Live | 0.004 | Business profile detail lookup by establishment name, `cid`, or `place_id`; currently not exposed through the research-agent plugin. |
| `GOOGLE_REVIEWS` | `google_reviews`, `fetch_google_reviews` | `business_data/google/reviews/task_post` | Queued | 0.005 | Review timestamps and review velocity; runner supports `cid`, `place_id`, and `sort_by=newest`. |
| `BACKLINKS_SUMMARY` | `backlinks_summary`, `fetch_backlinks_summary` | `backlinks/summary/live` | Live | 0.002 | Domain/page authority telemetry for top organic targets; runner requests `rank_scale=one_hundred`. |
| `LIGHTHOUSE` | `lighthouse`, `fetch_lighthouse` | `on_page/lighthouse/live` | Live | 0.006 | Page/site quality telemetry for top organic targets. |
| `LIGHTHOUSE_QUEUED` | batch helper only | `on_page/lighthouse/task_post` | Queued | 0.002 | Lower-cost Lighthouse acquisition option; not the default runner path. |
| `LOCATIONS` | `locations` | `serp/google/locations` | Live | 0.000 | DataForSEO location-code discovery/verification. |
| `GOOGLE_TRENDS` | `google_trends` | `keywords_data/google_trends/explore/live` | Live | 0.05 | Seasonality/trend shape for up to five keywords; currently used through the trends adapter, not benchmark recompute. |

DataForSEO also documents Google Ads Search Volume and Google Keyword Overview endpoints that overlap with Whidby's current demand source. The current Whidby path remains valid, but Phase 4 should decide whether to keep `keywords_data/google/search_volume/*` as canonical demand or migrate/augment with Google Ads Search Volume / Keyword Overview for richer `competition`, bid, monthly-search, intent, and update-timestamp fields.

### API-To-Benchmark Evidence Map

| Benchmark dimension | Active source | Key upstream fields | Repeatable identifier/provenance | Metric-level sample counts to derive |
| --- | --- | --- | --- | --- |
| Demand volume/CPC | DataForSEO Keywords Data Search Volume; candidate upgrade/augment from Google Ads Search Volume or Keyword Overview | keyword, `search_volume`, `cpc`, `competition`, `competition_level`, `monthly_searches`, `last_updated_time` where available | keyword, `location_code`, `language_code`, endpoint path, source window/month, keyword-intent class | `sample_size_keywords`, `sample_size_volume_non_null`, `sample_size_cpc_non_null`, `sample_size_monthly_searches_non_null` |
| Keyword expansion | DataForSEO Labs Keyword Suggestions and Keyword Overview | suggested keyword, volume trend, CPC, paid competition, search intent, SERP/backlink info where available | seed keyword, location/language, suggestion endpoint, returned keyword, extraction timestamp | `sample_size_suggestions`, `sample_size_intent_labeled`, `sample_size_expanded_keywords_used` |
| Organic SERP composition | DataForSEO Google Organic SERP Advanced | item type, `rank_group`, `rank_absolute`, title, URL, domain, SERP features, ads/local-pack/AIO item types | keyword, `location_code`, depth, device/language if configured, SERP datetime | `sample_size_serp_keywords`, `sample_size_top10_organic`, `sample_size_serp_features`, `sample_size_aio_observed` |
| Organic authority | DataForSEO Backlinks Summary with `rank_scale=one_hundred` | rank/domain-rank fields, backlinks, referring domains, page/domain summary fields | organic URL/domain from SERP, rank scale, endpoint path, collection timestamp | `sample_size_top5_da_attempted`, `sample_size_top5_da_non_null`, `sample_size_referring_domains_non_null` |
| Organic site quality | DataForSEO OnPage Lighthouse | performance score, SEO score, accessibility/best-practices categories, individual audits, Lighthouse version | canonical URL, device mode, Lighthouse version, endpoint mode, collection timestamp | `sample_size_top5_lighthouse_attempted`, `sample_size_top5_lighthouse_non_null`, `sample_size_lighthouse_versioned` |
| Local-pack difficulty | DataForSEO Maps Live Advanced | `rank_group`, `rank_absolute`, rating value, `votes_count`, `rating_distribution`, category, `cid`, `place_id`, claimed/listing flags | keyword, `location_code`, local-pack rank, `cid`, `place_id`, collection timestamp | `sample_size_local_pack_keywords`, `sample_size_top3_review_count_non_null`, `sample_size_local_identifiers_non_null` |
| Review velocity | DataForSEO Google Reviews | review timestamp/date, rating, review text/id/profile fields; supports `keyword`, `cid`, or `place_id`; supports `sort_by=newest` | `cid` or `place_id` first, fallback title keyword, `location_code`, sort, depth, review window | `sample_size_review_velocity_attempted`, `sample_size_review_velocity_non_null`, `sample_size_reviews_timestamped` |
| Business profile completeness | DataForSEO Google My Business Info, Business Listings | category, address, phone, URL/domain, images/photos, rating distribution, work hours, claimed/open status where returned | `cid`, `place_id`, category, location, source endpoint | `sample_size_gbp_profiles`, `sample_size_profiles_with_domain`, `sample_size_profiles_with_hours`, `sample_size_profiles_with_phone` |
| Monetization density | Census CBP remains canonical; DataForSEO Business Listings is supplemental | CBP establishments per NAICS/CBSA; DFS business count/listing quality can provide live market texture | CBSA, NAICS mapping version, CBP year; optional DFS category/location provenance | `sample_size_cbp_metros`, `sample_size_dfs_listings_non_null` |
| AI resilience / SERP displacement | Current SERP Advanced item types; candidate DataForSEO AI Optimization/LLM APIs for future work | AIO/AI Overview item presence, PAA, ads, local services, SERP feature mix; possible LLM mention/domain metrics if adopted later | keyword, location, SERP datetime, model/provider if LLM APIs are used | `sample_size_aio_observed`, `sample_size_serp_feature_keywords`, future `sample_size_llm_mentions` |

### Catalog Findings

| Finding | Implication |
| --- | --- |
| DataForSEO covers every currently required SEO evidence family, but Whidby uses different surfaces for demand, SERP, local, review, backlink, Lighthouse, trends, and listings. | Benchmark recompute needs source lineage per metric, not just one cell timestamp. |
| Stable local identifiers are available in Maps and Reviews through `cid` and `place_id`. | `seo_facts` or a companion evidence table should preserve these identifiers for top local-pack businesses before review velocity becomes benchmark-critical. |
| The acquisition runner already uses the richer review/backlink client paths (`cid`/`place_id`, `sort_by=newest`, `rank_scale=one_hundred`), but the research-agent plugin/tool wrappers still expose keyword-only reviews and no backlink `rank_scale` option. | If agent-driven acquisition becomes part of the workflow, update the plugin schema and `api_tools.py` so it cannot silently collect lower-quality evidence than `run_pilot.py`. |
| Current benchmark schema can store aggregate values but cannot prove per-metric evidence sufficiency. | Add metric-level sample counters or a benchmark-metric child table before enabling recompute-backed product claims. |
| Demand collection should decide between the current `keywords_data/google/search_volume/*` path and the newer/richer Google Ads Search Volume or Keyword Overview surfaces. | Phase 4 should specify the canonical demand endpoint, migration risk, and whether to store both legacy and enriched demand metadata during transition. |
| Business Listings and Google My Business Info are useful for local/GBP completeness, but CBP should remain canonical for establishment density. | Keep live business-listing counts as supplemental evidence rather than replacing census-backed monetization density. |
| Lighthouse is a page-quality audit, not an organic authority metric. | Keep Lighthouse separate from DA/backlink authority in metric-level confidence and explanations. |
| DataForSEO now documents broader AI/LLM/AI Optimization endpoints, but Whidby does not currently wrap them. | Keep current AI resilience based on SERP features until a separate Linear slice approves LLM/AI-search acquisition costs and schema. |

### Phase 3 Storage Requirements

The benchmark/data-collection update should be able to persist or derive the following for each paid evidence source:

1. Source endpoint path and mode (`live` or `standard`).
2. Request parameters that affect comparability: keyword, `location_code`, language, depth, device, sort, rank scale, Lighthouse version, and source window.
3. Stable entity identifiers: organic URL/domain for top-5 organic targets; `cid` and `place_id` for top local-pack targets.
4. Collection timestamp and upstream result datetime.
5. Cost and cache status from the DataForSEO client.
6. Metric-specific attempted/non-null counts.
7. Per-metric confidence labels that roll up into, but do not get hidden by, `seo_benchmarks.confidence_label`.

Phase 4 should turn these catalog gaps into required benchmark/data-model changes: canonical demand source decision, metric-level sufficiency schema, local-place lineage, raw evidence retention, agent tool parity, and paid acquisition guardrails.

## Benchmark Development Research: Stage 4 Gap Analysis

Stage 4 converts the Phase 1-3 research into platform and data-model gaps. This review includes the Strategy Discovery plan in `docs/superpowers/plans/2026-05-16-strategy-discovery-system.md` because strategy surfaces are downstream consumers of the same cached market intelligence. Strategy Discovery is intentionally a set of ranking lenses over canonical facts and benchmarks, not a separate scoring engine, so weak benchmark lineage becomes weak product guidance.

### Strategy Platform Needs

| Strategy/platform surface | Required evidence | Current risk |
| --- | --- | --- |
| Easy Win | Demand strength, organic difficulty, local difficulty, AI resilience, and benchmark confidence. | A single cell confidence label can hide which score dimensions are actually missing or stale. |
| GBP Blitz | Local-pack presence, top-3 review floor, review velocity, GBP/profile completeness, ratings, and stable local business identity. | Current core benchmark cells have null local review medians, and the strategy evidence table lacks stable `cid`/`place_id` lineage for repeat review acquisition. |
| Keyword Hijack | Primary keyword volume, CPC/commercial intent, local-pack presence, and exact-match GBP name availability. | Demand source is not yet canonicalized across DataForSEO keyword surfaces, and local name availability depends on local-pack evidence that is not sufficiently versioned. |
| Expand & Conquer | Metro feature vectors plus equal-or-lower organic and local competition versus a reference city. | `metro_feature_vectors` can rank similarity, but the competition baseline is only as reliable as the benchmark and V2 fact coverage behind each candidate. |
| `/agency` multi-market runs | Cached target discovery, batch caps, fresh-run lineage, and explicit target-level warnings. | Sparse benchmark cells can make broad target discovery appear complete while the underlying metric evidence is insufficient. |
| Strategy cache and run items | Source report ids, scored timestamps, evidence JSON, warnings, and strategy id. | The cache/run schema can store warnings but does not currently require benchmark version, metric sufficiency, pooling mode, or raw evidence lineage. |

### Gap Matrix

| Gap | Current state | Why it matters | Required update |
| --- | --- | --- | --- |
| Metric-level sufficiency | `seo_benchmarks.confidence_label` is a cell rollup; present cells can still have missing DA, Lighthouse, local review, or demand evidence. | Strategy scores need to distinguish weak markets from unknown markets. | Add metric-specific sufficiency fields or a child table keyed by benchmark cell, metric family, source window, attempted count, non-null count, and confidence label. |
| Demand source ambiguity | Whidby currently uses `keywords_data/google/search_volume/*`; DataForSEO also offers richer Google Ads Search Volume and Keyword Overview surfaces. | Keyword Hijack and demand scoring should not mix incompatible volume, CPC, competition, and intent semantics. | Choose the canonical demand endpoint before paid scale-out, then store endpoint path, source month/window, `location_code`, language, volume, CPC, competition, and monthly-search metadata. |
| Local-place lineage | Maps and Reviews can use stable `cid` and `place_id`, but `local_pack_listing_facts` is centered on rank, name, and keyword evidence. | GBP Blitz, Keyword Hijack, Competitor Intel, and review velocity refreshes need repeatable business identity, not title matching. | Persist `cid`, `place_id`, source query, DataForSEO `location_code`, listing URL/domain, review collection window, and review retrieval mode for top local-pack businesses. |
| Raw evidence retention | Benchmark aggregates are stored, but raw SERP, local-pack, review, backlink, and Lighthouse evidence is not a first-class benchmark recompute artifact. | Future formula/version changes should not require rerunning all paid collection. | Add or reuse an evidence-artifact layer with provider endpoint, request hash, response hash/location, collection timestamp, cache status, cost, and benchmark run id. |
| Benchmark versioning | Existing timestamps do not fully encode formula version, sample frame, source mix, acquisition flags, or pooling policy. | Moz/SISTRIX-style comparative scores are only comparable within a known data and formula universe. | Add `benchmark_run_id`, formula version, sample-frame version, source window, acquisition flags, and source mix to benchmark outputs and downstream strategy cache rows. |
| Pooling policy | The only possible current pooled core grouping is ad hoc; pooling is not represented as its own benchmark mode. | Hidden pooling can make a city-size-specific strategy recommendation look more precise than it is. | Define explicit benchmark modes such as `cell`, `pooled_adjacent_population`, and `service_family`, with product-visible warning codes and separate cache keys. |
| Agent tool parity | `run_pilot.py` supports richer review/backlink collection than the research-agent API wrappers. | Agent-driven acquisition can silently collect lower-quality evidence than the benchmark runner. | Expose review `cid`/`place_id`/`sort_by`, backlink `rank_scale`, queued task retrieval, and source-cost metadata through `DataForSEOPlugin` and `api_tools.py`. |
| Strategy warning semantics | Strategy results carry warning arrays, but benchmark warnings are mostly coarse strings such as low confidence or missing local pack. | Product surfaces need actionable warning copy: missing demand, missing local reviews, stale facts, pooled benchmark, or benchmark undersampled. | Standardize warning codes by metric family and make Explore, Reports, Strategies, and `/agency` render the same evidence-quality vocabulary. |
| Feature-vector readiness | `metro_feature_vectors` supports Expand & Conquer, but vector quality depends on source tables and feature completeness. | Similarity ranking can look authoritative even when candidate/reference competition data is sparse. | Version feature vectors with source tables, feature completeness, computed timestamp, and reference benchmark readiness before using them as paid-run targets. |
| Paid acquisition gates | Prior slices require canary and pilot gates, but Stage 4 gaps imply a more granular acquisition order. | The smallest useful paid work should fill the missing metric family that blocks product decisions, not just add more rows. | Keep no broad paid recompute. Sequence paid work as canary metric acquisition, metric-sufficiency audit, bounded cell backfill, then benchmark recompute only after read-only gates pass. |

### Required Platform Updates

1. Data model: add benchmark run/version lineage, metric-level sufficiency, local-place identifiers, raw evidence artifacts, pooling mode, and downstream strategy cache lineage.
2. Data collection: canonicalize demand collection, preserve local identifiers from Maps before Reviews, collect review velocity by `cid`/`place_id`, keep Backlinks Summary on `rank_scale=one_hundred`, and store Lighthouse separately from authority.
3. Strategy platform: treat benchmark confidence as structured evidence quality, not a single badge. Strategy results should know whether a score is weak because the market is easy or because demand/local/organic evidence is missing.
4. Product surfaces: reuse the same warning vocabulary across Explore, report detail, strategy gallery/detail pages, and `/agency` target review so sparse benchmark cells cannot be mistaken for completed market intelligence.
5. Guardrails: continue to block broad paid expansion and benchmark recompute until the read-only audits show usable metric-level coverage for the intended benchmark universe.

Stage 5 should turn these gaps into an implementation recommendation: schema changes first, then runner/tool parity, then the smallest paid acquisition batch needed to raise core-service cells above metric-level sufficiency thresholds.

## Benchmark Development Research: Stage 5 Recommendations

Stage 5 recommends updating the benchmark approach as a data contract upgrade before buying more coverage. The main change is to stop treating a benchmark cell as one all-or-nothing aggregate and instead make every downstream product surface read the same metric-level sufficiency, source lineage, and warning vocabulary.

### Recommended Implementation Sequence

| Step | Recommendation | Why this comes first | Acceptance signal |
| --- | --- | --- | --- |
| 1 | Add benchmark run and metric-sufficiency schema before recompute changes. | The current `seo_benchmarks` primary key can store aggregate values, but not enough provenance to explain or compare them later. | Every benchmark row can point to a benchmark run/version and every metric family has attempted/non-null counts, confidence, and source window. |
| 2 | Preserve local-place and raw evidence lineage during collection. | Review velocity, GBP Blitz, Keyword Hijack, and Competitor Intel all need stable local business identity before reviews become a benchmark-critical input. | Top local-pack rows preserve `cid`, `place_id`, source query, DataForSEO `location_code`, listing URL/domain, and review collection window. |
| 3 | Freeze demand v1, then canary enriched demand before migration. | Switching demand sources during a sparse benchmark build would make old and new cells hard to compare. | Current `keywords_data/google/search_volume/*` remains `demand_v1`; Google Ads Search Volume or Keyword Overview runs behind an explicit `demand_v2_candidate` source until a comparison audit approves it. |
| 4 | Update runner and agent tool parity before agent-led acquisition. | `run_pilot.py` already has richer review/backlink behavior than the research-agent wrappers. | `DataForSEOPlugin` and `api_tools.py` expose review `cid`/`place_id`/`sort_by`, backlink `rank_scale`, queued result retrieval, endpoint path, cost, and cache status. |
| 5 | Add product warning semantics before broad strategy ranking. | Explore, Reports, Strategies, and `/agency` must interpret sparse evidence the same way. | Shared warning codes distinguish `metric_missing`, `metric_undersampled`, `pooled_benchmark`, `stale_evidence`, `local_identifier_missing`, and `demand_source_candidate`. |
| 6 | Run a paid metric canary, then bounded cell backfill, then recompute. | Paid work should answer the smallest blocking question before expanding coverage. | Read-only audits show metric-level coverage improves for the selected cells before `recompute_seo_benchmarks` becomes eligible. |

### Data Model Updates

| Area | Recommended change | Notes |
| --- | --- | --- |
| Benchmark runs | Add a benchmark-run lineage record with formula version, sample-frame version, source window, source mix, acquisition flags, pooling mode, recompute timestamp, and cost summary. | This can be a new `seo_benchmark_runs` table or equivalent lineage envelope; do not overload `last_recomputed_at` with all version semantics. |
| Metric sufficiency | Add a child table keyed by benchmark cell and metric family: demand, organic SERP, organic authority, Lighthouse/site quality, local pack, review velocity, GBP profile, monetization, and AI/SERP displacement. | Store attempted metros, non-null metros, attempted observations, non-null observations, confidence label, source endpoint, and source window. |
| Benchmark cells | Extend or version `seo_benchmarks` with `benchmark_run_id`, `benchmark_mode`, `formula_version`, `sample_frame_version`, and metric-confidence rollups. | `confidence_label` should remain a rollup, but the product should be able to show the metric-level cause. |
| Local-pack facts | Extend `local_pack_listing_facts` with stable identifiers and request lineage: `cid`, `place_id`, source query, location code, result type, listing URL/domain, review retrieval mode, review window start/end, and upstream result timestamp. | Use `cid`/`place_id` first for review collection; keyword/name matching should be a flagged fallback. |
| Raw evidence | Add or reuse an evidence artifact layer for SERP, Maps, Reviews, Backlinks, Lighthouse, Keyword Volume, and Keyword Overview responses. | Store provider, endpoint path, normalized request params, request hash, response hash or storage pointer, cache status, cost, and collection timestamp. |
| Strategy cache | Add benchmark lineage and metric-confidence summaries to `strategy_score_cache` and strategy run items. | Strategy results should explain whether ranking is based on real weakness or incomplete evidence. |
| Feature vectors | Version `metro_feature_vectors` with source-table versions, feature completeness, and benchmark readiness. | Expand & Conquer should not treat a similarity score as enough when candidate/reference competition data is sparse. |

### Collection Approach Updates

1. Keep the current DataForSEO Search Volume endpoint as canonical `demand_v1` for the next benchmark recompute. Run Google Ads Search Volume or Keyword Overview as `demand_v2_candidate` only in a comparison canary.
2. Collect Maps before Reviews. Persist local-pack `cid` and `place_id`, then collect reviews by stable identifier with `sort_by=newest`; use keyword/title fallback only with an explicit warning.
3. Keep Backlinks Summary on `rank_scale=one_hundred` and store Lighthouse as site-quality evidence, not authority evidence.
4. Preserve request parameters that change comparability: keyword, location code, language, device/depth where applicable, rank scale, sort order, endpoint mode, and source window.
5. Backfill from existing pilot artifacts only into the new lineage fields where the source can be proven. Unknown provenance should stay unknown instead of being inferred.
6. Treat Business Listings and Google My Business Info as supplemental local-profile evidence. CBP remains the canonical monetization density source.

### Paid Acquisition Recommendation

Do not run broad paid expansion yet. The next paid work should be a metric canary with a hard cost cap and an audit gate:

| Paid slice | Scope | Gate |
| --- | --- | --- |
| Metric canary | One or two benchmark cells that already have V2 facts but lack DA/Lighthouse and review velocity. | `audit_signal_coverage` shows non-zero organic authority, Lighthouse, and review-velocity coverage for those cells. |
| Missing-service seed | Small batch for absent core services, especially `hvac`, `tree service`, and `electrician`, across the most product-relevant population classes. | Each selected service/population cell reaches enough non-null metric evidence to classify why it is still blocked or ready. |
| Cell-depth backfill | Bring selected core cells from sample sizes 1-4 toward `sample_size_metros >= 8`. | Metric-level confidence reaches at least medium for demand, organic SERP, local pack/reviews where applicable, and monetization. |
| Benchmark recompute | Run only after the read-only metric-sufficiency audit passes for selected cells. | New `seo_benchmarks` rows carry benchmark run/version lineage and do not hide metric-level insufficiency behind the rollup label. |

### Product And Strategy Recommendation

Strategy Discovery should use benchmark-backed rankings only when required metric families meet the strategy's minimum confidence:

| Strategy surface | Minimum required confidence before normal ranking | Fallback behavior |
| --- | --- | --- |
| Easy Win | Demand, organic SERP, local difficulty if local pack exists, and AI/SERP displacement. | Rank below qualified rows and show missing metric warnings. |
| GBP Blitz | Local pack, review velocity, GBP/profile completeness, and demand. | Show as evidence-needed, not as a low-competition win. |
| Keyword Hijack | Demand v1 plus local-pack/name-availability evidence; enriched demand can be shown only as candidate evidence until approved. | Block high-confidence recommendation if volume, local pack, or exact-match availability is missing. |
| Expand & Conquer | Feature-vector readiness plus candidate/reference organic and local competition sufficiency. | Allow exploration, but block paid target selection when benchmark readiness is incomplete. |
| `/agency` | Target-level warning rollup across the selected strategy's required metrics. | Keep targets selectable only with explicit sparse-evidence warnings and cost-aware confirmation. |

### Immediate Next Work

1. Draft the schema/data-model slice for benchmark run lineage, metric-level sufficiency, local identifiers, and raw evidence artifacts.
2. Update audit scripts to report metric-level sufficiency and strategy-surface readiness, not just cell sample size.
3. Update DataForSEO agent wrappers to match `run_pilot.py` collection quality.
4. Run a no-paid replay/backfill audit against existing artifacts to populate only proven lineage.
5. Approve a small paid metric canary with a cost cap after the schema and audit gates exist.

## App Surface Visibility

Linear: `WHI-105`

Schema source checked before querying:

- `.Codex/databricks-context/` is not present in this repo checkout.
- Supabase schema source is `supabase/migrations/001_core_schema.sql`, `supabase/migrations/010_v2_benchmarks.sql`, and `supabase/migrations/020_explore_market_cells.sql`.
- The live read-only audit selected the documented `reports`, `metro_scores`, `metro_score_v2`, `seo_facts`, `seo_benchmarks`, and `explore_market_cells` columns used by `scripts/explore/audit_scoring_strategy.py`.

WHI-105 verification scope is the current strategy audit universe: 401 medium/large/metro/mega metros x the 8 core services = 3,208 city-service pairs. The six ignored `coverage_*.jsonl` pilot artifacts were included only to confirm the original 96 pilot rows still classify as API/persistence successes.

| Measure | Result |
| --- | ---: |
| Query time | 2026-05-24T04:07:29Z |
| Production project | `eoajvifhbmqmoluiokcj` |
| `explore_market_cells` rows in inventory | 131,835 |
| `metro_score_v2` rows in inventory | 116 |
| `seo_facts` rows in inventory | 8,415 |
| Pilot rows classified as success | 96/96 |
| Audit pairs with a V2 score row | 81/3,208 |
| Audit pairs with benchmark confidence metadata | 81/3,208 |
| Audit pairs with report-backed Explore visibility | 110/3,208 |
| Audit pairs with V2-preferred Explore visibility | 64/3,208 |
| Audit pairs missing V2 score | 3,127/3,208 |
| Audit pairs using non-V2 Explore fallback or catalog-only rows | 3,144/3,208 |
| Audit pairs missing materialized Explore rows | 0/3,208 |
| Legacy-only pairs | 93 |

Report-detail lookup is not the blocker for rows that already carry report lineage. After collapsing Explore rows with the same normalized city-service key used by the audit, all 110 unique report-backed `report_id` values resolved to `reports` rows. A five-report production smoke check against `GET https://whidby-1.onrender.com/api/niches/{report_id}` returned HTTP 200 for every sampled report, with a matching `report_id` and a `metros` array in the API response.

Hidden-row causes:

| Cause | Count | Product implication |
| --- | ---: | --- |
| No V2 score row exists | 3,127/3,208 | Explore can render the catalog cell, but it cannot show V2 dimensions or benchmark confidence. |
| No report-backed Explore row exists | 3,098/3,208 | Report detail cannot open because the materialized cell has no `report_id`. |
| Legacy report-backed fallback | 46/3,208 | A detail row exists, but Explore is not using the V2 scoring surface. |
| V2 row exists but benchmark confidence is undersampled | 81/3,208 | The app can show V2 metadata, but the benchmark cell is still below the `sample_size_metros >= 8` usability gate. |

Explore has broad catalog/read-model coverage, but not enough V2-backed visibility for the scoring-hardening goal. The app can show many city-service rows through legacy or catalog fallback paths, yet only a narrow slice has the V2 score and benchmark confidence metadata needed for the new scoring surface.

## Recommendations

1. Keep the scoring runner path accepted. The 96/96 pilot validates API health, production project guardrails, target identity, and V2 persistence checks.
2. Do not run benchmark recompute yet. The benchmark usability gate is 0/48 at `sample_size_metros >= 8`.
3. Run only the smallest approved acquisition/backfill batch for missing DA/Lighthouse telemetry, local review velocity, and benchmark cells. Use the WHI-102 opt-in flags added in PR #81; keep preflight free of those paid add-ons.
4. Route WHI-104 to benchmark-cell sufficiency. The first question is which service x population cells can reach sample size 8 with the least paid work.
5. Route WHI-105 to app visibility. After benchmark and V2 facts improve, verify Explore/report surfaces prefer V2 rows and expose benchmark confidence without legacy-only fallbacks hiding the gap.
6. Defer scoring-framework changes to WHI-106. Formula changes should be based on a rerun of the read-only audits after data acquisition, not on this failing audit alone.
