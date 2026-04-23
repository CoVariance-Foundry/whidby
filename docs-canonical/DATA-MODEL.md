# Data Model

> **Canonical document** — Design intent. This file describes the data structures and their relationships.
> Schema changes require this doc to be updated FIRST.


| Metadata         | Value       |
| ---------------- | ----------- |
| **Status**       | approved    |
| **Version**      | `1.0.0`     |
| **Last Updated** | 2026-04-05  |
| **Owner**        | @widby-team |


---

## Entities


| Entity              | Storage                              | Primary Key      | Description                                                        |
| ------------------- | ------------------------------------ | ---------------- | ------------------------------------------------------------------ |
| KeywordExpansion    | In-memory (M4 output)                | niche (string)   | Expanded keyword set with intent/tier/AIO labels                   |
| RawCollectionResult | In-memory (M5 output)                | niche + geo      | Raw API responses organized per metro                              |
| MetroSignals        | In-memory (M6 output)                | cbsa_code        | Derived demand/competition/AI/monetization signals                 |
| MetroScores         | In-memory (M7 output)                | cbsa_code        | Computed scores (0-100) per signal domain                          |
| MetroClassification | In-memory (M8 output)                | cbsa_code        | SERP archetype, AI exposure, difficulty tier, guidance             |
| Report              | Supabase `reports` table             | report_id (UUID) | Complete report with all metro results                             |
| FeedbackLog         | Supabase `feedback_log` table        | log_id (UUID)    | Input context + scores for future optimization (legacy)            |
| KBEntity            | Supabase `kb_entities` table         | entity_id (UUID) | Canonical niche+geo identity for knowledge base lineage            |
| KBSnapshot          | Supabase `kb_snapshots` table        | snapshot_id (UUID) | Versioned derived-state snapshot with supersedence chain         |
| KBEvidenceArtifact  | Supabase `kb_evidence_artifacts`     | artifact_id (UUID) | Raw M5 collection payloads linked to snapshots                  |
| ApiResponseCache    | Supabase `api_response_cache` table  | cache_id (UUID)  | Persistent cross-run DataForSEO response cache                     |
| FeedbackEvent       | Supabase `feedback_events` table     | event_id (UUID)  | Runtime feedback linked to snapshots, reports, and entities        |


### PlaceSuggestion (autocomplete output — in-memory)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `place_id` | string | Yes | Mapbox canonical place identifier |
| `city` | string | Yes | Display city name (from `name_preferred`) |
| `region` | string | No | State/province/admin1 name |
| `country` | string | Yes | Country display name |
| `country_iso_code` | string | Yes | ISO 3166-1 alpha-2 code |
| `full_name` | string | Yes | Full formatted address string |
| `latitude` | float | No | WGS84 latitude |
| `longitude` | float | No | WGS84 longitude |
| `dataforseo_location_code` | integer | No | Best-effort bridged DataForSEO location code (null when no confident match) |
| `dataforseo_match_confidence` | string | No | `high`, `medium`, `low`, or null |

Source: `src/research_agent/places.py::PlaceSuggestion`. Returned by `GET /api/places/suggest`.

### HistoryEntry (client localStorage)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `city` | string | Yes | Display city name |
| `service` | string | Yes | Niche service keyword |
| `at` | number | Yes | Unix epoch timestamp |
| `state` | string | No | Two-letter state code (US entries) |
| `place_id` | string | No | Canonical Mapbox place id for rerun targeting |
| `dataforseo_location_code` | number | No | Bridged DFS code for rerun targeting |

Source: `apps/app/src/lib/niche-finder/history-storage.ts`. Dedupe key prefers `place_id` when present.

## Schema Definitions

### KeywordExpansion (M4 Output)


| Field                             | Type    | Required | Constraints             | Description                       |
| --------------------------------- | ------- | -------- | ----------------------- | --------------------------------- |
| `niche`                           | string  | Yes      | non-empty               | Normalized seed niche term        |
| `expanded_keywords`               | array   | Yes      | —                       | List of ExpandedKeyword records   |
| `total_keywords`                  | integer | Yes      | >= 0                    | Count of all keywords             |
| `actionable_keywords`             | integer | Yes      | >= 0                    | Count with actionable=true        |
| `informational_keywords_excluded` | integer | Yes      | >= 0                    | Count of informational exclusions |
| `expansion_confidence`            | string  | Yes      | `high`, `medium`, `low` | Overlap-based confidence          |


### ExpandedKeyword (M4 Keyword Record)


| Field        | Type    | Required | Constraints                                        | Description                       |
| ------------ | ------- | -------- | -------------------------------------------------- | --------------------------------- |
| `keyword`    | string  | Yes      | non-empty, unique per result                       | Normalized keyword text           |
| `tier`       | integer | Yes      | 1, 2, or 3                                         | Head / Service / Long-tail        |
| `intent`     | string  | Yes      | `transactional`, `commercial`, `informational`     | Search intent                     |
| `source`     | string  | Yes      | `input`, `llm`, `dataforseo_suggestions`, `merged` | Discovery origin                  |
| `aio_risk`   | string  | Yes      | `low`, `moderate`, `high`                          | AI Overview exposure risk         |
| `actionable` | boolean | Yes      | —                                                  | True for transactional/commercial |


### MetroSignals (M6 Output)


| Field                             | Type    | Description                                       |
| --------------------------------- | ------- | ------------------------------------------------- |
| `demand.volume`                   | integer | Effective search volume (AIO-adjusted)            |
| `demand.cpc`                      | float   | Average CPC across actionable keywords            |
| `demand.breadth`                  | integer | Number of Tier 2 keywords with volume > threshold |
| `organic_competition.da`          | integer | Average DA of top-5 organic results               |
| `organic_competition.aggregators` | integer | Count of known aggregator domains in top-10       |
| `local_competition.reviews`       | object  | Review count avg/max, velocity                    |
| `local_competition.gbp`           | object  | GBP completeness, photo count, posting activity   |
| `ai_resilience.aio_rate`          | float   | AIO trigger rate across tested keywords           |
| `ai_resilience.intent_ratio`      | float   | Transactional keyword ratio                       |
| `monetization.cpc`                | float   | Average CPC                                       |
| `monetization.density`            | integer | Business density count                            |
| `monetization.lsa`                | boolean | Local Service Ads present                         |


### MetroScores (M7 Output)


| Field                 | Type    | Range | Description                 |
| --------------------- | ------- | ----- | --------------------------- |
| `demand`              | integer | 0-100 | Demand score                |
| `organic_competition` | integer | 0-100 | Organic competition score   |
| `local_competition`   | integer | 0-100 | Local competition score     |
| `monetization`        | integer | 0-100 | Monetization score          |
| `ai_resilience`       | integer | 0-100 | AI resilience score         |
| `opportunity`         | integer | 0-100 | Composite opportunity score |
| `confidence.score`    | integer | 0-100 | Confidence score            |
| `confidence.flags`    | array   | —     | Warning flags               |


### MetroClassification (M8 Output)


| Field             | Type   | Values                                                                | Description                                         |
| ----------------- | ------ | --------------------------------------------------------------------- | --------------------------------------------------- |
| `serp_archetype`  | string | `LOCAL_PACK_VULNERABLE`, `AGGREGATOR_DOMINATED`, `ORGANIC_OPEN`, etc. | SERP structure classification                       |
| `ai_exposure`     | string | `AI_SHIELDED`, `AI_MODERATE`, `AI_EXPOSED`                            | AI Overview exposure level                          |
| `difficulty_tier` | string | `EASY`, `MODERATE`, `HARD`, `VERY_HARD`                               | Ranking difficulty                                  |
| `guidance`        | object | —                                                                     | Headline, strategy, priority actions, time estimate |


## Data Flow: Scoring Pipeline (M4 → M9)

```
User Input                    M4: KeywordExpansion               M5: RawCollectionResult
─────────────                 ─────────────────────              ───────────────────
niche_keyword: "plumber"  →   {                                  {
geo_scope: "state"              expanded_keywords: [               metros: {
geo_target: "AZ"                  {keyword, tier, intent,            "38060": {
strategy_profile: "balanced"       source, aio_risk}                   serp_organic: [...]
                                ],                          →          keyword_volume: [...]
                                total_keywords: 15,                    business_listings: [...]
                                actionable_keywords: 12,               ...
                                expansion_confidence: "high"         }
                              }                                    },
                                                                   meta: {cost, calls, time}
                                                                 }
                                    │                              │
                                    ▼                              ▼
                              M6: MetroSignals               M7: MetroScores
                              {demand, organic_competition,  {demand: 72, organic: 65,
                               local_competition,             local: 58, monetization: 81,
                               ai_resilience,                 ai_resilience: 92,
                               monetization}                  opportunity: 71}
                                    │                              │
                                    ▼                              ▼
                              M8: MetroClassification        M9: Report
                              {serp_archetype,               {input, keyword_expansion,
                               ai_exposure,                   metros: [...],
                               difficulty_tier,               meta: {cost, time}}
                               guidance}                      → Supabase
```

## Data Flow: Experiment Pipeline (M10 → M15)

```
Experiment Config         → M10: BusinessList             → M11: ScannedBusiness
                            [{name, url, email, bucket}]    {scan_results, weakness_score}
                                │                              │
                                ▼                              ▼
                          M12: Audit                     M13: OutreachRecord
                          {audit_id, url, html,          {business_id, emails_sent,
                           variant_id, depth}             status}
                                │                              │
                                ▼                              ▼
                          M14: Events                    M15: ExperimentResults
                          [{type, business_id, ts}]      {variant_metrics, ab_comparison,
                          EngagementScore                 rentability_signal}
                                                              │
                                                              ▼
                                                         Supabase: rentability_signals
                                                         → M7 feedback loop
```

## Research Constants (Algo Spec §16)

```python
AIO_CTR_REDUCTION = 0.59
INTENT_AIO_RATES = {"transactional": 0.021, "commercial": 0.043, "informational": 0.436}
LOCAL_QUERY_AIO_RATE = 0.079
MEDIAN_LOCAL_SERVICE_CPC = 5.00
FIXED_WEIGHTS = {"demand": 0.25, "monetization": 0.20, "ai_resilience": 0.15}
```

## Migration Strategy


| Strategy            | Tool                 | Notes                                                   |
| ------------------- | -------------------- | ------------------------------------------------------- |
| SQL migrations      | Supabase CLI         | `supabase/migrations/` directory, RLS policies included |
| In-memory contracts | Pydantic / TypedDict | Validated at module boundaries, no ORM                  |


---

## Revision History


| Version | Date       | Author        | Changes                                                      |
| ------- | ---------- | ------------- | ------------------------------------------------------------ |
| 0.1.0   | 2026-04-05 | DocGuard Init | Initial template                                             |
| 1.0.0   | 2026-04-05 | Migration     | Populated from `docs/algo_spec_v1_1.md`, `docs/data_flow.md` |
| 1.1.0   | 2026-04-22 | Mapbox autocomplete | Added PlaceSuggestion and HistoryEntry schemas for global autocomplete + canonical place targeting |


