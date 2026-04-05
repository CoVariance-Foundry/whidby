# Feature: Signal Extraction (M6)

**Feature branch:** `002-m06-signal-extraction-rib`  
**Status:** Draft  
**Module ID:** M6  
**Spec references:** `docs/algo_spec_v1_1.md` §6 (Phase 3); `docs/product_breakdown.md` (M6)

## Summary

For one metro's raw collection bundle plus keyword-expansion metadata, M6 derives `MetroSignals` with five categories: demand, organic competition, local competition, AI resilience, and monetization. Signal names, scales, and formulas follow Algo Spec V1.1 §6.1–§6.5, including AIO-adjusted effective volume, SERP feature rates, domain classification, review velocity, and GBP completeness.

## Dependencies

- **M5:** RawCollectionResult slice for one metro (all raw API payloads)
- **M4:** Keyword expansion metadata (intent, tier, transactional ratio, optional `local_fulfillment_required`)

## User Scenarios & Acceptance Scenarios

### US-1 — Demand analyst reviews demand signals

**Acceptance**

- **AS-1.1:** `demand` includes all eight keys from Algo §6.1 with expected types and ranges.
- **AS-1.2:** Transactional keywords without detected AIO apply intent-based expected AIO discount (~1.2% net volume reduction from `0.021 × 0.59`).
- **AS-1.3:** Informational keywords without detected AIO apply larger expected discount (~26% from `0.436 × 0.59`).
- **AS-1.4:** If `aio_detected_in_serp` is true, that keyword uses direct 59% CTR reduction.

### US-2 — SEO researcher inspects organic competition

**Acceptance**

- **AS-2.1:** `organic_competition` includes all eight keys from Algo §6.2.
- **AS-2.2:** Known aggregator domains increment `aggregator_count` when present in top organic results.

### US-3 — Local operator evaluates pack and GBP pressure

**Acceptance**

- **AS-3.1:** `local_competition` includes all ten keys from Algo §6.3.
- **AS-3.2:** Presence of local 3-pack sets `local_pack_present` and populates rating/review aggregates.
- **AS-3.3:** Missing local pack uses defined safe defaults for downstream scoring.

### US-4 — Product strategist assesses AI resilience and monetization

**Acceptance**

- **AS-4.1:** `ai_resilience` includes five keys from Algo §6.4.
- **AS-4.2:** Any AIO appearance in analyzed SERPs produces `aio_trigger_rate > 0`.
- **AS-4.3:** `monetization` includes six keys from Algo §6.5.

### US-5 — Cross-metro domain classification

**Acceptance**

- **AS-5.1:** Domains appearing in >=30% of analyzed metros are classified as national/directory for local-vs-national counting logic.
- **AS-5.2:** Fixture representing 8/20 metro appearance classifies domain as national.

### US-6 — GBP and review quality signals

**Acceptance**

- **AS-6.1:** GBP completeness uses seven binary components normalized to 0–1 (e.g., 5/7 -> 0.71).
- **AS-6.2:** `review_velocity_avg` derives from review timestamps as reviews/month.

## Requirements

### Functional

- **FR-1:** Entry point consumes one metro's M5 payload plus M4 expansion context and returns `MetroSignals`.
- **FR-2:** Output includes five categories with exact key sets from Algo §6.1–§6.5.
- **FR-3:** `effective_volume` implementation uses constants from `src/config/constants.py` (`AIO_CTR_REDUCTION`, `INTENT_AIO_RATES`) and algorithm from Algo §6.1.
- **FR-4:** `serp_parser` extracts features needed by AI resilience and monetization signals.
- **FR-5:** `domain_classifier` applies known aggregators and cross-metro national heuristic.
- **FR-6:** `review_velocity` and `gbp_completeness` are isolated modules with deterministic computations.

### Non-functional

- **NFR-1:** Signal extraction logic is pure and deterministic (no outbound API calls).
- **NFR-2:** Missing/partial raw data uses documented null-safe defaults.
- **NFR-3:** Types, linting, and tests satisfy constitution quality gates.

### Implementation Mapping

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
| SC-1 | Demand extraction | All 8 demand signals present and valid on happy-path fixture |
| SC-2 | Effective volume (transactional) | Discount behavior matches Algo §6.1 transactional path |
| SC-3 | Effective volume (informational) | Discount behavior matches Algo §6.1 informational path (~26%) |
| SC-4 | AIO detection | `aio_trigger_rate` reflects AIO presence in SERP fixture |
| SC-5 | Aggregator detection | Known aggregator (for example yelp.com) increments count |
| SC-6 | Cross-metro classification | 8/20 domain fixture classifies as national |
| SC-7 | Review velocity | Reviews/month calculation matches timestamp fixture |
| SC-8 | GBP completeness | 5/7 fields yields ~0.71 score |
| SC-9 | Local pack parsing | Pack fixture populates local-pack fields correctly |
| SC-10 | Missing data handling | No-pack fixture returns safe defaults without crashes |

## Assumptions

- M5 raw payload keys stay stable; parser changes remain isolated if upstream shape shifts.
- M4 provides transactional ratio and may provide `local_fulfillment_required`; if absent, default is documented.
- Cross-metro domain classification receives either batched metro context or a separate domain-frequency pass.

## Source Documentation

- `docs/algo_spec_v1_1.md` (§6.1–§6.7)
- `docs/product_breakdown.md` (M6 section)
- `docs/module_dependency.md` (M5 -> M6 -> M7)
- `docs/data_flow.md` (MetroSignals downstream use)
