# Feature Specification: M9 Report Generation + Feedback Logging

**Feature Branch**: `009-m09-report-generation`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: Module M9 — final ranked report JSON and feedback logging (Algo Spec V1.1 §10 Output Schema, §9 Feedback Logging)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Final ranked report for a niche run (Priority: P1)

As a Widby operator, I need a single assembled report for a scoring run that lists all metros ranked by opportunity score (descending) and includes the meta/cost summary so I can export or consume the run downstream.

**Why this priority**: The report is the deliverable of the core pipeline; ordering and schema correctness are contract-breaking if wrong.

**Independent Test**: Given outputs from M4–M8 for one run, report generation produces one JSON document validating against the output schema and metros sorted by `opportunity` descending.

**Acceptance Scenarios**:

1. **Given** a complete pipeline result set for multiple metros, **When** the report is assembled, **Then** every metro appears exactly once with scores, classifications, and guidance references per §10.
2. **Given** two metros A and B where A’s opportunity score is higher than B’s, **When** the report is generated, **Then** A appears before B in the metro list.
3. **Given** run metadata and API cost accounting inputs, **When** the report is generated, **Then** meta fields reflect accurate totals within the tolerance defined in module tasks (exact match on fixture costs).

---

### User Story 2 - Durable feedback log for calibration (Priority: P2)

As a Widby operator (and platform), I need each run logged to feedback storage so future calibration, experiments, and quality reviews can reference what was scored, with null-safe fields for incomplete outcomes.

**Why this priority**: Feedback logging underpins continuous improvement and experiment frameworks.

**Independent Test**: After a successful report write, a feedback log row (or equivalent) exists in persistence with foreign keys/metadata tying back to the run; null outcomes are stored without violating schema.

**Acceptance Scenarios**:

1. **Given** a completed report and Supabase availability, **When** feedback logging runs, **Then** a feedback log record is created per §9 with required identifiers and timestamps.
2. **Given** partial/null fields where the spec allows nulls (e.g. missing optional outcome), **When** feedback logging runs, **Then** the log row persists with nulls in permitted columns and does not fail the pipeline.
3. **Given** persistence failure, **When** feedback logging runs, **Then** behavior matches the error-handling contract (surface error, retry policy, or non-fatal warn — as defined in plan/tasks) without corrupting the on-disk report artifact if already written.

---

### User Story 3 - Schema-stable consumption (Priority: P3)

As a downstream integrator, I need the report JSON to validate against the published schema so dashboards and agents can parse fields reliably.

**Why this priority**: Breaking schema changes ripple to M16 and the research agent.

**Independent Test**: CI validates sample reports against JSON Schema or equivalent contract from §10.

**Acceptance Scenarios**:

1. **Given** a golden fixture report, **When** schema validation runs, **Then** validation passes with zero errors.
2. **Given** a report missing a required §10 field, **When** validation runs, **Then** validation fails with a clear pointer to the missing path.

---

### Edge Cases

- Zero metros in run: report is still well-formed or explicitly rejected with a defined error per spec/tasks.
- Tied opportunity scores: ordering tie-break is deterministic (e.g. stable secondary key such as metro id).
- Very large batches: report generation completes within agreed performance bounds in tasks; streaming/chunking only if spec allows.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST assemble M4–M8 outputs into a final report JSON conforming to `docs/algo_spec_v1_1.md` §10 (Output Schema).
- **FR-002**: System MUST rank metros by composite `opportunity` score descending in the report’s metro collection.
- **FR-003**: System MUST include accurate run meta including cost accounting fields per §10 and project constants.
- **FR-004**: System MUST write a feedback log entry per `docs/algo_spec_v1_1.md` §9 (Feedback Logging), using M2 Supabase persistence.
- **FR-005**: System MUST represent null outcomes in feedback logging where the schema permits nulls, without coercion to incorrect defaults.
- **FR-006**: System MUST depend on the full pipeline output through M8 and on M2 for feedback persistence; MUST NOT re-run scoring or classification inside the report generator except for trivial formatting.
- **FR-007**: Module implementation MUST live in `src/pipeline/report_generator.py` and `src/pipeline/feedback_logger.py` (paths may follow existing package layout; file names as listed).

### Key Entities

- **Pipeline run**: Identifier, timestamps, niche/metro set, configuration snapshot pointers.
- **Report document**: Versioned JSON matching §10, ordered metro array, meta/cost block.
- **Feedback log record**: Persisted row linking run id, key scores/outcomes, nullable fields per §9.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of golden reports pass automated schema validation for §10.
- **SC-002**: For random shuffled input metro order, generated reports always list metros in strict non-increasing opportunity order; ties broken deterministically.
- **SC-003**: Meta cost fields in the report match fixture expectations exactly in unit tests.
- **SC-004**: Feedback log creation is verified in tests (mock or test DB): a row exists after successful logging; null-outcome cases persist without error.

## Assumptions

- Supabase schema for feedback logging is delivered/updated in M2 migrations before M9 merges; environment provides service credentials in CI for integration tests where required.
- Report versioning aligns with `algo_spec_v1_1` §10 version field; breaking schema changes bump version and update consumers in the same release train.
- M4–M8 contracts are stable enough to freeze report assembly; changes require coordinated updates to §10 references.

## Source specifications


| Document                    | Role                                                         |
| --------------------------- | ------------------------------------------------------------ |
| `docs/algo_spec_v1_1.md`    | §10 Output Schema — report shape, required fields, meta/cost |
| `docs/algo_spec_v1_1.md`    | §9 Feedback Logging — persistence semantics and nullability  |
| `docs/product_breakdown.md` | Module map and eval criteria for M9                          |
| `docs/module_dependency.md` | M9 as consumer of M4–M8 and M2                               |
| `docs/data_flow.md`         | End-to-end assembly order and artifact names                 |
