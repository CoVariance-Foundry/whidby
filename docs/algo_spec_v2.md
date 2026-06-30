# Widby Niche Scoring Algorithm — V2 Specification

**Status:** Partially implemented methodology and support guide
**Author:** Antwoine Flowers / Kael
**Date:** 2026-06-02
**Supersedes:** `docs/algo_spec_v1_1.md`
**Classification:** Internal IP — Covariance

---

## 0. Why V2 — what changed and why

V1.1 worked as a v0 hypothesis test. SME review with Luke (rank-and-rent SME) and Coral (independent practitioner) surfaced six structural problems that V1.1 cannot fix by parameter tuning. V2 rebuilds the scoring contract around them.

The six load-bearing changes:

1. **Raw scoring is a vector; product ranking is a projection.** V1.1 collapsed five dimensions into one number, which forced contradictory direction conventions (high = better for demand, but high = harder for competition) and hid the cells that practitioners actually inspect. V2 stores a benchmark-aware vector. Product surfaces may project that vector into an "opportunity" or strategy score, but that projection is not a sixth observed fact.

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

Persisted flag triggers:

- `no_local_pack_detected`: true when `local_pack_present` is false; raw V2 `local_difficulty` is then `null`.
- `benchmark_undersampled`: true when no benchmark cell exists, the benchmark cell is marked undersampled, or the effective benchmark confidence is `low`/`insufficient`.
- `cbp_data_missing`: true when both `cbp_establishments` and legacy `establishments` are absent; monetization then uses the neutral CBP fallback.

In-memory V2 result flags that are not currently persisted to `metro_score_v2`:

- `top3_review_data_low_coverage`: true only when a local pack exists and either `top3_review_count_coverage` or `top3_review_velocity_coverage` is below `0.67`.
- `top5_organic_data_low_coverage`: true when top-5 DA coverage or top-5 Lighthouse coverage is below `0.60`; if explicit coverage is absent, the engine infers coverage from whether the corresponding aggregate value is present.

The vector above is the benchmark-aware scoring substrate used for debugging and read-model projection. The current product also carries a legacy 0-100 report headline score bundle in `reports.metros[*].scores` and `metro_scores`; support should identify which score surface a user is looking at before explaining a number.

### 1.1 Product and support score surfaces

There are four score surfaces used by product and support:

| Layer | Storage/API surface | How to read it | Benchmark role |
| --- | --- | --- | --- |
| Report headline scores | `reports.metros[*].scores`, `metro_scores`, report UI cards | 0-100 customer-facing scores: demand, organic ease, local ease, monetization, AI resilience, opportunity | Legacy M7 formulas do not read `seo_benchmarks`; they use the scoring-run cohort and observed signal values |
| V2 benchmark vector | `metro_score_v2` | Five raw dimensions with direction flags: high demand/monetization/AI is good; high organic/local difficulty is hard | `seo_benchmarks` directly affect demand, local difficulty, monetization, and benchmark confidence/flags |
| Explore cached score | `explore_market_cells.presentation_score`, Explore service DTOs | 0-100 sortable cached read-model score. Current V2 rows use `greatest(coalesce(demand_strength, 0) / 2, 0)::integer`; legacy fallback rows use legacy opportunity | Exposes V2 provenance such as `benchmark_confidence`, but does not return a warning list |
| Strategy projection | Strategy run items | 0-100 sortable product score for a selected lens such as Easy Win or GBP Blitz | Projects V2 fields and can carry strategy-specific warnings |

For support/debugging, call the report UI labels "product scores" and the `metro_score_v2` fields "raw V2 scores." Product scores intentionally render competition as ease, so higher is better. Raw V2 difficulty intentionally renders competition as difficulty, so higher is harder.

Current report headline semantics:

- `Demand` is a 0-100 legacy M7 score based on effective search volume percentile inside the run cohort, CPC, breadth, and transactional intent.
- `Organic ease` is the legacy `organic_competition` score. Higher means easier because it rewards weaker incumbent authority, more local-business presence, weaker technical/title signals, and fewer aggregators.
- `Local ease` is the legacy `local_competition` score. Higher means easier because it rewards lower review barriers, lower review velocity, weaker GBP completeness, lower photo count, and lower posting activity. A missing local pack uses the configured legacy default.
- `Monetization` is a 0-100 legacy M7 score based on CPC, business density, ads/LSA/aggregator activity, and GBP completeness.
- `AI resilience` is a 0-100 score where higher means less AI Overview displacement risk.
- `Opportunity` is a weighted sum of the five headline dimensions, clamped to `0-100`. Current default balanced weights are demand `0.25`, organic `0.15`, local `0.20`, monetization `0.20`, and AI resilience `0.15`; those implemented weights total `0.95`, so this is not a normalized weighted average. Organic/local weights can move by strategy profile. The composite is capped at `20` if any base component is below `5`, capped at `40` if any base component is below `15`, and capped at `50` when AI resilience is below `20`.

Current strategy projection example:

- Easy Win projection uses `min(demand_strength / 140, 1) * 100`, `100 - organic_difficulty`, `65` when `local_difficulty` is null otherwise `100 - local_difficulty`, and `ai_resilience`.
- Easy Win weights those projected values as demand `0.25`, organic ease `0.45`, local ease `0.20`, and AI resilience `0.10`.
- If `benchmark_confidence` is `low` or `insufficient`, the projection can still return a score, but it should carry a `benchmark_confidence_low` warning.

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
- Missing or non-positive benchmark values fall back to `DEFAULT_VOLUME_PER_CAPITA = 0.0025` and `MEDIAN_LOCAL_SERVICE_CPC = 5.00`; the score still computes. Missing, undersampled, low-confidence, or insufficient benchmark cells set `benchmark_undersampled`.

**Score formula:**
```python
def positive(value, default):
    return default if value is None or value <= 0 else value


def demand_strength(observed_volume, observed_cpc, population, benchmark):
    obs_vol_per_cap = observed_volume / max(population, 1)
    bench_vol_per_cap = positive(
        benchmark.median_total_volume_per_capita if benchmark else None,
        DEFAULT_VOLUME_PER_CAPITA,  # 0.0025
    )
    bench_cpc = positive(
        benchmark.median_avg_cpc if benchmark else None,
        MEDIAN_LOCAL_SERVICE_CPC,  # 5.00
    )

    # Volume relative to median, capped at 2x (200)
    vol_score = min(obs_vol_per_cap / bench_vol_per_cap, 2.0) * 100

    # CPC adjustment — if CPC is well above median, bump by up to 20%
    cpc_ratio = observed_cpc / max(bench_cpc, 0.01)
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
- Current score formula does not normalize organic difficulty against benchmark medians.
- Benchmark and metric-sufficiency coverage still matter for confidence and debugging, especially top-5 DA/Lighthouse sparsity.

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
    bench_floor = positive(
        benchmark.median_top3_review_count_min if benchmark else None,
        DEFAULT_REVIEW_FLOOR,  # 30.0
    )
    review_pressure = min(signals.top3_review_count_min / max(bench_floor, 1), 3.0)
    review_score = (review_pressure / 3.0) * 60  # max 60 points

    # Velocity — active markets are harder
    bench_vel = positive(
        benchmark.median_top3_review_velocity if benchmark else None,
        DEFAULT_REVIEW_VELOCITY,  # 3.0
    )
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
- `median_lsa_present_rate` and `median_ads_present_rate` are stored for analysis, but the current scoring formula uses observed ad/LSA presence directly rather than benchmark-normalizing those rates.

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

### 3.3 Benchmark coverage and acceptance gates

Coverage is evaluated by required launch cells, not by all rows that happen to exist in `seo_benchmarks`.

Canonical production acceptance currently requires:

- `48` usable benchmark cells for the eight core services across the required population-class frame.
- `48` metric-ready cells from `seo_benchmark_metric_sufficiency`, so sample size alone cannot make a cell production-ready.
- V2 Explore row visibility above the required threshold, verified through the read-model audit rather than direct table counts alone.
- Target Supabase project guard `eoajvifhbmqmoluiokcj` before any live acceptance claim.

Use the canonical acceptance command from `docs-canonical/TEST-SPEC.md` when validating readiness:

```bash
python -m scripts.explore.audit_signal_coverage \
  --coverage-threshold 0.6 \
  --min-benchmark-cells 48 \
  --min-benchmark-sample-size 8 \
  --min-metric-ready-cells 48 \
  --min-explore-v2-rows 48 \
  --acceptance-gates-only \
  --expected-project-ref eoajvifhbmqmoluiokcj
```

Support should not infer readiness from one of these gates in isolation. A complaint about a score needs the score's `benchmark_sample_size`, `benchmark_confidence`, and metric-family sufficiency status for the same `(niche_normalized, population_class)` cell.

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

Implemented boundary: V2 scoring reads `seo_benchmarks` through `src/scoring/benchmark_repository.py::SeoBenchmarkRepository`, with Supabase access isolated in `src/clients/seo_benchmark_repository.py::SupabaseSeoBenchmarkRepository`. Score formulas in `src/scoring/v2.py` consume repository-returned benchmark cells and do not query Supabase directly.

The benchmark's confidence carries forward to the score. `metro_score_v2.benchmark_confidence` is one of `{high, medium, low, insufficient}`.

Implementation detail: the persisted score uses the effective confidence from `src/scoring/v2.py`, not just the top-level benchmark label. The engine starts from `seo_benchmarks.confidence_label`, then lowers it when any required metric family in `metric_confidence_rollup` is weaker. Required families for effective confidence are:

- `demand`
- `organic_serp`
- `local_pack`
- `review_velocity`
- `gbp_profile`
- `monetization`
- `ai_serp_displacement`

`organic_authority` and `lighthouse_site_quality` remain canonical metric-sufficiency families for audits and top-5 organic telemetry. Current scoring treats sparse top-5 DA/Lighthouse as low-coverage evidence, not as zero authority or zero difficulty.

If no benchmark cell exists, the benchmark cell is marked undersampled, or effective `benchmark_confidence` is `low` or `insufficient`:
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

### 5.3 Difficulty tier

Current production `difficulty_tier` remains an M8 classification over legacy M7 ease-style competition scores, not raw V2 difficulty fields. It resolves the selected strategy profile into organic/local weights, normalizes those two weights against each other, and computes a combined ease score:

```python
combined_comp = (
    local_competition * local_weight_share
    + organic_competition * organic_weight_share
)

if combined_comp >= 70:  return "EASY"
if combined_comp >= 45:  return "MODERATE"
if combined_comp >= 25:  return "HARD"
return "VERY_HARD"
```

Because the current inputs are ease-style scores, higher `combined_comp` means easier ranking. A future V2-native difficulty tier can use `organic_difficulty`/`local_difficulty`, but support should not explain production report tiers that way until the classifier is migrated.

---

## 6. Removed from V1.1 (and why)

| V1.1 feature | Removed because |
|---|---|
| Fixed raw `composite_opportunity_score` as the V2 substrate | Hides cells practitioners actually inspect; forces direction conflicts. Product can still project vectors into opportunity/lens scores for sorting and reporting. |
| `breadth_bonus` (volume_breadth × 15) | Not validated by SME; arbitrary multiplier |
| `cohort_relative percentile_rank` for demand | Cohort isn't a stable reference; meaningless for single-metro queries |
| Effective volume AIO discount (`× (1 - aio_rate × 0.59)`) | Double-counts intent filtering; magic constants stacked |
| Fixed `local_competition_score = 75` when no local pack | Pack absence is a diagnostic, not a feature; should be NULL |
| Top-5 GBP completeness average | Includes non-ranking businesses; floor of top 3 is the meaningful bar |
| Legacy-only `strategy_profile` weight redistribution as the only explanation | V2 keeps raw vectors explainable first; strategy/profile/lens math belongs in the presentation or strategy projection layer and must be named as such. |

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

The UI must make the score surface explicit:

- Report headline cards render product scores where higher is always better. Organic and local are labeled "ease" because those values are already inverted from difficulty in the legacy report score bundle.
- V2 details and developer/debug views render `organic_difficulty` and `local_difficulty` as difficulty, where higher is harder. If those fields are shown to users, label them "difficulty" or invert them before labeling them "ease."
- Explore renders cached read-model `presentation_score`. For current V2 rows, this is `demand_strength / 2` clamped at zero; for legacy fallback rows, it is the legacy opportunity score.
- Strategy results render strategy `score` as a lens projection. That number is useful for ranking but should be explained as a lens score, not as a raw benchmark measurement.

### 8.1 Projection and color conventions

UI renders raw V2 cells using the dimension's `higher_is_better` flag:

- `true`: high values green, low values red
- `false`: high values red, low values green
- `null` value: gray with an info icon explaining why (for example, "No local pack detected for this keyword")

UI renders product/report scores as higher-is-better because the report payload already uses customer-facing ease/opportunity semantics.

### 8.2 Support explanation rule

When explaining a disputed score, do not say "the benchmark gave this market a 71." Say:

1. Observed facts came from the scoring run and durable SEO evidence rows.
2. The benchmark cell provided the expected baseline for that niche and population class.
3. The formula compared observed facts to that baseline where applicable.
4. Confidence and warning flags came from sample size, metric-family sufficiency, and missing-data coverage.
5. The product may then have projected raw fields into an opportunity or strategy lens score.

This wording prevents benchmark-relative scores from sounding like arbitrary averages and prevents product projections from sounding like raw measurements.

## 9. Support debugging checklist

Use this checklist when a customer disagrees with a score or a report looks suspicious.

1. Identify the score surface: report headline score, raw V2 `metro_score_v2` value, Explore cached `presentation_score`, or strategy projection score.
2. Capture the `report_id`, `cbsa_code`, `cbsa_name`, `niche_keyword`, `niche_normalized`, `spec_version`, and score timestamp.
3. Read `reports` and `metro_scores` for headline scores; read `metro_score_v2` for raw V2 scores, direction flags, benchmark confidence, sample size, and warning flags.
4. Read `seo_facts` for the observed facts behind the score and `seo_evidence_artifacts` when provider request/response lineage is needed.
5. Read `seo_benchmarks` using `niche_normalized` plus `population_class = metro_score_v2.benchmark_population_class`; verify `sample_size_metros`, confidence label, and benchmark medians used by the formula.
6. Read `seo_benchmark_metric_sufficiency` for the same benchmark run/cell to confirm whether each required metric family is ready, undersampled, or missing.
7. Check common disagreement causes:
   - The customer is comparing against a newer Google result than the report snapshot.
   - The market is being compared to its population class, not to a national average.
   - The score is preliminary because the benchmark is missing, undersampled, or low confidence.
   - Local pack absence makes raw V2 `local_difficulty` null; it should not be interpreted as either easy or hard.
   - Missing CBP data uses a neutral monetization fallback and sets `cbp_data_missing`.
   - Missing top-5 DA/Lighthouse lowers evidence confidence but does not become a free easy-score boost.

Recommended support language:

> This score is based on the facts we observed for this report snapshot, compared against the benchmark cell for the same service and metro population class. The benchmark changes the baseline and confidence, but it does not replace the observed SERP, review, demand, monetization, or AI-exposure facts.

---

## 10. Migration from V1.1

**Database:** V1.1 tables (`metro_scores`, `metro_signals`, `reports`, `report_keywords`) are preserved as-is. New tables (`seo_facts`, `seo_benchmarks`, `metro_score_v2`) coexist. No migration script — V2 reads/writes new tables only.

**Application code:**
1. FastAPI `/api/niches/score` writes `metro_score_v2` in addition to `metro_scores`.
2. Next.js report pages continue to render the report headline score bundle for compatibility, while Explore and strategy read models prefer V2-backed scores when present.
3. Do not deprecate `metro_scores` writes until report headline UX has an explicit V2 vector/ease projection replacement and report E2E tests prove old reports remain readable.

**Backfill strategy for existing reports:** None. V1.1 reports remain readable in their old shape; new scoring runs go through V2. The `feedback_log` schema is unchanged so the bandit work isn't disrupted.

---

## 11. Open questions

1. **Fallback when CBP cell is null** — some niches don't map cleanly to a single NAICS (e.g., "junk removal" spans 562111 and parts of 488490). Multi-NAICS aggregation is supported in `niche_naics_mapping.weight` but the scoring formula assumes a single value. Resolve in §2.4 implementation: sum CBP across all NAICS rows for the niche, weighted.
2. **Refresh cadence for `seo_facts` of stale (niche, metro) pairs** — DFS data drifts. Proposal: TTL on facts of 90 days for benchmark eligibility.
3. **Benchmark cell coverage** — once pilot data lands, audit cells with `confidence = 'insufficient'` and decide whether to expand sampling there or accept gaps.

---

## 12. References

- V1.1 spec: `docs/algo_spec_v1_1.md` (retained as historical reference)
- Migration: `supabase/migrations/010_v2_benchmarks.sql`
- Benchmark runner: `scripts/benchmarks/run_pilot.py`
- SME call: Luke <> Henock <> Antwoine, 2026-04-26 ([Fireflies](https://app.fireflies.ai/view/01KQ5A4P91TCSXJ1YBYHJWFSX1))
- Census data sources: ACS 2019-2023 5-yr (via api.census.gov), CBP 2023 MSA file (www2.census.gov)
