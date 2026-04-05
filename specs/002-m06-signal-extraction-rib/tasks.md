# Tasks: M6 Signal Extraction

**Input**: Design documents from `/specs/002-m06-signal-extraction-rib/`  
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included (TDD required by plan/constitution and explicitly described in `quickstart.md`).

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no blocking dependency)
- **[Story]**: User story label (`[US1]` ... `[US6]`) for story-phase tasks
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize M6 file layout and test fixture scaffolding.

- [ ] T001 Create extractor package scaffolding in `src/pipeline/extractors/__init__.py`
- [ ] T002 Create M6 fixture scaffolding in `tests/fixtures/m6_signal_extraction_fixtures.py`
- [ ] T003 [P] Add extractor test module skeleton in `tests/unit/test_signal_extractors.py`
- [ ] T004 [P] Add orchestrator test module skeleton in `tests/unit/test_signal_extraction.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build core shared utilities and baseline tests that all user stories depend on.

**CRITICAL**: User story implementation starts only after this phase completes.

- [ ] T005 [P] Add failing tests for SERP feature normalization in `tests/unit/test_serp_parser.py`
- [ ] T006 [P] Add failing tests for domain role classification in `tests/unit/test_domain_classifier.py`
- [ ] T007 [P] Add failing tests for AIO-adjusted volume math in `tests/unit/test_effective_volume.py`
- [ ] T008 [P] Add failing tests for review velocity computation in `tests/unit/test_review_velocity.py`
- [ ] T009 [P] Add failing tests for GBP completeness scoring in `tests/unit/test_gbp_completeness.py`
- [ ] T010 Implement shared SERP feature parser in `src/pipeline/serp_parser.py`
- [ ] T011 Implement shared domain classifier in `src/pipeline/domain_classifier.py`
- [ ] T012 Implement shared effective volume utility in `src/pipeline/effective_volume.py`
- [ ] T013 Implement shared review velocity utility in `src/pipeline/review_velocity.py`
- [ ] T014 Implement shared GBP completeness utility in `src/pipeline/gbp_completeness.py`

**Checkpoint**: Foundational utilities and their tests are green.

---

## Phase 3: User Story 1 - Demand Signal Extraction (Priority: P1) 🎯 MVP

**Goal**: Provide complete, range-safe demand signals including exact effective-volume behavior.

**Independent Test**: `demand` category always returns 8 required keys and matches transactional/informational discount expectations from Algo §6.1.

- [ ] T015 [P] [US1] Add failing demand extractor tests (keys, ranges, head-term logic) in `tests/unit/test_signal_extractors.py`
- [ ] T016 [P] [US1] Add failing effective-volume integration assertions in `tests/unit/test_signal_extraction.py`
- [ ] T017 [US1] Implement demand signal extractor in `src/pipeline/extractors/demand_signals.py`
- [ ] T018 [US1] Wire demand extraction into orchestrator in `src/pipeline/signal_extraction.py`
- [ ] T019 [US1] Add null-safe demand defaults and normalization guards in `src/pipeline/signal_extraction.py`

**Checkpoint**: US1 is independently functional and testable.

---

## Phase 4: User Story 2 - Organic Competition Signals (Priority: P2)

**Goal**: Extract complete organic competition signals with aggregator/local business counting.

**Independent Test**: `organic_competition` category always returns 8 keys; known aggregator domains increase `aggregator_count`.

- [ ] T020 [P] [US2] Add failing organic competition signal tests in `tests/unit/test_signal_extractors.py`
- [ ] T021 [P] [US2] Add failing aggregator/domain-classification integration tests in `tests/unit/test_signal_extraction.py`
- [ ] T022 [US2] Implement organic competition extractor in `src/pipeline/extractors/organic_competition.py`
- [ ] T023 [US2] Integrate organic competition extraction path in `src/pipeline/signal_extraction.py`
- [ ] T024 [US2] Add shared-value consistency checks for aggregator-derived fields in `src/pipeline/signal_extraction.py`

**Checkpoint**: US2 is independently functional and testable.

---

## Phase 5: User Story 3 - Local Pack and GBP Pressure Signals (Priority: P3)

**Goal**: Extract local competition signals for both pack-present and pack-missing scenarios.

**Independent Test**: `local_competition` always returns 10 keys, with correct parsing when pack exists and safe defaults when absent.

- [ ] T025 [P] [US3] Add failing local-pack parsing tests in `tests/unit/test_signal_extractors.py`
- [ ] T026 [P] [US3] Add failing no-pack default handling tests in `tests/unit/test_signal_extraction.py`
- [ ] T027 [US3] Implement local competition extractor in `src/pipeline/extractors/local_competition.py`
- [ ] T028 [US3] Integrate local competition extraction in `src/pipeline/signal_extraction.py`
- [ ] T029 [US3] Implement local-pack metric default strategy in `src/pipeline/extractors/local_competition.py`
- [ ] T030 [US3] Add source-to-signal trace comments for local pack derivations in `src/pipeline/extractors/local_competition.py`

**Checkpoint**: US3 is independently functional and testable.

---

## Phase 6: User Story 4 - AI Resilience and Monetization Signals (Priority: P4)

**Goal**: Produce AI resilience and monetization categories from SERP/keyword/listing data with contract-complete outputs.

**Independent Test**: `ai_resilience` returns 5 keys and `monetization` returns 6 keys; AIO detection and ads/LSA flags are correctly reflected.

- [ ] T031 [P] [US4] Add failing AI resilience tests in `tests/unit/test_signal_extractors.py`
- [ ] T032 [P] [US4] Add failing monetization signal tests in `tests/unit/test_signal_extractors.py`
- [ ] T033 [P] [US4] Add failing category-level integration tests in `tests/unit/test_signal_extraction.py`
- [ ] T034 [US4] Implement AI resilience extractor in `src/pipeline/extractors/ai_resilience.py`
- [ ] T035 [US4] Implement monetization extractor in `src/pipeline/extractors/monetization.py`
- [ ] T036 [US4] Integrate AI resilience and monetization in `src/pipeline/signal_extraction.py`

**Checkpoint**: US4 is independently functional and testable.

---

## Phase 7: User Story 5 - Cross-Metro Domain Classification (Priority: P5)

**Goal**: Apply optional cross-metro domain-frequency context to national/directory classification.

**Independent Test**: Domain appearing in 8/20 metros is classified as national and affects downstream local-vs-national counting.

- [ ] T037 [P] [US5] Add failing cross-metro classification tests in `tests/unit/test_domain_classifier.py`
- [ ] T038 [P] [US5] Add failing orchestrator cross-metro context tests in `tests/unit/test_signal_extraction.py`
- [ ] T039 [US5] Implement cross-metro threshold logic in `src/pipeline/domain_classifier.py`
- [ ] T040 [US5] Thread optional `cross_metro_domain_stats` through orchestrator in `src/pipeline/signal_extraction.py`

**Checkpoint**: US5 is independently functional and testable.

---

## Phase 8: User Story 6 - GBP Completeness and Review Velocity Quality (Priority: P6)

**Goal**: Ensure quality and correctness of review velocity and GBP completeness derivations under sparse and rich data.

**Independent Test**: 5/7 GBP fields yields ~0.71 score and review timestamps produce correct reviews/month.

- [ ] T041 [P] [US6] Add failing edge-case tests for review velocity in `tests/unit/test_review_velocity.py`
- [ ] T042 [P] [US6] Add failing edge-case tests for GBP completeness in `tests/unit/test_gbp_completeness.py`
- [ ] T043 [US6] Finalize review velocity edge-case handling in `src/pipeline/review_velocity.py`
- [ ] T044 [US6] Finalize GBP completeness edge-case handling in `src/pipeline/gbp_completeness.py`

**Checkpoint**: US6 is independently functional and testable.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, docs, and full validation across all stories.

- [ ] T045 [P] Add contract conformance regression assertions in `tests/unit/test_signal_extraction.py`
- [ ] T046 [P] Add/refresh fixture coverage for sparse and mixed SERP payloads in `tests/fixtures/m6_signal_extraction_fixtures.py`
- [ ] T047 Run M6-focused lint and unit test commands in `specs/002-m06-signal-extraction-rib/quickstart.md`
- [ ] T048 Update implementation notes and validation outcomes in `specs/002-m06-signal-extraction-rib/plan.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) -> Foundational (Phase 2) -> User Stories (Phases 3-8) -> Polish (Phase 9)
- User story phases can proceed in parallel after Phase 2 if team capacity exists.

### User Story Dependencies

- **US1 (P1)**: starts after Phase 2, no dependency on other user stories (MVP slice)
- **US2 (P2)**: starts after Phase 2, independent but shares domain/parser utilities
- **US3 (P3)**: starts after Phase 2, independent but shares review/GBP utilities
- **US4 (P4)**: starts after Phase 2, independent but shares SERP parser utilities
- **US5 (P5)**: starts after Phase 2; depends on baseline domain-classifier wiring
- **US6 (P6)**: starts after Phase 2; depends on baseline review/GBP utility modules

### Within Each User Story

- Add failing tests first
- Implement extractor/logic next
- Wire orchestration and defaults last
- Validate independent acceptance criteria before moving on

---

## Parallel Execution Examples

### User Story 1

```bash
Task: "T015 [US1] demand extractor tests in tests/unit/test_signal_extractors.py"
Task: "T016 [US1] effective-volume integration tests in tests/unit/test_signal_extraction.py"
```

### User Story 2

```bash
Task: "T020 [US2] organic competition tests in tests/unit/test_signal_extractors.py"
Task: "T021 [US2] aggregator integration tests in tests/unit/test_signal_extraction.py"
```

### User Story 3

```bash
Task: "T025 [US3] local-pack parsing tests in tests/unit/test_signal_extractors.py"
Task: "T026 [US3] missing-pack defaults tests in tests/unit/test_signal_extraction.py"
```

### User Story 4

```bash
Task: "T031 [US4] AI resilience tests in tests/unit/test_signal_extractors.py"
Task: "T032 [US4] monetization tests in tests/unit/test_signal_extractors.py"
Task: "T033 [US4] category integration tests in tests/unit/test_signal_extraction.py"
```

### User Story 5

```bash
Task: "T037 [US5] cross-metro classifier tests in tests/unit/test_domain_classifier.py"
Task: "T038 [US5] orchestrator cross-metro tests in tests/unit/test_signal_extraction.py"
```

### User Story 6

```bash
Task: "T041 [US6] review velocity edge-case tests in tests/unit/test_review_velocity.py"
Task: "T042 [US6] GBP completeness edge-case tests in tests/unit/test_gbp_completeness.py"
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate demand extraction criteria independently.
4. Demo or checkpoint before expanding to additional stories.

### Incremental Delivery

1. Deliver US1 (demand) first.
2. Add US2 + US3 for competition readiness.
3. Add US4 for AI + monetization readiness.
4. Add US5 + US6 for cross-metro and quality refinements.
5. Finish with Phase 9 polish and full validation.

### Parallel Team Strategy

1. Team aligns on Phase 1-2 first.
2. Then split by stories:
   - Engineer A: US1/US2
   - Engineer B: US3/US6
   - Engineer C: US4/US5
3. Rejoin for Phase 9 contract and regression polish.

---

## Notes

- `[P]` tasks are safe to run concurrently because they target separate files or test additions.
- All story phases are independently testable by their defined criteria.
- Keep implementation deterministic and pure (no outbound API behavior in M6).
