# Feature: Site Scanning + Weakness Scoring (M11)

**Feature branch:** `M11-site-scanning`  
**Status:** Draft  
**Module ID:** M11  
**Spec references:** `docs/outreach_experiment.md` §5 (Phase E2)

## Summary

Given qualified businesses from M10, the module fetches and analyzes each business website: runs Lighthouse (or equivalent performance/SEO signals), performs on-page and content analysis, detects structured data (schema) presence, computes a consolidated **SEO weakness score**, and assigns each site to a **quality bucket** (nascent / developing / established) for downstream audit personalization.

## Dependencies

- **M0:** DataForSEO client (where E2 uses DFS for on-page/SERP-adjacent fetches per plan—not a substitute for full browser/Lighthouse where required)
- **M10:** Business discovery output (URLs, identifiers, bucket hints, qualification context)

## User Scenarios & Acceptance Scenarios

### US-1 — System measures technical SEO health per site

**Acceptance**

- **AS-1.1 (Lighthouse):** Each eligible URL receives a **Lighthouse** (or approved equivalent) scan; scores and critical audits are persisted on the scan record.
- **AS-1.2 (failure handling):** Timeouts, blocks, or non-HTML responses produce a **structured error** without crashing the batch; partial results are allowed where documented.

### US-2 — Analyst inspects structured data coverage

**Acceptance**

- **AS-2.1 (schema detection):** Scan output includes **schema present / absent** (and optionally types detected) derived from on-page JSON-LD/microdata rules defined in plan.
- **AS-2.2 (false positives):** Detection rules are covered by unit tests with **fixture HTML** for positive and negative cases.

### US-3 — Weakness score differentiates weak vs strong sites

**Acceptance**

- **AS-3.1 (many issues):** Sites with **many** SEO issues (fixture-defined “bad” site) yield weakness score **> 60** on the 0–100 scale used by the product.
- **AS-3.2 (well optimized):** **Well-optimized** fixture sites yield weakness score **< 20**.
- **AS-3.3 (transparent composition):** The score decomposes into documented sub-signals (Lighthouse, on-page, schema, content) for debugging and audit copy.

### US-4 — Quality bucketing aligns with maturity

**Acceptance**

- **AS-4.1 (three buckets):** Every successfully scanned site maps to exactly one of **nascent**, **developing**, **established** per §5 / plan thresholds.
- **AS-4.2 (consistency):** Bucket boundaries are monotonic with weakness score (e.g. higher weakness → more immature bucket) unless experiment doc specifies exceptions.

### US-5 — Content analysis enriches audit inputs

**Acceptance**

- **AS-5.1 (content signals):** Scan output includes **content analysis** features used by M12 (e.g. thin copy, missing service pages, NAP consistency flags)—exact fields fixed in plan.
- **AS-5.2 (PII safety):** Scraped snippets stored for audits avoid logging secrets or unrelated user data; retention matches experiment policy.

## Requirements

### Functional

- **FR-1:** Expose an entry point that accepts **M10 business records** (batch-capable) and returns **SiteScanResult** per business: URL, timestamps, Lighthouse summary, schema flag/types, weakness score breakdown, quality bucket, content features, errors.
- **FR-2:** Implement **site scanning** in `site_scanner.py`: orchestration, concurrency limits, robots/respect policy as defined in plan, caching where appropriate.
- **FR-3:** Implement **weakness scoring** in `weakness_scorer.py` as a **pure function** of scan features (no side effects) per repo scoring rules.
- **FR-4:** Implement **quality bucketing** in `quality_bucketing.py` mapping weakness + optional content thresholds to **nascent / developing / established**.
- **FR-5:** Persist or return data in a shape **stable for M12** (audit generator consumes scan + bucket + issues list).

### Non-functional

- **NFR-1:** Unit tests use HTML/Lighthouse JSON **fixtures**—no live network in default CI.
- **NFR-2:** Scan concurrency and timeouts are configurable (constants or config module) to protect cost and runtime.

### Implementation mapping

- `src/experiment/site_scanner.py` — fetch, Lighthouse integration, on-page extraction
- `src/experiment/weakness_scorer.py` — composite SEO weakness score
- `src/experiment/quality_bucketing.py` — nascent / developing / established assignment

## Success Criteria

| ID | Criterion | Pass condition |
|----|-----------|----------------|
| SC-1 | Lighthouse | Lighthouse (or equivalent) runs and records audits per AS-1.1 |
| SC-2 | Schema | Present/absent (and types if required) per AS-2.1–AS-2.2 |
| SC-3 | Weak score high | “Many issues” fixture scores **> 60** per AS-3.1 |
| SC-4 | Weak score low | Well-optimized fixture scores **< 20** per AS-3.2 |
| SC-5 | Buckets | All scanned sites assigned to **nascent / developing / established** per AS-4.1 |
| SC-6 | Content analysis | Content features emitted for M12 per AS-5.1 |
| SC-7 | Resilience | Batch completes with structured errors for bad URLs per AS-1.2 |

## Assumptions

- Lighthouse execution environment (CLI, headless Chrome, or managed API) is chosen in `/speckit.plan`; this spec treats Lighthouse as the **required technical audit source** unless the experiment doc is updated.
- DataForSEO usage in E2 is optional/supplementary; M0 is listed as a dependency for consistency with product breakdown—actual DFS calls are plan-specific.
- Weakness score scale is **0–100** with **higher = weaker** unless plan inverts for display only.

## Source documentation

- `docs/outreach_experiment.md` — §5 (Phase E2)
- `docs/product_breakdown.md` — M11 I/O contract, eval criteria, file layout (if present)
- `docs/module_dependency.md` — ordering vs M10 and M12
- `docs/data_flow.md` — scan results consumed by audit generation
