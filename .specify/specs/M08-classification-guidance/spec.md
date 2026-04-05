# Feature Specification: M8 Classification + Guidance

**Feature Branch**: `008-m08-classification-guidance`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: Module M8 — SERP archetype, AI exposure, difficulty tier, and practitioner guidance (Algo Spec V1.1, §8 Phase 5)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - SERP archetype and AI exposure labels (Priority: P1)

As a Widby operator, I need each metro classified into a SERP archetype (one of eight types) and an AI exposure level (one of four levels) so I can understand the search landscape and AI disruption risk at a glance.

**Why this priority**: Classifications are the primary mental model for prioritizing niches and metros.

**Independent Test**: Given M6 signals and M7 scores for a metro, classification emits exactly one archetype and one exposure level per spec rules, including boundary cases (e.g. aggregator-dominated, local-pack vulnerable, barren SERPs).

**Acceptance Scenarios**:

1. **Given** signals characteristic of an aggregator-dominated SERP, **When** archetype classification runs, **Then** the archetype matches the spec’s decision rules for that pattern.
2. **Given** signals indicating local pack vulnerability, **When** archetype classification runs, **Then** the output archetype reflects local pack vulnerability per spec.
3. **Given** sparse or barren SERP patterns per spec, **When** classification runs, **Then** the archetype reflects barren / low-density behavior as defined.
4. **Given** shielded vs exposed AI contexts per spec, **When** AI exposure classification runs, **Then** the exposure level is one of the four defined levels and matches inputs (including “shielded” and “exposed” examples).

---

### User Story 2 - Difficulty tier for execution planning (Priority: P2)

As a Widby operator, I need a single difficulty tier (EASY / MODERATE / HARD / VERY_HARD) derived from signals and scores so I can sequence build and rent work realistically.

**Why this priority**: Tiers translate raw metrics into actionable effort expectations.

**Independent Test**: Controlled changes to competition or AI exposure move the tier in the direction predicted by the spec (e.g. harder competition → same or harder tier).

**Acceptance Scenarios**:

1. **Given** fixed M6/M7 outputs representing a “easy win” profile, **When** difficulty is computed, **Then** tier is EASY or MODERATE per spec thresholds (not HARD/VERY_HARD).
2. **Given** outputs representing high competitive and AI headwinds, **When** difficulty is computed, **Then** tier is HARD or VERY_HARD per spec thresholds.

---

### User Story 3 - Readable, niche-aware guidance (Priority: P3)

As a Widby operator, I need short, readable guidance text that references my niche and metro context so I know what to build, what to avoid, and how to interpret the classification.

**Why this priority**: Guidance closes the loop from metrics to action; LLM text must be grounded in structured outputs.

**Independent Test**: Guidance generation uses M3 LLM client with templates; outputs stay on-template, mention niche/metro where required, and do not contradict archetype/tier/exposure.

**Acceptance Scenarios**:

1. **Given** a classified metro and niche metadata, **When** guidance is generated, **Then** text is human-readable, grammatically coherent, and includes niche-specific language (not generic filler).
2. **Given** two different archetypes for the same niche name, **When** guidance is generated for each, **Then** the guidance differs in a way that reflects archetype (not a single static blurb).
3. **Given** LLM failure or timeout, **When** guidance is requested, **Then** behavior follows project rules for degradation (fallback copy or explicit “guidance unavailable” — exact behavior per plan/tasks, without silent wrong advice).

---

### Edge Cases

- Conflicting weak signals: classification rules define precedence; tests cover tie-break and default archetype/exposure behavior per spec.
- Missing optional LLM fields: structured classification still completes; guidance path fails safe per FR-003/implementation plan.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement SERP archetype classification across eight archetypes per `docs/algo_spec_v1_1.md` §8.
- **FR-002**: System MUST implement AI exposure classification across four levels per Algo Spec V1.1 §8, including shielded vs exposed outcomes.
- **FR-003**: System MUST assign exactly one difficulty tier in `EASY | MODERATE | HARD | VERY_HARD` from M6 signals and M7 scores per spec.
- **FR-004**: System MUST generate actionable guidance text using the M3 LLM client and template-driven prompts.
- **FR-005**: System MUST depend on M6 (signals) and M7 (scores) for classification inputs; MUST NOT recompute scores inside classification modules.
- **FR-006**: Module implementation MUST live in: `src/classification/serp_archetype.py`, `ai_exposure.py`, `difficulty_tier.py`, `guidance_generator.py`, and `templates/guidance_templates.py`.

### Key Entities

- **SERP archetype**: One of eight enumerated landscape types for a metro + niche query context.
- **AI exposure level**: One of four enumerated levels describing AI-driven disruption risk.
- **Difficulty tier**: One of four execution difficulty buckets.
- **Guidance bundle**: Template-structured content merged with LLM output for final user-facing text.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a golden set of labeled fixtures (aggregator-dominated, local-pack vulnerable, barren, shielded, exposed), archetype and exposure classifications match expected labels in ≥ the threshold defined in module tasks (100% on golden set unless spec explicitly allows ambiguity).
- **SC-002**: 100% of classified metros emit a valid difficulty tier enum value.
- **SC-003**: Sample guidance reviewed for readability: short paragraphs, no contradictory advice vs archetype/tier/exposure, and niche-specific phrasing in representative cases.
- **SC-004**: All evaluation cases in module tasks pass: archetype classification, AI exposure levels, difficulty tiers, readable guidance, and niche-specific guidance.

## Assumptions

- M3 LLM client is available with retry and observability consistent with foundation module docs.
- Template library starts small and grows; new archetypes/exposure rules are spec-driven before code changes.
- English-only guidance for v1 unless product specifies otherwise.

## Source specifications

| Document | Role |
|----------|------|
| `docs/algo_spec_v1_1.md` | §8 (Phase 5) — archetypes, exposure, difficulty, guidance rules |
| `docs/product_breakdown.md` | Module map, eval criteria, file layout for M8 |
| `docs/module_dependency.md` | M8 dependencies (M6, M7, M3) |
| `docs/data_flow.md` | Classification inputs/outputs in the pipeline |
