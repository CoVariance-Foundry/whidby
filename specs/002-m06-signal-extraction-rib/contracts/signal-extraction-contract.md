# Contract: M6 Signal Extraction Interface

## Purpose

Define the interface between M5 data collection outputs and M7 scoring inputs for signal extraction.

## Input Contract

### `extract_signals(raw_metro_bundle, keyword_expansion, cross_metro_domain_stats=None)`

#### Required Inputs

- `raw_metro_bundle`:
  - one metro's M5 category payloads
  - expected categories include SERP data, keyword volume/CPC data, backlinks, business listings, reviews, GBP details, lighthouse metrics
- `keyword_expansion`:
  - list of expanded keywords with metadata used by M6 (`intent`, `tier`, and mapping needed for transactional ratio / fulfillment context)

#### Optional Inputs

- `cross_metro_domain_stats`:
  - domain frequency map used for national/directory classification (>=30% metro appearance heuristic)

#### Validation Requirements

- fail fast on missing top-level required payloads
- tolerate missing nested sections with explicit default behavior
- normalize domain and SERP structures before category extraction

## Output Contract

Returns `MetroSignals` with this shape and required keys:

```text
{
  "demand": {
    "total_search_volume": <number>,
    "effective_search_volume": <number>,
    "head_term_volume": <number>,
    "volume_breadth": <number 0..1>,
    "avg_cpc": <number>,
    "max_cpc": <number>,
    "cpc_volume_product": <number>,
    "transactional_ratio": <number 0..1>
  },
  "organic_competition": {
    "avg_top5_da": <number>,
    "min_top5_da": <number>,
    "da_spread": <number>,
    "aggregator_count": <number>,
    "local_biz_count": <number>,
    "avg_lighthouse_performance": <number>,
    "schema_adoption_rate": <number 0..1>,
    "title_keyword_match_rate": <number 0..1>
  },
  "local_competition": {
    "local_pack_present": <bool>,
    "local_pack_position": <number>,
    "local_pack_review_count_avg": <number>,
    "local_pack_review_count_max": <number>,
    "local_pack_rating_avg": <number>,
    "review_velocity_avg": <number>,
    "gbp_completeness_avg": <number 0..1>,
    "gbp_photo_count_avg": <number>,
    "gbp_posting_activity": <number 0..1>,
    "citation_consistency": <number 0..1>
  },
  "ai_resilience": {
    "aio_trigger_rate": <number 0..1>,
    "featured_snippet_rate": <number 0..1>,
    "transactional_keyword_ratio": <number 0..1>,
    "local_fulfillment_required": <0|1>,
    "paa_density": <number>
  },
  "monetization": {
    "avg_cpc": <number>,
    "business_density": <number>,
    "gbp_completeness_avg": <number 0..1>,
    "lsa_present": <bool>,
    "aggregator_presence": <number>,
    "ads_present": <bool>
  }
}
```

## Behavioral Guarantees

- all five categories are always returned
- all required signal keys are always present (safe defaults when source data missing)
- effective volume follows Algo §6.1 formula using shared constants
- aggregator/national classification is deterministic from known sets + optional domain-frequency input
- shared quantities (`avg_cpc`, `gbp_completeness_avg`, aggregator-derived counts) are internally consistent across categories

## Error Handling Contract

- malformed top-level input raises structured validation errors
- sparse/missing nested source data does not fail extraction; defaults are emitted
- no outbound API/network behavior occurs inside M6
