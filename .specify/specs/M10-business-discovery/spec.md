# Feature: Business Discovery + Qualification (M10)

**Feature branch:** `M10-business-discovery`  
**Status:** Draft  
**Module ID:** M10  
**Spec references:** `docs/outreach_experiment.md` §4 (Phase E1), §5.3 (Qualification Gates)

## Summary

For a given niche+metro, the experiment framework discovers candidate businesses via DataForSEO Business Listings, resolves contact emails where possible, applies qualification gates (including chain filtering and site-quality heuristics), and emits a stratified sample grouped into three outreach buckets for downstream site scanning and audits.

## Dependencies

- **M0:** DataForSEO client (Business Listings and related endpoints, auth, caching, cost controls)
- **M1:** Metro database (canonical metro identifiers and geo parameters for listing queries)

## User Scenarios & Acceptance Scenarios

### US-1 — Operator discovers a sufficient business pool for a niche+metro

**Acceptance**

- **AS-1.1 (volume):** For a typical local niche in a mid-size metro, discovery returns **at least 50** qualified or pre-qualified businesses before stratified sampling (eval: discovery ≥ 50).
- **AS-1.2 (geo binding):** Listing requests use M1 metro resolution so results are scoped to the intended metro (no silent cross-metro bleed).

### US-2 — System filters chains and unsuitable entities

**Acceptance**

- **AS-2.1 (chain filtering):** National or franchise chains identified by configured rules (name patterns, brand lists, or API flags) are excluded or tagged **ineligible** for outreach per Experiment Framework qualification policy.
- **AS-2.2 (traceability):** Each excluded business records a **reason code** (e.g. `chain`, `no_website`, `high_quality_site`) for audit and tuning.

### US-3 — Contact email discovery supports outreach readiness

**Acceptance**

- **AS-3.1 (email discovery):** For businesses with a public site or listing metadata, the pipeline attempts email discovery and attaches **verified or candidate** emails with source metadata (scraped, API, inferred) where the spec allows.
- **AS-3.2 (no email handling):** Businesses without a discoverable email are either dropped or routed to a **manual / alternate channel** bucket per product rules; behavior is documented and test-covered.

### US-4 — Qualification gates enforce outreach eligibility

**Acceptance**

- **AS-4.1 (no website):** Businesses **without a website URL** (or with unusable/placeholder URLs) are **ineligible** for standard outreach track.
- **AS-4.2 (high-quality site):** Businesses whose sites meet **high-quality** criteria (e.g. strong technical/content signals defined in plan) are **ineligible** for the “weak site” experiment arm—matching §5.3 qualification intent.

### US-5 — Stratified sampling produces three buckets

**Acceptance**

- **AS-5.1 (three buckets):** The output partitions eligible candidates into **exactly three** stratified buckets (names and definitions per `docs/outreach_experiment.md` / plan) for balanced experiment cells.
- **AS-5.2 (deterministic sampling):** Given fixed inputs and a fixed random seed, bucket assignment is reproducible in tests.

## Requirements

### Functional

- **FR-1:** Expose orchestration that accepts **niche + metro** (M1-backed) and returns a **BusinessDiscoveryResult** (exact schema fixed in `/speckit.plan`) including discovered businesses, qualification outcomes, emails, and bucket assignments.
- **FR-2:** Implement **business discovery** via DataForSEO Business Listings (M0), with pagination/batching and idempotent deduplication by stable business keys where available.
- **FR-3:** Implement **email discovery** as a separate concern (harvest from listings, site crawl hints, or third-party as approved in plan) with explicit **confidence/source** fields.
- **FR-4:** Implement **business qualification** applying §5.3 gates: no-website ineligibility, high-quality-site ineligibility, chain filtering, plus any additional gates from the experiment doc.
- **FR-5:** Implement **stratified sampling** into **three buckets** with documented stratification dimensions (e.g. weakness proxy, size, or random-with-quota per plan).

### Non-functional

- **NFR-1:** Unit tests run without network (M0 mocked; M1 fixtures for metro resolution).
- **NFR-2:** Integration tests (`@pytest.mark.integration`) MAY hit live DataForSEO; not required in default CI.

### Implementation mapping

- `src/experiment/business_discovery.py` — listings fetch, dedupe, niche+metro binding
- `src/experiment/email_discovery.py` — email resolution and metadata
- `src/experiment/business_qualification.py` — gates, chain filter, eligibility, bucketing input

## Success Criteria


| ID   | Criterion          | Pass condition                                                                |
| ---- | ------------------ | ----------------------------------------------------------------------------- |
| SC-1 | Discovery volume   | Typical niche+metro yields **≥ 50** businesses in discovery set per AS-1.1    |
| SC-2 | Chain filtering    | Chains excluded or marked ineligible with reason per AS-2.1                   |
| SC-3 | Email discovery    | Email fields populated where spec expects; sources recorded per AS-3.1        |
| SC-4 | No website gate    | No-website businesses ineligible per AS-4.1                                   |
| SC-5 | High-quality gate  | High-quality sites ineligible for weak-site arm per AS-4.2                    |
| SC-6 | Stratified buckets | Three buckets with reproducible assignment under fixed seed per AS-5.1–AS-5.2 |
| SC-7 | Traceability       | Exclusions carry reason codes per AS-2.2                                      |


## Assumptions

- DataForSEO Business Listings payloads and rate limits are as documented when M0 was built; field mapping for “chain” or brand detection may require plan-time alignment with actual API responses.
- “High-quality site” pre-screen may use lightweight signals (e.g. listing richness only) until M11 provides full weakness scores; if so, M10 MUST not duplicate M11’s full scoring—only gates documented for E1.
- Constants (thresholds, chain lists, bucket quotas) live in `src/config/constants.py` per repo rules.

## Source documentation

- `docs/outreach_experiment.md` — §4 (Phase E1), §5.3 (Qualification Gates)
- `docs/product_breakdown.md` — M10 I/O contract, eval criteria, file layout (if present)
- `docs/module_dependency.md` — ordering vs M11+
- `docs/data_flow.md` — handoff to site scanning