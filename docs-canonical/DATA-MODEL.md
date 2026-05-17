# Data Model

> **Canonical document** — Design intent. This file describes the data structures and their relationships.
> Schema changes require this doc to be updated FIRST.


| Metadata         | Value       |
| ---------------- | ----------- |
| **Status**       | approved    |
| **Version**      | `1.4.0`     |
| **Last Updated** | 2026-05-16  |
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
| Report              | Supabase `reports` table             | id (UUID)        | Complete report with all metro results                             |
| ExploreRefreshPolicy | Supabase `explore_refresh_policies` table | id (UUID) | Refresh cadence, scope defaults, and pipeline flags for Explore cached market reports |
| ExploreRefreshTarget | Supabase `explore_refresh_targets` table | id (UUID) | Service + CBSA market target monitored for staleness and scheduled refresh |
| ExploreRefreshRun | Supabase `explore_refresh_runs` table | id (UUID) | Manual or scheduled refresh execution envelope |
| ExploreRefreshRunItem | Supabase `explore_refresh_run_items` table | id (UUID) | Per-target refresh result linking old report to new report and errors |
| ExploreReportSnapshot | Supabase `explore_report_snapshots` table | id (UUID) | Normalized historical score row per report + CBSA for trend analysis |
| StrategyRun | Supabase `strategy_runs` table | id (UUID) | Cached/fresh strategy run envelope for account-scoped lineage |
| StrategyRunItem | Supabase `strategy_run_items` table | id (UUID) | Ranked strategy result row for a city/service/keyword |
| LocalPackListingFact | Supabase `local_pack_listing_facts` table | id (UUID) | Keyword + CBSA local pack listing evidence used by GBP Blitz and Keyword Hijack |
| MetroFeatureVector | Supabase `metro_feature_vectors` table | cbsa_code + feature_version | Derived metro similarity vector used by Expand & Conquer |
| StrategyScoreCache | Supabase `strategy_score_cache` table | strategy_id + cbsa_code + niche + keyword | Optional read-optimized strategy projection cache |
| FeedbackLog         | Supabase `feedback_log` table        | log_id (UUID)    | Input context + scores for future optimization (legacy)            |
| KBEntity            | Supabase `kb_entities` table         | entity_id (UUID) | Canonical niche+geo identity for knowledge base lineage            |
| KBSnapshot          | Supabase `kb_snapshots` table        | snapshot_id (UUID) | Versioned derived-state snapshot with supersedence chain         |
| KBEvidenceArtifact  | Supabase `kb_evidence_artifacts`     | artifact_id (UUID) | Raw M5 collection payloads linked to snapshots                  |
| ApiResponseCache    | Supabase `api_response_cache` table  | cache_id (UUID)  | Persistent cross-run DataForSEO response cache                     |
| FeedbackEvent       | Supabase `feedback_events` table     | event_id (UUID)  | Runtime feedback linked to snapshots, reports, and entities        |
| MetroBenchmarkSource | Supabase `metros` table             | cbsa_code        | ACS-backed metro demographics and population class                 |
| CBPEstablishment    | Supabase `census_cbp_establishments` table | cbsa_code + naics_code + year | Census CBP establishment density for monetization benchmarks |
| SeoFact             | Supabase `seo_facts` table           | id (UUID); unique niche + cbsa + keyword + date | Keyword-grain observations used to build benchmarks             |
| SeoBenchmark        | Supabase `seo_benchmarks` table      | niche + population_class | V2 benchmark cell used by scoring                              |
| ServiceACVEstimate  | Supabase `service_acv_estimates` table | naics_code + cbsa_code | BLS-derived ACV estimates                                      |
| ExploreMarketCell   | Derived Explore read model            | cbsa_code + niche_normalized | Materialized city-service market cell for Explore latency |
| ExploreCitySummary  | DTO from Explore Cities service       | cbsa_code        | Filterable cached market row combining metro demographics, cached scores, density, growth, and freshness |
| ExploreServiceMetric | DTO from Explore Cities service      | cbsa_code + niche_normalized | Cached service score, score-system provenance, density/growth lineage, and refresh/run-report target data |
| UserProfile         | Supabase `user_profiles` table        | user_id (UUID)   | Consumer profile linked 1:1 to Supabase Auth user |
| Account             | Supabase `accounts` table             | account_id (UUID) | Billing and data-isolation boundary |
| AccountMembership   | Supabase `account_memberships` table  | account_id + user_id | User access to an account, with role |
| Subscription        | Supabase `subscriptions` table        | subscription_id (UUID) | Active tier state synced from Stripe |
| UsageCounter        | Supabase `usage_counters` table       | account + metric + period | Atomic monthly quota usage for fresh reports |
| BillingCustomer     | Supabase `billing_customers` table    | account_id       | Stripe customer mapping |
| OnboardingProfile   | Supabase `onboarding_profiles` table  | id (UUID); unique user_id | Durable signup/onboarding answers, recommended strategy, and resume route |
| OnboardingTarget    | Supabase `onboarding_targets` table   | id (UUID); unique profile + strategy | Selected strategy, service, and resolved geography for first-report handoff |


### Sonar Slice-Lite Entities

| Entity | Storage | Primary Key | Description |
| --- | --- | --- | --- |
| SonarCell | Supabase `sonar.cells` | `cell_id` | Cell registry keyed by NAICS, geo level, geo id, and year. |
| SonarCellRun | Supabase `sonar.cell_runs` | `run_id` | Versioned CellRecord JSONB output. Slice-lite records include explicit data-quality warnings for missing NES, BDS, Trends, geo crosswalk, and residual model inputs. |
| SonarScoringWeights | Supabase `sonar.scoring_weights` | `version` | Active score weights by Sonar score version. |

Full Sonar residuals require additional canonical layers before implementation: `geo.canonical_geo`, `geo.crosswalk`, county-level NES source tables, BDS source tables, historical CBP source tables, and residual model artifact storage. Do not mark a Sonar cell as full-spec unless residuals are computed from a peer matrix with `peer_count >= 30` and recorded model quality.


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
| `enrichment_status` | string | No | `enriched`, `mapbox_only`, `not_configured`, `timeout`, `degraded`, or `fallback_cbsa` |
| `enrichment_reason` | string | No | Human-readable reason when enrichment degrades or falls back |

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
| `metadata_source` | string | No | `typed`, `mapbox_selected`, `recent_history`, or `fallback_cbsa` |

Source: `apps/app/src/lib/niche-finder/history-storage.ts`. Dedupe key prefers `place_id` when present.

### ExploreMarketCell (derived read model)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `cbsa_code` | text | Yes | Metro key from `public.metros` |
| `niche_normalized` | text | Yes | Service key from `public.niche_naics_mapping` or cached score row |
| `niche_keyword` | text | Yes | Display service label |
| `presentation_score` | integer | No | V2 lens projection when present, else legacy opportunity score |
| `score_system` | text | Yes | `v2`, `legacy`, or `none` |
| `business_density_per_1k` | numeric | No | Weighted CBP establishments per 1,000 residents for this service |
| `establishment_growth_yoy` | numeric | No | Annualized establishment growth for this service |
| `growth_available` | boolean | Yes | False when no historical CBP prior year is loaded |
| `latest_scored_at` | timestamptz | No | Latest cached score time |
| `refresh_target_id` | uuid | No | Refresh target for cached rows |
| `stale` | boolean | Yes | Freshness relative to active cadence |

This is a derived read model for Explore latency. Canonical source tables remain `metros`, `census_cbp_establishments`, `niche_naics_mapping`, `reports`, `metro_scores`, `metro_score_v2`, and Explore refresh tables.

### ExploreCitySummary (service DTO)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `cbsa_code` | string | Yes | Metro key from `public.metros` |
| `cbsa_name` | string | Yes | Display metro name |
| `state` | string | Yes | Primary state from `public.metros` |
| `population` | integer | No | ACS population |
| `population_class` | string | No | Derived class from `public.metros.population_class` |
| `median_household_income_usd` | integer | No | ACS median household income |
| `owner_occupancy_rate` | float | No | ACS owner-occupied housing units / households |
| `median_age_years` | float | No | ACS median age |
| `metric_service` | string | No | Service label for density/growth when no active service filter is selected and metrics come from a representative cached service |
| `business_density_per_1k` | float | No | Weighted CBP establishments per 1,000 residents for the active service filter |
| `establishment_growth_yoy` | float | No | Annualized CBP establishment growth for the active service filter |
| `growth_available` | boolean | Yes | False when historical CBP years needed for growth are not loaded |
| `cached_services_count` | integer | Yes | Count of latest cached service rows for the metro |
| `best_score` | integer | No | V2 lens projection when available; legacy opportunity fallback otherwise |
| `score_system` | string | Yes | `v2`, `legacy`, or `none` |
| `last_scored_at` | timestamptz | No | Latest cached score timestamp |
| `stale` | boolean | Yes | Whether latest score exceeds the active freshness cadence |

Source: `src/domain/services/explore_city_service.py`. The frontend must treat this as an already-filtered backend result, not as a raw table dump.

### ExploreServiceMetric (service DTO)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `cbsa_code` | string | Yes | Metro key |
| `niche_keyword` | string | Yes | Display service keyword |
| `niche_normalized` | string | Yes | Stable service key used for joins |
| `report_id` | UUID | No | Source report |
| `score_system` | string | Yes | `v2` if `metro_score_v2` exists, else `legacy` when sourced from `metro_scores` |
| `v2_scores` | object | No | Demand, organic difficulty, local difficulty, monetization, and AI resilience vector |
| `legacy_opportunity_score` | integer | No | Legacy V1.1 opportunity score fallback |
| `presentation_score` | integer | No | User-selected V2 lens projection or legacy opportunity fallback |
| `business_density_per_1k` | float | No | Weighted CBP establishments per 1,000 residents for this service |
| `establishment_growth_yoy` | float | No | Annualized establishment growth for this service |
| `benchmark_confidence` | string | No | V2 benchmark confidence label |
| `latest_scored_at` | timestamptz | No | Latest score timestamp |
| `refresh_target_id` | UUID | No | Existing refresh target when configured |
| `next_refresh_at` | timestamptz | No | Next scheduled refresh time |
| `stale` | boolean | Yes | Whether this cached service exceeds the active freshness cadence |

Source: `src/domain/explore/entities.py` and `src/domain/services/explore_city_service.py`.

### StrategyResult (service DTO)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `strategy_id` | string | Yes | `easy_win`, `gbp_blitz`, `keyword_hijack`, `expand_conquer`, or `cash_cow` |
| `rank` | integer | Yes | Rank within the returned result set |
| `score` | number | Yes | Strategy projection score, 0-100 |
| `cbsa_code` | string | Yes | Metro key |
| `niche_normalized` | string | Yes | Stable service key |
| `primary_keyword` | string | No | Required for Keyword Hijack rows |
| `evidence` | object | Yes | Strategy-specific signal facts used to explain the score |
| `warnings` | array | Yes | AI resilience, benchmark confidence, stale data, missing local pack, and entitlement warnings |

### Explore Metric Formulas

Business density is service-aware and based on CBP establishments, not DataForSEO business-listing count:

```text
weighted_establishments =
  sum(census_cbp_establishments.est * niche_naics_mapping.weight)

business_density_per_1k =
  weighted_establishments / metros.population * 1,000
```

`seo_benchmarks` may continue to store the same concept per 100,000 residents (`median_establishments_per_100k`) for benchmark scoring. Explore uses per 1,000 residents for table readability.

Establishment growth is annualized from historical CBP establishment counts:

```text
establishment_growth_yoy =
  (latest_weighted_establishments / prior_weighted_establishments) ** (1 / year_span) - 1
```

If historical CBP years are not loaded, return `establishment_growth_yoy = null` and `growth_available = false`; do not silently filter out all cities.

Freshness uses the latest cached score timestamp and the active policy cadence:

```text
stale = latest_scored_at < now() - cadence_days
```

Default `cadence_days` is 30 until a persisted refresh policy overrides it.

### Consumer Account and Report Ownership

Consumer account state is account-scoped even when an account has one user. New users default to `free`; Stripe webhooks move accounts to `plus` or `pro`. The first-account bootstrap serializes by authenticated user and `account_memberships.user_id` is unique in V1, so concurrent first requests cannot create multiple default accounts for the same user.

| Tier | Monthly price | Fresh report quota |
| --- | ---: | ---: |
| `free` | 0 | 0 |
| `plus` | 4900 cents | 10 |
| `pro` | 10000 cents | 50 |

Reports have two visibility modes:

| `reports.access_scope` | Ownership | Read rule |
| --- | --- | --- |
| `cached` | `owner_account_id` is null | Authenticated users can read as shared product cache |
| `account` | `owner_account_id` required | Only members of the owning account can read |

Fresh scoring requests must persist generated reports as `account`; existing ownerless reports are treated as `cached`. Report child tables (`report_keywords`, `metro_signals`, `metro_scores`) inherit read access through their parent report. Authenticated users do not receive direct `UPDATE` access to report payloads; account-owned soft archive is exposed only through `archive_account_report(report_id)`.

### Consumer Onboarding State

Onboarding is account-scoped, but each authenticated user has at most one active onboarding profile. It captures product intent and first-run target state only; it does not own scoring outputs.

Valid profile statuses:

| Status | Meaning |
| --- | --- |
| `profile_started` | Identity or initial answers exist, but routing is incomplete. |
| `profile_completed` | Intent/focus answers are persisted. |
| `strategy_recommended` | `recommended_strategy_id` and `next_route` are available. |
| `target_selected` | A service + geography target is ready for cached/fresh handoff. |
| `report_queued` | A fresh report request was accepted by the scoring path. |
| `cached_route_selected` | Free or researching user was routed to cached Explore/report data. |
| `upgrade_required` | User selected a fresh flow without a plan/quota that allows it. |
| `report_ready` | The first generated report is available. |

`recommended_strategy_id` must be one of the strategy catalog ids from the consumer app (`easy_win`, `cash_cow`, `blue_ocean`, `gbp_blitz`, `portfolio_builder`, `expand_conquer`, `seasonal_arbitrage`). Strategy routing is deterministic from `intent`, `focus`, and optional `coach_or_agency` so it remains testable without Supabase.

`onboarding_targets` stores the user's selected target for resume and report start. City-level targets should preserve Mapbox/DataForSEO metadata when selected through autocomplete; state or broad-region targets should preserve `geo_scope`, `state`, and `resolved_label` and hand off to Explore or batch workflows when no single city scoring target exists.

Free users can persist onboarding state and cached-route choices, but fresh scoring still follows `usage_counters` and account entitlement rules.

## Schema Definitions

### OnboardingProfile (`onboarding_profiles`)

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | UUID | Yes | primary key | Stable onboarding profile id |
| `user_id` | UUID | Yes | unique, references `user_profiles.id` | Authenticated consumer user |
| `account_id` | UUID | Yes | references `accounts.id` | Account used for entitlement and report ownership |
| `intent` | text | No | `find_first`, `scale`, `coach_agency`, `researching` | Primary onboarding job-to-be-done |
| `focus` | text | No | non-empty when required by intent | Adaptive second answer used for strategy routing |
| `coach_or_agency` | text | No | `coaching`, `agency`, `both` | Sub-segmentation for coach/agency users |
| `referral_source` | text | No | — | Optional attribution answer |
| `recommended_strategy_id` | text | No | strategy catalog id | Deterministic starter strategy |
| `available_strategy_ids` | text[] | Yes | default empty array | Strategies shown unlocked/recommended after onboarding |
| `next_route` | text | No | app-relative path | Product surface to open after profile completion |
| `status` | text | Yes | default `profile_started` | Resume/status state for onboarding |
| `created_at` | timestamptz | Yes | default now() | Creation timestamp |
| `updated_at` | timestamptz | Yes | default now() | Last profile update timestamp |
| `completed_at` | timestamptz | No | — | Set when profile answers are complete |

### OnboardingTarget (`onboarding_targets`)

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | UUID | Yes | primary key | Stable target id |
| `onboarding_profile_id` | UUID | Yes | references `onboarding_profiles.id` | Parent onboarding profile |
| `strategy_id` | text | Yes | strategy catalog id | Strategy used to interpret target shape |
| `niche_keyword` | text | Yes | non-empty | Display service/niche keyword |
| `service_category_id` | text | No | — | Optional predefined service category from UI |
| `geo_scope` | text | Yes | `city`, `state`, `region`, `nationwide` | Target geography shape |
| `city` | text | No | — | City display name for city targets |
| `state` | text | No | two-letter code when available | State/admin region |
| `cbsa_code` | text | No | references `metros.cbsa_code` when available | CBSA target for seeded metro workflows |
| `place_id` | text | No | — | Mapbox canonical place id |
| `dataforseo_location_code` | integer | No | — | DataForSEO location code from place enrichment |
| `resolved_label` | text | No | — | Human-readable target summary |
| `metadata_source` | text | No | `typed`, `mapbox_selected`, `recent_history`, `fallback_cbsa` | Provenance for scoring handoff |
| `created_at` | timestamptz | Yes | default now() | Creation timestamp |
| `updated_at` | timestamptz | Yes | default now() | Last target update timestamp |

### ExploreRefreshPolicy (`explore_refresh_policies`)

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | UUID | Yes | primary key | Stable refresh policy identifier |
| `name` | text | Yes | default `base-30-day-refresh` | Human-readable policy name for cached Explore refreshes |
| `enabled` | boolean | Yes | default true | Allows scheduled refresh to pick targets for this policy |
| `cadence_days` | integer | Yes | default 30, 1-365 | Freshness window before a target becomes stale |
| `scope` | text | Yes | `all_cached`, `stale_only`, `filtered`; default `all_cached` | Default target-selection scope |
| `flags` | jsonb | Yes | default includes `force`, `dry_run`, `strategy_profile`, `max_items`, `concurrency` | Pipeline flags passed to the scoring bridge |
| `created_by` | UUID | No | — | Operator or service identity that created the policy |
| `created_at` | timestamptz | Yes | default now() | Creation timestamp |
| `updated_at` | timestamptz | Yes | default now() | Last metadata update timestamp |

### ExploreRefreshTarget (`explore_refresh_targets`)

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | UUID | Yes | primary key | Stable service + CBSA target identifier |
| `policy_id` | UUID | Yes | references `explore_refresh_policies.id` | Policy controlling cadence and scoring flags |
| `niche_keyword` | text | Yes | non-empty | Display service/niche keyword monitored for freshness |
| `niche_normalized` | text | Yes | non-empty | Normalized service key used for uniqueness and refresh lookup |
| `cbsa_code` | text | Yes | references `metros.cbsa_code` | CBSA market monitored for refresh |
| `cbsa_name` | text | Yes | non-empty | Display CBSA market name |
| `state` | text | No | — | Two-letter state code when available |
| `latest_report_id` | UUID | No | references `reports.id` | Latest cached report used by `/explore` |
| `latest_scored_at` | timestamptz | No | — | Timestamp for the latest cached score |
| `next_refresh_at` | timestamptz | No | indexed | Next scheduled eligibility timestamp |
| `active` | boolean | Yes | default true | Allows scheduler selection for this target |
| `priority` | integer | Yes | default 100 | Lower values sort earlier for due refresh selection |
| `created_at` | timestamptz | Yes | default now() | Creation timestamp |
| `updated_at` | timestamptz | Yes | default now() | Last metadata update timestamp |

### ExploreRefreshRun (`explore_refresh_runs`)

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | UUID | Yes | primary key | Refresh execution envelope identifier |
| `policy_id` | UUID | No | references `explore_refresh_policies.id` | Policy used for scheduled/default flags |
| `mode` | text | Yes | `manual`, `scheduled` | Source of the run request |
| `scope` | text | Yes | `selected`, `visible`, `stale`, `all` | Target-selection mode for the run |
| `status` | text | Yes | `queued`, `running`, `succeeded`, `partial_failed`, `failed`, `canceled`; default `queued` | Current run state |
| `flags` | jsonb | Yes | default `{}` | Run-level execution flags captured from policy or request |
| `requested_by` | UUID | No | — | User that requested a manual run |
| `target_count` | integer | Yes | default 0, >= 0 | Targets selected for the run |
| `success_count` | integer | Yes | default 0, >= 0 | Items that produced a new report and snapshot |
| `failure_count` | integer | Yes | default 0, >= 0 | Items that ended with an error |
| `error_message` | text | No | — | Run-level failure summary |
| `started_at` | timestamptz | No | — | Run start timestamp |
| `completed_at` | timestamptz | No | — | Run terminal timestamp |
| `created_at` | timestamptz | Yes | default now() | Creation timestamp |

### ExploreRefreshRunItem (`explore_refresh_run_items`)

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | UUID | Yes | primary key | Per-target refresh item identifier |
| `run_id` | UUID | Yes | references `explore_refresh_runs.id` | Parent refresh run |
| `target_id` | UUID | Yes | references `explore_refresh_targets.id` | Target evaluated by the item |
| `old_report_id` | UUID | No | references `reports.id` | Previously cached report for lineage and delta calculations |
| `new_report_id` | UUID | No | references `reports.id` | Newly generated report when refresh succeeds |
| `status` | text | Yes | `queued`, `running`, `succeeded`, `failed`, `skipped` | Item state |
| `error_message` | text | No | — | Human-readable failure detail |
| `opportunity_before` | integer | No | 0-100 | Previous opportunity score |
| `opportunity_after` | integer | No | 0-100 | Refreshed opportunity score |
| `score_delta` | integer | No | — | `opportunity_after - opportunity_before` for trend display |
| `started_at` | timestamptz | No | — | Item start timestamp |
| `completed_at` | timestamptz | No | — | Item terminal timestamp |
| `created_at` | timestamptz | Yes | default now() | Creation timestamp |

### ExploreReportSnapshot (`explore_report_snapshots`)

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `id` | UUID | Yes | primary key | Historical score row identifier |
| `report_id` | UUID | Yes | references `reports.id` | Source report for the snapshot |
| `run_id` | UUID | No | references `explore_refresh_runs.id` | Refresh run that created the report |
| `target_id` | UUID | No | references `explore_refresh_targets.id` | Target represented by this snapshot |
| `niche_keyword` | text | Yes | non-empty | Display service/niche represented by the normalized row |
| `niche_normalized` | text | Yes | non-empty | Normalized service key for trend grouping |
| `cbsa_code` | text | Yes | references `metros.cbsa_code` | Market represented by the normalized row |
| `cbsa_name` | text | Yes | non-empty | Display CBSA market name |
| `state` | text | No | — | Two-letter state code when available |
| `strategy_profile` | text | Yes | default `balanced` | Strategy profile used for the score |
| `scored_at` | timestamptz | Yes | — | Timestamp from the scoring result |
| `opportunity_score` | integer | No | 0-100 | Composite score shown in `/explore` |
| `demand_score` | integer | No | 0-100 | Demand component score |
| `organic_competition_score` | integer | No | 0-100 | Organic competition component score |
| `local_competition_score` | integer | No | 0-100 | Local competition component score |
| `monetization_score` | integer | No | 0-100 | Monetization component score |
| `ai_resilience_score` | integer | No | 0-100 | AI resilience component score |
| `confidence_score` | integer | No | 0-100 | Confidence score from the scoring result |
| `serp_archetype` | text | No | — | SERP archetype classification |
| `ai_exposure` | text | No | — | AI exposure classification |
| `difficulty_tier` | text | No | — | Difficulty classification |
| `meta` | jsonb | Yes | default `{}` | Scoring metadata and lineage payload |
| `created_at` | timestamptz | Yes | default now() | Creation timestamp |

Trend deltas for Explore targets come from the planned `explore_target_trends` view over `explore_report_snapshots`.

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
| Consumer billing    | Stripe Checkout + Portal | Plus/Pro subscription state synced to Supabase by webhook |
| Feature flags       | PostHog              | Rollout controls only; never the authority for RLS or billing |
| In-memory contracts | Pydantic / TypedDict | Validated at module boundaries, no ORM                  |


---

## Revision History


| Version | Date       | Author        | Changes                                                      |
| ------- | ---------- | ------------- | ------------------------------------------------------------ |
| 0.1.0   | 2026-04-05 | DocGuard Init | Initial template                                             |
| 1.0.0   | 2026-04-05 | Migration     | Populated from `docs/algo_spec_v1_1.md`, `docs/data_flow.md` |
| 1.1.0   | 2026-04-22 | Mapbox autocomplete | Added PlaceSuggestion and HistoryEntry schemas for global autocomplete + canonical place targeting |
| 1.2.0   | 2026-05-14 | Explore Cities system design | Added Explore service DTOs, density/growth/freshness formulas, and backend filtering expectations |
| 1.3.0   | 2026-05-14 | Explore refresh control | Added refresh policy, target, run, run item, and report snapshot entities for cached Explore refreshes |
| 1.4.0   | 2026-05-16 | Strategy Discovery system design | Added strategy run/cache entities, local pack and metro vector facts, and StrategyResult DTO |
