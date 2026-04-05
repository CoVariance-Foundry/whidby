# Feature: Data Collection Pipeline (M5)

**Feature branch:** `M05-data-collection`  
**Status:** Draft  
**Module ID:** M5  
**Spec references:** `docs/algo_spec_v1_1.md` §5 (Phase 2); `docs/product_breakdown.md` (M5)

## Summary

For a keyword expansion (M4), a list of metros (M1), and a strategy profile, the pipeline plans and executes all DataForSEO calls required for the scoring engine: volume/CPC for every keyword × metro, SERP and maps for eligible keywords and cities, then dependent calls (backlinks, Lighthouse, GBP, reviews, business listings) with batching, ordering, resilience, and aggregated cost/latency metadata.

## Dependencies

- **M0:** DataForSEO client (queue + live endpoints, caching, retries, per-call cost)
- **M1:** Metro database (CBSA, principal cities, DataForSEO location codes)
- **M4:** Keyword expansion (tiers, intents, which keywords get SERP vs volume-only per Algo §5)

## User Scenarios & Acceptance Scenarios

### US-1 — Collect full raw dataset for one metro

**Acceptance**

- **AS-1.1 (data types):** For a single metro, `RawCollectionResult.metros[cbsa]` includes slots for: `serp_organic`, `serp_maps`, `keyword_volume`, `business_listings`, `google_reviews`, `gbp_info`, `backlinks`, `lighthouse` (product breakdown; empty where legitimately not applicable MUST be explicit, not missing keys if contract is fixed dict).
- **AS-1.2 (SERP scope):** SERP organic pulls run only for Tier 1 and Tier 2 keywords with transactional or commercial intent; informational keywords receive keyword volume (+ CPC) only, not SERP analysis (Algo §5.1 optimization).
- **AS-1.3 (principal cities):** Organic SERP collection uses M1 principal cities for the metro (Algo §3.x city-level pull, aggregated later in M6).

### US-2 — Collect for multiple metros

**Acceptance**

- **AS-2.1 (partitioning):** Results are keyed by metro identifier (e.g. CBSA code `38060`) with no cross-metro leakage.
- **AS-2.2 (consistency):** Each metro receives the same keyword volume coverage for the full expanded set; SERP subsets follow the same tier/intent rules per metro.

### US-3 — Dependent calls run in correct order

**Acceptance**

- **AS-3.1 (Step 1 parallel):** Keyword volume tasks and SERP tasks for eligible keywords start without waiting for each other (Algo §5.2 Step 1).
- **AS-3.2 (Step 2 dependencies):** Backlink summaries use domains derived from organic SERP top results; Lighthouse targets top organic URLs; GBP info targets top GBP listings; Google Reviews target top local-pack businesses — no backlink/Lighthouse/GBP/review call is issued before its prerequisite SERP (or maps) identifiers exist (Algo §5.2 Step 2).
- **AS-3.3 (dedup):** Backlink calls deduplicate domains globally across metros where specified in Algo §5.2 (implementation records dedup stats in meta if useful).

### US-4 — Cost, time, and failures are visible

**Acceptance**

- **AS-4.1 (cost tracking):** `meta.total_cost_usd` equals the sum of per-call costs returned by M0 for that run (within floating-point tolerance), matching product breakdown eval.
- **AS-4.2 (call count):** `meta.total_api_calls` reflects executed tasks (including queue round-trips as counted by the client contract).
- **AS-4.3 (duration):** `meta.collection_time_seconds` captures wall-clock for the orchestrated collection.
- **AS-4.4 (error resilience):** If one sub-task fails, other independent tasks complete; failures are listed in `meta.errors` with enough context to retry or diagnose (product breakdown).

### US-5 — SERP features are preserved for downstream parsing

**Acceptance**

- **AS-5.1 (raw features):** Stored SERP payloads retain structured feature flags needed by M6 (`ai_overview`, `local_pack`, `featured_snippet`, `people_also_ask`, ads, LSA, etc.) per Algo §5.1 SERP feature extraction note.

### US-6 — Keyword volume batching is efficient

**Acceptance**

- **AS-6.1 (700 limit):** Up to 700 keywords per metro are submitted in a single search volume task (ceil division per Algo §5.1); the planner MUST NOT issue one task per keyword when under the batch limit (product breakdown “batch efficiency”).

## Requirements

### Functional

- **FR-1:** Entry point (e.g. `collect_data(keywords, metros, strategy_profile) -> RawCollectionResult`) accepts:
  - Keyword expansion object from M4 (full set + tier/intent metadata)
  - List of metro records from M1
  - `strategy_profile` string (passed through for logging/plan variance if any; core matrix per Algo §5)
- **FR-2:** Output **RawCollectionResult** structure per product breakdown:
  - `metros`: map of metro id → per-type raw response collections (organic SERP per keyword, maps, volume rows, listings, reviews, GBP, backlinks, lighthouse)
  - `meta`: `total_api_calls`, `total_cost_usd`, `collection_time_seconds`, `errors` (list)
- **FR-3:** Implement collection phases per Algo §5.2 with explicit dependency graph in code (`collection_plan.py` + `batch_executor.py`).
- **FR-4:** Enforce SERP vs volume-only keyword filtering per Algo §5.1 (Tier 1+2 transactional/commercial → SERP; informational → volume only).
- **FR-5:** Maps SERP: scope per Algo matrix (e.g. head term per metro/city as spec’d — planner MUST encode the spec’s “M × 1 head term” rule explicitly).

### Non-functional

- **NFR-1:** Respect M0 rate limits, retries, and cache TTLs.
- **NFR-2:** Unit tests use fixtures (`mock_serp_response.json`, etc.); no live API in default CI.

### Implementation mapping (from product breakdown)

- `src/pipeline/data_collection.py` — orchestrator
- `src/pipeline/collection_plan.py` — plan from keywords + metros
- `src/pipeline/batch_executor.py` — ordered/concurrent execution
- `src/pipeline/result_assembler.py` — normalize into RawCollectionResult

## Success Criteria

| ID | Criterion | Pass condition |
|----|-----------|----------------|
| SC-1 | Single metro | All eight data categories populated or explicitly empty per contract per AS-1.1 |
| SC-2 | Multi-metro | Correct partitioning per AS-2.1 |
| SC-3 | Dependency ordering | Backlinks/Lighthouse/GBP/Reviews never precede required SERP-derived inputs per AS-3.2 |
| SC-4 | Cost tracking | `meta.total_cost_usd` matches summed call costs per AS-4.1 |
| SC-5 | Error resilience | Partial failure still returns partial data + `meta.errors` per AS-4.4 |
| SC-6 | SERP feature preservation | Raw payloads usable by M6 for feature detection per AS-5.1 |
| SC-7 | Keyword filtering | No organic SERP task for informational-only keywords per AS-1.2 |
| SC-8 | Batch efficiency | Volume tasks respect 700-keyword batching per AS-6.1 |

## Assumptions

- M0 endpoint wrappers exist for each row in Algo §5.1 matrix (task_post/task_get vs live documented per endpoint).
- Exact “top N domains / businesses” counts (5 organic domains, 3 pack businesses, etc.) follow Algo §5.2; if implementation chooses slightly different N, product_breakdown and this spec MUST be updated in the same PR.
- Strategy profile does not change the API matrix in V1 unless explicitly added in plan/tasks; default is balanced pass-through.

## Source documentation

- `docs/algo_spec_v1_1.md` — §5.1–§5.3 (matrix, order, cost model)
- `docs/product_breakdown.md` — M5 I/O, eval criteria, fixtures
- `docs/module_dependency.md` — M4 → M5 → M6
- `docs/data_flow.md` — RawCollectionResult → M6
