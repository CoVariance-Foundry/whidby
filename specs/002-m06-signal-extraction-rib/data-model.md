# Data Model: M6 Signal Extraction

## Overview

M6 transforms one metro's M5 raw collection payload plus M4 keyword metadata into a normalized `MetroSignals` object consumed by M7 scoring.

## Entities

### 1) SignalExtractionInput

- **Description**: Aggregated input envelope for one metro extraction execution.
- **Fields**:
  - `metro_id`: unique metro/cbsa identifier
  - `raw_metro_bundle`: M5 category payloads for this metro (SERP, volume, backlinks, reviews, GBP, listings, lighthouse)
  - `keyword_expansion`: M4 keyword descriptors with intent/tier metadata
  - `cross_metro_domain_stats` (optional): domain-to-metro-frequency map for national classification
- **Validation Rules**:
  - `metro_id` is required and non-empty
  - `raw_metro_bundle` and `keyword_expansion` are required
  - keyword entries must include intent and volume context needed for demand derivation

### 2) KeywordSignalInput

- **Description**: Per-keyword normalized record used for demand and AI resilience derivation.
- **Fields**:
  - `keyword`: string
  - `intent`: enum-like string (`transactional`, `commercial`, `informational`, or fallback)
  - `tier`: keyword tier label
  - `monthly_volume`: numeric search volume
  - `cpc`: numeric CPC value
  - `aio_detected_in_serp`: boolean
- **Validation Rules**:
  - `keyword` non-empty
  - numeric fields are non-negative
  - missing `aio_detected_in_serp` defaults to false

### 3) ParsedSerpFeatures

- **Description**: Canonical SERP feature projection consumed by multiple extractors.
- **Fields**:
  - `has_aio`: boolean
  - `has_featured_snippet`: boolean
  - `paa_count`: integer
  - `has_local_pack`: boolean
  - `local_pack_position`: integer or null
  - `has_ads`: boolean
  - `has_lsa`: boolean
  - `organic_domains`: ordered list of domains for top results
- **Validation Rules**:
  - booleans always present
  - counts default to 0 when absent
  - missing domains yield empty list

### 4) DomainClassification

- **Description**: Domain role assignment used in organic and monetization signals.
- **Fields**:
  - `domain`: normalized host/domain
  - `is_aggregator`: boolean
  - `is_national`: boolean
  - `is_local_business`: boolean
- **Validation Rules**:
  - classification is deterministic from known sets plus frequency heuristic
  - exactly one of `is_local_business` vs (`is_aggregator` or `is_national`) is true for counted domains

### 5) LocalPackBusiness

- **Description**: Local-pack business facts used by local-competition extractors.
- **Fields**:
  - `business_id` or canonical listing key
  - `rating`
  - `review_count`
  - `review_timestamps`
  - `gbp_profile` (phone/hours/website/photos/description/services/attributes, photos count, posting recency)
- **Validation Rules**:
  - review and rating fields default safely when absent
  - timestamp list may be empty

### 6) MetroSignals

- **Description**: Final M6 output schema for one metro.
- **Fields**:
  - `demand` (8 signals)
  - `organic_competition` (8 signals)
  - `local_competition` (10 signals)
  - `ai_resilience` (5 signals)
  - `monetization` (6 signals)
- **Validation Rules**:
  - all category objects must exist
  - all required keys must exist, even for sparse/missing raw data
  - value ranges follow Algo §6 scales

## Relationships

- `SignalExtractionInput` 1:N `KeywordSignalInput`
- `SignalExtractionInput` 1:N `ParsedSerpFeatures`
- `ParsedSerpFeatures` 1:N `DomainClassification`
- `LocalPackBusiness` contributes to `local_competition` and `monetization` shared fields
- All derived entities roll up into one `MetroSignals`

## State Transitions

### Extraction lifecycle

`received -> parsed -> extracted -> normalized -> emitted`

- `received -> parsed`: raw payloads converted into canonical keyword/SERP/domain/local-pack views
- `parsed -> extracted`: category extractors compute signal values
- `extracted -> normalized`: defaults and scale guards applied
- `normalized -> emitted`: complete `MetroSignals` contract returned
