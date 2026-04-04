# Data Flow

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
                                                                 meta: {cost, calls, time}
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
     │                        }
     │                              │
     │                              ▼
     │
     │                        M8: Classification
     │                        ─────────────────
     │                        MetroClassification {
     │                          serp_archetype: "LOCAL_PACK_VULNERABLE"
     │                          ai_exposure: "AI_SHIELDED"
     │                          difficulty_tier: "MODERATE"
     │                          guidance: {headline, strategy, actions}
     │                        }
     │                              │
     ▼                              ▼
     
M9: Report Generation
─────────────────────
Report {
  input: {niche, geo, strategy_profile, resolved_weights}
  keyword_expansion: {...}
  metros: [
    {cbsa, scores, confidence, archetype, ai_exposure, difficulty, signals, guidance}
    ... (sorted by opportunity score desc)
  ]
  meta: {cost, time, feedback_log_id}
}
     │
     ▼

Supabase: reports table + feedback_log table
```

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