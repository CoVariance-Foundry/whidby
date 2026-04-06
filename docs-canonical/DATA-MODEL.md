# Data Model

> **Canonical document** — Design intent. This file describes the data structures and their relationships.
> Schema changes require this doc to be updated FIRST.


| Metadata         | Value       |
| ---------------- | ----------- |
| **Status**       | approved    |
| **Version**      | `1.1.0`     |
| **Last Updated** | 2026-04-06  |
| **Owner**        | @widby-team |


---

## Entities

### In-Memory Pipeline Contracts (M4–M8)

| Entity              | Storage               | Primary Key    | Code Location                        | Description                                        |
| ------------------- | --------------------- | -------------- | ------------------------------------ | -------------------------------------------------- |
| KeywordExpansion    | In-memory (M4 output) | niche (string) | `src/pipeline/keyword_expansion.py`  | Expanded keyword set with intent/tier/AIO labels   |
| RawCollectionResult | In-memory (M5 output) | niche + geo    | `src/pipeline/types.py`              | Raw API responses organized per metro              |
| MetroSignals        | In-memory (M6 output) | cbsa_code      | —                                    | Derived demand/competition/AI/monetization signals |
| MetroScores         | In-memory (M7 output) | cbsa_code      | —                                    | Computed scores (0-100) per signal domain          |
| MetroClassification | In-memory (M8 output) | cbsa_code      | —                                    | SERP archetype, AI exposure, difficulty tier       |

### Supabase: Scoring Pipeline (001_core_schema)

| Table              | Primary Key | Parent FK           | Description                                    |
| ------------------ | ----------- | ------------------- | ---------------------------------------------- |
| `reports`          | id (UUID)   | —                   | Complete report; JSONB snapshot + scalar fields |
| `report_keywords`  | id (UUID)   | `reports.id`        | Normalized M4 keywords per report              |
| `metro_signals`    | id (UUID)   | `reports.id`        | M6 signals per metro per report (JSONB cols)   |
| `metro_scores`     | id (UUID)   | `reports.id`        | M7 scores + M8 classification per metro        |
| `feedback_log`     | id (UUID)   | —                   | Input context + scores for bandit optimisation |

### Supabase: Experiment Framework (002_experiment_schema)

| Table                    | Primary Key | Parent FK                   | Description                                  |
| ------------------------ | ----------- | --------------------------- | -------------------------------------------- |
| `experiments`            | id (UUID)   | —                           | Top-level experiment (niche + metro scope)   |
| `experiment_variants`    | id (UUID)   | `experiments.id`            | A/B variant config (audit depth, template)   |
| `experiment_businesses`  | id (UUID)   | `experiments.id`            | Discovered businesses and scan results       |
| `outreach_events`        | id (UUID)   | `experiments.id`, `experiment_businesses.id` | Send/open/click/reply events  |
| `reply_classifications`  | id (UUID)   | `outreach_events.id`, `experiment_businesses.id` | LLM-classified reply sentiment |
| `rentability_signals`    | id (UUID)   | `experiments.id` (optional) | Aggregated rentability score per niche+metro |

### Supabase: Shared Infrastructure (003_shared_tables)

| Table                  | Primary Key     | Description                                  |
| ---------------------- | --------------- | -------------------------------------------- |
| `api_usage_log`        | id (UUID)       | DataForSEO call tracking (M0 cost tracking)  |
| `metro_location_cache` | cbsa_code (PK)  | Pre-computed metro → location code mapping   |
| `suppression_list`     | email (PK)      | Global outreach suppression (M13)            |

### Research Agent Storage (Filesystem)

| Store                | Format / Location                         | Description                                          |
| -------------------- | ----------------------------------------- | ---------------------------------------------------- |
| Research Graph       | JSON file (`RESEARCH_GRAPH_PATH` env var) | NetworkX-backed knowledge graph (nodes + edges)      |
| Run Artifacts        | `research_runs/{run_id}/`                 | Per-run directory tree (see layout below)             |


---

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


### reports (Supabase)

| Column              | Type        | Constraints                    | Description                                   |
| ------------------- | ----------- | ------------------------------ | --------------------------------------------- |
| `id`                | UUID        | PK, auto-generated             | Report identifier                             |
| `created_at`        | TIMESTAMPTZ | NOT NULL, default `now()`      | Creation timestamp                            |
| `spec_version`      | TEXT        | NOT NULL, default `'1.1'`      | Algo spec version used                        |
| `niche_keyword`     | TEXT        | NOT NULL                       | Seed niche                                    |
| `geo_scope`         | TEXT        | NOT NULL                       | `state`, `metro`, etc.                        |
| `geo_target`        | TEXT        | NOT NULL                       | Target geography code                         |
| `report_depth`      | TEXT        | NOT NULL, default `'standard'` | `standard` or `deep`                          |
| `strategy_profile`  | TEXT        | NOT NULL, default `'balanced'` | Scoring strategy                              |
| `resolved_weights`  | JSONB       | —                              | Final weight vector used for scoring          |
| `keyword_expansion` | JSONB       | —                              | Full M4 output snapshot (denormalized)        |
| `metros`            | JSONB       | —                              | Full per-metro results snapshot (denormalized) |
| `meta`              | JSONB       | —                              | Run metadata (cost, API calls, time)          |
| `feedback_log_id`   | UUID        | —                              | Link to `feedback_log` row                    |

> **Dual-storage invariant:** JSONB columns (`keyword_expansion`, `metros`, `meta`) are
> the **primary snapshot** and source of truth for V1. The normalized child tables
> (`report_keywords`, `metro_signals`, `metro_scores`) are written in the same
> transaction for query/aggregation convenience. If only one path can be written,
> write the JSONB columns on `reports` — that is the minimum-viable record.
> See [Dual Storage Rules](#dual-storage-rules) for the full policy.


### report_keywords (Supabase)

| Column          | Type    | Constraints                               | Description            |
| --------------- | ------- | ----------------------------------------- | ---------------------- |
| `id`            | UUID    | PK                                        | Row identifier         |
| `report_id`     | UUID    | FK → `reports.id`, ON DELETE CASCADE      | Parent report          |
| `keyword`       | TEXT    | NOT NULL                                  | Keyword text           |
| `tier`          | INT     | NOT NULL, CHECK (1, 2, 3)                 | Keyword tier           |
| `intent`        | TEXT    | NOT NULL, CHECK (trans/comm/info)         | Search intent          |
| `source`        | TEXT    | NOT NULL                                  | Discovery origin       |
| `aio_risk`      | TEXT    | NOT NULL, default `'low'`                 | AI Overview risk       |
| `search_volume` | INT     | —                                         | Volume (post-enrichment) |
| `cpc`           | NUMERIC | —                                         | CPC (post-enrichment)  |


### metro_signals (Supabase)

| Column                 | Type | Constraints                          | Description                 |
| ---------------------- | ---- | ------------------------------------ | --------------------------- |
| `id`                   | UUID | PK                                   | Row identifier              |
| `report_id`            | UUID | FK → `reports.id`, ON DELETE CASCADE | Parent report               |
| `cbsa_code`            | TEXT | NOT NULL                             | Metro CBSA code             |
| `cbsa_name`            | TEXT | NOT NULL                             | Metro display name          |
| `demand`               | JSONB | —                                   | Demand signal object        |
| `organic_competition`  | JSONB | —                                   | Organic competition signals |
| `local_competition`    | JSONB | —                                   | Local competition signals   |
| `ai_resilience`        | JSONB | —                                   | AI resilience signals       |
| `monetization`         | JSONB | —                                   | Monetization signals        |


### metro_scores (Supabase)

Combines M7 scores and M8 classification in a single row per metro per report.

| Column                       | Type  | Constraints                          | Description                    |
| ---------------------------- | ----- | ------------------------------------ | ------------------------------ |
| `id`                         | UUID  | PK                                   | Row identifier                 |
| `report_id`                  | UUID  | FK → `reports.id`, ON DELETE CASCADE | Parent report                  |
| `cbsa_code`                  | TEXT  | NOT NULL                             | Metro CBSA code                |
| `demand_score`               | INT   | —                                    | M7: Demand (0-100)             |
| `organic_competition_score`  | INT   | —                                    | M7: Organic competition (0-100)|
| `local_competition_score`    | INT   | —                                    | M7: Local competition (0-100)  |
| `monetization_score`         | INT   | —                                    | M7: Monetization (0-100)       |
| `ai_resilience_score`        | INT   | —                                    | M7: AI resilience (0-100)      |
| `opportunity_score`          | INT   | —                                    | M7: Composite (0-100)          |
| `confidence_score`           | INT   | —                                    | M7: Confidence (0-100)         |
| `confidence_flags`           | JSONB | —                                    | M7: Warning flags              |
| `serp_archetype`             | TEXT  | —                                    | M8: SERP structure class       |
| `ai_exposure`                | TEXT  | —                                    | M8: AI Overview exposure level |
| `difficulty_tier`            | TEXT  | —                                    | M8: Ranking difficulty         |
| `guidance`                   | JSONB | —                                    | M8: Strategy guidance object   |

> **Naming note:** SQL columns use `_score` suffixes (e.g. `demand_score`) while the
> in-memory MetroScores TypedDict uses bare names (`demand`). Both refer to
> the same 0-100 integer values.


### feedback_log (Supabase)

| Column               | Type        | Constraints               | Description                |
| -------------------- | ----------- | ------------------------- | -------------------------- |
| `id`                 | UUID        | PK                        | Row identifier             |
| `created_at`         | TIMESTAMPTZ | NOT NULL, default `now()` | Timestamp                  |
| `context`            | JSONB       | NOT NULL                  | Input context (see below)  |
| `signals`            | JSONB       | NOT NULL                  | Raw M6 signals snapshot    |
| `scores`             | JSONB       | NOT NULL                  | M7 scores snapshot         |
| `classification`     | JSONB       | NOT NULL                  | M8 classification snapshot |
| `recommendation_rank`| INT         | —                         | Rank in output list        |
| `outcome`            | JSONB       | —                         | Later-observed outcome     |

**Expected JSONB keys for `context`:**

| Key                | Type   | Description                  |
| ------------------ | ------ | ---------------------------- |
| `niche_keyword`    | string | Seed niche (indexed in SQL)  |
| `geo_scope`        | string | Geographic scope             |
| `geo_target`       | string | Target code                  |
| `strategy_profile` | string | Strategy used                |
| `cbsa_code`        | string | Metro evaluated              |
| `spec_version`     | string | Algo spec version            |


### Experiment Tables (Supabase)

#### experiments

| Column              | Type        | Constraints                                                                                  | Description             |
| ------------------- | ----------- | -------------------------------------------------------------------------------------------- | ----------------------- |
| `id`                | UUID        | PK                                                                                           | Experiment identifier   |
| `created_at`        | TIMESTAMPTZ | NOT NULL, default `now()`                                                                    | Creation timestamp      |
| `status`            | TEXT        | NOT NULL, CHECK (`draft`, `discovery`, `scanning`, `generating`, `sending`, `tracking`, `analysis`, `closed`) | Lifecycle state |
| `niche_keyword`     | TEXT        | NOT NULL                                                                                     | Target niche            |
| `cbsa_code`         | TEXT        | NOT NULL                                                                                     | Target metro            |
| `cbsa_name`         | TEXT        | —                                                                                            | Metro display name      |
| `sample_size`       | INT         | NOT NULL, default 100                                                                        | Business sample size    |
| `business_filters`  | JSONB       | —                                                                                            | Qualification filters   |
| `variants`          | JSONB       | —                                                                                            | Variant config snapshot |
| `results`           | JSONB       | —                                                                                            | Aggregated results      |
| `rentability_signal`| JSONB       | —                                                                                            | Computed rentability    |

#### experiment_variants

| Column           | Type    | Constraints                               | Description          |
| ---------------- | ------- | ----------------------------------------- | -------------------- |
| `id`             | UUID    | PK                                        | Row identifier       |
| `experiment_id`  | UUID    | FK → `experiments.id`, ON DELETE CASCADE  | Parent experiment    |
| `variant_id`     | TEXT    | NOT NULL, UNIQUE(experiment_id, variant_id) | Variant label      |
| `name`           | TEXT    | —                                         | Display name         |
| `audit_depth`    | TEXT    | CHECK (`minimal`, `standard`, `visual_mockup`) | Audit depth    |
| `email_template` | TEXT    | —                                         | Outreach template    |
| `value_prop`     | TEXT    | —                                         | Value proposition    |
| `allocation_pct` | NUMERIC | —                                         | Traffic allocation % |

#### experiment_businesses

| Column                 | Type        | Constraints                              | Description              |
| ---------------------- | ----------- | ---------------------------------------- | ------------------------ |
| `id`                   | UUID        | PK                                       | Row identifier           |
| `experiment_id`        | UUID        | FK → `experiments.id`, ON DELETE CASCADE | Parent experiment        |
| `variant_id`           | TEXT        | —                                        | Assigned variant         |
| `business_data`        | JSONB       | NOT NULL                                 | Discovered business info |
| `contact`              | JSONB       | —                                        | Contact information      |
| `qualification_status` | TEXT        | default `'pending'`                      | Qualification state      |
| `scan_results`         | JSONB       | —                                        | M11 scan output          |
| `weakness_score`       | INT         | —                                        | Website weakness score   |
| `quality_bucket`       | TEXT        | —                                        | Quality segmentation     |
| `audit_url`            | TEXT        | —                                        | Generated audit page URL |
| `outreach_status`      | TEXT        | default `'pending'`                      | Outreach lifecycle       |
| `engagement_score`     | INT         | —                                        | Computed engagement      |
| `created_at`           | TIMESTAMPTZ | NOT NULL, default `now()`                | Row creation time        |

#### outreach_events

| Column          | Type        | Constraints                                        | Description         |
| --------------- | ----------- | -------------------------------------------------- | ------------------- |
| `id`            | UUID        | PK                                                 | Row identifier      |
| `experiment_id` | UUID        | FK → `experiments.id`, ON DELETE CASCADE           | Parent experiment   |
| `business_id`   | UUID        | FK → `experiment_businesses.id`, ON DELETE CASCADE | Target business     |
| `variant_id`    | TEXT        | —                                                  | Variant label       |
| `event_type`    | TEXT        | NOT NULL                                           | send/open/click/reply |
| `event_data`    | JSONB       | —                                                  | Event payload       |
| `metadata`      | JSONB       | —                                                  | Tracking metadata   |
| `timestamp`     | TIMESTAMPTZ | NOT NULL, default `now()`                          | Event time          |

#### reply_classifications

| Column          | Type        | Constraints                                        | Description         |
| --------------- | ----------- | -------------------------------------------------- | ------------------- |
| `id`            | UUID        | PK                                                 | Row identifier      |
| `event_id`      | UUID        | FK → `outreach_events.id`, ON DELETE CASCADE       | Source reply event  |
| `business_id`   | UUID        | FK → `experiment_businesses.id`, ON DELETE CASCADE | Business context    |
| `reply_text`    | TEXT        | —                                                  | Raw reply body      |
| `classification`| TEXT        | —                                                  | Sentiment label     |
| `confidence`    | NUMERIC     | —                                                  | Classification conf |
| `key_phrases`   | JSONB       | —                                                  | Extracted phrases   |
| `classified_at` | TIMESTAMPTZ | NOT NULL, default `now()`                          | Classification time |

#### rentability_signals

| Column               | Type        | Constraints                        | Description                    |
| -------------------- | ----------- | ---------------------------------- | ------------------------------ |
| `id`                 | UUID        | PK                                 | Row identifier                 |
| `niche_keyword`      | TEXT        | NOT NULL, UNIQUE(niche, cbsa)      | Target niche                   |
| `cbsa_code`          | TEXT        | NOT NULL, UNIQUE(niche, cbsa)      | Target metro                   |
| `experiment_id`      | UUID        | FK → `experiments.id` (optional)   | Source experiment               |
| `sample_size`        | INT         | —                                  | Businesses sampled             |
| `response_rate`      | NUMERIC     | —                                  | Outreach response rate         |
| `positive_intent_rate`| NUMERIC    | —                                  | Positive-reply rate            |
| `engagement_avg`     | NUMERIC     | —                                  | Average engagement score       |
| `rentability_score`  | INT         | —                                  | Composite rentability (0-100)  |
| `confidence`         | TEXT        | —                                  | Confidence level               |
| `segment_data`       | JSONB       | —                                  | Per-segment breakdown          |
| `created_at`         | TIMESTAMPTZ | NOT NULL, default `now()`          | Row creation time              |


### Research Graph (Filesystem)

Persisted as a single JSON file (default `research_graph.json`, override via
`RESEARCH_GRAPH_PATH` env var). Backed by NetworkX `DiGraph`; serialized via
`networkx.node_link_data` / `node_link_graph`.

#### GraphNode

| Field                 | Type   | Values / Constraints                                                   | Description                 |
| --------------------- | ------ | ---------------------------------------------------------------------- | --------------------------- |
| `id`                  | string | UUID                                                                   | Node identifier             |
| `node_type`           | enum   | `hypothesis`, `experiment`, `proxy_metric`, `recommendation`, `observation` | Node category          |
| `title`               | string | —                                                                      | Short label                 |
| `description`         | string | —                                                                      | Full description            |
| `status`              | enum   | `active`, `validated`, `invalidated`, `superseded`, `pending`          | Current state               |
| `confidence`          | float  | 0.0–1.0                                                               | Confidence score            |
| `version`             | int    | >= 1                                                                   | Revision counter            |
| `metadata`            | object | —                                                                      | Arbitrary context           |
| `provenance_artifact` | string | nullable                                                               | File path for auditability  |
| `created_at`          | string | ISO 8601                                                               | Creation timestamp          |
| `updated_at`          | string | ISO 8601                                                               | Last modification timestamp |

#### GraphEdge

| Field        | Type   | Values / Constraints                                                 | Description          |
| ------------ | ------ | -------------------------------------------------------------------- | -------------------- |
| `source_id`  | string | Must reference existing node                                         | Source node           |
| `target_id`  | string | Must reference existing node                                         | Target node           |
| `edge_type`  | enum   | `supports`, `contradicts`, `derived_from`, `supersedes`, `tested_by` | Relationship kind    |
| `weight`     | float  | default 1.0                                                         | Strength / relevance |
| `metadata`   | object | —                                                                    | Arbitrary context    |
| `created_at` | string | ISO 8601                                                             | Creation timestamp   |


### Research Run Artifacts (Filesystem)

Per-run directory layout under `research_runs/{run_id}/`:

```
{run_id}/
  progress.jsonl              # Append-only learning/event log
  backlog.json                # Current hypothesis backlog
  loop_state.json             # Crash-recovery loop state
  experiment_results/
    {experiment_id}.json      # Per-experiment result snapshot
  tool_outputs/
    {step}_{tool_name}.json   # Raw tool responses for replay
  snapshots/
    baseline.json             # Baseline scoring snapshot
    candidate_{n}.json        # Candidate scoring snapshot
```


---

## Dual Storage Rules

The `reports` table uses two complementary storage strategies:

1. **JSONB snapshot columns** (`keyword_expansion`, `metros`, `meta`, `resolved_weights`) —
   complete, self-contained representation of the entire report. This is the
   **source of truth** for V1 and the minimum-viable record.

2. **Normalized child tables** (`report_keywords`, `metro_signals`, `metro_scores`) —
   broken-out rows for SQL-native querying, aggregation, and indexing. These
   duplicate data from the JSONB columns.

**Rules:**

- Both paths must be written within the same database transaction when possible.
- If a writer can only complete one path (e.g. partial failure), it must write the
  JSONB columns on `reports` — never child rows without a parent JSONB snapshot.
- Reads for report display should use the JSONB columns. Reads for cross-report
  analytics (e.g. "average opportunity score for plumber niches") should use the
  normalized tables.
- Schema evolution that adds fields must update both the JSONB shape and the
  corresponding normalized table columns.


---

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
| Research artifacts  | Filesystem (JSON)    | Per-run dirs, crash-recoverable, no external DB         |


---

## Revision History


| Version | Date       | Author        | Changes                                                      |
| ------- | ---------- | ------------- | ------------------------------------------------------------ |
| 0.1.0   | 2026-04-05 | DocGuard Init | Initial template                                             |
| 1.0.0   | 2026-04-05 | Migration     | Populated from `docs/algo_spec_v1_1.md`, `docs/data_flow.md` |
| 1.1.0   | 2026-04-06 | Data model review | Added normalized report tables, experiment entities, research agent storage, feedback_log key spec, dual-storage rules |


