# Feature: Signal Extraction (M6)

**Feature branch:** `M06-signal-extraction`  
**Status:** Draft  
**Module ID:** M6  
**Spec references:** `docs/algo_spec_v1_1.md` §6 (Phase 3); `docs/product_breakdown.md` (M6)

## Summary

For one metro’s raw collection bundle plus the keyword expansion metadata, the module derives **MetroSignals**: five categories (demand, organic competition, local competition, AI resilience, monetization) with the exact signal names and scales defined in Algo §6.1–§6.5, including effective volume with AIO discounting, SERP feature rates, domain classification (aggregator / national heuristics), review velocity, and GBP completeness.

## Dependencies

- **M5:** RawCollectionResult slice for the metro (all raw API payloads)
- **M4:** Keyword expansion (intent, tier, transactional ratio, optional `local_fulfillment_required`)

## User Scenarios & Acceptance Scenarios

### US-1 — Demand analyst reviews demand signals

**Acceptance**

- **AS-1.1 (eight demand signals):** `demand` contains all eight keys from Algo §6.1: `total_search_volume`, `effective_search_volume`, `head_term_volume`, `volume_breadth`, `avg_cpc`, `max_cpc`, `cpc_volume_product`, `transactional_ratio` with types and scales per spec tables.
- **AS-1.2 (effective volume — transactional):** For transactional intent, when no AIO is detected in SERP for that keyword, effective volume uses expected AIO rate ~2.1% in the discount formula (Algo §6.1, `effective_volume` code block) — implied discount small (~1.2% of volume from `0.021 × 0.59`).
- **AS-1.3 (effective volume — informational):** For informational intent without detected AIO, expected rate ~43.6% yields discount ~26% (`0.436 × 0.59`), matching product breakdown eval order-of-magnitude.
- **AS-1.4 (detected AIO):** When SERP parsing marks `aio_detected_in_serp` for a keyword, that keyword’s contribution uses `(1 - 0.59)` multiplier on volume regardless of intent (Algo §6.1 snippet).

### US-2 — SEO researcher inspects organic competition

**Acceptance**

- **AS-2.1 (eight organic signals):** All keys from Algo §6.2 present: DA stats, `aggregator_count`, `local_biz_count`, Lighthouse performance average, `schema_adoption_rate`, `title_keyword_match_rate`.
- **AS-2.2 (aggregator detection):** Known aggregator domains (Algo §6.6 `KNOWN_AGGREGATORS`) in top organic results increment `aggregator_count` appropriately (product breakdown: Yelp example → count ≥ 1).

### US-3 — Local operator evaluates pack and GBP pressure

**Acceptance**

- **AS-3.1 (ten local signals):** All keys from Algo §6.3 present including pack presence/position, review stats, `review_velocity_avg`, GBP averages, posting activity, `citation_consistency`.
- **AS-3.2 (local pack parsing):** When raw SERP includes a local 3-pack, `local_pack_present` is true and review/rating aggregates are populated from reviews/maps sources per spec.
- **AS-3.3 (missing pack):** When no local pack exists, booleans and numeric signals use documented defaults (product breakdown: sensible defaults without crashing M7).

### US-4 — Product strategist assesses AI resilience and monetization

**Acceptance**

- **AS-4.1 (five AI resilience signals):** Keys from Algo §6.4: `aio_trigger_rate`, `featured_snippet_rate`, `transactional_keyword_ratio`, `local_fulfillment_required`, `paa_density`.
- **AS-4.2 (AIO rate):** If any analyzed SERP contains AI Overview, `aio_trigger_rate` > 0 (product breakdown).
- **AS-4.3 (six monetization signals):** Keys from Algo §6.5: `avg_cpc`, `business_density`, `gbp_completeness_avg`, `lsa_present`, `aggregator_presence`, `ads_present`.

### US-5 — Cross-metro classification

**Acceptance**

- **AS-5.1 (national/directory heuristic):** When the same domain appears in ≥ 30% of analyzed metros (Algo §6.7), classification treats it as national/directory for `local_biz_count` / organic parsing rules as implemented (exact hook documented in plan).
- **AS-5.2 (fixture):** Same domain in 8/20 metros classifies per cross-metro dedup eval in product breakdown.

### US-6 — GBP and review quality signals

**Acceptance**

- **AS-6.1 (GBP completeness):** Completeness uses seven binary components (phone, hours, website, photos, description, services, attributes), normalized 0–1; e.g. 5/7 → ~0.71 (product breakdown).
- **AS-6.2 (review velocity):** `review_velocity_avg` is derived from review timestamps as reviews per month for top local-pack businesses (Algo §6.3).

## Requirements

### Functional

- **FR-1:** Entry point (e.g. `extract_signals(raw_metro_bundle, keyword_expansion) -> MetroSignals`) consumes one metro’s M5 payload plus expansion context.
- **FR-2:** Output **MetroSignals** MUST include these categories and keys:
  - **demand (8):** per Algo §6.1
  - **organic_competition (8):** per Algo §6.2
  - **local_competition (10):** per Algo §6.3
  - **ai_resilience (5):** per Algo §6.4
  - **monetization (6):** per Algo §6.5  
  Shared keys (`avg_cpc`, `gbp_completeness_avg`, aggregator counts) MUST be consistent where they are the same economic quantity (document single source of truth in implementation).
- **FR-3:** Implement `effective_volume` exactly as Algo §6.1 (constants from `src/config/constants.py`: `AIO_CTR_REDUCTION`, `INTENT_AIO_RATES`).
- **FR-4:** **serp_parser** extracts SERP features required for AI resilience and monetization flags from M5 raw SERP JSON (Algo §5.1 / §6.4–6.5).
- **FR-5:** **domain_classifier** applies `KNOWN_AGGREGATORS` and cross-metro national heuristic (Algo §6.6–6.7) with `KNOWN_NATIONAL_BRANDS` extension point as stub or data-driven follow-up.
- **FR-6:** **review_velocity** and **gbp_completeness** modules encapsulate timestamp-based velocity and 7-signal completeness scoring.

### Non-functional

- **NFR-1:** Signal extraction functions are pure over inputs (no API calls); unit tests use fixtures only.
- **NFR-2:** Missing partial raw data produces defined defaults and/or null-safe behavior documented per signal.

### Implementation mapping (from product breakdown)

- `src/pipeline/signal_extraction.py`
- `src/pipeline/extractors/demand_signals.py`
- `src/pipeline/extractors/organic_competition.py`
- `src/pipeline/extractors/local_competition.py`
- `src/pipeline/extractors/ai_resilience.py`
- `src/pipeline/extractors/monetization.py`
- `src/pipeline/serp_parser.py`
- `src/pipeline/domain_classifier.py`
- `src/pipeline/effective_volume.py`
- `src/pipeline/review_velocity.py`
- `src/pipeline/gbp_completeness.py`

## Success Criteria

| ID | Criterion | Pass condition |
|----|-----------|----------------|
| SC-1 | Demand extraction | All eight demand signals non-null with valid ranges for fixture “happy path” per AS-1.1 |
| SC-2 | Effective volume transactional | Discount magnitude matches intent-based formula per AS-1.2 |
| SC-3 | Effective volume informational | ~26% discount path per AS-1.3 |
| SC-4 | AIO detection | `aio_trigger_rate` reflects presence in fixture SERP per AS-4.2 |
| SC-5 | Aggregator detection | Yelp (or other known aggregator) increments count per AS-2.2 |
| SC-6 | Cross-metro dedup | National heuristic affects classification per AS-5.1–5.2 |
| SC-7 | Review velocity | Computed from timestamps per AS-6.2 |
| SC-8 | GBP completeness | 5/7 fields → score 0.71 (± rounding) per AS-6.1 |
| SC-9 | Local pack parsing | Pack present fixture sets flags and aggregates per AS-3.2 |
| SC-10 | Missing data | No local pack → defaults safe for downstream per AS-3.3 |

## Assumptions

- M5 raw shapes are stable; if DataForSEO JSON paths differ, `serp_parser` adapts in one layer without changing MetroSignals names.
- `transactional_keyword_ratio` and `local_fulfillment_required` align with M4 outputs; if M4 omits fulfillment flag, default is documented (e.g. 1 for local service niches) until LLM classification lands.
- Cross-metro dedup for national domains requires optional access to all metros’ SERP extracts in one batch job; API may be `extract_signals_batch` or a separate classifier pass — to be fixed in `/speckit.plan` without changing signal names.

## Source documentation

- `docs/algo_spec_v1_1.md` — §6.1–§6.7 (signal tables, effective_volume, aggregators, cross-metro dedup)
- `docs/product_breakdown.md` — M6 I/O example, eval criteria, file layout
- `docs/module_dependency.md` — M5 → M6 → M7
- `docs/data_flow.md` — MetroSignals → scoring
