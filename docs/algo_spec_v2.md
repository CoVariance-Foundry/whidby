# Widby Niche Scoring Algorithm — V2 Specification

**Status:** Draft
**Author:** Antwoine Flowers / Kael
**Date:** 2026-04-27
**Supersedes:** `docs/algo_spec_v1_1.md`
**Classification:** Internal IP — Covariance

---

## 0. Why V2 — what changed and why

V1.1 worked as a v0 hypothesis test. SME review with Luke (rank-and-rent SME) and Coral (independent practitioner) surfaced six structural problems that V1.1 cannot fix by parameter tuning. V2 rebuilds the scoring contract around them.

The six load-bearing changes:

1. **No composite opportunity score.** V1.1 collapsed five dimensions into one number, which forced contradictory direction conventions (high = better for demand, but high = harder for competition) and hid the cells that practitioners actually inspect. V2 outputs a vector. UI applies an archetype filter to derive sortable views client-side.

2. **Direction is per-dimension and explicit.** V1.1 fought "higher = better" by inverse-scaling competition; SME feedback was unanimous: every other SEO tool uses high-competition = harder. V2 outputs a `higher_is_better` boolean per dimension and stops trying to normalize direction.

3. **Cohort-relative percentiles replaced with absolute, census-grounded benchmarks.** V1.1's `percentile_rank(volume, all_metro_signals)` was meaningless when the cohort wasn't a stable reference. V2 reads from `seo_benchmarks` keyed by `(niche_normalized, population_class)` — pre-computed p25/median/p75 with explicit `sample_size` and `confidence_label`.

4. **Local difficulty is nullable when no local pack exists.** V1.1 hardcoded `score = 75` when `local_pack_present == False`. SME: pack absence is a *diagnostic* about the keyword/city pairing, not a feature of the opportunity. V2 returns `local_difficulty = NULL` and surfaces a `no_local_pack_detected` flag.

5. **Top-3 floor, not top-5 average.** V1.1 averaged GBP completeness across top 5 listings, including businesses that don't actually rank. V2 uses the top 3 of the local pack and the *floor* (min review count) as the bar to clear.

6. **Demand uses transactional+commercial volume only, no breadth bonus, no AIO multiplier on volume.** V1.1's `effective_search_volume = volume × intent × (1 - aio_rate × 0.59)` over-engineered intent filtering already done in keyword expansion. V2 sums transactional+commercial volume (per Coral). AIO is reported as a separate flag, not as a discount on demand.

V1.1's AI Resilience scoring is preserved unchanged — Coral validated the approach on the call.

---

## 1. Output contract

V2 produces a **score vector**, not a score number. Persisted to `metro_score_v2`:

```json
{
  "report_id": "uuid",
  "niche_normalized": "concrete contractor",
  "cbsa_code": "38060",
  "scores": {
    "demand_strength":     {"value": 142, "higher_is_better": true,  "range": "0-200"},
    "organic_difficulty":  {"value": 58,  "higher_is_better": false, "range": "0-100"},
    "local_difficulty":    {"value": 41,  "higher_is_better": false, "range": "0-100"},
    "monetization_signal": {"value": 167, "higher_is_better": true,  "range": "0-200"},
    "ai_resilience":       {"value": 92,  "higher_is_better": true,  "range": "0-100"}
  },
  "benchmark": {
    "population_class": "metro_1m_5m",
    "sample_size": 75,
    "confidence_label": "high"
  },
  "flags": {
    "no_local_pack_detected": false,
    "benchmark_undersampled": false,
    "cbp_data_missing": false
  },
  "serp_archetype": "FRAGMENTED_WEAK",
  "ai_exposure": "AI_SHIELDED",
  "spec_version": "2.0"
}
```

**No composite.** Sorting and ranking are presentation concerns. The UI receives the vector + an archetype filter (set by user) and projects to a sortable column client-side. See §8.

---

## 2. The five dimensions

Each dimension follows the same scoring template:

```
1. Pull observed signals from the live scoring pipeline (or seo_facts).
2. Look up the relevant benchmark cell from seo_benchmarks.
3. Compute a benchmark-relative score on the dimension's specified range.
4. Stamp direction (higher_is_better) and benchmark provenance on the output.
```

Benchmark cell key: `(niche_normalized, population_class)` where `population_class` is the metro's pre-computed bucket from `metros.population_class`.

### 2.1 Demand strength — `0-200`, higher = better

**Question answered:** Is there enough commercial search demand here to justify ranking?

**Inputs:**
- Sum of `search_volume_monthly` across keywords with `intent IN ('transactional', 'commercial')` for this `(niche, metro)`
- Metro `population` (denominator for per-capita normalization)
- Average `cpc_usd` weighted by volume

**Benchmark lookup:**
- `seo_benchmarks.median_total_volume_per_capita`
- `seo_benchmarks.median_avg_cpc`

**Score formula:**
```python
def demand_strength(observed_volume, observed_cpc, population, benchmark):
    obs_vol_per_cap = observed_volume / max(population, 1)
    bench_vol_per_cap = benchmark.median_total_volume_per_capita

    if bench_vol_per_cap == 0:
        return None  # no benchmark — flag as undersampled

    # Volume relative to median, capped at 2x (200)
    vol_score = min(obs_vol_per_cap / bench_vol_per_cap, 2.0) * 100

    # CPC adjustment — if CPC is well above median, bump by up to 20%
    cpc_ratio = observed_cpc / max(benchmark.median_avg_cpc, 0.01)
    cpc_adj = min(max(cpc_ratio, 0.5), 1.5)  # clamp 0.5x-1.5x

    return clamp(round(vol_score * cpc_adj), 0, 200)
```

**Reading the score:**
- `100` = exactly median demand for this niche × pop class
- `200` = 2× median (a top market for this niche)
- `0` = effectively no commercial demand

### 2.2 Organic difficulty — `0-100`, higher = harder

**Question answered:** How hard is it to rank in the blue links for this niche × metro?

**Inputs (from SERP for top 2 head keywords):**
- `aggregator_count_top10`
- `local_biz_count_top10`
- (Optional, if pulled) `avg_top5_da` from backlinks API

**Benchmark lookup:**
- `seo_benchmarks.median_aggregator_count`
- `seo_benchmarks.median_local_biz_count`

**Score formula:**
```python
def organic_difficulty(signals, benchmark):
    # Aggregator dominance — high agg count = hard for new sites
    agg_pressure = signals.aggregator_count_top10 / 10.0  # 0-1

    # Local biz density — many local sites = beatable but crowded
    local_density = signals.local_biz_count_top10 / 10.0

    # Use absolute thresholds, not benchmark-relative for organic.
    # Reasoning: SERP composition is pretty universal across pop classes;
    # cohort-relative would mask the signal.
    raw = (agg_pressure * 0.55 + local_density * 0.30) * 100

    # If we have DA data, blend it in (15% weight)
    if signals.avg_top5_da is not None:
        raw = raw * 0.85 + (signals.avg_top5_da / 60.0) * 100 * 0.15

    return clamp(round(raw), 0, 100)
```

**Note on direction:** This is the V1.1 reversal — high score now means harder, matching every external SEO tool (Ahrefs KD, Moz DA). The UI renders high values in red.

### 2.3 Local difficulty — `0-100`, higher = harder, **nullable**

**Question answered:** How hard is it to rank in the local pack?

**Inputs:**
- `local_pack_present` (gates the entire dimension)
- `top3_review_count_min` (the floor — what a new GBP must beat)
- `top3_review_velocity_avg` (active markets are harder to displace)
- `top3_rating_avg`

**Benchmark lookup:**
- `seo_benchmarks.median_top3_review_count_min`
- `seo_benchmarks.median_top3_review_velocity`

**Score formula:**
```python
def local_difficulty(signals, benchmark):
    # Hard gate: no local pack → no local difficulty score
    if not signals.local_pack_present:
        return None  # Caller surfaces no_local_pack_detected = True

    # Review barrier — if floor is well above median, hard
    bench_floor = benchmark.median_top3_review_count_min or 30
    review_pressure = min(signals.top3_review_count_min / max(bench_floor, 1), 3.0)
    review_score = (review_pressure / 3.0) * 60  # max 60 points

    # Velocity — active markets are harder
    bench_vel = benchmark.median_top3_review_velocity or 3.0
    vel_pressure = min(signals.top3_review_velocity_avg / max(bench_vel, 0.1), 3.0)
    vel_score = (vel_pressure / 3.0) * 40  # max 40 points

    return clamp(round(review_score + vel_score), 0, 100)
```

**Why no GBP completeness:** V1.1 used a 7-signal completeness score averaged across top 5 listings. SME feedback was that completeness scores are noisy and the meaningful signal is the *floor* — what a competitor with a brand-new GBP has to beat. Reviews + velocity are the floor.

### 2.4 Monetization signal — `0-200`, higher = better

**Question answered:** If we rank, are there businesses here who'll pay for leads?

**Inputs:**
- `lsa_present`, `ads_present` (per top-keyword SERP)
- `establishments` count from `census_cbp_establishments` joined on the niche's NAICS code(s)
- `population` (denominator)

**Benchmark lookup:**
- `seo_benchmarks.median_establishments_per_100k`
- `seo_benchmarks.median_lsa_present_rate`
- `seo_benchmarks.median_ads_present_rate`

**Score formula:**
```python
def monetization_signal(signals, cbp_establishments, population, benchmark):
    if cbp_establishments is None:
        # Flag cbp_data_missing in caller; fallback uses ad signals only.
        cbp_score = 50  # neutral
    else:
        est_per_100k = (cbp_establishments / max(population, 1)) * 100_000
        bench_density = benchmark.median_establishments_per_100k or 50
        # 100 = at median, 200 = 2x median
        cbp_score = min(est_per_100k / bench_density, 2.0) * 100

    # Active spending signals — LSA + ads = market is paying for leads now
    spend_signal = 0
    if signals.lsa_present:
        spend_signal += 30
    if signals.ads_present:
        spend_signal += 20

    # Final: weight CBP density 70%, ad spending 30%
    return clamp(round(cbp_score * 0.70 + spend_signal * 1.5 * 0.30), 0, 200)
```

**Note:** SME feedback addressed exactly this signal — Coral pointed out that small markets won't have LSA but can still be monetizable. The CBP density grounding (real establishment counts per capita) is what fixes the V1.1 failure mode where Albany was scored low because DataForSEO's business listings API returned only 1 result.

### 2.5 AI resilience — `0-100`, higher = better

**Preserved from V1.1 unchanged.** Coral validated the approach.

```python
def ai_resilience(signals):
    # AIO exposure — lower trigger rate = more resilient
    aio_safety = inverse_scale(signals.aio_trigger_rate, floor=0, ceiling=0.50)

    # Transactional intent ratio
    intent_safety = signals.transactional_keyword_ratio * 100

    # Local fulfillment requirement — physical services are AI-proof
    fulfillment_bonus = signals.local_fulfillment_required * 20

    # PAA density as risk indicator
    paa_risk = inverse_scale(signals.paa_density, floor=0, ceiling=8)

    raw = (aio_safety * 0.40 + intent_safety * 0.25 +
           fulfillment_bonus * 0.15 + paa_risk * 0.20)
    return clamp(raw, 0, 100)
```

---

## 3. Benchmark computation

`seo_benchmarks` is recomputed periodically from `seo_facts`. Recommended cadence: nightly during data accumulation phase, weekly once stable.

The executable recompute contract is `public.recompute_seo_benchmarks(p_window_days integer)` from `supabase/migrations/012_recompute_seo_benchmarks.sql`.

### 3.1 Aggregation SQL

The executable recompute function aggregates at metro grain before producing benchmark cells:

- Roll up actionable `seo_facts` only, using `WHERE f.intent IN ('transactional', 'commercial')`, by `(niche_normalized, cbsa_code)`.
- Join `metros` to attach `population_class` and `population`, then compute per-metro demand, CPC, local pack, organic, paid, and AIO measures.
- Normalize `niche_naics_mapping.weight` within each niche before joining `census_cbp_establishments`, so multi-NAICS CBP density is weighted without inflating establishments.
- Aggregate metro rollups into `(niche_normalized, population_class)` benchmark cells, including percentile bands, sample counts, fact window bounds, and confidence labels.
- Upsert the computed cells into `seo_benchmarks` via `public.recompute_seo_benchmarks(p_window_days integer)`.

### 3.2 Confidence labeling

```
high          n_metros >= 20    -- stable percentiles, regression-ready
medium        n_metros >= 8     -- usable for scoring; UI shows "Limited data" hint
low           n_metros >= 3     -- shown but flagged prominently as preliminary
insufficient  n_metros < 3      -- no benchmark; score is computed without one and flagged
```

Minimum usable benchmark cell: sample_size_metros >= 8
Stable benchmark cell: sample_size_metros >= 20
Required before production cutover: every launch niche has at least one medium cell in its most common population class.

### 3.3 Benchmark coverage

Current staging audit after the latest pilot recompute:

Current coverage totals are 43 insufficient cells, 12 low cells, and 0 medium/high cells.

| Confidence | Cell count | Notes |
|------------|------------|-------|
| insufficient | 43 | Below scoring coverage target |
| low | 12 | Preliminary only |
| medium | 0 | No usable benchmark cells yet |
| high | 0 | No stable benchmark cells yet |

Full-sample runs are required before medium coverage is possible; the default pilot slice remains too thin for `sample_size_metros >= 8`.

Thin-cell follow-up:

| Niche | Population class | Sample metros | Confidence | Follow-up |
|-------|------------------|---------------|------------|-----------|
| auto repair | micro_under_50k | 1 | insufficient | +7 metros to medium |
| concrete contractor | medium_100_300k | 1 | insufficient | +7 metros to medium |
| plumber | large_300k_1m | 1 | insufficient | +7 metros to medium |
| roofing contractor | large_300k_1m | 1 | insufficient | +7 metros to medium |

Expanded paid collection has not yet been run in this implementation pass.

### 3.4 Refresh trigger

Initial bulk load: run benchmark generator (`scripts/benchmarks/run_pilot.py` for pilot scope, or `--full-sample` when expanding benchmark coverage). Recompute benchmarks after each batch.

Steady state: benchmarks recomputed nightly via cron. Each user-initiated scoring run also adds to `seo_facts`, so benchmarks accumulate naturally.

---

## Sonar Compatibility Boundary

The current benchmark tables can produce a Sonar slice-lite CellRecord for LA plumbing (`238220__msa__31080__2023`) using ACS-backed `metros`, CBP-backed `census_cbp_establishments`, NAICS mapping, and DataForSEO-derived `seo_facts`.

The full Sonar residual spec remains blocked on these source layers:

| Required layer | Current status | Blocking effect |
| --- | --- | --- |
| `geo.canonical_geo` and `geo.crosswalk` | Not loaded | Cannot roll county-level NES or BDS to MSA with auditable weights. |
| NES county extracts | Not loaded | Cannot compute `nonemp_to_emp_ratio`. |
| BDS 2018-2023 extracts | Not loaded | Cannot compute establishment exit/churn trajectory. |
| CBP 2018-2022 history | Not loaded | Cannot compute five-year establishment CAGR. |
| Google Trends 24-month series | Adapter exists, not stored by cell | Cannot compute `trends_slope_24mo` or `seasonality_index`. |
| Top-3 review floors | `seo_facts` columns exist, current rows are null | Cannot compute Sonar local-pack review barriers until paid collection is rerun. |
| Residual peer matrix | Not materialized | Cannot rank cells on actual-minus-expected residuals. |

Slice-lite scores must use `score_version = "sonar-lite-0.1"` and include data-quality warnings for each missing layer. Full Sonar scores must use a distinct score version after residuals are backed by a peer matrix.

---

## 4. Confidence in the per-(niche, metro) score

Current boundary: Phase 7 completes when `seo_benchmarks` can be recomputed and audited in staging. V2 scoring integration is the next implementation slice and should add a repository around `seo_benchmarks` rather than querying Supabase ad hoc from scoring formulas.

The benchmark's confidence carries forward to the score. `metro_score_v2.benchmark_confidence` is one of `{high, medium, low, insufficient}` — copied from the benchmark cell used.

If `benchmark_confidence == 'insufficient'`:
- Compute scores anyway using fallback heuristics (e.g., median CPC = $5.00 default for the volume_per_capita normalization)
- Set `benchmark_undersampled = TRUE`
- UI surfaces a prominent banner: "Limited benchmark data for this niche — scores are preliminary"

This degrades gracefully. V1.1 had no equivalent — scores were computed identically regardless of evidence.

---

## 5. Classification (preserved with adjustments)

### 5.1 SERP archetype

Same eight categories as V1.1 §8.1, with one rename:
- `LOCAL_PACK_VULNERABLE` → kept
- `LOCAL_PACK_ESTABLISHED` → kept
- `LOCAL_PACK_FORTIFIED` → kept
- `AGGREGATOR_DOMINATED` → kept
- `FRAGMENTED_WEAK` → kept
- `FRAGMENTED_COMPETITIVE` → kept
- `BARREN` → kept
- `MIXED` → kept

Classification thresholds reference benchmark-relative values where applicable (e.g., `LOCAL_PACK_FORTIFIED` triggers when `top3_review_count_min` is in the top quartile of the benchmark cell).

### 5.2 AI exposure

Preserved unchanged from V1.1 §8.2.

### 5.3 Difficulty tier — *renamed and reframed*

V1.1's `difficulty_tier` (EASY/MODERATE/HARD/VERY_HARD) collapsed organic+local competition into a single tier. V2 keeps the labels but bases them on the *combined* difficulty values rather than on a `combined_comp` inversely-scaled value:

```python
def difficulty_tier(organic_difficulty, local_difficulty):
    # If no local pack, pure organic
    if local_difficulty is None:
        max_diff = organic_difficulty
    else:
        max_diff = max(organic_difficulty, local_difficulty)

    if max_diff < 30:    return 'EASY'
    if max_diff < 55:    return 'MODERATE'
    if max_diff < 75:    return 'HARD'
    return 'VERY_HARD'
```

Uses `max()` deliberately — the harder of the two channels gates the practitioner's strategy. A market with hard local + easy organic is still hard if the practitioner needs the local pack.

---

## 6. Removed from V1.1 (and why)

| V1.1 feature | Removed because |
|---|---|
| `composite_opportunity_score` | Hides cells practitioners actually inspect; forces direction conflicts |
| `breadth_bonus` (volume_breadth × 15) | Not validated by SME; arbitrary multiplier |
| `cohort_relative percentile_rank` for demand | Cohort isn't a stable reference; meaningless for single-metro queries |
| Effective volume AIO discount (`× (1 - aio_rate × 0.59)`) | Double-counts intent filtering; magic constants stacked |
| Fixed `local_competition_score = 75` when no local pack | Pack absence is a diagnostic, not a feature; should be NULL |
| Top-5 GBP completeness average | Includes non-ranking businesses; floor of top 3 is the meaningful bar |
| `strategy_profile` weight redistribution | Within composite — irrelevant once composite is removed. Replaced by archetype filter at presentation. |

---

## 7. Output table (`metro_score_v2`)

Defined in `supabase/migrations/010_v2_benchmarks.sql`. Key columns:

```
report_id, niche_normalized, cbsa_code,
demand_strength, organic_difficulty, local_difficulty,
monetization_signal, ai_resilience,
demand_strength_higher_is_better, organic_difficulty_higher_is_better,
local_difficulty_higher_is_better, monetization_signal_higher_is_better,
ai_resilience_higher_is_better,
benchmark_population_class, benchmark_confidence, benchmark_sample_size,
no_local_pack_detected, benchmark_undersampled, cbp_data_missing,
serp_archetype, ai_exposure, spec_version
```

`local_difficulty` is the only nullable score column. All `*_higher_is_better` flags are populated even when the value is null, so UI can render the legend consistently.

---

## 8. Presentation contract (UI implications)

V2 doesn't render a "Total opportunity: 71" badge. The UI receives the score vector + a user-selected **archetype filter**, and projects to a sortable column.

### 8.1 Archetype filter (user-controlled lens)

| Archetype | Sort logic |
|---|---|
| `pure_rank_and_rent` | demand_strength × (100 - organic_difficulty) / 100. Local difficulty ignored. |
| `gbp_first` | demand_strength × (100 - local_difficulty) / 100, where local_difficulty is null treated as 50. |
| `mixed_authority` | demand_strength × (200 - organic_difficulty - local_difficulty_or_50) / 200. |
| `directory_bypass_longtail` | Filters to FRAGMENTED_* archetypes; sort by demand × ai_resilience. |

These are *presentation* aggregations, not scoring. A user can switch archetypes without rerunning scoring. The composite-as-narrative becomes the user's chosen lens, not a fixed formula in the engine.

### 8.2 Color conventions

UI renders cells using the dimension's `higher_is_better` flag:
- `true`: high values green, low values red
- `false`: high values red, low values green
- `null` value: gray with an info icon explaining why (e.g., "No local pack detected for this keyword")

---

## 9. Migration from V1.1

**Database:** V1.1 tables (`metro_scores`, `metro_signals`, `reports`, `report_keywords`) are preserved as-is. New tables (`seo_facts`, `seo_benchmarks`, `metro_score_v2`) coexist. No migration script — V2 reads/writes new tables only.

**Application code:**
1. Update FastAPI `/api/niches/score` to write `metro_score_v2` in addition to `metro_scores` for one release cycle.
2. Update Next.js scoring UI (`apps/admin`, `apps/app`) to read `metro_score_v2` and render the vector view.
3. Once UI is validated, deprecate `metro_scores` writes.

**Backfill strategy for existing reports:** None. V1.1 reports remain readable in their old shape; new scoring runs go through V2. The `feedback_log` schema is unchanged so the bandit work isn't disrupted.

---

## 10. Open questions

1. **Fallback when CBP cell is null** — some niches don't map cleanly to a single NAICS (e.g., "junk removal" spans 562111 and parts of 488490). Multi-NAICS aggregation is supported in `niche_naics_mapping.weight` but the scoring formula assumes a single value. Resolve in §2.4 implementation: sum CBP across all NAICS rows for the niche, weighted.
2. **Refresh cadence for `seo_facts` of stale (niche, metro) pairs** — DFS data drifts. Proposal: TTL on facts of 90 days for benchmark eligibility.
3. **Benchmark cell coverage** — once pilot data lands, audit cells with `confidence = 'insufficient'` and decide whether to expand sampling there or accept gaps.

---

## 11. References

- V1.1 spec: `docs/algo_spec_v1_1.md` (retained as historical reference)
- Migration: `supabase/migrations/010_v2_benchmarks.sql`
- Benchmark runner: `scripts/benchmarks/run_pilot.py`
- SME call: Luke <> Henock <> Antwoine, 2026-04-26 ([Fireflies](https://app.fireflies.ai/view/01KQ5A4P91TCSXJ1YBYHJWFSX1))
- Census data sources: ACS 2019-2023 5-yr (via api.census.gov), CBP 2023 MSA file (www2.census.gov)
