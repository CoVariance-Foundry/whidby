# Phase 0 Research: M04 Keyword Expansion

## Decision 1: Expansion confidence bands use overlap thresholds (high/medium/low)

- **Decision**: Compute overlap between top LLM candidates and DataForSEO suggestions and map confidence as:
  - `low` if overlap < 0.30
  - `medium` if overlap >= 0.30 and < 0.60
  - `high` if overlap >= 0.60
- **Rationale**: The algorithm spec explicitly defines the low-confidence floor (<30%) and leaves room for deterministic upper bands. Introducing a fixed medium/high split keeps behavior testable and avoids ad hoc interpretation.
- **Alternatives considered**:
  - Binary confidence (`low`/`high`) only — rejected because the output contract includes `medium`.
  - Heuristic confidence using many inputs (cost, token count, niche rarity) — rejected for complexity and lower determinism.

## Decision 2: Canonical intent assignment uses strict precedence

- **Decision**: Use deterministic precedence for intent label assignment:
  1. Explicit intent from validated structured LLM keyword payload
  2. Rule-based keyword matcher for clear lexical patterns (e.g., "how to", "what is", "near me", "best")
  3. Fallback single-query intent classification call
  4. Default intent `commercial` on classification failure
- **Rationale**: Existing M3 behavior already defaults to `commercial` on classifier failure. A strict precedence chain avoids run-to-run drift and makes FR-004 and SC-002 verifiable.
- **Alternatives considered**:
  - Always classify every keyword independently — rejected due to avoidable latency/cost increase.
  - Majority-vote ensemble between rule-based and classifier outputs — rejected due to unnecessary complexity for V1.

## Decision 3: Keyword deduplication normalization policy

- **Decision**: Normalize before deduplication with this deterministic transform:
  - trim leading/trailing whitespace
  - lowercase
  - collapse repeated internal whitespace
  - remove terminal punctuation-only differences
  - preserve semantic words/order (no stemming or synonym merging)
- **Rationale**: This resolves formatting-variant duplicates while preserving meaning differences required for scoring and auditability.
- **Alternatives considered**:
  - Aggressive normalization with stemming/lemmatization — rejected because it can merge distinct commercial intents.
  - Exact-string dedupe only — rejected because it misses trivial formatting variants and violates SC-003.

## Decision 4: Upstream failure handling returns partial-but-usable result

- **Decision**: If one enrichment source fails (LLM or DataForSEO), return a structured `KeywordExpansion` result from the remaining source and force `expansion_confidence="low"` with explicit quality counters.
- **Rationale**: The spec requires a usable structured response even under degraded conditions (FR-011) and explicit confidence signaling (FR-008).
- **Alternatives considered**:
  - Hard fail and return error only — rejected because it blocks downstream workflow unnecessarily.
  - Silent fallback without confidence downgrade — rejected because it hides quality degradation.

## Decision 5: Sort order is deterministic and stable

- **Decision**: Final keyword ordering is stable by `(tier asc, intent priority, keyword asc)` where intent priority is `transactional`, `commercial`, `informational`.
- **Rationale**: Deterministic ordering is required by FR-010 and SC-005, and this sequence aligns with actionability-first downstream usage.
- **Alternatives considered**:
  - Preserve source insertion order — rejected because upstream source response ordering can vary.
  - Sort by external metrics (volume/CPC) in M4 — rejected because those metrics are collected in M5.

## Decision 6: Contract scope includes downstream compatibility fields

- **Decision**: The M4 contract includes all fields required by downstream modules: keyword text, tier, intent, source, aio_risk, actionability flags, confidence, and reconciled counts.
- **Rationale**: `docs/data_flow.md` and `docs/module_dependency.md` show M5/M6 dependence on M4 output. Capturing the full contract now reduces integration ambiguity.
- **Alternatives considered**:
  - Minimal contract with only keyword text + intent — rejected because it shifts required decisions to downstream modules and weakens module boundaries.
