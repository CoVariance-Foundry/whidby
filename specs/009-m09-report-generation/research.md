# Research: M9 Report Generation + Feedback Logging

## Decision 1: Split assembly and persistence into separate modules

- **Decision**: Implement `src/pipeline/report_generator.py` as a pure report assembler and `src/pipeline/feedback_logger.py` as the Supabase write boundary.
- **Rationale**: Keeps deterministic report construction isolated from I/O failures and matches FR-007 responsibility split.
- **Alternatives considered**:
  - Single module performing both duties (rejected: mixes side effects with pure formatting/sorting).
  - Writing feedback before report assembly (rejected: risks logging incomplete/failed runs).

## Decision 2: Enforce deterministic ranking with explicit tie-break keys

- **Decision**: Sort metros by descending `scores.opportunity`, then secondary stable keys (`cbsa_code`, then `cbsa_name`) when scores tie.
- **Rationale**: Spec edge-case requires deterministic ordering for ties and stable downstream exports.
- **Alternatives considered**:
  - Sort only by opportunity (rejected: non-deterministic on equal values).
  - Preserve input order for ties (rejected: upstream order can be shuffled and unstable).

## Decision 3: Treat report JSON contract as canonical output boundary

- **Decision**: Validate generated report objects against an M9 contract document mirroring Algo Spec v1.1 section 10.1 required fields.
- **Rationale**: Downstream consumers (M16 UI, research agent) depend on schema-stable fields and versioning.
- **Alternatives considered**:
  - Ad hoc dict assertions in unit tests only (rejected: weaker contract visibility).
  - Deferring schema checks to integration only (rejected: slower feedback and harder debugging).

## Decision 4: Log one feedback tuple per ranked metro with nullable outcomes

- **Decision**: Persist one row per metro recommendation containing context/signals/scores/classification plus nullable `outcome` fields exactly as allowed by Algo Spec section 9.2.
- **Rationale**: Supports future bandit training requirements and satisfies FR-004/FR-005 null-safe persistence.
- **Alternatives considered**:
  - One log row per run only (rejected: loses per-metro learning signal).
  - Omitting null fields when unknown (rejected: breaks explicit schema semantics).

## Decision 5: Define failure policy that protects report artifact integrity

- **Decision**: Report generation completes first; feedback logging failures surface explicit errors/return status without mutating an already-built report object.
- **Rationale**: Meets user story 2 acceptance scenario for persistence failure handling without corrupting output.
- **Alternatives considered**:
  - Fail entire pipeline and drop report output (rejected: harms operator workflow).
  - Silently swallow persistence exceptions (rejected: hides data loss and violates observability).

## Decision 6: Reuse existing M4-M8 output contracts without recomputation

- **Decision**: M9 consumes upstream outputs as inputs and performs only assembly/transformation/ordering; no recalculating scores/classifications.
- **Rationale**: Preserves module boundaries and constitution principle II (module-first architecture).
- **Alternatives considered**:
  - Recompute derived fields inside M9 for convenience (rejected: drift risk and redundant logic).
  - Fetch fresh external data at report time (rejected: violates deterministic stage boundaries).

