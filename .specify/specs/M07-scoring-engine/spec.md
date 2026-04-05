# Feature Specification: M7 Scoring Engine

**Feature Branch**: `007-m07-scoring-engine`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: Module M7 — deterministic scoring from extracted signals (Algo Spec V1.1, §7 Phase 4)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sub-scores and composite from signals (Priority: P1)

As a Widby operator, I need each metro’s extracted signals turned into five interpretable sub-scores plus one composite opportunity score so I can compare metros on demand, competition, monetization, and AI resilience in a single run.

**Why this priority**: Without bounded sub-scores and a composite, downstream ranking and reporting cannot exist.

**Independent Test**: Given validated `metro_signals` and a cohort `all_metro_signals`, running the scoring engine produces one `MetroScores` record per metro with all numeric scores in range and a composite consistent with the spec.

**Acceptance Scenarios**:

1. **Given** complete signals for a metro and a non-empty `all_metro_signals` cohort, **When** scoring runs with a valid `strategy_profile`, **Then** outputs include `demand`, `organic_competition`, `local_competition`, `monetization`, and `ai_resilience` each on a 0–100 scale and an `opportunity` composite.
2. **Given** the same inputs and profile, **When** scoring runs twice, **Then** numeric outputs are identical (reproducible given same inputs and constants).
3. **Given** competition-oriented signals, **When** scores are computed, **Then** higher competitive pressure does not incorrectly inflate opportunity (competition inversion behavior per algo spec).

---

### User Story 2 - Strategy profile-aware weighting (Priority: P2)

As a Widby operator, I need the composite and contributing logic to respect the active strategy profile so rankings reflect my rank-and-rent posture (not a one-size-fits-all weighting).

**Why this priority**: Strategy profiles are a core product differentiator for practitioner workflows.

**Independent Test**: Switching only `strategy_profile` changes `resolved_weights` and may change composite ordering while sub-score components remain well-defined.

**Acceptance Scenarios**:

1. **Given** two distinct valid strategy profiles and the same signal inputs, **When** scoring runs for each, **Then** `resolved_weights` differ in a way documented by the algo spec and composite scores may differ accordingly.
2. **Given** a profile with defined weight constraints, **When** scoring runs, **Then** emitted `resolved_weights` satisfy those constraints (e.g. normalization and bounds per spec).

---

### User Story 3 - Confidence, gates, and percentiles (Priority: P3)

As a Widby operator, I need confidence to reflect data quality and rule outcomes (including flags and penalties), and sub-scores that depend on cohort context (e.g. percentiles) to use the full metro set I’m evaluating.

**Why this priority**: Prevents false certainty and enables fair relative ranking within a batch.

**Independent Test**: Injecting known signal gaps or threshold failures changes confidence (score and/or flags) predictably; percentile-based components move when cohort composition changes.

**Acceptance Scenarios**:

1. **Given** `all_metro_signals` for percentile ranking, **When** a metro’s relative position in the cohort changes, **Then** percentile-dependent components update consistently with the new cohort.
2. **Given** inputs that trigger review-barrier, no-local-pack default, CPC scaling, AI floor, or threshold-gate rules per spec, **When** scoring runs, **Then** the resulting scores and confidence reflect those rules (including penalties where specified).
3. **Given** local-service vs informational niches, **When** AI resilience is scored, **Then** behavior matches the distinct handling defined in the algo spec for each case.

---

### Edge Cases

- Missing or partial signals for a metro: scores and confidence degrade gracefully per spec (flags/penalties), without throwing for recoverable gaps.
- Single-metro or very small cohorts: percentile logic remains defined (documented fallback or degenerate behavior per algo spec).
- Boundary values at 0 and 100: all emitted sub-scores remain clamped or validated to 0–100 inclusive.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST consume `metro_signals`, cohort `all_metro_signals` (for percentile ranking), and `strategy_profile` as defined in `docs/algo_spec_v1_1.md` §7 and `docs/data_flow.md`.
- **FR-002**: System MUST depend on M6 signal extraction output only for signal inputs (no re-fetching raw SERP/API data inside pure scoring functions).
- **FR-003**: System MUST produce `MetroScores` containing: `demand`, `organic_competition`, `local_competition`, `monetization`, `ai_resilience` (all 0–100), `opportunity` composite, `confidence` (numeric score plus flags), and `resolved_weights`.
- **FR-004**: System MUST implement competition inversion, review barrier, no-local-pack default, CPC scaling, AI resilience (local services vs informational), threshold gate, AI floor, strategy profile resolution, confidence penalties, and percentile ranking exactly as specified in Algo Spec V1.1 §7.
- **FR-005**: Scoring functions MUST remain pure (no side effects, no I/O) per `docs/product_breakdown.md` / project architecture rules.
- **FR-006**: System MUST keep research constants (weights, thresholds, rate-related scalars) in configuration (e.g. `src/config/constants.py`) rather than undocumented literals.
- **FR-007**: Module implementation MUST be decomposed across the following artifacts: `src/scoring/engine.py`, `demand_score.py`, `organic_competition_score.py`, `local_competition_score.py`, `monetization_score.py`, `ai_resilience_score.py`, `composite_score.py`, `confidence_score.py`, `strategy_profiles.py`, `normalization.py`.

### Key Entities

- **MetroSignals (input)**: Per-metro extracted signals from M6, including fields required for the five sub-scores and confidence.
- **MetroScores (output)**: Per-metro scoring result with sub-scores, composite, confidence breakdown, and `resolved_weights`.
- **Strategy profile**: Named configuration determining weighting and profile-specific rules for composite resolution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every scored metro in a batch, all five sub-scores and the composite are present and each lies in the closed interval 0–100.
- **SC-002**: For a fixed input fixture and strategy profile, 100% of repeated scoring runs produce identical outputs (reproducibility).
- **SC-003**: Automated evaluation covers: score range 0–100, competition inversion, review barrier, no-local-pack default, CPC scaling, AI resilience (local services and informational), threshold gate, AI floor, strategy profiles, confidence penalties, percentile ranking, and reproducibility — with failing tests blocking merge.
- **SC-004**: Changing only the cohort used for percentiles changes only the components documented as cohort-relative, without breaking validity of all sub-scores.

## Assumptions

- M6 output schema is stable for M7 development; any contract change updates `docs/data_flow.md` and `docs/product_breakdown.md` in the same delivery.
- Strategy profiles enumerated in product specs cover all launch personas; new profiles are additive and documented before use in production scoring.
- Constants in `src/config/constants.py` reflect Algo Spec V1.1 §7; spec changes drive constant updates and migration notes.

## Source specifications

| Document | Role |
|----------|------|
| `docs/algo_spec_v1_1.md` | §7 (Phase 4) — authoritative formulas, gates, floors, and score semantics |
| `docs/product_breakdown.md` | Module map, file layout, eval criteria for M7 |
| `docs/module_dependency.md` | M7 position in the DAG (after M6) |
| `docs/data_flow.md` | `metro_signals` → `MetroScores` contracts |
