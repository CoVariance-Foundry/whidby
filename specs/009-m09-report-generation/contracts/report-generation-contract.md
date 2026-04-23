# Contract: M9 Report Generation + Feedback Logging

## Purpose

Define the M9 input/output and persistence contract used by downstream consumers and tests.

## 1) Module Interface Contract

### 1.1 Report Generation Interface

- **Function**: `generate_report(run_input) -> report_document`
- **Input requirements**:
  - `run_input` includes consolidated outputs from M4-M8
  - each metro includes `scores.opportunity` and M8 classification fields
  - run metadata includes `total_api_calls`, `total_cost_usd`, and processing time
  - all required paths validated; missing/null fields raise `ReportValidationError` with dotted path
  - all numeric coercions (`meta` fields, `scores.opportunity`) raise `ReportValidationError` on invalid types
- **Output guarantees**:
  - object includes `report_id`, `generated_at`, `spec_version`, `input`, `keyword_expansion`, `metros`, `meta`
  - `meta.feedback_log_id` is always set (UUID generated during report construction)
  - `metros` sorted by `scores.opportunity` descending
  - deterministic tie-break order using stable secondary keys (`cbsa_code`, `cbsa_name`)
  - no recomputation of M7 scores or M8 classifications

### 1.2 Feedback Logging Interface

- **Function**: `log_feedback(report_document, persistence_client) -> feedback_result`
- **Input requirements**:
  - valid `report_document` from M9 generation — full report contract enforced (not just `report_id/generated_at/metros`)
  - all required report-document paths validated including `meta.feedback_log_id`
  - each metro validated against the full metro entry contract; arbitrary dicts with partial fields are rejected
  - persistence client configured for M2/Supabase target table and must expose `insert_feedback(row)`
- **Output guarantees**:
  - one feedback row attempted per ranked metro
  - each feedback row context includes `feedback_log_id` from the report meta
  - returns IDs/status metadata for persisted rows (or structured failure)
  - null outcomes remain null at initial write

## 2) Report JSON Shape (Required Fields)

```json
{
  "report_id": "uuid",
  "generated_at": "ISO-8601",
  "spec_version": "1.1",
  "input": {},
  "keyword_expansion": {},
  "metros": [
    {
      "cbsa_code": "string",
      "cbsa_name": "string",
      "population": 0,
      "scores": {
        "demand": 0,
        "organic_competition": 0,
        "local_competition": 0,
        "monetization": 0,
        "ai_resilience": 0,
        "opportunity": 0
      },
      "confidence": {},
      "serp_archetype": "enum",
      "ai_exposure": "enum",
      "difficulty_tier": "enum",
      "signals": {},
      "guidance": {}
    }
  ],
  "meta": {
    "total_api_calls": 0,
    "total_cost_usd": 0.0,
    "processing_time_seconds": 0.0,
    "feedback_log_id": "uuid or reference"
  }
}
```

## 3) Feedback Log Shape (Per Metro)

```json
{
  "log_id": "uuid",
  "timestamp": "ISO-8601",
  "context": {},
  "signals": {},
  "scores": {},
  "classification": {},
  "recommendation_rank": 1,
  "outcome": {
    "user_acted": null,
    "site_built": null,
    "ranking_achieved_days": null,
    "local_pack_entered_days": null,
    "first_lead_days": null,
    "monthly_lead_volume": null,
    "monthly_revenue": null,
    "user_satisfaction_rating": null,
    "outcome_reported_at": null
  }
}
```

## 4) Error Handling Contract

- All validation failures (missing fields, null values, invalid numeric types) raise `ReportValidationError` with a dotted path pointer to the offending field.
- Metro-level validation errors include the metro index in the message (e.g. `metros[0] missing required field: scores.demand`).
- If report validation fails, `generate_report` raises `ReportValidationError` and does not call logging.
- `log_feedback` validates the full report-document contract before persisting; arbitrary/partial dicts raise `ReportValidationError`.
- If feedback persistence fails after report generation, the report object remains valid and unchanged; failure is surfaced via explicit error/status for retry policy handling.

## 5) Knowledge Base Lineage

After a report is persisted to the `reports` table, the scoring handler additionally:

- Resolves a canonical key via `src/pipeline/canonical_key.py` (deterministic `niche_normalized + geo_normalized + geo_scope`).
- Upserts a `kb_entities` row (one per unique niche+geo pair).
- Creates a `kb_snapshots` row (versioned, with `is_current=true`; prior snapshot is superseded atomically).
- Stores evidence artifacts in `kb_evidence_artifacts` (score bundles and keyword expansion payloads).
- Links the report row back to the KB via `entity_id` and `snapshot_id` columns (migration 008).
- Writes feedback events to `feedback_events` via the existing `log_feedback` function (now wired at runtime).

Persistent DataForSEO response caching (`api_response_cache` table) is used by the shared app-lifetime `DataForSEOClient` to avoid redundant API spend across scoring runs.

Reports use soft-archive (`archived_at` timestamp) instead of hard-delete to preserve KB lineage integrity.

## 6) Verification Obligations

- Contract tests must verify:
  - required top-level and nested fields in report output including `meta.feedback_log_id`
  - deterministic ordering for tie and non-tie score cases
  - null-safe feedback outcome persistence
  - persistence failure behavior does not mutate generated report content
  - metro-level missing/invalid fields raise `ReportValidationError` with indexed path
  - invalid meta numeric types raise `ReportValidationError` with path
  - arbitrary/minimal dicts are rejected by `log_feedback` (full contract enforcement)
  - feedback row context includes `feedback_log_id` from report meta
  - canonical key determinism (same niche+geo → same entity, same input_hash)
  - snapshot supersedence transitions (new snapshot marks old as `is_current=false`)
  - persistent cache TTL behavior (expired entries are not returned)
  - feedback events are written to `feedback_events` table after successful report persistence

