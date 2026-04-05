# Tasks: M07 Scoring Engine

**Input**: Design documents from `/.specify/specs/M07-scoring-engine/`  
**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`

**Tests**: Tests are required by the feature spec (`SC-003`) and must be written first for each story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`)
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create feature-local design artifacts and base scaffolding required for implementation.

- [X] T001 Create rule-mapping notes in `.specify/specs/M07-scoring-engine/research.md`
- [X] T002 Define M07 input/output entities in `.specify/specs/M07-scoring-engine/data-model.md`
- [X] T003 [P] Add execution and validation scenarios in `.specify/specs/M07-scoring-engine/quickstart.md`
- [X] T004 [P] Define `MetroScores` contract schema in `.specify/specs/M07-scoring-engine/contracts/metro-scores.schema.json`
- [X] T005 [P] Add M07 constants placeholders and documented defaults in `src/config/constants.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core building blocks that must exist before user story implementation.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [X] T006 Create deterministic scoring fixtures in `tests/fixtures/m07_scoring_fixtures.py`
- [X] T007 [P] Implement base normalization helpers (`clamp`, safe scaling, percentile helpers scaffold) in `src/scoring/normalization.py`
- [X] T008 [P] Add score module skeletons with typed function signatures in `src/scoring/demand_score.py`
- [X] T009 [P] Add score module skeletons with typed function signatures in `src/scoring/organic_competition_score.py`
- [X] T010 [P] Add score module skeletons with typed function signatures in `src/scoring/local_competition_score.py`
- [X] T011 [P] Add score module skeletons with typed function signatures in `src/scoring/monetization_score.py`
- [X] T012 [P] Add score module skeletons with typed function signatures in `src/scoring/ai_resilience_score.py`
- [X] T013 [P] Add typed composite and profile resolver scaffolds in `src/scoring/composite_score.py` and `src/scoring/strategy_profiles.py`
- [X] T014 [P] Add engine/confidence orchestration scaffolds in `src/scoring/engine.py` and `src/scoring/confidence_score.py`

**Checkpoint**: Foundation ready - user story implementation can begin.

---

## Phase 3: User Story 1 - Sub-scores and composite from signals (Priority: P1) 🎯 MVP

**Goal**: Produce five bounded sub-scores and one composite opportunity score from metro signals with reproducible output and correct competition inversion behavior.

**Independent Test**: Given complete fixture signals and a valid profile, the engine emits all required scores in range 0-100, is reproducible across repeated runs, and does not inflate opportunity under higher competition pressure.

### Tests for User Story 1 (required)

- [X] T015 [P] [US1] Add sub-score presence/range tests in `tests/unit/test_m07_scores_us1.py`
- [X] T016 [P] [US1] Add reproducibility tests for repeated identical runs in `tests/unit/test_m07_reproducibility_us1.py`
- [X] T017 [P] [US1] Add competition inversion behavior tests in `tests/unit/test_m07_competition_inversion_us1.py`

### Implementation for User Story 1

- [X] T018 [P] [US1] Implement demand score calculations in `src/scoring/demand_score.py`
- [X] T019 [P] [US1] Implement organic competition score calculations in `src/scoring/organic_competition_score.py`
- [X] T020 [P] [US1] Implement local competition score calculations in `src/scoring/local_competition_score.py`
- [X] T021 [P] [US1] Implement monetization score calculations in `src/scoring/monetization_score.py`
- [X] T022 [P] [US1] Implement baseline AI resilience scoring in `src/scoring/ai_resilience_score.py`
- [X] T023 [US1] Implement baseline opportunity composition with competition inversion in `src/scoring/composite_score.py`
- [X] T024 [US1] Wire US1 sub-score orchestration and output shaping in `src/scoring/engine.py`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Strategy profile-aware weighting (Priority: P2)

**Goal**: Resolve and enforce profile-specific weights/constraints and propagate `resolved_weights` into composite scoring.

**Independent Test**: Switching only `strategy_profile` changes `resolved_weights` and may change composite ranking while preserving valid bounded sub-scores.

### Tests for User Story 2 (required)

- [X] T025 [P] [US2] Add strategy profile constraints and normalization tests in `tests/unit/test_m07_strategy_profiles_us2.py`
- [X] T026 [P] [US2] Add profile-dependent composite outcome tests in `tests/unit/test_m07_composite_profiles_us2.py`

### Implementation for User Story 2

- [X] T027 [US2] Implement profile definitions, resolution, and bounds checks in `src/scoring/strategy_profiles.py`
- [X] T028 [US2] Integrate profile-resolved weights into opportunity composition in `src/scoring/composite_score.py`
- [X] T029 [US2] Emit `resolved_weights` in engine output contracts in `src/scoring/engine.py`

**Checkpoint**: User Stories 1 and 2 work independently with profile-aware behavior.

---

## Phase 5: User Story 3 - Confidence, gates, and percentiles (Priority: P3)

**Goal**: Implement confidence penalties/flags, cohort-relative percentile behavior, and rule-based gates/floors per spec.

**Independent Test**: Injected signal gaps and rule triggers alter confidence and affected scores predictably; changing cohort composition updates only percentile-relative components.

### Tests for User Story 3 (required)

- [X] T030 [P] [US3] Add confidence penalty/flag tests in `tests/unit/test_m07_confidence_us3.py`
- [X] T031 [P] [US3] Add cohort percentile sensitivity and isolation tests in `tests/unit/test_m07_percentiles_us3.py`
- [X] T032 [P] [US3] Add review barrier/no-local-pack/CPC/threshold/AI floor tests in `tests/unit/test_m07_rule_gates_us3.py`
- [X] T033 [P] [US3] Add AI resilience niche-type split tests (local-service vs informational) in `tests/unit/test_m07_ai_resilience_us3.py`

### Implementation for User Story 3

- [X] T034 [US3] Implement confidence scoring and flags in `src/scoring/confidence_score.py`
- [X] T035 [US3] Implement percentile ranking and small-cohort fallback rules in `src/scoring/normalization.py`
- [X] T036 [US3] Implement review barrier/no-local-pack/CPC/threshold/AI floor logic in `src/scoring/demand_score.py`, `src/scoring/local_competition_score.py`, `src/scoring/monetization_score.py`, and `src/scoring/ai_resilience_score.py`
- [X] T037 [US3] Integrate confidence and percentile-dependent components in `src/scoring/engine.py`

**Checkpoint**: All three user stories are independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, docs sync, and quality gates across all stories.

- [X] T038 [P] Update scoring exports and module docs in `src/scoring/__init__.py`
- [X] T039 [P] Update canonical contracts as needed in `docs-canonical/DATA-MODEL.md`, `docs-canonical/REQUIREMENTS.md`, and `docs-canonical/TEST-SPEC.md`
- [X] T040 [P] Sync detailed scoring flow docs in `docs/data_flow.md` and `docs/product_breakdown.md`
- [X] T041 Run `ruff check src tests` and record results in `.specify/specs/M07-scoring-engine/quickstart.md`
- [X] T042 Run `pytest tests/unit/ -v` and record results in `.specify/specs/M07-scoring-engine/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all story implementation
- **Phase 3 (US1)**: Depends on Phase 2 completion
- **Phase 4 (US2)**: Depends on Phase 2 and integrates with US1 composite/output contracts
- **Phase 5 (US3)**: Depends on Phase 2 and integrates with US1/US2 scoring paths
- **Phase 6 (Polish)**: Depends on completion of target user stories

### User Story Dependencies

- **US1 (P1)**: Starts first after foundational tasks; defines baseline scoring outputs
- **US2 (P2)**: Depends on US1 composite/output baseline to add profile-resolved weighting
- **US3 (P3)**: Depends on US1 scoring baseline and US2 output shape (`resolved_weights`) for final confidence/gates/percentiles

### Within Each User Story

- Write tests first and verify they fail before implementation
- Implement score-domain logic before orchestration wiring
- Complete story-level tests before moving to next priority

### Parallel Opportunities

- Foundational file scaffolds (`T007`-`T014`) run in parallel
- US1 domain score modules (`T018`-`T022`) run in parallel
- US2 tests (`T025`-`T026`) run in parallel
- US3 tests (`T030`-`T033`) run in parallel
- Polish doc-sync tasks (`T039`-`T040`) run in parallel

---

## Parallel Example: User Story 1

```bash
# Run US1 test authoring in parallel:
Task: "T015 Add sub-score presence/range tests in tests/unit/test_m07_scores_us1.py"
Task: "T016 Add reproducibility tests in tests/unit/test_m07_reproducibility_us1.py"
Task: "T017 Add competition inversion tests in tests/unit/test_m07_competition_inversion_us1.py"

# Run US1 score module implementation in parallel:
Task: "T018 Implement demand score calculations in src/scoring/demand_score.py"
Task: "T019 Implement organic competition score calculations in src/scoring/organic_competition_score.py"
Task: "T020 Implement local competition score calculations in src/scoring/local_competition_score.py"
Task: "T021 Implement monetization score calculations in src/scoring/monetization_score.py"
Task: "T022 Implement baseline AI resilience scoring in src/scoring/ai_resilience_score.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2
2. Complete Phase 3 (US1)
3. Validate US1 independently via its test suite
4. Share MVP output for early review

### Incremental Delivery

1. Deliver US1 (bounded/reproducible baseline scoring)
2. Add US2 (profile-aware weighting and `resolved_weights`)
3. Add US3 (confidence, gates, cohort percentiles)
4. Finish with Phase 6 quality gates and docs sync

### Parallel Team Strategy

1. One developer handles shared scaffolding and engine contracts
2. One developer handles US1 score modules
3. One developer handles US3 confidence/percentile modules
4. Merge at story checkpoints with tests passing

---

## Notes

- `[P]` tasks target different files and minimal coupling
- Every user story includes independent test criteria from the spec
- Avoid cross-story hidden dependencies; use explicit engine contracts

