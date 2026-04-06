# Tasks: M9 Report Generation + Feedback Logging

**Input**: Design documents from `/specs/009-m09-report-generation/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/report-generation-contract.md`, `quickstart.md`

**Tests**: Tests are required for this feature (spec + constitution enforce TDD and independent story validation).
**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Story label for user-story phases only (`[US1]`, `[US2]`, `[US3]`)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish M9 module/test scaffolding and imports needed by all stories.

- [X] T001 Create M9 module skeleton with docstrings in `src/pipeline/report_generator.py` and `src/pipeline/feedback_logger.py`
- [X] T002 [P] Export M9 module entry points in `src/pipeline/__init__.py`
- [X] T003 [P] Add base M9 fixture builders for run input and metro payloads in `tests/fixtures/m9_report_fixtures.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core contracts and shared structures that block user story implementation.

**CRITICAL**: No user story implementation starts until this phase is complete.

- [X] T004 Define typed report/feedback helper models and validation utilities in `src/pipeline/types.py`
- [X] T005 [P] Add shared M9 error classes for validation and persistence failures in `src/pipeline/errors.py`
- [X] T006 Create reusable contract assertion helpers for report shape paths in `tests/unit/test_report_contract.py`
- [X] T007 Add deterministic tie-break test fixtures (equal opportunity with different CBSA keys) in `tests/fixtures/m9_report_fixtures.py`

**Checkpoint**: Foundation complete - user story work can proceed.

---

## Phase 3: User Story 1 - Final ranked report for a niche run (Priority: P1) 🎯 MVP

**Goal**: Assemble one schema-stable report JSON from M4-M8 outputs with deterministic metro ordering and accurate meta/cost fields.

**Independent Test**: Given fixture M4-M8 outputs, `generate_report()` returns one report matching required section-10 shape and sorted by descending `scores.opportunity` with deterministic tie-break behavior.

### Tests for User Story 1

- [X] T008 [P] [US1] Add report assembly field-presence tests in `tests/unit/test_report_generator.py`
- [X] T009 [P] [US1] Add deterministic ordering and tie-break tests in `tests/unit/test_report_generator.py`
- [X] T010 [P] [US1] Add exact meta/cost passthrough tests in `tests/unit/test_report_generator.py`

### Implementation for User Story 1

- [X] T011 [US1] Implement input validation and required-field guards in `src/pipeline/report_generator.py`
- [X] T012 [US1] Implement report assembly mapping from M4-M8 payloads in `src/pipeline/report_generator.py`
- [X] T013 [US1] Implement stable metro ranking (opportunity desc, `cbsa_code`, `cbsa_name`) in `src/pipeline/report_generator.py`
- [X] T014 [US1] Implement report meta construction (`total_api_calls`, `total_cost_usd`, `processing_time_seconds`) in `src/pipeline/report_generator.py`
- [X] T015 [US1] Wire report generation API (`generate_report`) and return contract in `src/pipeline/report_generator.py`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Durable feedback log for calibration (Priority: P2)

**Goal**: Persist one null-safe feedback record per ranked metro recommendation without mutating a valid generated report.

**Independent Test**: After report generation, `log_feedback()` writes one row per metro with nullable outcome fields preserved and surfaces persistence failures without corrupting the report object.

### Tests for User Story 2

- [X] T016 [P] [US2] Add per-metro feedback row creation tests in `tests/unit/test_feedback_logger.py`
- [X] T017 [P] [US2] Add nullable outcome persistence tests in `tests/unit/test_feedback_logger.py`
- [X] T018 [P] [US2] Add persistence failure integrity tests (report unchanged) in `tests/unit/test_feedback_logger.py`
- [X] T019 [P] [US2] Add optional integration test for Supabase persistence in `tests/integration/test_report_feedback_integration.py`

### Implementation for User Story 2

- [X] T020 [US2] Implement feedback row mapping from ranked metros (`context`, `signals`, `scores`, `classification`) in `src/pipeline/feedback_logger.py`
- [X] T021 [US2] Implement nullable outcome handling and defaults-as-null behavior in `src/pipeline/feedback_logger.py`
- [X] T022 [US2] Implement persistence adapter call flow for one-row-per-metro writes in `src/pipeline/feedback_logger.py`
- [X] T023 [US2] Implement structured failure handling/status return for persistence errors in `src/pipeline/feedback_logger.py`
- [X] T024 [US2] Expose feedback logging API (`log_feedback`) and result envelope in `src/pipeline/feedback_logger.py`

**Checkpoint**: User Stories 1 and 2 both run with independent validation.

---

## Phase 5: User Story 3 - Schema-stable consumption (Priority: P3)

**Goal**: Guarantee report schema stability for downstream consumers with clear validation failures.

**Independent Test**: Golden report fixtures pass schema/contract validation; fixtures missing required fields fail with clear JSON path pointers.

### Tests for User Story 3

- [X] T025 [P] [US3] Add golden report contract-pass tests in `tests/unit/test_report_contract.py`
- [X] T026 [P] [US3] Add missing-required-field contract-fail tests with path assertions in `tests/unit/test_report_contract.py`

### Implementation for User Story 3

- [X] T027 [US3] Implement contract validation helpers for top-level and nested required fields in `tests/unit/test_report_contract.py`
- [X] T028 [US3] Add spec-version and required-field enforcement in `src/pipeline/report_generator.py`

**Checkpoint**: All user stories are independently functional and contract-validated.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality gates, docs sync, and end-to-end feature checks.

- [X] T029 [P] Update M9 module references and usage notes in `docs/product_breakdown.md`
- [X] T030 [P] Add/update report + feedback workflow notes in `docs/data_flow.md`
- [X] T031 Run focused quality gates from quickstart in `tests/unit/test_report_generator.py`, `tests/unit/test_feedback_logger.py`, and `tests/unit/test_report_contract.py`
- [X] T032 Run lint gate for touched files in `src/pipeline/report_generator.py`, `src/pipeline/feedback_logger.py`, and `tests/fixtures/m9_report_fixtures.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user story phases.
- **Phase 3 (US1)**: Depends on Phase 2; delivers MVP.
- **Phase 4 (US2)**: Depends on Phase 3 report generation output contract.
- **Phase 5 (US3)**: Depends on Phase 3 report shape; can run in parallel with late US2 hardening once US1 is stable.
- **Phase 6 (Polish)**: Depends on completion of all selected stories.

### User Story Dependencies

- **US1 (P1)**: Starts after foundational phase; no dependency on other stories.
- **US2 (P2)**: Depends on US1 generated report contract.
- **US3 (P3)**: Depends on US1 output schema, independent from US2 persistence internals.

### Within Each User Story

- Tests first and failing before implementation (`T008-T010`, `T016-T019`, `T025-T026`).
- Core implementation follows tests.
- Story checkpoint validates independent completion before next priority.

### Parallel Opportunities

- Setup: `T002` and `T003` can run in parallel after `T001`.
- Foundational: `T005` can run in parallel with `T004`; `T007` can run after `T003`.
- US1 tests `T008-T010` can be authored in parallel.
- US2 tests `T016-T019` can be authored in parallel.
- US3 tests `T025-T026` can be authored in parallel.
- Polish docs tasks `T029-T030` can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Write US1 tests in parallel:
Task: "T008 Add report assembly field-presence tests in tests/unit/test_report_generator.py"
Task: "T009 Add deterministic ordering and tie-break tests in tests/unit/test_report_generator.py"
Task: "T010 Add exact meta/cost passthrough tests in tests/unit/test_report_generator.py"
```

---

## Parallel Example: User Story 2

```bash
# Write US2 tests in parallel:
Task: "T016 Add per-metro feedback row creation tests in tests/unit/test_feedback_logger.py"
Task: "T017 Add nullable outcome persistence tests in tests/unit/test_feedback_logger.py"
Task: "T018 Add persistence failure integrity tests in tests/unit/test_feedback_logger.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup).
2. Complete Phase 2 (Foundational).
3. Complete Phase 3 (US1).
4. Validate US1 independently as MVP deliverable.

### Incremental Delivery

1. Deliver US1 (report assembly and ranking).
2. Add US2 (feedback persistence and failure handling).
3. Add US3 (schema-stability contract enforcement).
4. Finish with polish and quality gates.

### Team Parallelization Strategy

1. One engineer completes Setup + Foundational.
2. After US1 test scaffolding lands, one engineer finishes US1 implementation while another prepares US2/US3 test scaffolds.
3. Merge story phases in priority order with checkpoint validation.

---

## Phase 7: Remediation — Validation & Contract Gaps

**Purpose**: Address code-review findings: exception normalization, `feedback_log_id`, bypass prevention, and testing gaps.

- [X] T033 Centralize M9 validation constants and `coerce_numeric` helper in `src/pipeline/types.py`
- [X] T034 Fix metro-level exception normalization (catch `ValueError` not `ReportValidationError`) in `src/pipeline/report_generator.py`
- [X] T035 Wrap all meta numeric coercions in `try/except` mapped to `ReportValidationError` in `src/pipeline/report_generator.py`
- [X] T036 Set `meta.feedback_log_id` (UUID) during report construction in `src/pipeline/report_generator.py`
- [X] T037 Enforce full report-document contract in `log_feedback` input validation in `src/pipeline/feedback_logger.py`
- [X] T038 Validate each metro in report_document against full metro entry contract in `src/pipeline/feedback_logger.py`
- [X] T039 Include `feedback_log_id` in each feedback row context in `src/pipeline/feedback_logger.py`
- [X] T040 [P] Add metro-level missing-field and non-dict tests in `tests/unit/test_report_generator.py`
- [X] T041 [P] Add non-numeric opportunity and invalid meta type tests in `tests/unit/test_report_generator.py`
- [X] T042 [P] Add `feedback_log_id` presence test in `tests/unit/test_report_generator.py`
- [X] T043 [P] Add strict feedback input rejection tests in `tests/unit/test_feedback_logger.py`
- [X] T044 [P] Add `feedback_log_id` round-trip test in `tests/unit/test_feedback_logger.py`
- [X] T045 [P] Add `feedback_log_id` and metro-validation contract tests in `tests/unit/test_report_contract.py`
- [X] T046 [P] Add `feedback_log_id` integration round-trip test in `tests/integration/test_report_feedback_integration.py`
- [X] T047 Update M9 contract doc to reflect `feedback_log_id`, strict validation, and bypass prevention in `specs/009-m09-report-generation/contracts/report-generation-contract.md`

---

## Notes

- All tasks use strict checklist format: checkbox, Task ID, optional `[P]`, required `[USx]` for story tasks, and explicit file paths.
- Keep M9 deterministic: no recomputation of upstream scores/classifications inside report assembly.
- Keep feedback persistence failures observable and non-mutating to the already-generated report artifact.
- All validation failures must surface as `ReportValidationError` with dotted field paths — no raw `ValueError`/`TypeError` leaks from M9 public APIs.
