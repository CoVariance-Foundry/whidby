# Tasks: Niche Finder Exploration Interface

**Input**: Design documents from `/specs/011-niche-exploration-ui/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: No explicit TDD/test-first requirement was stated in the feature spec, so implementation tasks are prioritized. Validation is included via quickstart and quality gate execution tasks.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`) for story-phase tasks only
- All tasks include exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare dual-surface UI scaffolding and shared contracts for implementation.

- [X] T001 Create task baseline notes and implementation checklist in `specs/011-niche-exploration-ui/quickstart.md`
- [X] T002 [P] Create shared niche finder input/output TypeScript types in `apps/app/src/lib/niche-finder/types.ts`
- [X] T003 [P] Create exploration evidence and assistant response TypeScript types in `apps/app/src/lib/niche-finder/exploration-types.ts`
- [X] T004 Create shared query normalization utility for city/service input in `apps/app/src/lib/niche-finder/query-normalization.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement common flows required by all user stories.

**⚠️ CRITICAL**: User story implementation starts only after this phase is complete.

- [X] T005 Build shared scoring request proxy route for normalized city/service queries in `apps/app/src/app/api/agent/scoring/route.ts`
- [X] T006 Build shared exploration request proxy route that returns score and evidence payload in `apps/app/src/app/api/agent/exploration/route.ts`
- [X] T007 [P] Add server-side payload validation and user-readable error mapping in `apps/app/src/lib/niche-finder/request-validation.ts`
- [X] T008 [P] Add backend adapter for parity-safe scoring/exploration response shaping in `apps/app/src/lib/niche-finder/response-adapter.ts`
- [X] T009 Wire query context state helper for cross-surface preservation in `apps/app/src/lib/niche-finder/session-context.ts`

**Checkpoint**: Shared APIs, validation, and context preservation utilities are ready.

---

## Phase 3: User Story 1 - Generate Comparable Niche Scores (Priority: P1) 🎯 MVP

**Goal**: Deliver standard niche finder flow where valid city/service inputs return scored results with clear validation feedback.

**Independent Test**: Submit valid and invalid city/service inputs from standard surface and verify score success and validation handling without using exploration components.

### Implementation for User Story 1

- [X] T010 [US1] Implement standard niche finder input form and submit action in `apps/app/src/components/niche-finder/StandardNicheForm.tsx`
- [X] T011 [US1] Implement standard score result panel for opportunity and classification output in `apps/app/src/components/niche-finder/StandardScoreResult.tsx`
- [X] T012 [US1] Integrate standard surface flow into protected home page in `apps/app/src/app/(protected)/page.tsx`
- [X] T013 [US1] Add standard surface loading/empty/error states in `apps/app/src/components/niche-finder/StandardSurfaceState.tsx`
- [X] T014 [US1] Ensure standard surface submit path uses shared normalization and scoring API contract in `apps/app/src/lib/niche-finder/standard-surface-service.ts`

**Checkpoint**: User Story 1 is functional and independently demonstrable.

---

## Phase 4: User Story 2 - Inspect Score Rationale with Raw Inputs (Priority: P1)

**Goal**: Deliver exploration surface that returns the same score for equivalent input while exposing score-driving evidence.

**Independent Test**: Run matching city/service queries in standard and exploration surfaces and verify score parity plus visible evidence sections (including partial evidence handling).

### Implementation for User Story 2

- [X] T015 [P] [US2] Implement exploration query form with shared city/service inputs in `apps/app/src/components/niche-finder/ExplorationQueryForm.tsx`
- [X] T016 [P] [US2] Implement exploration score summary panel aligned with standard output in `apps/app/src/components/niche-finder/ExplorationScoreSummary.tsx`
- [X] T017 [P] [US2] Implement raw evidence section list with category/label/source rendering in `apps/app/src/components/niche-finder/EvidencePanel.tsx`
- [X] T018 [US2] Implement explicit missing-evidence fallback rows in `apps/app/src/components/niche-finder/EvidenceMissingState.tsx`
- [X] T019 [US2] Compose exploration surface page and bind evidence + score views in `apps/app/src/app/(protected)/exploration/page.tsx`
- [X] T020 [US2] Add score parity comparison guard for standard vs exploration responses in `apps/app/src/lib/niche-finder/parity-guard.ts`
- [X] T021 [US2] Preserve active query context when toggling between standard and exploration surfaces in `apps/app/src/components/Sidebar.tsx`

**Checkpoint**: User Stories 1 and 2 are independently usable with parity and transparency guarantees.

---

## Phase 5: User Story 3 - Investigate with Guided Agent Queries (Priority: P2)

**Goal**: Add exploration assistant follow-up capability that uses approved plugin-backed querying while keeping city/service context stable.

**Independent Test**: Ask follow-up questions from exploration surface and verify evidence-referenced responses, unsupported fallback guidance, and preserved query context.

### Implementation for User Story 3

- [X] T022 [US3] Implement exploration assistant chat panel UI bound to active query context in `apps/app/src/components/niche-finder/ExplorationAssistantPanel.tsx`
- [X] T023 [US3] Create assistant follow-up API route for exploration sessions in `apps/app/src/app/api/agent/exploration-chat/route.ts`
- [X] T024 [US3] Add request/response contract mapping for assistant payloads in `apps/app/src/lib/niche-finder/exploration-assistant-service.ts`
- [X] T025 [US3] Extend plugin-backed assistant orchestration for exploration mode in `src/research_agent/agent/claude_agent.py`
- [X] T026 [P] [US3] Add exploration-safe scoring plugin tool path for follow-up evidence retrieval in `src/research_agent/plugins/scoring_plugin.py`
- [X] T027 [P] [US3] Add exploration-safe SERP plugin tool path for follow-up data retrieval in `src/research_agent/plugins/dataforseo_plugin.py`
- [X] T028 [US3] Implement unsupported/partial assistant response guidance mapping in `apps/app/src/components/niche-finder/AssistantFallbackState.tsx`

**Checkpoint**: All user stories are independently functional and collectively integrated.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cross-story hardening, docs alignment, and quality gate execution.

- [X] T029 [P] Update architecture and requirements notes for dual-surface and exploration assistant behavior in `docs-canonical/ARCHITECTURE.md`
- [X] T030 [P] Update detailed feature references for niche scoring and exploration flow in `docs/product_breakdown.md`
- [X] T031 Run Python quality gates for changed backend/plugin files with `ruff check src tests` from repository root
- [X] T032 Run Python unit tests for changed backend/plugin behavior with `pytest tests/unit/ -v` from repository root
- [X] T033 Run web lint validation for changed app files with `npm run lint` from repository root
- [X] T034 Execute end-to-end quickstart validation checklist in `specs/011-niche-exploration-ui/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Starts immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks story work
- **Phase 3 (US1)**: Depends on Phase 2; serves as MVP
- **Phase 4 (US2)**: Depends on Phase 2 and integrates with US1 outputs for parity checks
- **Phase 5 (US3)**: Depends on Phase 2 and uses exploration context from US2
- **Phase 6 (Polish)**: Depends on completion of desired user stories

### User Story Dependencies

- **US1 (P1)**: Independent once foundational work is complete
- **US2 (P1)**: Independent once foundational work is complete, with parity checks against US1 score output
- **US3 (P2)**: Depends on exploration surface context from US2 and shared foundational APIs

### Within Each User Story

- Shared helpers first, then UI/service wiring, then route integration
- Context preservation tasks complete before cross-surface navigation validation
- Assistant contract mapping complete before plugin-orchestration extension

### Parallel Opportunities

- **Setup**: T002 and T003 can run in parallel
- **Foundational**: T007 and T008 can run in parallel after T005/T006 path definitions
- **US2**: T015, T016, and T017 can run in parallel
- **US3**: T026 and T027 can run in parallel after T025 exploration mode scaffold
- **Polish**: T029 and T030 can run in parallel

---

## Parallel Example: User Story 2

```bash
Task: "T015 [US2] Implement exploration query form in apps/app/src/components/niche-finder/ExplorationQueryForm.tsx"
Task: "T016 [US2] Implement exploration score summary in apps/app/src/components/niche-finder/ExplorationScoreSummary.tsx"
Task: "T017 [US2] Implement evidence panel in apps/app/src/components/niche-finder/EvidencePanel.tsx"
```

## Parallel Example: User Story 3

```bash
Task: "T026 [US3] Add exploration-safe scoring plugin path in src/research_agent/plugins/scoring_plugin.py"
Task: "T027 [US3] Add exploration-safe SERP plugin path in src/research_agent/plugins/dataforseo_plugin.py"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1 and Phase 2
2. Deliver Phase 3 (US1) for score generation flow
3. Validate independent US1 behavior before expanding scope

### Incremental Delivery

1. Add US2 to introduce transparent evidence and parity guarantees
2. Add US3 to provide guided exploration with assistant follow-ups
3. Run Phase 6 quality gates and docs updates before handoff

### Parallel Team Strategy

1. One developer completes foundational APIs and validation helpers
2. One developer owns US2 UI evidence components
3. One developer owns US3 assistant backend/plugin extensions
4. Merge by contract boundaries and run shared validation gates

---

## Notes

- `[P]` tasks are scoped to separate files and can be executed concurrently
- Story labels (`[US1]`, `[US2]`, `[US3]`) are applied to all user-story phase tasks
- Tasks are written to preserve independent testability of each user story
- Suggested MVP scope: complete through Phase 3 (US1) before starting US2/US3
