# Feature: Experiment Analysis + Rentability Signal (M15)

**Feature branch:** `M15-experiment-analysis`  
**Status:** Draft  
**Module ID:** M15  
**Spec references:** `docs/outreach_experiment.md` §9 (Phase E6); `docs/product_breakdown.md` (M15)

## Summary

Analyzes completed outreach experiments: computes per-variant metrics, performs Bayesian (or spec-defined) A/B comparisons with segment breakdowns, derives a **rentability signal** with shrinkage for small samples, persists the signal to Supabase for consumption by M7, and documents how the Widby scoring pipeline reads that signal.

## Dependencies

- **M14:** Event log, reply classifications, engagement scores, audit analytics
- **M2 (Supabase):** Read experiment results; write rentability signal rows and provenance metadata

## User Scenarios & Acceptance Scenarios

### US-1 — Analyst reviews experiment outcomes

**Acceptance**

- **AS-1.1 (metrics):** For each variant, the analyzer emits core rates (e.g. reply rate, positive rate, click-to-reply) as defined in plan; denominators exclude suppressed/ineligible sends per documented rules.
- **AS-1.2 (segments):** Metrics can be broken down by at least one dimension from plan (e.g. metro, niche bucket, template id) without cross-segment leakage.

### US-2 — A/B decision support is statistically principled

**Acceptance**

- **AS-2.1 (Bayesian comparison):** Variant A vs B comparison produces a posterior or credible-interval style summary (exact method fixed in `ab_analysis.py` spec in plan) suitable for “probability B beats A” style reporting.
- **AS-2.2 (small samples):** Wide credible intervals or explicit “insufficient data” flags appear when cell sizes fall below thresholds in plan.

### US-3 — Rentability signal feeds scoring (M7)

**Acceptance**

- **AS-3.1 (scale):** Published `rentability_score` for a standard experiment with ~**5% response rate** falls in the **40–70** band (calibration constants live in `src/config/constants.py`).
- **AS-3.2 (shrinkage):** For small n, the signal **shrinks toward 50** (neutral) per a documented formula in `rentability_signal.py` (no hardcoded magic numbers outside constants module).
- **AS-3.3 (persistence):** Final signal + metadata (experiment id, variant id, computed_at, inputs hash) are written to Supabase for auditability.

### US-4 — M7 integration contract is explicit

**Acceptance**

- **AS-4.1 (read path):** M7 scoring reads the signal via a documented query/view or injected field on the scoring input DTO; absence of signal uses a documented default (e.g. 50 or “no uplift”) without crashing.

## Requirements

### Functional

- **FR-1:** Implement `src/experiment/experiment_analyzer.py` to aggregate M14 data into experiment-level and variant-level metric tables.
- **FR-2:** Implement `src/experiment/ab_analysis.py` for pairwise and multi-variant comparisons per Bayesian (or approved frequentist) plan in `/speckit.plan`.
- **FR-3:** Implement `src/experiment/rentability_signal.py` to map metrics + uncertainty into a single score with shrinkage and calibration to the 40–70 anchor for 5% response.
- **FR-4:** Write outputs to Supabase including lineage fields for reproducibility (input snapshot ids or hashes).
- **FR-5:** Document and implement the M7 read contract (module boundary: scoring reads signal, does not re-implement experiment math).

### Non-functional

- **NFR-1:** Analysis jobs are deterministic given fixed inputs and constants (no LLM in core metric path unless explicitly added in plan).
- **NFR-2:** Unit tests cover edge cases: zero sends, 100% bounce, single reply, extreme rates.

### Implementation mapping (from product breakdown / this spec)

- `src/experiment/experiment_analyzer.py` — metric computation
- `src/experiment/ab_analysis.py` — A/B and multi-arm analysis
- `src/experiment/rentability_signal.py` — shrinkage + calibration + Supabase write

## Success Criteria

| ID | Criterion | Pass condition |
|----|-----------|----------------|
| SC-1 | Metric computation | Variant metrics match fixture datasets per AS-1.1 |
| SC-2 | Segment breakdown | Segment slices sum correctly per AS-1.2 |
| SC-3 | A/B Bayesian | Comparison output matches approved method per AS-2.1 |
| SC-4 | Small-sample behavior | Shrinkage toward 50 + uncertainty flags per AS-2.2 / AS-3.2 |
| SC-5 | Calibration | 5% response calibration in 40–70 band per AS-3.1 |
| SC-6 | Supabase write | Signal + metadata persisted per AS-3.3 |
| SC-7 | M7 integration | Documented read path + safe default per AS-4.1 |

## Assumptions

- Experiment and variant identifiers are stable across M13–M15; renaming requires a migration plan.
- “5% response rate” anchor refers to reply rate unless outreach spec names a different primary KPI; plan clarifies if split metrics are used.
- M7 changes to consume the signal may land in the same delivery branch or a follow-up task but the contract is defined here and in `docs/algo_spec_v1_1.md` if scores are affected.

## Source documentation

- `docs/outreach_experiment.md` — §9 / Phase E6 (analysis and feedback)
- `docs/product_breakdown.md` — M15 I/O, eval criteria, file layout
- `docs/algo_spec_v1_1.md` — M7 scoring inputs if rentability signal alters composite score
- `docs/module_dependency.md` — M14 → M15 → M7 feedback loop
- `docs/data_flow.md` — signal persistence and read path
