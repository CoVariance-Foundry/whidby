# Data Flow

> **Canonical notice:** Entity schemas and data flow diagrams have been migrated to
> `docs-canonical/DATA-MODEL.md`. This file is retained as detailed reference.
> Update canonical docs first when making data shape changes.

## Niche Scoring Pipeline (M4 → M9)

```
User Input                    M4: Keyword Expansion              M5: Data Collection
─────────────                 ─────────────────────              ───────────────────
niche_keyword: "plumber"  →   KeywordExpansion {                 RawCollectionResult {
geo_scope: "state"            expanded_keywords: [               metros: {
geo_target: "AZ"                {keyword, tier, intent,            "38060": {
strategy_profile: "balanced"     source, aio_risk}                   serp_organic: [...]
                              ],                                     serp_maps: [...]
                              total_keywords: 15,         →          keyword_volume: [...]
                              actionable_keywords: 12,               business_listings: [...]
                              expansion_confidence: "high"           google_reviews: [...]
                             }                                       gbp_info: [...]
                                                                     backlinks: [...]
                                                                     lighthouse: [...]
                                                                   }
                                                                 },
                                                                 meta: {
                                                                   total_cost_usd,
                                                                   total_api_calls,
                                                                   collection_time_seconds,
                                                                   errors: [{task_id, task_type, metro_id, message, is_retryable}]
                                                                 }
                                                                }

     │                              │
     │                              ▼
     │
     │                        M6: Signal Extraction
     │                        ─────────────────────
     │                        MetroSignals {
     │                          demand: {volume, cpc, breadth, ...}
     │                          organic_competition: {da, aggregators, ...}
     │                          local_competition: {reviews, gbp, ...}
     │                          ai_resilience: {aio_rate, intent_ratio, ...}
     │                          monetization: {cpc, density, lsa, ...}
     │                        }
     │
     │                              │
     │                              ▼
     │
     │                        M7: Scoring Engine
     │                        ─────────────────
     │                        MetroScores {
     │                          demand: 72
     │                          organic_competition: 65
     │                          local_competition: 58
     │                          monetization: 81
     │                          ai_resilience: 92
     │                          opportunity: 71
     │                          confidence: {score: 95, flags: []}
     │                          resolved_weights: {organic: 0.15, local: 0.20}
     │                        }
     │                              │
     │                              ▼
     │
     │                        M8: Classification + Guidance
     │                        ────────────────────────────
     │                        Validates required nested numeric fields
     │                        (fail-fast on missing/malformed inputs).
     │                        ClassificationGuidanceBundle {
     │                          serp_archetype: "LOCAL_PACK_VULNERABLE"
     │                          ai_exposure: "AI_SHIELDED"
     │                          difficulty_tier: "MODERATE"
     │                          guidance: {headline, strategy, priority_actions,
     │                                     ai_resilience_note, guidance_status}
     │                          metadata: {serp_rule_id, difficulty_inputs,
     │                                     guidance_fallback_reason}
     │                        }
     │                              │
     ▼                              ▼
     
M9: Report Generation + Feedback Logging
───────────────────────────────────────
Report {
  report_id: UUID
  generated_at: ISO-8601
  spec_version: "1.1"
  input: {niche, geo, strategy_profile, resolved_weights}
  keyword_expansion: {...}
  metros: [
    {cbsa, scores, confidence, archetype, ai_exposure, difficulty, signals, guidance}
    ... (sorted by opportunity score desc, then cbsa_code/cbsa_name tie-break)
  ]
  meta: {total_api_calls, total_cost_usd, processing_time_seconds}
}
     │
     ▼
Feedback rows (one per ranked metro): {
  context, signals, scores, classification, recommendation_rank, outcome:nullables
}
     │
     ▼
SupabasePersistence.persist_report(report) in src/clients/supabase_persistence.py
     │
     ├──→ reports (one row)
     ├──→ report_keywords (N rows, one per expanded keyword)
     ├──→ metro_signals (N rows, one per scored metro)
     ├──→ metro_scores (N rows, one per scored metro)
     ├──→ metro_score_v2 (upsert by report_id + cbsa_code when V2 scores exist)
     ├──→ seo_facts (upsert by niche + CBSA + keyword + UTC snapshot date when V2 scores exist)
     └──→ feedback_log (future — not yet wired; M9 returns a feedback_log_id placeholder)

Consumer /reports read path (not shown above):
     apps/app Next BFF `/api/agent/reports`
             │
             ▼
     Supabase `reports` + `metro_score_v2` read model with entitlement filtering
             │
             ▼
     dashboard/reports client surfaces
```

The write path above is triggered by the FastAPI `POST /api/niches/score` handler after `score_niche_for_metro` returns a report. V2 score persistence is idempotent on `report_id + cbsa_code`; keyword-grain facts preserve nullable top-3/top-5 fields for benchmark recompute. Consumer report list/detail reads go through app-owned Next route handlers so entitlement and V2 read-model logic stays server-side.

Bulk Explore data builds use `scripts/explore/bulk_score.py` as an operational runner over the same scoring and persistence path. The runner selects DataForSEO-ready metros with a rank-and-rent default ordering, caps `mega_5m_plus` markets only for the default strategy, accepts explicit repeated `--service-name` values for production seed runs, validates requested services against `niche_naics_mapping`, calls `POST /api/niches/score` for each city/service pair, verifies `reports`, `metro_scores`, `metro_score_v2`, and `seo_facts` persistence before marking an attempt successful, and appends a JSONL audit row for every success, partial persistence failure, or API failure. Legacy resume state merges report-backed `explore_market_cells` rows with legacy `metro_scores` + `reports` rows so interrupted runs skip all known cached reports rather than only one read model. V2-aware recovery uses `--resume-v2` to skip only pairs that already have normalized `metro_score_v2` and `seo_facts` rows, while `--retry-failed-from <jsonl>` reruns failed or partial audit rows from a specific run.

## Consumer Account, Billing, and Quota Flow

```
Supabase Auth user
     │
     ▼
ensure_account_for_current_user()
     │
     ├──→ user_profiles
     ├──→ accounts
     ├──→ account_memberships
     └──→ subscriptions
             ▲
             │
Stripe Checkout / Portal / Webhook
             │
             ▼
syncSubscriptionToAccount()
```

Consumer fresh-report generation is account-scoped. `apps/app/src/app/api/agent/scoring/route.ts` resolves the authenticated Supabase user, account entitlement, and server feature flags before calling the Render/FastAPI scoring bridge. If quota enforcement is enabled, the route calls `consume_report_quota(account_id)` before forwarding the scoring request and calls `refund_report_quota(account_id)` when validation or upstream scoring fails.

The route forwards `owner_account_id` and `created_by_user_id` to `POST /api/niches/score`. FastAPI validates those UUIDs, `MarketService` attaches them to the generated report, and `SupabasePersistence.persist_report()` writes them to `reports`. Reports with `access_scope = 'account'` are readable only by account members; ownerless reports remain shared cached reports with `access_scope = 'cached'`.

## Explore Refresh Control Flow

```
apps/app /explore refresh control
     │
     ▼
Next.js /api/explore/refresh/* proxy routes
     │
     ▼
FastAPI /api/explore/refresh/* endpoints
     │
     ▼
ExploreRefreshService
     │
     ├──→ SupabaseExploreRefreshStore
     │       ├──→ explore_refresh_policies
     │       ├──→ explore_refresh_targets
     │       ├──→ explore_refresh_runs
     │       ├──→ explore_refresh_run_items
     │       └──→ explore_report_snapshots
     │
     └──→ MarketService.score()
             │
             ▼
        reports + score tables
```

Manual refresh requests select existing cached city/service targets by selected IDs, visible filters, stale targets, or all targets. Scheduled due checks call the same FastAPI service through the app-scoped Vercel cron route and require the configured cron secret. Successful refreshes update target freshness, record run-item before/after opportunity scores, and insert normalized report snapshots for latest-score and trend views.

## Explore Data Model Population Flow

Explore city population and benchmark-readiness helpers are staged before live writes:

```
ACS/CBP source files + PostgREST reads
     │
     ├──→ scripts/explore/audit_explore_sources.py
     ├──→ scripts/explore/backfill_metros.py
     ├──→ scripts/explore/backfill_cbp_establishments.py
     └──→ scripts/explore/recompute_benchmark_readiness.py
             │
             ▼
        public.metros + public.census_cbp_establishments readiness
             │
             ▼
        src/domain/explore metrics and ExploreCityService DTOs
             │
             ▼
        apps/app Explore loader optional density/growth fields
```

Backfill scripts default to preview mode and only write through PostgREST when `--apply` and service-role Supabase env are present. Optional `public.metros` fields such as `business_density_per_1k` and `establishment_growth_yoy` are read when present; the consumer loader falls back to the base metro select when PostgREST reports those optional columns missing.

## Strategy Discovery Flow

Strategy discovery is a read-model projection over existing market intelligence, not a separate scoring engine:

```
Cached reports + metro scores + SEO facts + local-pack facts + metro feature vectors
     │
     ▼
StrategyRepository
     │
     ▼
DiscoveryService strategy projection
     │
     ├──→ FastAPI /api/strategies
     ├──→ FastAPI /api/discover
     └──→ FastAPI /api/strategy-runs
             │
             ▼
        strategy_runs + strategy_run_items lineage
```

The consumer app proxies strategy reads and run creation through `apps/app/src/app/api/strategies/*`. Free users remain cached-only; plus/pro users can create fresh strategy runs within the configured caps. Migration `017_strategy_discovery_system.sql` owns strategy run lineage, local-pack listing facts, metro feature vectors, and the optional strategy score cache after onboarding migration `016_consumer_onboarding.sql`.

## Experiment Pipeline (M10 → M15)

```
Experiment Config               M10: Business Discovery          M11: Site Scanning
─────────────────               ────────────────────             ──────────────────
niche: "plumber"           →    BusinessList [                   ScannedBusiness {
metro: "Phoenix"                  {name, url, reviews,             business_data: {...}
sample_size: 100                   rating, email,          →       scan_results: {
variants: [A, B]                   qualified: bool,                  lighthouse: {...}
                                   bucket: "developing"}             schema: {...}
                                ]                                    content: {...}
                                                                     cwv: {...}
                                                                   }
                                                                   weakness_score: 67
                                                                   weakness_issues: [...]
                                                                   quality_bucket: "developing"
                                                                 }

     │                              │
     │                              ▼
     │
     │                        M12: Audit Generation
     │                        ─────────────────────
     │                        Audit {
     │                          audit_id: "uuid"
     │                          url: "https://insights.widby.co/audit/..."
     │                          html: "..."
     │                          variant_id: "A"
     │                          audit_depth: "standard"
     │                        }
     │
     │                              │
     │                              ▼
     │
     │                        M13: Outreach Delivery
     │                        ─────────────────────
     │                        OutreachRecord {
     │                          business_id, variant_id
     │                          emails_sent: [{seq: 0, sent_at, template}]
     │                          status: "sent" | "bounced" | "replied" | "completed"
     │                        }
     │
     │                              │
     │                              ▼  (webhooks from email platform)
     │
     │                        M14: Response Tracking
     │                        ─────────────────────
     │                        Events: [
     │                          {type: "email_opened", business_id, timestamp}
     │                          {type: "audit_page_loaded", ...}
     │                          {type: "email_replied", classification: "POSITIVE_INTENT"}
     │                        ]
     │                        EngagementScore: 75
     │
     │                              │
     ▼                              ▼

M15: Experiment Analysis
────────────────────────
ExperimentResults {
  variant_metrics: {A: {open_rate, reply_rate, ...}, B: {...}}
  ab_comparison: {probability_b_better: 0.87}
  segment_breakdown: {by_review_bucket: {...}, ...}
  rentability_signal: {
    rentability_score: 62
    confidence: "medium"
  }
}
     │
     ▼

Supabase: rentability_signals table
     │
     ▼ (feedback loop)

M7: Scoring Engine reads rentability_signals to calibrate monetization_score
```

## Research Agent Feedback Loop

```
Scoring Output (M7-M9)        Research Agent
──────────────────────         ──────────────
MetroScores {                  RalphResearchLoop {
  demand: 72                     1. select_task (hypothesis from backlog)
  organic_competition: 45  →     2. run_experiment (modify params, re-score)
  local_competition: 58          3. evaluate (baseline vs candidate)
  monetization: 81               4. record_learning (filesystem + graph)
  ai_resilience: 92              5. reprioritize (update backlog)
  opportunity: 71              }
}
     │                              │
     ▼                              ▼

HypothesisGenerator              FilesystemStore
───────────────────              ───────────────
Analyzes weak proxies            research_runs/{run_id}/
Generates hypotheses    →          progress.jsonl
Ranks by priority                  backlog.json
                                   experiment_results/
     │                             snapshots/
     ▼
                                    │
ExperimentPlanner                   ▼
─────────────────
target_proxy              ResearchGraphStore
modifications        →    ──────────────────
rollback_condition         hypothesis nodes
sample_requirements        experiment nodes
                           supports/contradicts edges
     │                     recommendation nodes
     ▼

Recommender
───────────
Synthesizes validated outcomes
Generates prioritized recommendations  →  docs/algo_spec_v1_1.md updates
Produces improvement report               docs/system_design.md updates
```
