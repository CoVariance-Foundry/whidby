# Research: M5 Data Collection Refresh

## Decision 1: Use deterministic two-phase execution plan

- **Decision**: Split execution into (a) independent base pulls and (b) dependency-based enrichment pulls.
- **Rationale**: The spec requires parallelism for independent work and strict dependency ordering for backlink, lighthouse, GBP info, and reviews.
- **Alternatives considered**:
  - Single flat task queue with ad hoc dependencies (rejected: harder to reason about and test deterministically).
  - Fully sequential execution (rejected: violates performance and batching goals).

## Decision 2: Preserve existing DataForSEO client boundary

- **Decision**: M5 orchestrator will call existing `DataForSEOClient` methods without bypassing client internals.
- **Rationale**: Existing client already encapsulates retries, queue/live endpoint handling, and cost tracking metadata.
- **Alternatives considered**:
  - Direct HTTP calls from M5 (rejected: duplicates logic, increases drift risk).
  - New client wrapper layer (rejected: unnecessary abstraction for current scope).

## Decision 3: Build explicit task graph from keyword and metro inputs

- **Decision**: Implement a planner that emits typed task groups and dependency edges before execution.
- **Rationale**: Planning enables testable assertions around keyword eligibility, batching, deduplication, and dependency constraints.
- **Alternatives considered**:
  - Generate tasks inside executor on the fly (rejected: difficult to validate planning logic independently).

## Decision 4: Batch keyword volume by metro with 700-keyword cap

- **Decision**: Partition keyword volume requests into chunks of up to 700 keywords per metro.
- **Rationale**: Aligns with documented endpoint limits and required batch-efficiency acceptance criteria.
- **Alternatives considered**:
  - One request per keyword (rejected: too expensive and slow).
  - Global batches across metros (rejected: breaks metro partitioning semantics).

## Decision 5: Deduplicate downstream targets within run scope

- **Decision**: Deduplicate backlinks by domain and deduplicate other enrichment targets where duplicates do not alter scoring outcomes.
- **Rationale**: Reduces external call volume and cost while preserving output quality.
- **Alternatives considered**:
  - No deduplication (rejected: cost inflation and unnecessary repeated calls).
  - Cross-run deduplication cache in M5 (rejected: out of scope for this feature).

## Decision 6: Return explicit empty category collections

- **Decision**: Always include all required data categories per metro, using explicit empty lists/maps when no data is available.
- **Rationale**: Downstream modules and tests rely on stable contracts without missing keys.
- **Alternatives considered**:
  - Omit unavailable categories (rejected: ambiguous contract and extra downstream branching).

## Decision 7: Track run-level metadata as first-class output

- **Decision**: Compute and return total calls, total cost, total duration, and structured errors in run metadata.
- **Rationale**: Required by acceptance criteria and critical for operational diagnostics.
- **Alternatives considered**:
  - Logging-only metrics (rejected: not machine-consumable for downstream/reporting validation).

