# Requirements

<!-- docguard:version 1.0.0 -->
<!-- docguard:status approved -->
<!-- docguard:last-reviewed 2026-04-05 -->
<!-- docguard:owner @widby-team -->

> Tracks functional requirements, non-functional requirements, and success criteria.
> Use requirement IDs (FR-NNN, NFR-NNN, SC-NNN) for traceability back to code and tests.

---

## Functional Requirements

### Phase 0: Input Configuration (Algo Spec §3)

| ID | Priority | Requirement | Status |
|----|----------|-------------|--------|
| FR-001 | P1 | System MUST accept `niche_keyword` (string), `geo_scope` (state/region/custom), `geo_target`, and optional `strategy_profile` and `report_depth` | Implemented (M0-M3) |
| FR-002 | P1 | System MUST resolve geo targets to MSA/CBSA codes via the Metro Database | Implemented (M1) |
| FR-003 | P1 | System MUST support strategy profiles: `organic_first`, `balanced`, `local_dominant`, `auto` | Implemented (constants.py) |

### Phase 1: Keyword Expansion (Algo Spec §4, Module M4)

| ID | Priority | Requirement | Status |
|----|----------|-------------|--------|
| FR-010 | P1 | System MUST expand a single niche keyword into a classified keyword set with tier, intent, source, and AIO risk | Implemented (M4) |
| FR-011 | P1 | System MUST merge LLM-generated and DataForSEO suggestion candidates into one deduplicated list | Implemented (M4) |
| FR-012 | P1 | System MUST assign intent (transactional/commercial/informational) to every keyword | Implemented (M4) |
| FR-013 | P1 | System MUST assign tier (1=head, 2=service, 3=long-tail) to every keyword | Implemented (M4) |
| FR-014 | P1 | System MUST exclude informational keywords from SERP analysis while tracking counts | Implemented (M4) |
| FR-015 | P2 | System MUST compute `expansion_confidence` from LLM/DFS overlap ratio | Implemented (M4) |
| FR-016 | P1 | System MUST return deterministic output for identical input | Implemented (M4) |

### Phase 2: Data Collection (Module M5)

| ID | Priority | Requirement | Status |
|----|----------|-------------|--------|
| FR-020 | P1 | System MUST collect SERP organic + maps results per metro per actionable keyword | Pending |
| FR-021 | P1 | System MUST collect keyword volume/CPC via DataForSEO | Pending |
| FR-022 | P1 | System MUST collect business listings, reviews, GBP info, backlinks, and Lighthouse data | Pending |
| FR-023 | P2 | System MUST respect DataForSEO rate limits (2000 calls/min) | Implemented (M0) |

### Phase 3-5: Signal Extraction, Scoring, Classification (Modules M6-M8)

| ID | Priority | Requirement | Status |
|----|----------|-------------|--------|
| FR-030 | P1 | System MUST extract demand, organic competition, local competition, AI resilience, and monetization signals | Pending |
| FR-031 | P1 | System MUST compute scores (0-100) for each signal domain | Pending |
| FR-032 | P1 | System MUST compute composite opportunity score with strategy-profile-weighted components | Pending |
| FR-033 | P1 | System MUST classify SERP archetype, AI exposure level, and difficulty tier per metro | Pending |
| FR-034 | P2 | System MUST generate actionable guidance text per metro | Pending |

### Phase 6: Report + Feedback (Module M9)

| ID | Priority | Requirement | Status |
|----|----------|-------------|--------|
| FR-040 | P1 | System MUST assemble a complete report matching the output schema (Algo Spec §10) | Pending |
| FR-041 | P1 | System MUST persist reports and feedback logs to Supabase | Pending |

## Non-Functional Requirements

| ID | Category | Requirement | Metric |
|----|----------|-------------|--------|
| NFR-001 | Performance | Total report generation time < 10 minutes | Measured via `meta.processing_time_seconds` |
| NFR-002 | Performance | Keyword expansion completes within 5-15 seconds | Measured via pipeline timing |
| NFR-003 | Determinism | Identical inputs MUST produce identical outputs at temperature=0 | Verified by repeated-run tests |
| NFR-004 | Cost | Standard 20-metro report < $5.00 API cost | Tracked by CostTracker |
| NFR-005 | Testability | Unit tests run without network or API keys | Enforced by fixture-only test suite |
| NFR-006 | Quality | All Python code passes `ruff check` (line-length 100, py311) | CI gate |
| NFR-007 | Quality | All TypeScript/JS passes `npm run lint` | CI gate |
| NFR-008 | Reliability | Partial upstream failure returns usable low-confidence result | Verified by degraded-mode tests |

## Success Criteria

| ID | Criteria | Measurement | Target |
|----|----------|-------------|--------|
| SC-001 | Non-empty keyword expansion | Unit test: valid niche → non-empty result | 95% of eval set |
| SC-002 | Valid intent + tier labels | Unit test: every keyword has allowed values | 100% |
| SC-003 | Keyword uniqueness | Unit test: no duplicates after normalization | 100% |
| SC-004 | Counter reconciliation | Unit test: summary counts match keyword-level records | 100% |
| SC-005 | Deterministic ordering | Repeated-run test | >=99% identical |
| SC-006 | Informational exclusion tracking | Unit test: exclusions reported at result level | 100% |

## User Input Configuration

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `niche_keyword` | string | Yes | Primary niche term (e.g., "plumber") |
| `geo_scope` | enum | Yes | `state`, `region`, or `custom` |
| `geo_target` | string/list | Yes | State code, region name, or list of MSA codes |
| `report_depth` | enum | No | `standard` (top 20) or `deep` (all). Default: `standard` |
| `strategy_profile` | enum | No | `organic_first`, `balanced`, `local_dominant`, `auto`. Default: `balanced` |

## Strategy Profiles

| Profile | `organic_weight` | `local_weight` | When to use |
|---------|-----------------|----------------|-------------|
| `organic_first` | 0.25 | 0.10 | Classic rank-and-rent: build a site, rank it, rent leads. No GBP needed. |
| `balanced` | 0.15 | 0.20 | Hybrid approach: build a site AND optimize GBP. Default. |
| `local_dominant` | 0.05 | 0.35 | GBP-first: compete primarily in the local pack. |
| `auto` | dynamic | dynamic | System detects local pack presence and adjusts weights. |

## Keyword Classification Rules

| Tier | Pattern | Example (plumber) | Demand Weight |
|------|---------|-------------------|---------------|
| Head (1) | `{niche}`, `{niche} near me`, `{niche} {city}` | "plumber", "plumber near me" | 40% |
| Service (2) | `{sub-service}`, `{modifier} {niche}` | "drain cleaning", "emergency plumber" | 40% |
| Long-tail (3) | `{problem description}`, `{specific job}` | "water heater leaking" | 20% |

| Intent | AIO Trigger Rate | Demand Weight Multiplier | Include in SERP Analysis? |
|--------|-----------------|-------------------------|--------------------------|
| Transactional | ~2.1% | 1.0x | Yes |
| Commercial | ~4.3% | 0.9x | Yes |
| Informational | ~43%+ | 0.3x | No — exclude from SERP pulls |

## Traceability Matrix (M4 — Implemented)

| Requirement | Source File | Test File | Status |
|-------------|------------|-----------|--------|
| FR-010 | `src/pipeline/keyword_expansion.py` | `tests/unit/test_keyword_expansion.py` | ✅ |
| FR-011 | `src/pipeline/keyword_deduplication.py` | `tests/unit/test_keyword_deduplication.py` | ✅ |
| FR-012 | `src/pipeline/intent_classifier.py` | `tests/unit/test_intent_classifier.py` | ✅ |
| FR-013 | `src/pipeline/keyword_expansion.py` | `tests/unit/test_keyword_expansion.py` | ✅ |
| FR-014 | `src/pipeline/keyword_expansion.py` | `tests/unit/test_keyword_expansion.py` | ✅ |
| FR-015 | `src/pipeline/keyword_expansion.py` | `tests/unit/test_keyword_expansion.py` | ✅ |
| FR-016 | `src/pipeline/keyword_expansion.py` | `tests/unit/test_keyword_expansion.py` | ✅ |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-04-05 | DocGuard Init | Initial template |
| 1.0.0 | 2026-04-05 | Migration | Populated from `docs/algo_spec_v1_1.md`, `docs/product_breakdown.md` |
