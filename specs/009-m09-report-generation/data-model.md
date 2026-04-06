# Data Model: M9 Report Generation + Feedback Logging

## Overview

M9 consumes completed pipeline outputs (M4-M8) and emits two durable artifacts:
1) a final report document matching Algo Spec v1.1 section 10, and
2) feedback log records matching section 9 for future calibration.

## Entities

### 1) PipelineRunInput

- **Description**: Full upstream envelope available at M9 entry.
- **Fields**:
  - `run_id` (uuid/string)
  - `generated_at` (ISO-8601 timestamp)
  - `input` (niche/geography/strategy metadata)
  - `keyword_expansion` (M4 summary and lists)
  - `metros` (array of metro-level bundles containing signals, scores, and classification/guidance from M5-M8)
  - `meta` (api calls, cost, processing time)
- **Validation Rules**:
  - `metros` must be present (may be empty only if explicitly allowed by policy)
  - each metro must include `scores.opportunity`
  - upstream score/classification fields are read-only in M9

### 2) RankedMetroEntry

- **Description**: One metro row in the final ordered report.
- **Fields**:
  - `cbsa_code`, `cbsa_name`, `population`
  - `scores` (`demand`, `organic_competition`, `local_competition`, `monetization`, `ai_resilience`, `opportunity`)
  - `confidence`
  - `serp_archetype`, `ai_exposure`, `difficulty_tier`
  - `signals`
  - `guidance`
- **Validation Rules**:
  - required score keys must exist
  - enums must match M8 contract values
  - tie-break ordering keys (`cbsa_code`, `cbsa_name`) must be available for deterministic sorting

### 3) ReportDocument

- **Description**: Final exportable JSON document for one run.
- **Fields**:
  - `report_id` (uuid)
  - `generated_at` (ISO-8601)
  - `spec_version` (string, expected `1.1` for current contract)
  - `input`
  - `keyword_expansion`
  - `metros` (ordered `RankedMetroEntry[]`)
  - `meta` (`total_api_calls`, `total_cost_usd`, `processing_time_seconds`, `feedback_log_id` or aggregate reference)
- **Validation Rules**:
  - must conform to Algo Spec section 10.1 field presence and shape
  - `metros` sorted by opportunity descending, deterministic on ties
  - `meta` totals must match fixture expectations exactly in unit tests

### 4) FeedbackLogRecord

- **Description**: Persisted recommendation tuple for one metro recommendation.
- **Fields**:
  - `log_id` (uuid), `timestamp`
  - `context` (niche, metro ids/names, population, keyword_count, confidence/profile fields)
  - `signals` (selected M6 signal snapshot)
  - `scores` (M7 values plus confidence)
  - `classification` (M8 labels)
  - `recommendation_rank` (1-based rank in ordered output)
  - `outcome` (nullable outcome attributes)
- **Validation Rules**:
  - one row per ranked metro
  - required context/signals/scores/classification fields are non-null
  - nullable outcome fields stay nullable and are not defaulted incorrectly

### 5) FeedbackOutcome

- **Description**: Nullable delayed-outcome payload embedded in feedback log.
- **Fields**:
  - `user_acted`, `site_built`
  - `ranking_achieved_days`, `local_pack_entered_days`, `first_lead_days`
  - `monthly_lead_volume`, `monthly_revenue`
  - `user_satisfaction_rating`
  - `outcome_reported_at`
- **Validation Rules**:
  - all fields may be null at initial write
  - when provided later, values must respect domain bounds (to be enforced in persistence schema/app validators)

## Relationships

- `PipelineRunInput` 1:1 `ReportDocument`
- `ReportDocument` 1:N `RankedMetroEntry`
- `RankedMetroEntry` 1:1 `FeedbackLogRecord`
- `FeedbackLogRecord` 1:1 `FeedbackOutcome`

## State Transitions

`received -> validated -> assembled -> ranked -> report_emitted -> feedback_persisted`

- `received -> validated`: ensure required fields from M4-M8 exist
- `validated -> assembled`: map upstream structures into report schema
- `assembled -> ranked`: deterministic ordering by opportunity with tie-breaks
- `ranked -> report_emitted`: emit/return final report document
- `report_emitted -> feedback_persisted`: persist per-metro feedback tuples without mutating emitted report

