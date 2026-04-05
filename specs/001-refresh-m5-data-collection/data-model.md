# Data Model: M5 Data Collection Refresh

## Overview

M5 ingests expanded keywords and metros, creates a deterministic execution plan, and returns normalized per-metro raw collections with run metadata.

## Entities

### 1) CollectionRequest

- **Description**: Input payload for one data-collection run.
- **Fields**:
  - `keywords`: Expanded keyword set with tier and intent metadata
  - `metros`: Metro records with unique metro identifiers and location context
  - `strategy_profile`: Strategy selector for run context
- **Validation Rules**:
  - `keywords` must be non-empty
  - `metros` must be non-empty
  - each metro identifier must be unique in the request

### 2) KeywordDescriptor

- **Description**: Keyword plus classification metadata used by planner.
- **Fields**:
  - `keyword`: normalized query text
  - `tier`: keyword tier classification
  - `intent`: intent classification
  - `is_serp_eligible`: computed planner flag
- **Validation Rules**:
  - `keyword` must be non-empty
  - `tier` and `intent` must be present

### 3) CollectionTask

- **Description**: Planned execution unit for one external data pull.
- **Fields**:
  - `task_id`: stable unique identifier for the run
  - `metro_id`: owning metro
  - `task_type`: category (volume, serp, maps, backlinks, lighthouse, gbp_info, reviews, listings)
  - `payload`: endpoint request payload
  - `depends_on`: list of prerequisite task identifiers
  - `dedup_key`: optional key for deduplication
- **Validation Rules**:
  - `task_type` must map to a supported collection category
  - dependency references must point to valid existing tasks
  - tasks in execution groups must be acyclic

### 4) MetroCollectionResult

- **Description**: Raw per-metro output container for downstream extraction.
- **Fields**:
  - `metro_id`
  - `serp_organic`
  - `serp_maps`
  - `keyword_volume`
  - `business_listings`
  - `google_reviews`
  - `gbp_info`
  - `backlinks`
  - `lighthouse`
- **Validation Rules**:
  - all required category keys must exist, even when empty
  - category collections must contain only data from the owning `metro_id`

### 5) FailureRecord

- **Description**: Structured failure event for retry and diagnostics.
- **Fields**:
  - `task_id`
  - `task_type`
  - `metro_id`
  - `message`
  - `is_retryable`
- **Validation Rules**:
  - must include enough scope to replay only failed segment(s)

### 6) RunMetadata

- **Description**: Aggregated operational metrics for the run.
- **Fields**:
  - `total_api_calls`
  - `total_cost_usd`
  - `collection_time_seconds`
  - `errors`: list of `FailureRecord`
- **Validation Rules**:
  - numeric metrics are non-negative
  - `total_cost_usd` reconciles with per-call cost records

### 7) RawCollectionResult

- **Description**: Top-level M5 output contract consumed by M6.
- **Fields**:
  - `metros`: map of `metro_id -> MetroCollectionResult`
  - `meta`: `RunMetadata`
- **Validation Rules**:
  - every requested metro id appears in output map
  - no metro output is omitted due to failures in unrelated metros

## Relationships

- `CollectionRequest` 1:N `CollectionTask`
- `CollectionTask` N:1 `MetroCollectionResult` (except globally deduplicated tasks that fan out to multiple metros)
- `MetroCollectionResult` N:1 `RawCollectionResult`
- `FailureRecord` N:1 `RunMetadata`

## State Transitions

### CollectionTask lifecycle

`planned -> running -> succeeded | failed`

- `planned -> running`: executor dispatches task when dependencies are satisfied
- `running -> succeeded`: valid response returned and normalized
- `running -> failed`: request error, timeout, or invalid response

### Run lifecycle

`initialized -> planning_complete -> phase1_complete -> phase2_complete -> assembled`

