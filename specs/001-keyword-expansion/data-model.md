# Data Model: M04 Keyword Expansion

## Entity: NicheInput

- **Description**: Seed input used to generate the keyword universe for one pipeline run.
- **Fields**:
  - `niche` (string, required): Human-provided niche term.
- **Validation Rules**:
  - MUST be non-empty after trimming.
  - SHOULD contain at least one alphabetic character.
  - Leading/trailing whitespace MUST be removed before processing.

## Entity: ExpandedKeyword

- **Description**: Canonical keyword record produced by M4 and consumed by downstream modules.
- **Fields**:
  - `keyword` (string, required): Normalized keyword text.
  - `tier` (integer, required): Keyword tier (`1`, `2`, or `3`).
  - `intent` (string, required): Intent label (`transactional`, `commercial`, `informational`).
  - `source` (string, required): Discovery origin (`input`, `llm`, `dataforseo_suggestions`, `merged`).
  - `aio_risk` (string, required): Expected AIO exposure (`low`, `moderate`, `high`).
  - `actionable` (boolean, required): Whether keyword qualifies for primary opportunity analysis.
- **Validation Rules**:
  - `keyword` MUST be unique within one result after normalization.
  - `tier` MUST be in allowed set `{1,2,3}`.
  - `intent` MUST be in allowed set.
  - `actionable` MUST be `false` for informational keywords.
  - `aio_risk` MUST be present for every keyword.

## Entity: ExpansionQualityMetrics

- **Description**: Aggregate counters and quality signals for one expansion run.
- **Fields**:
  - `total_keywords` (integer, required): Count of all returned keywords.
  - `actionable_keywords` (integer, required): Count of keywords with `actionable=true`.
  - `informational_keywords_excluded` (integer, required): Count excluded from primary SERP-oriented analysis.
  - `expansion_confidence` (string, required): `high`, `medium`, or `low`.
- **Validation Rules**:
  - `total_keywords` MUST equal length of `expanded_keywords`.
  - `actionable_keywords + informational_keywords_excluded` MUST be less than or equal to `total_keywords`.
  - `expansion_confidence` MUST be from allowed enum.

## Entity: KeywordExpansion

- **Description**: Top-level M4 output contract passed to M5/M6.
- **Fields**:
  - `niche` (string, required)
  - `expanded_keywords` (array of `ExpandedKeyword`, required)
  - `total_keywords` (integer, required)
  - `actionable_keywords` (integer, required)
  - `informational_keywords_excluded` (integer, required)
  - `expansion_confidence` (string, required)
- **Relationships**:
  - One `KeywordExpansion` contains many `ExpandedKeyword`.
  - One `KeywordExpansion` contains one `ExpansionQualityMetrics` tuple represented as top-level counters.

## Derived State Rules

- **Actionability state**:
  - informational -> non-actionable
  - transactional/commercial -> actionable
- **Confidence state**:
  - derived from overlap quality and source availability
  - low confidence does not block output generation

## State Transitions

1. `NicheInput received`
2. `Candidate keywords generated`
3. `Candidates normalized and deduplicated`
4. `Intent/tier/aio labels assigned`
5. `Actionability and metrics computed`
6. `KeywordExpansion emitted`
