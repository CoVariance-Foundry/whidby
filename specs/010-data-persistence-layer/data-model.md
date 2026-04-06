# Data Model: Data Persistence Layer

**Branch**: `010-data-persistence-layer` | **Date**: 2026-04-06

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 1: Observation Store                                          │
│                                                                     │
│  observations ──────────────────────── Supabase Storage bucket      │
│  (Postgres index)     storage_path ──► observations/{path}.json.gz  │
│                                                                     │
│  Relationships:                                                     │
│    observations.run_id ──► reports.id (optional, for pipeline runs) │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ LAYER 2: Canonical Reference Store                                  │
│                                                                     │
│  canonical_metros                                                   │
│  canonical_benchmarks ──► (niche_keyword, metro_size_tier, metric)  │
│  canonical_niches                                                   │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ LAYER 3: Anchor Search System                                       │
│                                                                     │
│  anchor_configs ◄──── anchor_runs (1:N)                             │
│       │                                                             │
│       └──────────── signal_snapshots (1:N, one per day)             │
│                          │                                          │
│                          └── observation_ids ──► observations (N:M) │
└─────────────────────────────────────────────────────────────────────┘
```

## Entity Definitions

### observations (Layer 1)

Immutable index row for every DataForSEO API response. Full payload stored in
object storage; this table is the fast-lookup metadata layer.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, auto | Observation identifier |
| `endpoint` | TEXT | NOT NULL | DataForSEO endpoint path |
| `query_params` | JSONB | NOT NULL | Request parameters (sorted, cleaned) |
| `query_hash` | TEXT | NOT NULL | SHA-256 of normalized endpoint + params |
| `observed_at` | TIMESTAMPTZ | NOT NULL, default `now()` | When the API was called |
| `source` | TEXT | NOT NULL, default `'pipeline'`, CHECK (`pipeline`, `anchor`, `manual`) | What triggered the call |
| `run_id` | UUID | nullable | Pipeline run / report this belongs to |
| `cost_usd` | NUMERIC(10,6) | NOT NULL, default 0 | DataForSEO cost for this call |
| `api_queue_mode` | TEXT | nullable | `standard` or `live` |
| `storage_path` | TEXT | NOT NULL | Object storage path to gzipped payload |
| `payload_size_bytes` | INTEGER | nullable | Compressed payload size |
| `ttl_category` | TEXT | NOT NULL | Freshness category (see TTL table) |
| `expires_at` | TIMESTAMPTZ | NOT NULL | When this observation becomes stale |
| `status` | TEXT | NOT NULL, default `'ok'` | `ok` or `error` |
| `error_message` | TEXT | nullable | Error detail if status = error |
| `payload_purged` | BOOLEAN | default false | True after retention cleanup |

**Indexes**:
- `(query_hash, expires_at DESC)` — cache freshness check (primary hot path)
- `(query_hash, observed_at DESC)` — temporal query by hash
- `(source, observed_at)` — cost attribution by source
- `(expires_at)` — retention cleanup scan

**TTL Categories**:

| Category | Duration | Endpoints |
|----------|----------|-----------|
| `serp` | 24 hours | serp_organic, serp_maps |
| `keyword` | 30 days | keyword_volume, keyword_suggestions |
| `business` | 7 days | business_listings, google_my_business_info |
| `review` | 7 days | google_reviews |
| `technical` | 14 days | lighthouse, backlinks_summary |
| `reference` | 90 days | locations |

---

### canonical_metros (Layer 2)

Enriched metro reference data with size-tier classification. Supersedes
`metro_location_cache` and the in-memory `cbsa_seed.json`.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `cbsa_code` | TEXT | PK | CBSA identifier |
| `cbsa_name` | TEXT | NOT NULL | Metro display name |
| `state` | TEXT | NOT NULL | Primary state |
| `region` | TEXT | NOT NULL | Census region |
| `population` | INTEGER | NOT NULL | Population count |
| `population_year` | INTEGER | NOT NULL | Census year of population figure |
| `population_growth_pct` | NUMERIC(5,2) | nullable | Annual growth rate |
| `principal_cities` | JSONB | NOT NULL | List of principal cities |
| `dataforseo_location_codes` | JSONB | NOT NULL | DFS location code mappings |
| `metro_size_tier` | TEXT | NOT NULL, CHECK (`major`, `mid`, `small`) | Population-based tier |
| `updated_at` | TIMESTAMPTZ | default `now()` | Last refresh timestamp |

**Size tier thresholds**: major = 1M+, mid = 250K–1M, small = 50K–250K.

---

### canonical_benchmarks (Layer 2)

Industry benchmark metrics scoped by niche and optionally by metro size tier.
Computed weekly from observations or seeded from external sources.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, auto | Row identifier |
| `niche_keyword` | TEXT | NOT NULL | Target niche |
| `metro_size_tier` | TEXT | nullable | Tier scope (NULL = national) |
| `metric_name` | TEXT | NOT NULL | e.g. `median_cpc`, `avg_review_count` |
| `metric_value` | NUMERIC | NOT NULL | Computed or seeded value |
| `sample_size` | INTEGER | NOT NULL | Number of observations used |
| `computed_at` | TIMESTAMPTZ | NOT NULL, default `now()` | When computed |
| `valid_until` | TIMESTAMPTZ | NOT NULL | Expiry for priority resolution |
| `source` | TEXT | NOT NULL, default `'computed'`, CHECK (`computed`, `external`) | Origin |

**Unique constraint**: `(niche_keyword, metro_size_tier, metric_name)` — upsert on recompute.

**Benchmark metrics**:

| Metric Name | Signal Source | Aggregation |
|-------------|--------------|-------------|
| `median_cpc` | keyword_volume observations | Median CPC across keywords |
| `median_search_volume` | keyword_volume observations | Median total search volume |
| `avg_da_top5` | serp_organic observations | Mean DA of top-5 results |
| `avg_review_count` | google_reviews observations | Mean review count for top-3 pack |
| `avg_review_velocity` | google_reviews observations (delta) | Mean monthly new reviews |
| `avg_business_density` | business_listings observations | Mean listing count |
| `aio_trigger_rate` | serp_organic observations | Fraction of SERPs with AIO |
| `median_aggregator_count` | serp_organic observations | Median aggregator domains in top-10 |
| `avg_gbp_photo_count` | google_my_business_info observations | Mean GBP photos |
| `avg_lighthouse_score` | lighthouse observations | Mean performance score |

---

### canonical_niches (Layer 2)

Niche taxonomy for category mapping and default parameters.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `niche_keyword` | TEXT | PK | Normalized niche term |
| `dataforseo_category` | TEXT | nullable | DFS business category |
| `parent_vertical` | TEXT | nullable | Vertical classification |
| `requires_physical_fulfillment` | BOOLEAN | default true | Service locality indicator |
| `typical_aio_exposure` | TEXT | nullable | Default AIO risk level |
| `modifier_patterns` | JSONB | nullable | Known good keyword modifiers |
| `created_at` | TIMESTAMPTZ | default `now()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | default `now()` | Last update timestamp |

**Verticals**: `home_services`, `automotive`, `legal`, `medical`, `specialty_services`.

---

### anchor_configs (Layer 3)

Subscription-like configuration for automated niche×metro monitoring.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, auto | Config identifier |
| `niche_keyword` | TEXT | NOT NULL | Target niche |
| `cbsa_code` | TEXT | NOT NULL | Target metro |
| `enabled` | BOOLEAN | default true | Active flag |
| `collect_serp` | BOOLEAN | default true | Collect SERP data |
| `collect_keyword_volume` | BOOLEAN | default true | Collect keyword volume |
| `collect_reviews` | BOOLEAN | default true | Collect Google reviews |
| `collect_gbp` | BOOLEAN | default false | Collect GBP info |
| `collect_lighthouse` | BOOLEAN | default false | Collect Lighthouse |
| `tracked_keywords` | JSONB | NOT NULL | Keywords to track |
| `keywords_sourced_from` | TEXT | nullable | Run ID that seeded keywords |
| `keywords_refreshed_at` | TIMESTAMPTZ | nullable | Last keyword refresh |
| `frequency` | TEXT | NOT NULL, default `'daily'`, CHECK (`daily`, `weekly`, `monthly`) | Schedule |
| `last_run_at` | TIMESTAMPTZ | nullable | Last execution time |
| `next_run_at` | TIMESTAMPTZ | nullable | Next scheduled run |
| `max_daily_cost_usd` | NUMERIC(10,2) | default 1.00 | Daily budget cap |
| `cumulative_cost_usd` | NUMERIC(10,2) | default 0 | Running total cost |
| `created_at` | TIMESTAMPTZ | default `now()` | Creation timestamp |

**Unique constraint**: `(niche_keyword, cbsa_code)`.

---

### anchor_runs (Layer 3)

Execution log for each anchor data collection cycle.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, auto | Run identifier |
| `anchor_config_id` | UUID | FK → `anchor_configs.id` | Parent config |
| `started_at` | TIMESTAMPTZ | NOT NULL, default `now()` | Run start time |
| `completed_at` | TIMESTAMPTZ | nullable | Run end time |
| `status` | TEXT | NOT NULL, default `'running'`, CHECK (`running`, `completed`, `failed`, `budget_exceeded`) | Run outcome |
| `observations_created` | INTEGER | default 0 | Count of new observations |
| `cost_usd` | NUMERIC(10,6) | default 0 | Total cost this run |
| `error_message` | TEXT | nullable | Failure detail |

---

### signal_snapshots (Layer 3)

Denormalized daily signal summary per anchor for time-series queries.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, auto | Snapshot identifier |
| `anchor_config_id` | UUID | FK → `anchor_configs.id` | Parent config |
| `niche_keyword` | TEXT | NOT NULL | Niche (denormalized) |
| `cbsa_code` | TEXT | NOT NULL | Metro (denormalized) |
| `snapshot_date` | DATE | NOT NULL | Date of snapshot |
| `serp_avg_da_top5` | NUMERIC | nullable | Avg DA of top-5 organic |
| `serp_aggregator_count` | INTEGER | nullable | Aggregator domains in top-10 |
| `serp_local_biz_count` | INTEGER | nullable | Local businesses in SERP |
| `serp_aio_present` | BOOLEAN | nullable | AIO detected in SERP |
| `serp_local_pack_present` | BOOLEAN | nullable | Local pack detected |
| `local_pack_review_avg` | NUMERIC | nullable | Avg reviews in local pack |
| `local_pack_review_max` | INTEGER | nullable | Max reviews in local pack |
| `local_pack_review_velocity` | NUMERIC | nullable | Monthly review growth rate |
| `keyword_volume_total` | INTEGER | nullable | Total search volume |
| `keyword_cpc_avg` | NUMERIC | nullable | Average CPC |
| `observation_ids` | JSONB | NOT NULL | Source observation UUIDs |
| `created_at` | TIMESTAMPTZ | default `now()` | Row creation timestamp |

**Unique constraint**: `(anchor_config_id, snapshot_date)`.

**Index**: `(niche_keyword, cbsa_code, snapshot_date)` for time-series queries.

---

## State Transitions

### Observation Lifecycle

```
API call triggered
    │
    ├─ Cache HIT (expires_at > now()) → return cached payload, no new row
    │
    └─ Cache MISS → call DataForSEO API
         │
         ├─ Success → status='ok', payload uploaded to Storage
         │     │
         │     ├─ Within TTL: serves as cache for subsequent requests
         │     │
         │     └─ After expires_at: no longer served as cache, still queryable
         │           │
         │           └─ After 24 months: payload_purged=true, Storage file deleted
         │                               Index row retained indefinitely
         │
         └─ Failure → status='error', error_message set, never served as cache
```

### Benchmark Lifecycle

```
External seed loaded (source='external', valid_until = +90 days)
    │
    ▼
Weekly recompute job runs
    │
    ├─ sample_size >= 5 → computed benchmark upserted (source='computed', valid_until = +7 days)
    │     │
    │     └─ Supersedes external seed in priority resolution
    │
    └─ sample_size < 5 → existing benchmark retained, valid_until extended +7 days
```

### Anchor Run Lifecycle

```
pg_cron triggers Edge Function
    │
    ▼
Query anchor_configs WHERE enabled AND next_run_at <= now()
    │
    ├─ Budget check: cumulative_cost + estimated_cost > max_daily_cost
    │     └─ YES → status='budget_exceeded', skip
    │
    └─ NO → status='running'
          │
          ├─ Call M0 client for each enabled data type
          │   (write-through to observation store is automatic)
          │
          ├─ Extract signal snapshot from collected observations
          │
          ├─ Success → status='completed', update next_run_at
          │
          └─ Failure → status='failed', error_message logged, continue to next anchor
```

---

## Validation Rules

| Entity | Rule |
|--------|------|
| observations | `query_hash` must be deterministic: same endpoint + params always produces same hash |
| observations | `expires_at` must equal `observed_at + TTL_DURATIONS[ttl_category]` |
| observations | `storage_path` must follow convention `{group}/{YYYY}/{MM}/{DD}/{hash}_{id}.json.gz` |
| observations | Rows with `status='error'` are never returned by cache lookup |
| canonical_benchmarks | `sample_size` must be >= 5 for `source='computed'` rows |
| canonical_benchmarks | `valid_until` for computed = `computed_at + 7 days`; for external = `computed_at + 90 days` |
| anchor_configs | `tracked_keywords` must contain at least one Tier 1 or Tier 2 keyword |
| signal_snapshots | `observation_ids` must reference valid observation UUIDs |
