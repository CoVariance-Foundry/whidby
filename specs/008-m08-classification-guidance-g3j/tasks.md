# Tasks: M8 Classification + Guidance

**Input**: Design documents from `/specs/008-m08-classification-guidance-g3j/`  
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included (TDD required by feature spec and constitution).

**Organization**: Tasks are grouped by user story to enable independent implementation and validation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no blocking dependency)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`) for story-phase tasks
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create M8 module and fixture/test scaffolding for story-driven TDD.

- [X] T001 Create classification package export scaffold in `src/classification/__init__.py`
- [X] T002 Create fixture scaffold for M8 labeled scenarios in `tests/fixtures/m8_classification_fixtures.py`
- [X] T003 [P] Create archetype test module scaffold in `tests/unit/test_serp_archetype.py`
- [X] T004 [P] Create AI exposure test module scaffold in `tests/unit/test_ai_exposure.py`
- [X] T005 [P] Create difficulty tier test module scaffold in `tests/unit/test_difficulty_tier.py`
- [X] T006 [P] Create guidance generator test module scaffold in `tests/unit/test_guidance_generator.py`
- [X] T007 [P] Create end-to-end classification pipeline test scaffold in `tests/unit/test_classification_pipeline.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared typed contracts, template matrix, and orchestration shell used by all stories.

**CRITICAL**: No user story work should start before this phase is complete.

- [X] T008 [P] Define core enums and typed bundles (`ClassificationInput`, `ClassificationGuidanceBundle`) in `src/classification/types.py`
- [X] T009 [P] Add contract-shape validation tests for output bundle in `tests/unit/test_classification_pipeline.py`
- [X] T010 [P] Implement base guidance template matrix keyed by archetype x difficulty in `src/classification/templates/guidance_templates.py`
- [X] T011 [P] Add template coverage tests for required matrix entries in `tests/unit/test_guidance_generator.py`
- [X] T012 Implement `classify_and_generate_guidance(...)` orchestration shell with validation hooks in `src/classification/guidance_generator.py`
- [X] T013 Wire module exports for classifier entry points in `src/classification/__init__.py`

**Checkpoint**: Shared contracts/templates/orchestration are ready for story-specific behavior.

---

## Phase 3: User Story 1 - SERP archetype and AI exposure labels (Priority: P1) 🎯 MVP

**Goal**: Emit exactly one valid SERP archetype and one valid AI exposure label from M6/M7 inputs with deterministic precedence.

**Independent Test**: Given golden fixtures (aggregator-dominated, local-pack vulnerable, barren, shielded, exposed), classification returns one valid archetype and one valid exposure label matching Algo §8 thresholds/rules.

### Tests for User Story 1 (TDD first)

- [X] T014 [P] [US1] Add failing archetype precedence and boundary tests in `tests/unit/test_serp_archetype.py`
- [X] T015 [P] [US1] Add failing AI exposure threshold boundary tests in `tests/unit/test_ai_exposure.py`
- [X] T016 [P] [US1] Add failing integration tests for single-label guarantee in `tests/unit/test_classification_pipeline.py`

### Implementation for User Story 1

- [X] T017 [US1] Implement ordered SERP archetype rules in `src/classification/serp_archetype.py`
- [X] T018 [US1] Implement AI exposure threshold mapper in `src/classification/ai_exposure.py`
- [X] T019 [US1] Integrate archetype and exposure classifiers into orchestration flow in `src/classification/guidance_generator.py`
- [X] T020 [US1] Add deterministic fallback rule metadata handling in `src/classification/serp_archetype.py`

**Checkpoint**: US1 classifications are independently functional and testable.

---

## Phase 4: User Story 2 - Difficulty tier for execution planning (Priority: P2)

**Goal**: Emit one difficulty tier using M7 competition values and strategy-profile-consistent weighting.

**Independent Test**: Controlled changes in organic/local competition values move tiers monotonically toward harder/easier buckets under the same strategy profile.

### Tests for User Story 2 (TDD first)

- [X] T021 [P] [US2] Add failing difficulty tier threshold tests for EASY/MODERATE/HARD/VERY_HARD in `tests/unit/test_difficulty_tier.py`
- [X] T022 [P] [US2] Add failing strategy-profile weighting tests in `tests/unit/test_difficulty_tier.py`
- [X] T023 [P] [US2] Add failing pipeline tests asserting valid tier enum output for all fixtures in `tests/unit/test_classification_pipeline.py`

### Implementation for User Story 2

- [X] T024 [US2] Implement weighted competition blend and tier mapping in `src/classification/difficulty_tier.py`
- [X] T025 [US2] Integrate difficulty tier computation into classification orchestration in `src/classification/guidance_generator.py`
- [X] T026 [US2] Add no-score-recomputation guardrails using M7-provided inputs only in `src/classification/guidance_generator.py`

**Checkpoint**: US2 tiering is independently functional and testable.

---

## Phase 5: User Story 3 - Readable, niche-aware guidance (Priority: P3)

**Goal**: Generate readable, niche/metro-aware guidance aligned with archetype/exposure/tier and fail safely on LLM errors.

**Independent Test**: For the same niche with different archetypes, generated guidance differs by context while remaining consistent with classifications; when LLM fails, fallback guidance is returned with explicit degraded status.

### Tests for User Story 3 (TDD first)

- [X] T027 [P] [US3] Add failing template-context rendering tests for niche/metro substitution in `tests/unit/test_guidance_generator.py`
- [X] T028 [P] [US3] Add failing non-contradiction tests against archetype/tier/exposure in `tests/unit/test_guidance_generator.py`
- [X] T029 [P] [US3] Add failing LLM timeout/error fallback tests in `tests/unit/test_guidance_generator.py`
- [X] T030 [P] [US3] Add failing end-to-end guidance status tests (`generated` vs `fallback_template`) in `tests/unit/test_classification_pipeline.py`

### Implementation for User Story 3

- [X] T031 [US3] Implement template-context builder and guidance assembly in `src/classification/guidance_generator.py`
- [X] T032 [US3] Implement bounded M3 client prompt construction and response normalization in `src/classification/guidance_generator.py`
- [X] T033 [US3] Implement explicit fallback guidance path with reason metadata in `src/classification/guidance_generator.py`
- [X] T034 [US3] Add AI resilience note injection rules for `AI_MODERATE` and `AI_EXPOSED` in `src/classification/templates/guidance_templates.py`

**Checkpoint**: US3 guidance is independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finalize quality gates, docs alignment, and end-to-end validation across stories.

- [X] T035 [P] Add regression fixtures for edge cases (conflicting weak signals, sparse optional LLM fields) in `tests/fixtures/m8_classification_fixtures.py`
- [X] T036 [P] Add contract conformance assertions against classification-guidance contract in `tests/unit/test_classification_pipeline.py`
- [X] T037 Run M8 focused lint and unit test commands documented in `specs/008-m08-classification-guidance-g3j/quickstart.md`
- [X] T038 Document implementation validation outcomes in `specs/008-m08-classification-guidance-g3j/plan.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) -> Foundational (Phase 2) -> User Stories (Phases 3-5) -> Polish (Phase 6)
- User story phases can run in priority order (P1 -> P2 -> P3) or in parallel after Phase 2, but MVP targets US1 first.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2; no dependency on other stories.
- **US2 (P2)**: Starts after Phase 2; depends only on foundational typed contracts/orchestration.
- **US3 (P3)**: Starts after Phase 2; depends on classification outputs from US1/US2 for contradiction checks.

### Within Each User Story

- Tests must be written and fail first.
- Rule/algorithm implementation follows tests.
- Orchestration wiring follows core function completion.
- Story checkpoint must pass before moving to polish.

---

## Parallel Execution Examples

### User Story 1

```bash
Task: "T014 [US1] archetype precedence tests in tests/unit/test_serp_archetype.py"
Task: "T015 [US1] AI exposure threshold tests in tests/unit/test_ai_exposure.py"
Task: "T016 [US1] single-label integration tests in tests/unit/test_classification_pipeline.py"
```

### User Story 2

```bash
Task: "T021 [US2] difficulty tier threshold tests in tests/unit/test_difficulty_tier.py"
Task: "T022 [US2] strategy-profile weighting tests in tests/unit/test_difficulty_tier.py"
Task: "T023 [US2] tier enum integration tests in tests/unit/test_classification_pipeline.py"
```

### User Story 3

```bash
Task: "T027 [US3] template-context tests in tests/unit/test_guidance_generator.py"
Task: "T028 [US3] non-contradiction tests in tests/unit/test_guidance_generator.py"
Task: "T029 [US3] fallback behavior tests in tests/unit/test_guidance_generator.py"
Task: "T030 [US3] guidance status integration tests in tests/unit/test_classification_pipeline.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate golden archetype/exposure fixtures independently.
4. Stop and review before adding tier/guidance complexity.

### Incremental Delivery

1. Deliver US1 (classification labels).
2. Add US2 (difficulty tier).
3. Add US3 (guidance generation + fallback).
4. Finish with cross-cutting regression and contract checks.

### Parallel Team Strategy

1. Team completes Setup + Foundational tasks together.
2. Split story work after Phase 2:
   - Engineer A: US1
   - Engineer B: US2
   - Engineer C: US3
3. Rejoin for polish and validation tasks.

---

## Notes

- `[P]` indicates tasks that can run concurrently due to file-level independence.
- Story labels ensure every story remains independently implementable and testable.
- Keep M8 deterministic: no score recomputation and no silent LLM failure paths.
