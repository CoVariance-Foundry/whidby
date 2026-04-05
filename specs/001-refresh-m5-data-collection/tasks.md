# Tasks: M5 Data Collection Refresh

**Input**: Design documents from `specs/001-refresh-m5-data-collection/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/data-collection-contract.md`, `quickstart.md`

**Tests**: Included and required (TDD-first per constitution + quickstart).  
**Organization**: Tasks are grouped by user story to keep each increment independently testable and deployable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`) for story-phase tasks only
- Every task includes an explicit file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the M5 module/test skeleton and baseline fixtures used across all stories.

- [X] T001 Create pipeline package initializer in `src/pipeline/__init__.py`
- [X] T002 Create M5 type contract module scaffold in `src/pipeline/types.py`
- [X] T003 [P] Create shared M5 fixture module in `tests/fixtures/m5_collection_fixtures.py`
- [X] T004 [P] Create unit test file skeletons in `tests/unit/test_collection_plan.py`, `tests/unit/test_batch_executor.py`, `tests/unit/test_result_assembler.py`, and `tests/unit/test_data_collection.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared contracts and helpers required by all user stories.

**CRITICAL**: No user story implementation starts before this phase completes.

- [X] T005 Implement request/result dataclasses and validation helpers in `src/pipeline/types.py`
- [X] T006 [P] Implement task graph primitives and dependency validation helpers in `src/pipeline/task_graph.py`
- [X] T007 [P] Implement M5 error and failure-record normalization helpers in `src/pipeline/errors.py`
- [X] T008 Implement base result category initializers (explicit empty categories) in `src/pipeline/result_assembler.py`
- [X] T009 Implement shared test fixtures for request payloads and API response stubs in `tests/fixtures/m5_collection_fixtures.py`
- [X] T010 Add foundational unit tests for type validation and graph acyclicity in `tests/unit/test_collection_plan.py`

**Checkpoint**: Foundation complete; user stories can proceed.

---

## Phase 3: User Story 1 - Run complete collection for one metro (Priority: P1) 🎯 MVP

**Goal**: Deliver complete single-metro collection with required categories, batching/eligibility, and run metadata.

**Independent Test**: Run collection for one metro and verify all categories are present (explicit empties allowed) and `meta` includes calls, cost, duration, and errors.

### Tests for User Story 1

- [X] T011 [P] [US1] Add planner tests for keyword eligibility and 700-keyword batching in `tests/unit/test_collection_plan.py`
- [X] T012 [P] [US1] Add executor tests for phase-1 parallel dispatch and dependency-gated phase-2 dispatch in `tests/unit/test_batch_executor.py`
- [X] T013 [P] [US1] Add assembler tests for explicit empty categories and metadata aggregation in `tests/unit/test_result_assembler.py`
- [X] T014 [US1] Add orchestrator unit test for single-metro end-to-end happy path in `tests/unit/test_data_collection.py`

### Implementation for User Story 1

- [X] T015 [US1] Implement request-to-task planning (volume + SERP/maps) in `src/pipeline/collection_plan.py`
- [X] T016 [US1] Implement deterministic two-phase task execution in `src/pipeline/batch_executor.py`
- [X] T017 [US1] Implement raw response normalization and metro-category assembly in `src/pipeline/result_assembler.py`
- [X] T018 [US1] Implement top-level `collect_data` orchestration entrypoint in `src/pipeline/data_collection.py`
- [X] T019 [US1] Add run metadata reconciliation (call count, cost, duration, errors) in `src/pipeline/data_collection.py`
- [X] T020 [US1] Add contract conformance assertions for single-metro output shape in `tests/unit/test_data_collection.py`

**Checkpoint**: US1 is fully functional and independently testable (MVP).

---

## Phase 4: User Story 2 - Run collection across multiple metros consistently (Priority: P2)

**Goal**: Ensure strict metro partitioning and consistent per-metro rule application for multi-metro requests.

**Independent Test**: Run with 2+ metros and verify no cross-metro data leakage and consistent keyword eligibility/batching behavior per metro.

### Tests for User Story 2

- [X] T021 [P] [US2] Add multi-metro planning tests for partitioned task generation in `tests/unit/test_collection_plan.py`
- [X] T022 [P] [US2] Add assembler tests for metro-isolated outputs and required category completeness in `tests/unit/test_result_assembler.py`
- [X] T023 [US2] Add orchestrator unit test for multi-metro consistency and partitioning in `tests/unit/test_data_collection.py`

### Implementation for User Story 2

- [X] T024 [US2] Implement multi-metro task partitioning and stable metro identifiers in `src/pipeline/collection_plan.py`
- [X] T025 [US2] Implement cross-metro dedup strategy for eligible downstream targets in `src/pipeline/batch_executor.py`
- [X] T026 [US2] Implement per-metro assembly guards preventing cross-metro leakage in `src/pipeline/result_assembler.py`

**Checkpoint**: US1 and US2 both pass independently.

---

## Phase 5: User Story 3 - Continue useful collection during partial failures (Priority: P3)

**Goal**: Keep independent work progressing on failures and return structured failure records with partial results.

**Independent Test**: Inject sub-task failures and verify successful independent results remain, with retry-scoped errors in `meta.errors`.

### Tests for User Story 3

- [X] T027 [P] [US3] Add executor failure-isolation tests for dependency and non-dependency paths in `tests/unit/test_batch_executor.py`
- [X] T028 [P] [US3] Add orchestrator tests for partial-result returns and structured failure records in `tests/unit/test_data_collection.py`

### Implementation for User Story 3

- [X] T029 [US3] Implement failure isolation and continuation behavior in `src/pipeline/batch_executor.py`
- [X] T030 [US3] Implement retry-scoped failure record enrichment in `src/pipeline/errors.py`
- [X] T031 [US3] Implement partial-result merge rules in failure scenarios in `src/pipeline/data_collection.py`

**Checkpoint**: All user stories pass independently with resilient failure behavior.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality, docs sync, and verification across all stories.

- [X] T032 [P] Add integration coverage for M5 orchestration against client boundary in `tests/integration/test_dataforseo_integration.py`
- [X] T033 [P] Add/refresh module docstrings and inline contract notes in `src/pipeline/data_collection.py`, `src/pipeline/collection_plan.py`, `src/pipeline/batch_executor.py`, and `src/pipeline/result_assembler.py`
- [X] T034 Validate quickstart commands and update command examples in `specs/001-refresh-m5-data-collection/quickstart.md`
- [X] T035 Run quality gates and capture results in `specs/001-refresh-m5-data-collection/plan.md` (ruff + unit tests + optional integration note)

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 (Setup): starts immediately.
- Phase 2 (Foundational): depends on Phase 1 and blocks all story work.
- Phase 3 (US1): depends on Phase 2; defines MVP.
- Phase 4 (US2): depends on US1 core contracts (T015-T020).
- Phase 5 (US3): depends on executor/orchestrator baseline from US1 (T016-T020); can proceed after US2 tests start.
- Phase 6 (Polish): depends on completion of selected story phases.

### User Story Dependencies

- **US1 (P1)**: no dependency on other user stories.
- **US2 (P2)**: depends on US1 data contracts and base planner/executor.
- **US3 (P3)**: depends on US1 execution baseline; integrates cleanly with US2 behavior.

### Task-Level Key Dependencies

- T005 depends on T002.
- T006 depends on T002.
- T008 depends on T005.
- T010 depends on T005 and T006.
- T015 depends on T005, T006, T009, T010.
- T016 depends on T006 and T009.
- T017 depends on T008 and T009.
- T018 depends on T015, T016, T017.
- T024 depends on T015.
- T025 depends on T016 and T024.
- T029 depends on T016.
- T031 depends on T018 and T029.
- T035 depends on T032, T033, and T034.

---

## Parallel Execution Opportunities

- **Setup**: T003 and T004 can run in parallel after T001/T002.
- **Foundational**: T006 and T007 can run in parallel; T009 can run in parallel with T006/T007.
- **US1 tests**: T011, T012, and T013 can run in parallel.
- **US2 tests**: T021 and T022 can run in parallel.
- **US3 tests**: T027 and T028 can run in parallel.
- **Polish**: T032 and T033 can run in parallel.

## Parallel Example: User Story 1

```bash
Task: "T011 [US1] Add planner tests in tests/unit/test_collection_plan.py"
Task: "T012 [US1] Add executor tests in tests/unit/test_batch_executor.py"
Task: "T013 [US1] Add assembler tests in tests/unit/test_result_assembler.py"
```

## Parallel Example: User Story 2

```bash
Task: "T021 [US2] Add multi-metro planning tests in tests/unit/test_collection_plan.py"
Task: "T022 [US2] Add metro-isolation assembler tests in tests/unit/test_result_assembler.py"
```

## Parallel Example: User Story 3

```bash
Task: "T027 [US3] Add failure-isolation executor tests in tests/unit/test_batch_executor.py"
Task: "T028 [US3] Add partial-result orchestrator tests in tests/unit/test_data_collection.py"
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate single-metro end-to-end behavior before expanding scope.

### Incremental Delivery

1. Deliver US1 (single metro completeness + metadata).
2. Add US2 (multi-metro partitioning + dedup).
3. Add US3 (partial-failure resilience).
4. Finish with polish and quality gate runs.

### Suggested MVP Scope

- **MVP**: Phase 1 + Phase 2 + Phase 3 (through T020).

