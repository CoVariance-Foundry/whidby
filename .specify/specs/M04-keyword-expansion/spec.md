# Feature: Keyword Expansion + Intent Classification (M4)

**Feature branch:** `M04-keyword-expansion`  
**Status:** Draft  
**Module ID:** M4  
**Spec references:** `docs/algo_spec_v1_1.md` §4 (Phase 1); `docs/product_breakdown.md` (M4)

## Summary

Given a single niche keyword, the pipeline expands it into a deduplicated, classified keyword set using LLM generation plus DataForSEO keyword suggestions, assigns tier and intent, labels AI-overview risk, and computes expansion quality metrics for downstream demand and AI-resilience scoring.

## Dependencies

- **M0:** DataForSEO client (keyword suggestions live endpoint, caching, cost)
- **M3:** LLM client (structured JSON expansion, temperature=0 for determinism)

## User Scenarios & Acceptance Scenarios

### US-1 — Practitioner runs expansion for a standard local niche

**Acceptance**

- **AS-1.1 (head terms):** When the niche is a typical local service (e.g. `plumber`), the expansion includes the head niche term and high-intent head patterns such as `{niche} near me` where applicable (Algo §4.3 Tier 1).
- **AS-1.2 (service terms):** The set includes sub-service and modifier patterns consistent with Tier 2 (e.g. drain cleaning, emergency plumber) for that vertical.
- **AS-1.3 (intent labels):** Every keyword in `expanded_keywords` has a valid `intent` ∈ {`transactional`, `commercial`, `informational`}.
- **AS-1.4 (tier labels):** Every keyword has `tier` ∈ {1, 2, 3} per Algo §4.3 (head / service / long-tail).
- **AS-1.5 (informational handling):** Informational queries (e.g. “how to …”) are either excluded from SERP-oriented sets or retained only with explicit `aio_risk` and schema notes per Algo §4.5; `informational_keywords_excluded` reflects the count excluded from SERP analysis.

### US-2 — System validates expansion against DataForSEO

**Acceptance**

- **AS-2.1 (DFS call):** Keyword suggestions are requested via DataForSEO Labs (`/v3/dataforseo_labs/google/keyword_suggestions/live`) using the niche plus top LLM-generated seeds (Algo §4.2).
- **AS-2.2 (confidence):** `expansion_confidence` is `low` when overlap between LLM top terms and DFS-derived terms is below 30%; otherwise `high` or `medium` as defined in implementation (Algo §4.6).
- **AS-2.3 (source field):** Each keyword records `source` (e.g. `llm`, `dataforseo_suggestions`, `input`) for traceability.

### US-3 — Operator needs stable, auditable results

**Acceptance**

- **AS-3.1 (determinism):** With LLM temperature 0 and fixed prompts, two runs with the same `niche_keyword` produce identical `expanded_keywords` ordering and fields (product breakdown eval).
- **AS-3.2 (AIO risk):** Each keyword has `aio_risk` consistent with intent (informational → high; transactional → low; commercial appropriately moderate/low per Algo §4.4).
- **AS-3.3 (deduplication):** Normalized duplicates from LLM + DFS merge appear once in `expanded_keywords` (product breakdown).

### US-4 — Edge niches still return usable output

**Acceptance**

- **AS-4.1 (obscure niche):** For an uncommon but valid niche (e.g. septic tank pumping), the pipeline returns a reasonable keyword set without crashing; `expansion_confidence` may be `low`.
- **AS-4.2 (variety):** For a non-generic niche (e.g. mobile dog grooming), expanded terms are specific to that vertical, not boilerplate unrelated services.

## Requirements

### Functional

- **FR-1:** Expose an entry point (e.g. `expand_keywords(niche: str) -> KeywordExpansion`) that accepts a single niche keyword string.
- **FR-2:** Output MUST match the **KeywordExpansion** shape from Algo §4.5 / product breakdown:
  - `niche` (string)
  - `expanded_keywords[]`: each item includes `keyword`, `tier`, `intent`, `source`, `aio_risk`; optional `note` where informational items are volume-only.
  - `total_keywords` (int)
  - `actionable_keywords` (int) — count suitable for transactional/commercial SERP focus
  - `informational_keywords_excluded` (int)
  - `expansion_confidence` ∈ {`high`, `medium`, `low`}
- **FR-3:** Implement the four-step pipeline from Algo §4.2: LLM expansion → DFS suggestions → merge/dedupe/intent filter → tier + intent assignment.
- **FR-4:** Apply intent-based rules from Algo §4.4 for weighting implications (documented in code/constants); informational keywords MUST NOT be scheduled for SERP pulls in M5 (contract for downstream).
- **FR-5:** **Optional niche-level output:** If the LLM classifies whether the niche requires local in-person fulfillment, expose it in a form consumable by M6 (`local_fulfillment_required` per Algo §6.4) without breaking the core KeywordExpansion schema (extension field or parallel return documented in plan phase).

### Non-functional

- **NFR-1:** Unit tests run without network or live API keys (fixtures/mocks for M0/M3).
- **NFR-2:** Integration tests (`@pytest.mark.integration`) MAY validate live LLM + DFS behavior; not required in default CI.

### Implementation mapping (from product breakdown)

- `src/pipeline/keyword_expansion.py` — orchestration
- `src/pipeline/intent_classifier.py` — intent logic
- `src/pipeline/keyword_deduplication.py` — normalize + dedupe

## Success Criteria

| ID | Criterion | Pass condition |
|----|-----------|----------------|
| SC-1 | Head term generation | Expansion for `plumber` includes core head patterns (niche + near me class terms) per AS-1.1 |
| SC-2 | Service term generation | Expansion includes plausible Tier-2 sub-services/modifiers per AS-1.2 |
| SC-3 | Intent classification | 100% of `expanded_keywords` have valid `intent` per AS-1.3 |
| SC-4 | Informational filtering | Informational queries counted and excluded from SERP use per AS-1.5 |
| SC-5 | DFS validation | Suggestions merged; `expansion_confidence` follows overlap rule per AS-2.2 |
| SC-6 | Tier assignment | All keywords have `tier` 1–3 per AS-1.4 |
| SC-7 | Determinism | Same input twice → identical expansion at temp=0 per AS-3.1 |
| SC-8 | AIO risk labeling | `aio_risk` aligns with intent policy per AS-3.2 |
| SC-9 | Edge niche | Obscure niche completes with reasonable output per AS-4.1 |

## Assumptions

- M0 and M3 are available and conform to their published contracts (auth, rate limits, JSON parsing).
- Keyword suggestion filtering for “local/transactional intent signals” follows DataForSEO response fields as implemented in M0; exact filter predicates will be fixed in `/speckit.plan` if API payloads vary.
- `local_fulfillment_required` may be produced during expansion or stubbed with a documented default until M6 consumes it.
- Constants for AIO rates (`INTENT_AIO_RATES`, overlap threshold 30%) live in `src/config/constants.py` per repo rules, not scattered literals.

## Source documentation

- `docs/algo_spec_v1_1.md` — §4.1–§4.6 (pipeline, tiers, intent, schema, confidence)
- `docs/product_breakdown.md` — M4 I/O contract, eval criteria, file layout
- `docs/module_dependency.md` — ordering vs M5/M6
- `docs/data_flow.md` — KeywordExpansion consumed by M5 and M6
