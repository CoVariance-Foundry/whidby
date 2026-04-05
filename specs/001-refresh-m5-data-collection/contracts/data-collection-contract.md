# Contract: M5 Data Collection Interface

## Purpose

Define the contract between upstream keyword/metro preparation (M4/M1) and downstream signal extraction (M6) for the M5 collection module.

## Input Contract

### `collect_data(request)`

`request` MUST include:

- `keywords`: list of keyword descriptors
  - required fields per keyword: `keyword`, `tier`, `intent`
- `metros`: list of metro descriptors
  - required fields per metro: `metro_id`, location context for endpoint targeting
- `strategy_profile`: strategy context string

Validation requirements:

- reject empty keyword sets
- reject empty metro sets
- reject duplicate metro identifiers in same request

## Output Contract

Returns `RawCollectionResult` with this shape:

```text
{
  "metros": {
    "<metro_id>": {
      "serp_organic": [...],
      "serp_maps": [...],
      "keyword_volume": [...],
      "business_listings": [...],
      "google_reviews": [...],
      "gbp_info": [...],
      "backlinks": [...],
      "lighthouse": [...]
    }
  },
  "meta": {
    "total_api_calls": <int>,
    "total_cost_usd": <float>,
    "collection_time_seconds": <float>,
    "errors": [
      {
        "task_id": "<string>",
        "task_type": "<string>",
        "metro_id": "<string>",
        "message": "<string>",
        "is_retryable": <bool>
      }
    ]
  }
}
```

Contract guarantees:

- every requested metro id is present in `metros`
- every metro includes all required category keys (explicit empty allowed)
- `meta` is always present even for partial-failure outcomes

## Behavioral Rules

- keyword volume is collected for all keywords
- deeper SERP pulls run only for SERP-eligible keywords
- dependent enrichment pulls must not run before prerequisites are available
- independent failures do not fail the whole run

## Error Contract

- errors are returned in `meta.errors` (not only logs)
- each error includes task and metro scope for targeted retries
- partial results remain available for successful tasks

