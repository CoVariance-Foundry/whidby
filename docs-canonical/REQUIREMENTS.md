# Requirements

<!-- docguard:version 1.2.0 -->
<!-- docguard:status approved -->
<!-- docguard:last-reviewed 2026-07-11 -->
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
| FR-042 | P1 | Interactive first reports MUST make bounded attempts for one keyword-volume batch, at most six representative eligible organic SERPs, one maps SERP, GBP info, and business listings. Backlinks, Lighthouse, review-velocity acquisition, and generated M8 copy are optional enrichment and MUST NOT block the first readable report. If providers fail, the system MUST persist and immediately read a complete degraded report containing the normalized seed keyword, resolved target, complete report schema, deterministic fallback signals and scores, low confidence, and structured provider failures. | Planned (Feature 016) |

### Consumer Synthesis Reflow

| ID | Priority | Requirement | Status |
|----|----------|-------------|--------|
| FR-100 | P1 | Consumer app MUST treat Widby Synthesis Reflow as a full production replacement for the stale strategy gallery/proto-convergence direction, not as a parallel experiment | Planned |
| FR-101 | P1 | Segment routing MUST map `find_first -> /`, `scale -> /strategies`, `coach_agency -> /agency`, and `researching -> /explore` from persisted profile/report state | Planned |
| FR-102 | P1 | The `find_first` dashboard MUST use the A2 starter hero as the first useful surface and preserve existing entitlement/quota gates for fresh scans | Planned |
| FR-103 | P1 | `/strategies` MUST render a B2 path/rail instead of a flat gallery while keeping the nav label `Strategies` | Planned |
| FR-104 | P1 | Strategy unlocks MUST be shared state: scan completion advances Easy Win to GBP Blitz, ranked-site declaration unlocks Expand & Conquer, and Keyword Hijack requires feasibility preflight before spend | Planned |
| FR-105 | P1 | The visible catalog MUST include Easy Win, GBP Blitz, Expand & Conquer, Keyword Hijack, and locked Portfolio Builder only; all other cross-metro plays remain deferred | Planned |
| FR-106 | P1 | Report V1.1 MUST be the durable detail surface behind inline strategy results and include path-aware next steps | Planned |
| FR-107 | P1 | AI Resilience MUST be a shared modifier with default threshold `40`, configurable in scan/user controls where exposed | Planned |
| FR-108 | P1 | The reflow MUST preserve existing account entitlement, quota consumption/refund, and cached-report visibility behavior | Planned |
| FR-109 | P2 | GBP Blitz copy MUST stay soft on address requirements and MUST NOT introduce an address-dependent scoring engine in this project | Planned |
| FR-110 | P2 | `balanced` weighting MAY remain available internally/debugging, but MUST NOT be presented as a user-facing strategy choice in the synthesis reflow | Planned |

## Non-Functional Requirements

| ID | Category | Requirement | Metric |
|----|----------|-------------|--------|
| NFR-001 | Performance | Interactive first-report acceptance MUST return a successful `POST /api/niches/score` with a non-null `report_id` and no `persist_warning`, then immediately return a successful, schema-valid `GET /api/niches/{report_id}` for that same ID within `<= 60.0` seconds under one shared deadline measured from immediately before POST through GET parsing and validation. | Production-image Docker acceptance gate |
| NFR-002 | Performance | Keyword expansion completes within 5-15 seconds | Measured via pipeline timing |
| NFR-003 | Determinism | Identical inputs MUST produce identical outputs at temperature=0 | Verified by repeated-run tests |
| NFR-004 | Cost | Standard 20-metro report < $5.00 API cost | Tracked by CostTracker |
| NFR-005 | Testability | Unit tests run without network or API keys | Enforced by fixture-only test suite |
| NFR-006 | Quality | All Python code passes `ruff check` (line-length 100, py311) | CI gate |
| NFR-007 | Quality | All TypeScript/JS passes `npm run lint` | CI gate |
| NFR-008 | Reliability | Partial upstream failure returns usable low-confidence result | Verified by degraded-mode tests |
| NFR-009 | Execution | Every synthesis reflow child ticket records exact tests, visual evidence paths, and residual risks in Linear before closeout | Linear handoff gate |
| NFR-010 | Frontend QA | Every touched frontend state has Playwright coverage or an explicit no-frontend-change note plus desktop/mobile screenshot evidence when UI changes | Visual QA gate |
| NFR-011 | Source of truth | Readiness claims MUST be based on current repo, CI, rendered UI, and live-provider evidence when relevant; memory-only claims are prohibited | Review gate |
| NFR-012 | Memory | Every accepted cold or repeated interactive first-report run MUST keep cgroup v2 `memory.peak <= 500000000` bytes. | Production-image container launched with `--memory=500000000 --memory-swap=500000000` |
| NFR-013 | Retained state | Three sequential interactive reports in one container MUST each pass NFR-001; after five seconds of quiescence following each report, `memory.current <= 500000000` bytes and process RSS `<= 500000000` bytes, and neither run-three value may exceed its run-one value by more than `50000000` bytes. | Three-run production-image retained-state gate |

## Success Criteria

| ID | Criteria | Measurement | Target |
|----|----------|-------------|--------|
| SC-001 | Non-empty keyword expansion | Unit test: valid niche → non-empty result | 95% of eval set |
| SC-002 | Valid intent + tier labels | Unit test: every keyword has allowed values | 100% |
| SC-003 | Keyword uniqueness | Unit test: no duplicates after normalization | 100% |
| SC-004 | Counter reconciliation | Unit test: summary counts match keyword-level records | 100% |
| SC-005 | Deterministic ordering | Repeated-run test | >=99% identical |
| SC-006 | Informational exclusion tracking | Unit test: exclusions reported at result level | 100% |
| SC-100 | Synthesis source of truth | Canonical docs and execution runbook describe the accepted routing, unlock, catalog, and verification contract | 100% before Wave 1 |
| SC-101 | Visual replacement confidence | Playwright traces/screenshots cover every frontend state touched by a synthesis child ticket | 100% of touched states |
| SC-102 | Entitlement preservation | Existing free/plus/pro/quota-exempt tests continue to pass after synthesis changes | 100% of existing gates |

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

## Traceability Matrix (Synthesis Reflow - Planned)

| Requirement | Source File / Contract | Test / Evidence | Status |
|-------------|------------------------|-----------------|--------|
| FR-100 | `docs-canonical/ARCHITECTURE.md`, `docs/widby-synthesis-reflow-agent-runbook.md` | `npx docguard-cli guard`, Linear handoff | Planned |
| FR-101 | `apps/app/src/lib/onboarding/`, future segment router | Segment-router unit tests + Playwright routing smoke | Planned |
| FR-102 | `apps/app/src/components/home/`, `apps/app/src/app/(protected)/page.tsx` | Component tests + dashboard visual QA | Planned |
| FR-103 | `apps/app/src/app/(protected)/strategies/`, strategy path registry | Component tests + `/strategies` Playwright visual QA | Planned |
| FR-104 | Strategy path registry + ranked-site declaration state | Unit tests for unlock matrix + E2E unlock smoke | Planned |
| FR-105 | Strategy path registry | Catalog contract tests + screenshot of locked Portfolio Builder | Planned |
| FR-106 | `apps/app/src/app/(protected)/reports/` | Report V1.1 component tests + report detail visual QA | Planned |
| FR-107 | Shared AI Resilience controls/state | Unit/component tests for threshold `40` and user overrides | Planned |
| FR-108 | Existing entitlement/quota routes and tests | Existing route tests plus touched-flow E2E | Planned |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-04-05 | DocGuard Init | Initial template |
| 1.0.0 | 2026-04-05 | Migration | Populated from `docs/algo_spec_v1_1.md`, `docs/product_breakdown.md` |
| 1.1.0 | 2026-06-30 | Synthesis Reflow | Added product replacement, segment routing, unlock, catalog, Report V1.1, and agent execution requirements |
| 1.2.0 | 2026-07-11 | First-report performance | Replaced the stale ten-minute target with the synchronous 60-second readable-report contract, bounded interactive evidence, 500,000,000-byte peak, and repeated-state limits |
