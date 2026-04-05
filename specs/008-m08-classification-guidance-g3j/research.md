# Research: M8 Classification + Guidance

## Decision 1: Implement archetype classification as ordered deterministic rules

- **Decision**: Use an explicit first-match rule chain in `serp_archetype.py` that mirrors Algo §8.1 precedence (aggregator dominance first, then local-pack branches, then fragmented/barren, then mixed fallback).
- **Rationale**: The spec requires exactly one archetype output with deterministic tie-break behavior for conflicting weak signals.
- **Alternatives considered**:
  - Score-based multi-label classifier (rejected: harder to debug and not required by spec).
  - LLM-only archetype labeling (rejected: violates deterministic pipeline intent).

## Decision 2: Keep AI exposure classification orthogonal and threshold-based

- **Decision**: Implement `ai_exposure.py` as a pure threshold mapper over `aio_trigger_rate` with four outputs: `AI_SHIELDED`, `AI_MINIMAL`, `AI_MODERATE`, `AI_EXPOSED`.
- **Rationale**: Algo §8.2 defines clear cutoff bands and treats exposure as independent from archetype.
- **Alternatives considered**:
  - Blend exposure into archetype (rejected: mixes two dimensions and reduces clarity).
  - Dynamic percentiles by batch (rejected: non-deterministic across runs).

## Decision 3: Difficulty tier must reuse strategy-profile weighting logic from scoring

- **Decision**: `difficulty_tier.py` will consume `organic_competition` and `local_competition` scores with strategy-profile weight resolution aligned to M7 so tiers and opportunity remain internally consistent.
- **Rationale**: Algo §8.3 explicitly ties difficulty weighting to the same profile logic used in composite scoring.
- **Alternatives considered**:
  - Static equal weighting (rejected: would diverge from strategy profile behavior).
  - Recompute competition from raw signals (rejected: violates FR-005 and module boundaries).

## Decision 4: Guidance generation will be template-first with bounded LLM completion

- **Decision**: `guidance_generator.py` will build structured prompt/context from classification outputs and niche/metro inputs, then request concise copy from M3 with explicit guardrails (tone, length, non-contradiction).
- **Rationale**: FR-004 requires M3 usage while preserving deterministic structure and readability.
- **Alternatives considered**:
  - Fully static guidance text only (rejected: insufficient contextual variation).
  - Free-form LLM generation with no template anchors (rejected: contradiction risk).

## Decision 5: Define explicit fail-safe behavior for LLM timeout/error

- **Decision**: On LLM failure, return template-only guidance with `guidance_status` indicating degraded mode; never emit fabricated uncertain claims.
- **Rationale**: Acceptance scenario requires non-silent degradation and avoids wrong advice.
- **Alternatives considered**:
  - Raise hard error and block M8 output (rejected: classification should still complete).
  - Return empty guidance text (rejected: poor UX and ambiguous failure semantics).

## Decision 6: Keep templates in a dedicated matrix keyed by archetype × difficulty

- **Decision**: Store headline/strategy/priority-action scaffolds in `templates/guidance_templates.py`, then inject niche/metro stats and optional AI-resilience notes.
- **Rationale**: Maintains clear mapping between structured classes and human guidance while enabling test coverage by key combination.
- **Alternatives considered**:
  - Inline template literals in generator code (rejected: brittle and hard to audit).
  - External JSON/YAML templates in v1 (rejected: added loading complexity without near-term benefit).

## Decision 7: Contract-first output bundle for downstream M9 usage

- **Decision**: Define a `ClassificationGuidanceBundle` contract with strict enums and required fields for each metro.
- **Rationale**: M9/reporting integration depends on stable output keys and deterministic enum values.
- **Alternatives considered**:
  - Ad hoc dict responses (rejected: weaker type safety and drift risk).
  - Splitting outputs across independent returns (rejected: harder orchestration and validation).
