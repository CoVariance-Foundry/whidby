# M07 Data Model

## MetroSignals (input)

Per-metro extracted signal payload consumed by M7. Keys are grouped by score domain:

- Demand: `effective_search_volume`, `avg_cpc`, `volume_breadth`, `transactional_ratio`
- Organic competition: `avg_top5_da`, `local_biz_count`, `avg_lighthouse_performance`, `schema_adoption_rate`, `title_keyword_match_rate`, `aggregator_count`
- Local competition: `local_pack_present`, `local_pack_position`, `local_pack_review_count_avg`, `review_velocity_avg`, `gbp_completeness_avg`, `gbp_photo_count_avg`, `gbp_posting_activity`
- Monetization: `avg_cpc`, `business_density`, `lsa_present`, `ads_top_present` (canonical; `ads_present` accepted for backward compatibility), `aggregator_presence`, `gbp_completeness_avg`
- AI resilience: `aio_trigger_rate`, `transactional_keyword_ratio`, `local_fulfillment_required`, `paa_density`, `niche_type`
- Confidence inputs: `expansion_confidence`, `lighthouse_results_count`, `backlink_results_count`, `serp_results_count`, `review_results_count`, `gbp_results_count`, `total_search_volume`

## MetroScores (output)

```json
{
  "demand": 0.0,
  "organic_competition": 0.0,
  "local_competition": 0.0,
  "monetization": 0.0,
  "ai_resilience": 0.0,
  "opportunity": 0.0,
  "confidence": {
    "score": 0.0,
    "flags": [{"code": "flag_name", "penalty": -10}]
  },
  "resolved_weights": {
    "organic": 0.15,
    "local": 0.20
  }
}
```

## Strategy Profile

- Input profile names: `organic_first`, `balanced`, `local_dominant`, `auto`
- Output `resolved_weights` always includes `organic` and `local`
- Constraints:
  - `organic >= 0`
  - `local >= 0`
  - `organic + local == 0.35`
- `auto` resolution branches:
  - `signals` is `None` -> balanced fallback
  - No local pack -> organic_first behavior (0.25 / 0.10)
  - Pack present, `local_pack_position <= 3` -> above-fold (0.08 / 0.27)
  - Pack present, position > 3 or missing -> balanced fallback
