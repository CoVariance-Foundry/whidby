# Feature Specification: M5 Data Collection Refresh

**Feature Branch**: `001-refresh-m5-data-collection`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "@.specify/specs/M05-data-collection/spec.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run complete collection for one metro (Priority: P1)

As a scoring operator, I can run one collection request and receive a complete, structured raw dataset for a single metro so downstream scoring can proceed without manual data gathering.

**Why this priority**: This is the minimum slice that unlocks end-to-end scoring value for any niche and metro.

**Independent Test**: Submit one metro and a valid expanded keyword set, then verify the response includes all required data categories (or explicit empty values where not applicable) plus run metadata.

**Acceptance Scenarios**:

1. **Given** a valid keyword expansion and a valid metro, **When** collection completes, **Then** the result includes every required raw data category with explicit values or explicit empties.
2. **Given** the same input, **When** collection completes, **Then** the result includes run-level metadata for call count, total cost, total duration, and encountered errors.

---

### User Story 2 - Run collection across multiple metros consistently (Priority: P2)

As a scoring operator, I can run the same collection request across multiple metros and get clearly partitioned results per metro so market comparisons are reliable.

**Why this priority**: Multi-metro consistency is required for ranking opportunities and avoiding cross-market contamination.

**Independent Test**: Submit at least two metros in one run, then verify each metro has isolated outputs and consistent coverage rules.

**Acceptance Scenarios**:

1. **Given** two or more metros in one request, **When** collection completes, **Then** each metro's output is isolated under its own metro identifier.
2. **Given** the same keyword expansion for all metros, **When** collection completes, **Then** each metro receives equivalent keyword coverage and consistent eligibility rules for deeper data pulls.

---

### User Story 3 - Continue useful collection during partial failures (Priority: P3)

As a scoring operator, I still receive usable partial results when some external lookups fail so analysis and troubleshooting can continue without rerunning everything immediately.

**Why this priority**: External data dependencies can fail intermittently; resilience reduces rerun costs and operational delays.

**Independent Test**: Simulate failures in selected external lookups and confirm independent lookups continue, partial results are returned, and failures are documented.

**Acceptance Scenarios**:

1. **Given** one or more failed sub-requests, **When** collection completes, **Then** successful independent sub-requests are still included in the output.
2. **Given** one or more failed sub-requests, **When** collection completes, **Then** each failure is recorded with enough context to diagnose and retry the failed scope.

---

### Edge Cases

- A metro has no principal cities available at collection time.
- The keyword expansion for a metro is empty or exceeds normal batching thresholds.
- Upstream responses include duplicate domains or businesses across metros in the same run.
- A data source returns partial payloads missing expected attributes.
- Cost metadata is unavailable for a subset of successful calls.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a collection request containing expanded keywords, one or more metros, and a strategy profile context.
- **FR-002**: The system MUST return results partitioned by metro, with each metro containing the full required raw data categories for downstream scoring.
- **FR-003**: The system MUST enforce keyword eligibility rules so only eligible keywords trigger deeper search-result collection while all keywords receive baseline demand metrics.
- **FR-004**: The system MUST execute independent collection tasks in parallel where possible and enforce dependency ordering where downstream tasks require prior identifiers.
- **FR-005**: The system MUST deduplicate repeated downstream lookup targets within a run where duplicates would not change scoring outcomes.
- **FR-006**: The system MUST preserve raw search-result feature signals required by downstream extraction and scoring steps.
- **FR-007**: The system MUST batch high-volume keyword demand requests efficiently rather than issuing one request per keyword when batching is possible.
- **FR-008**: The system MUST provide run metadata including total external call count, total cost, total collection duration, and a structured error list.
- **FR-009**: The system MUST continue independent collection work after a sub-task failure and return partial results with failure details instead of failing the entire run.

### Key Entities *(include if feature involves data)*

- **Collection Request**: Input object containing expanded keywords, metros, and strategy profile context for a single run.
- **Metro Collection Result**: Per-metro container of raw collected datasets grouped by required data category.
- **Run Metadata**: Aggregated operational summary for a run, including duration, external call count, estimated cost, and failure records.
- **Failure Record**: Structured diagnostic event describing what failed, where it failed, and the scope affected.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In test runs with one valid metro, 100% of completed runs return all required raw data categories with explicit populated or explicit empty values.
- **SC-002**: In test runs with at least three metros, 100% of completed runs return metro-partitioned outputs with no cross-metro data leakage.
- **SC-003**: In controlled failure tests, at least 90% of independent sub-tasks still complete and are returned when one dependency path fails.
- **SC-004**: For each completed run, reported total cost and call count reconcile with summed per-call records to within 1% tolerance.
- **SC-005**: In keyword sets at or below batching thresholds, collection uses batched demand lookups in at least 95% of eligible cases.
- **SC-006**: In downstream extraction validation, at least 95% of sampled collected search-result payloads contain the feature fields required for scoring.

## Assumptions

- The expanded keyword input includes enough metadata to determine eligibility for deeper collection.
- Metro inputs include valid location identifiers and principal-city context from upstream data preparation.
- External data providers can return intermittent failures; this feature optimizes for resilient completion and transparent error reporting.
- This feature focuses on collection quality and completeness; ranking logic remains the responsibility of downstream modules.
- Existing reporting consumers can accept explicit empty category values when data is legitimately unavailable.
