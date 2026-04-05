# Tasks: M04 Keyword Expansion

**Input**: Design documents from `/specs/001-keyword-expansion/`  
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included and required for this feature (constitution + quickstart mandate TDD/unit coverage).  
**Organization**: Tasks are grouped by user story so each story remains independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependency)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`)
- Every task includes an explicit file path.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create skeleton files and fixtures required before core logic.

- [X] T001 Create M4 module scaffolding in `src/pipeline/keyword_expansion.py`
- [X] T002 [P] Create intent module scaffolding in `src/pipeline/intent_classifier.py`
- [X] T003 [P] Create deduplication module scaffolding in `src/pipeline/keyword_deduplication.py`
- [X] T004 [P] Create shared M4 fixtures in `tests/fixtures/keyword_expansion_fixtures.py`
- [X] T005 [P] Create unit test scaffolding in `tests/unit/test_keyword_expansion.py`
- [X] T006 [P] Create unit test scaffolding in `tests/unit/test_intent_classifier.py`
- [X] T007 [P] Create unit test scaffolding in `tests/unit/test_keyword_deduplication.py`
- [X] T008 [P] Create integration test scaffolding in `tests/integration/test_keyword_expansion_integration.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared deterministic primitives used by all stories.  
**⚠️ CRITICAL**: Complete this phase before user-story work.

- [X] T009 Add M4 constants/enums (intent, tier, confidence thresholds, AIO risk defaults) in `src/config/constants.py`
- [X] T010 [P] Implement keyword normalization helper functions in `src/pipeline/keyword_deduplication.py`
- [X] T011 [P] Implement canonical dedupe merge API in `src/pipeline/keyword_deduplication.py`
- [X] T012 [P] Implement intent rule matcher primitives in `src/pipeline/intent_classifier.py`
- [X] T013 [P] Define typed output structures for `ExpandedKeyword` and `KeywordExpansion` in `src/pipeline/keyword_expansion.py`
- [X] T014 Add shared fixture payloads for LLM/DataForSEO responses in `tests/fixtures/keyword_expansion_fixtures.py`

**Checkpoint**: Foundation complete; user stories can now be implemented.

---

## Phase 3: User Story 1 - Expand a niche into actionable keywords (Priority: P1) 🎯 MVP

**Goal**: Produce non-empty, relevant, deduplicated keyword expansion from one niche input with traceable sources.  
**Independent Test**: Run unit tests proving non-empty output, head/service inclusion, and dedupe of format variants.

### Tests for User Story 1

- [X] T015 [P] [US1] Write failing test for non-empty expansion output in `tests/unit/test_keyword_expansion.py`
- [X] T016 [P] [US1] Write failing test for head/service candidate coverage in `tests/unit/test_keyword_expansion.py`
- [X] T017 [P] [US1] Write failing dedupe normalization test for formatting variants in `tests/unit/test_keyword_deduplication.py`

### Implementation for User Story 1

- [X] T018 [US1] Implement LLM + DataForSEO candidate collection orchestration in `src/pipeline/keyword_expansion.py`
- [X] T019 [US1] Implement candidate merge and dedupe integration call in `src/pipeline/keyword_expansion.py`
- [X] T020 [US1] Implement source traceability assignment (`input`/`llm`/`dataforseo_suggestions`/`merged`) in `src/pipeline/keyword_expansion.py`
- [X] T021 [US1] Implement initial aggregate counters (`total_keywords`) in `src/pipeline/keyword_expansion.py`

**Checkpoint**: US1 is independently testable and delivers MVP keyword expansion value.

---

## Phase 4: User Story 2 - Understand keyword intent for prioritization (Priority: P2)

**Goal**: Ensure every returned keyword includes valid intent and tier with actionability/exclusion behavior.  
**Independent Test**: Run unit tests proving every keyword has valid intent+tier and informational handling is explicit.

### Tests for User Story 2

- [X] T022 [P] [US2] Write failing intent classification validity tests in `tests/unit/test_intent_classifier.py`
- [X] T023 [P] [US2] Write failing tier assignment validity tests in `tests/unit/test_keyword_expansion.py`
- [X] T024 [P] [US2] Write failing informational exclusion/count test in `tests/unit/test_keyword_expansion.py`

### Implementation for User Story 2

- [X] T025 [US2] Implement intent precedence flow (structured intent -> rules -> fallback classify -> default) in `src/pipeline/intent_classifier.py`
- [X] T026 [US2] Implement tier assignment mapping rules in `src/pipeline/keyword_expansion.py`
- [X] T027 [US2] Implement actionability mapping and informational exclusion counters in `src/pipeline/keyword_expansion.py`
- [X] T028 [US2] Implement AIO risk labeling by intent in `src/pipeline/keyword_expansion.py`
- [X] T029 [US2] Reconcile `actionable_keywords` and `informational_keywords_excluded` counters in `src/pipeline/keyword_expansion.py`

**Checkpoint**: US2 is independently testable and intent-driven prioritization is available.

---

## Phase 5: User Story 3 - Trust output quality before downstream scoring (Priority: P3)

**Goal**: Add deterministic ordering, confidence scoring, and resilient degraded-mode output for sparse/failing upstream data.  
**Independent Test**: Run unit tests proving stable ordering, threshold-based confidence, and low-confidence partial fallback behavior.

### Tests for User Story 3

- [X] T030 [P] [US3] Write failing deterministic ordering test for repeated runs in `tests/unit/test_keyword_expansion.py`
- [X] T031 [P] [US3] Write failing confidence threshold mapping test in `tests/unit/test_keyword_expansion.py`
- [X] T032 [P] [US3] Write failing degraded-mode partial output test in `tests/unit/test_keyword_expansion.py`
- [X] T033 [P] [US3] Write failing contract-shape compliance test using schema fields in `tests/unit/test_keyword_expansion.py`

### Implementation for User Story 3

- [X] T034 [US3] Implement deterministic final sort order `(tier, intent priority, keyword)` in `src/pipeline/keyword_expansion.py`
- [X] T035 [US3] Implement overlap-based `expansion_confidence` computation in `src/pipeline/keyword_expansion.py`
- [X] T036 [US3] Implement degraded-mode fallback when one upstream source fails in `src/pipeline/keyword_expansion.py`
- [X] T037 [US3] Enforce final contract field population for all keywords and top-level counters in `src/pipeline/keyword_expansion.py`
- [X] T038 [US3] Add live integration scenario (optional marker) for end-to-end keyword expansion in `tests/integration/test_keyword_expansion_integration.py`

**Checkpoint**: US3 is independently testable with quality/reliability guarantees.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality, docs alignment, and regression hardening.

- [X] T039 [P] Add counter-reconciliation regression cases in `tests/unit/test_keyword_expansion.py`
- [X] T040 [P] Add module-level docstrings/type hints cleanup in `src/pipeline/keyword_expansion.py`
- [X] T041 [P] Add module-level docstrings/type hints cleanup in `src/pipeline/intent_classifier.py`
- [X] T042 [P] Add module-level docstrings/type hints cleanup in `src/pipeline/keyword_deduplication.py`
- [X] T043 Update M4 quickstart verification notes and command list in `specs/001-keyword-expansion/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: starts immediately.
- **Phase 2 (Foundational)**: depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: depends on Phase 2 completion.
- **Phase 4 (US2)**: depends on Phase 2 completion; can proceed after/alongside US1, but priority order favors US1 first.
- **Phase 5 (US3)**: depends on Phase 2 and benefits from US1/US2 logic being present.
- **Phase 6 (Polish)**: depends on completion of all selected user stories.

### User Story Dependency Graph

- **US1 (P1)**: independent MVP slice after foundational setup.
- **US2 (P2)**: independent from business perspective, but shares M4 files with US1.
- **US3 (P3)**: quality/reliability layer on top of US1/US2 outputs.

### Within Each User Story

- Write tests first and confirm they fail.
- Implement core logic second.
- Re-run targeted tests before moving to next story.

### Parallel Opportunities

- Setup tasks marked `[P]` can run in parallel.
- Foundational tasks T010-T013 can run in parallel.
- US1 test tasks T015-T017 can run in parallel.
- US2 test tasks T022-T024 can run in parallel.
- US3 test tasks T030-T033 can run in parallel.
- Polish tasks T039-T042 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Parallel test-authoring tasks:
Task: "T015 [US1] in tests/unit/test_keyword_expansion.py"
Task: "T016 [US1] in tests/unit/test_keyword_expansion.py"
Task: "T017 [US1] in tests/unit/test_keyword_deduplication.py"
```

## Parallel Example: User Story 2

```bash
# Parallel test-authoring tasks:
Task: "T022 [US2] in tests/unit/test_intent_classifier.py"
Task: "T023 [US2] in tests/unit/test_keyword_expansion.py"
Task: "T024 [US2] in tests/unit/test_keyword_expansion.py"
```

## Parallel Example: User Story 3

```bash
# Parallel test-authoring tasks:
Task: "T030 [US3] in tests/unit/test_keyword_expansion.py"
Task: "T031 [US3] in tests/unit/test_keyword_expansion.py"
Task: "T032 [US3] in tests/unit/test_keyword_expansion.py"
Task: "T033 [US3] in tests/unit/test_keyword_expansion.py"
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate US1 independently via its targeted tests.

### Incremental Delivery

1. Deliver US1 (expansion + dedupe).
2. Add US2 (intent/tier/actionability).
3. Add US3 (confidence + determinism + fallback resilience).
4. Finish with Phase 6 polish tasks.

### Parallel Team Strategy

1. One developer completes foundational primitives in Phase 2.
2. Then split by story:
   - Dev A: US1 orchestration tasks
   - Dev B: US2 intent/tier tasks
   - Dev C: US3 reliability tasks
3. Merge at phase checkpoints with targeted regression runs.

---

## Notes

- `[P]` tasks indicate safe parallelization by file/dependency boundaries.
- `[USx]` labels maintain traceability to spec user stories.
- Each story has an explicit independent test criterion.
- Suggested MVP scope is **Phase 3 / US1**.
