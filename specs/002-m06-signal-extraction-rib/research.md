# Research: M6 Signal Extraction

## Decision 1: Keep signal extraction as a pure transformation stage

- **Decision**: Implement M6 as deterministic pure functions over M5 + M4 input data, with no network calls.
- **Rationale**: Constitution principles and M6 module boundaries require reproducible, testable extraction independent of external service behavior.
- **Alternatives considered**:
  - Call APIs during extraction (rejected: violates module contract and determinism).
  - Merge extraction into M7 scoring (rejected: blurs responsibilities and weakens test isolation).

## Decision 2: Use category-specific extractor modules with one orchestration entry point

- **Decision**: Implement `extract_signals(...)` as orchestration over five extractor modules (`demand`, `organic_competition`, `local_competition`, `ai_resilience`, `monetization`).
- **Rationale**: Aligns with Algo §6 category boundaries and simplifies TDD with focused fixtures.
- **Alternatives considered**:
  - Single monolithic extractor file (rejected: difficult to maintain and test).
  - Per-signal micro-functions only (rejected: excessive indirection for current scope).

## Decision 3: Implement effective volume exactly from constants and Algo §6.1

- **Decision**: `effective_volume` uses `AIO_CTR_REDUCTION` and `INTENT_AIO_RATES` from `src/config/constants.py` and applies detected-AIO override first.
- **Rationale**: The feature requires exact parity with Algo §6.1 formula and avoids duplicated literals.
- **Alternatives considered**:
  - Hardcode rates in extractor modules (rejected: drift risk).
  - Use one blended global AIO rate (rejected: loses intent fidelity and breaks acceptance criteria).

## Decision 4: Centralize SERP feature parsing

- **Decision**: Build `serp_parser` utilities that normalize feature flags/counters (`aio`, `featured snippet`, `paa`, `local pack`, `ads`, `lsa`) from raw M5 SERP payloads.
- **Rationale**: Multiple extractor categories depend on shared SERP facts; one parser keeps feature semantics consistent.
- **Alternatives considered**:
  - Parse SERP features separately in each extractor (rejected: duplicate logic and potential inconsistencies).
  - Store parser output as persisted intermediate data (rejected: unnecessary persistence for V1).

## Decision 5: Hybrid domain classification (known sets + cross-metro frequency)

- **Decision**: `domain_classifier` combines `KNOWN_AGGREGATORS` with a cross-metro frequency heuristic (>=30% metros => national/directory).
- **Rationale**: Matches Algo §6.6-6.7 and supports both known directories and emergent national domains.
- **Alternatives considered**:
  - Known-list only classification (rejected: misses unknown national brands).
  - Frequency-only classification (rejected: slower convergence and weaker deterministic behavior for known aggregators).

## Decision 6: Compute review velocity and GBP completeness in dedicated helpers

- **Decision**: Isolate `review_velocity` and `gbp_completeness` into dedicated modules with explicit defaults.
- **Rationale**: These are reusable derived signals with clear formulas and edge-case handling needs.
- **Alternatives considered**:
  - Inline computation in local competition extractor (rejected: harder to unit test and reuse).
  - Leave missing data as nulls only (rejected: downstream scoring requires stable defaults).

## Decision 7: Define explicit defaulting rules for missing local-pack and GBP data

- **Decision**: Output all required keys with safe defaults when source data is absent.
- **Rationale**: M7 expects stable contracts and should not branch on missing keys.
- **Alternatives considered**:
  - Omit unavailable keys (rejected: contract instability).
  - Raise extraction errors on missing categories (rejected: brittle for real-world sparse SERPs).

## Decision 8: Treat cross-metro context as explicit optional input

- **Decision**: Keep one-metro extraction API for core output and accept optional cross-metro domain-frequency context for national classification.
- **Rationale**: Preserves M6 single-metro contract while enabling AS-5.1/AS-5.2 behavior.
- **Alternatives considered**:
  - Require full batch data always (rejected: reduces composability).
  - Ignore cross-metro rule in M6 (rejected: violates accepted spec behavior).
