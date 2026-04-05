# Data Model: M8 Classification + Guidance

## Overview

M8 consumes one metro's M6 signals plus M7 scores and emits a stable classification and guidance bundle for downstream reporting and UI surfaces.

## Entities

### 1) ClassificationInput

- **Description**: Full input envelope for one metro classification operation.
- **Fields**:
  - `niche`: normalized niche keyword/label
  - `metro_name`: metro display name
  - `signals`: M6 signal object (especially organic/local competition and AI resilience fields)
  - `scores`: M7 score object (organic competition, local competition, opportunity/context values)
  - `strategy_profile`: one of `organic_first | balanced | local_dominant | auto`
- **Validation Rules**:
  - `signals` and `scores` are required
  - required fields for classification formulas must exist and be numeric
  - `strategy_profile` defaults to `balanced` when omitted

### 2) SerpArchetypeClassification

- **Description**: Single archetype label derived from ordered SERP pattern rules.
- **Fields**:
  - `serp_archetype`: enum in
    - `AGGREGATOR_DOMINATED`
    - `LOCAL_PACK_FORTIFIED`
    - `LOCAL_PACK_ESTABLISHED`
    - `LOCAL_PACK_VULNERABLE`
    - `FRAGMENTED_WEAK`
    - `FRAGMENTED_COMPETITIVE`
    - `BARREN`
    - `MIXED`
  - `rule_id`: identifier for matched rule path (for traceability/debug)
- **Validation Rules**:
  - exactly one archetype must be emitted
  - fallback rule must always resolve to `MIXED` if no earlier rule matches

### 3) AIExposureClassification

- **Description**: AI disruption vulnerability class from `aio_trigger_rate`.
- **Fields**:
  - `ai_exposure`: enum in `AI_SHIELDED | AI_MINIMAL | AI_MODERATE | AI_EXPOSED`
  - `aio_trigger_rate`: normalized decimal in [0, 1]
- **Validation Rules**:
  - exactly one exposure enum must be emitted
  - boundary thresholds are inclusive/exclusive per Algo §8.2

### 4) DifficultyTierClassification

- **Description**: Execution effort bucket using weighted competition blend.
- **Fields**:
  - `difficulty_tier`: enum in `EASY | MODERATE | HARD | VERY_HARD`
  - `combined_competition`: weighted score used for tier assignment
  - `resolved_weights`: resolved organic/local weight pair from strategy profile
- **Validation Rules**:
  - exactly one tier must be emitted
  - tier thresholds follow Algo §8.3 mapping and preserve deterministic output

### 5) GuidanceTemplateContext

- **Description**: Structured variables provided to template + LLM guidance generation.
- **Fields**:
  - `niche`
  - `metro_name`
  - `serp_archetype`
  - `ai_exposure`
  - `difficulty_tier`
  - `supporting_metrics` (review counts, aggregator count, AIO rate, etc.)
- **Validation Rules**:
  - required context keys must exist before generation
  - optional metrics may be omitted but should default to safe textual placeholders

### 6) GuidanceBundle

- **Description**: User-facing guidance payload aligned with classifications.
- **Fields**:
  - `headline`
  - `strategy`
  - `priority_actions` (ordered list)
  - `ai_resilience_note` (optional)
  - `guidance_status` (`generated | fallback_template`)
- **Validation Rules**:
  - text must remain consistent with archetype/exposure/tier inputs
  - fallback mode must be explicit when LLM call fails/times out

### 7) ClassificationGuidanceBundle (Output)

- **Description**: Final M8 output for one metro.
- **Fields**:
  - `serp_archetype`
  - `ai_exposure`
  - `difficulty_tier`
  - `guidance` (`GuidanceBundle`)
  - `metadata` (optional diagnostics such as matched rule ids and fallback reason)
- **Validation Rules**:
  - all enum fields are required and valid
  - guidance object is always present, even in degraded mode

## Relationships

- `ClassificationInput` 1:1 `SerpArchetypeClassification`
- `ClassificationInput` 1:1 `AIExposureClassification`
- `ClassificationInput` 1:1 `DifficultyTierClassification`
- `ClassificationInput` + classifications 1:1 `GuidanceTemplateContext`
- `GuidanceTemplateContext` 1:1 `GuidanceBundle`
- all derived entities compose into one `ClassificationGuidanceBundle`

## State Transitions

### Classification lifecycle

`received -> classified -> contextualized -> guided -> emitted`

- `received -> classified`: derive archetype, exposure, and tier deterministically
- `classified -> contextualized`: assemble template inputs and render base guidance structure
- `contextualized -> guided`: call LLM for constrained refinement, or apply fallback
- `guided -> emitted`: return complete bundle with explicit guidance status
