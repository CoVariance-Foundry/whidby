# Widby Niche Scoring Algorithm — V1.1 Specification

> **Canonical notice:** Requirements, data models, test obligations, and environment
> config from this spec have been migrated to `docs-canonical/REQUIREMENTS.md`,
> `docs-canonical/DATA-MODEL.md`, `docs-canonical/TEST-SPEC.md`, and
> `docs-canonical/ENVIRONMENT.md`. This file is retained as the authoritative
> algorithm reference. Update canonical docs first when making scoring/schema changes.

**Status:** Draft — Research-Updated
**Author:** Antwoine Flowers / Kael
**Date:** 2026-04-03
**Classification:** Internal IP — Covariance
**Changelog:** V1.1 incorporates findings from first-principles SEO measurement research. Key changes: split competition into organic + local, added AI resilience scoring, intent-classified keyword expansion, review velocity signals, AIO exposure detection, feedback logging schema for future bandit optimization.

---

## 1. Purpose

This document specifies the algorithm that powers Widby's core recommendation engine. The system ingests a user-provided niche keyword and geographic scope, collects market data from DataForSEO APIs, processes it through multiple analytical layers, and outputs a ranked list of metro-level opportunities with composite scores, SERP archetype classifications, and actionable guidance.

This is the **engine spec**, not the product spec. It defines what gets computed and how — not how it's presented to users.

### 1.1 Research Basis

This spec is informed by:
- Whitespark 2026 Local Search Ranking Factors survey (47 expert respondents, Nov 2025)
- Ahrefs 146-million-SERP study on AI Overview triggers (2025-2026)
- Seer Interactive CTR study (3,119 queries, 42 organizations, 2025)
- Princeton/Georgia Tech GEO paper (KDD 2024)
- BrightLocal local ranking factor analysis
- Google patent US20060218114A1 (location-based search)
- Contextual bandit literature from ad-tech (BayesMAB, ACM CIKM 2024)

---

## 2. System Overview

```
INPUT                  COLLECTION              TRANSFORMATION          SCORING                  OUTPUT
─────                  ──────────              ──────────────          ───────                  ──────
Niche keyword    →     Keyword Expansion   →   Signal Extraction   →  Demand Score          →  Ranked Metro List
Geographic scope →     SERP Collection     →   SERP Parsing        →  Organic Competition   →  Opportunity Scores
                       Keyword Data Pull   →   Competitor Profiling →  Local Competition     →  SERP Archetypes
                       Business Data Pull  →   GBP Analysis        →  Monetization Score    →  AI Resilience Flags
                       Reviews Data Pull   →   Review Analysis     →  AI Resilience Score   →  Guidance Labels
                       Backlink/OnPage     →   Authority Mapping   →  Composite Score       →  Confidence Flags
                                                                      Confidence Level      →  Feedback Log Entry
```

### Processing Phases

| Phase | Name | Input | Output | Latency Target |
|-------|------|-------|--------|----------------|
| 0 | Configuration | User input | Validated params | <1s |
| 1 | Keyword Expansion + Intent Classification | Niche keyword | Expanded keyword set with intent labels | 5-15s (LLM + API) |
| 2 | Data Collection | Keywords + Metros | Raw API responses | 2-8 min (batch queue) |
| 3 | Signal Extraction | Raw responses | Derived signals per metro | <30s (compute) |
| 4 | Scoring | Signals | Scores per metro | <5s (compute) |
| 5 | Classification | Scores + signals | Archetypes + guidance | <5s (compute + LLM) |
| 6 | Feedback Logging | Scores + input context | Logged tuple for future bandit training | <1s |

**Total target: <10 minutes per report.**

---

## 3. Phase 0 — Input Configuration

### 3.1 User Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `niche_keyword` | string | Yes | Primary niche term (e.g., "plumber", "mobile dog grooming") |
| `geo_scope` | enum | Yes | One of: `state`, `region`, `custom` |
| `geo_target` | string/list | Yes | State code (e.g., "CA"), region name (e.g., "Southwest"), or list of MSA codes |
| `report_depth` | enum | No | `standard` (top 20 MSAs in scope) or `deep` (all MSAs in scope). Default: `standard` |
| `strategy_profile` | enum | No | Controls how organic vs. local competition is weighted. See §3.4. Default: `balanced` |

### 3.4 Strategy Profiles

The relative importance of organic rankings vs. local pack (GBP) rankings depends on the practitioner's go-to-market strategy. This parameter tunes the scoring weights across the entire pipeline — composite opportunity score, difficulty tier calculation, and guidance templates.

**Why this matters:** GBP-based competition is fundamentally harder to overcome than organic competition for most rank-and-rent practitioners. A verified Google Business Profile requires a physical address, review generation takes months, and Google actively polices fake listings. Organic ranking via a well-built site is the classic rank-and-rent playbook. The right weight depends on the practitioner's capabilities and the niche's SERP structure.

| Profile | `organic_weight` | `local_weight` | When to use |
|---------|-----------------|----------------|-------------|
| `organic_first` | 0.25 | 0.10 | Classic rank-and-rent: build a site, rank it, rent the leads via tracked phone number. No GBP needed. Best for niches where organic results appear above the local pack or where no local pack exists. |
| `balanced` | 0.15 | 0.20 | Hybrid approach: build a site AND optimize GBP. The practitioner has (or can get) a physical address. Most versatile default. |
| `local_dominant` | 0.05 | 0.35 | GBP-first: practitioner has a verified location and will compete primarily in the local pack. The site is secondary. Best for niches where the local 3-pack dominates the SERP. |
| `auto` | dynamic | dynamic | System detects local pack presence/prominence per metro and adjusts weights automatically. If no local pack exists for the niche, shifts to `organic_first`. If local pack is above-fold, shifts toward `local_dominant`. |

**Weight redistribution:** The organic + local weights always sum to 0.35 (the total "competition" allocation in the composite score). The other components (demand 0.25, monetization 0.20, ai_resilience 0.15, remaining competition 0.05 buffer) stay fixed. This means the practitioner's strategy choice only redistributes emphasis *within* the competition dimension, not across all dimensions.

```python
STRATEGY_PROFILES = {
    "organic_first": {"organic_weight": 0.25, "local_weight": 0.10},
    "balanced":      {"organic_weight": 0.15, "local_weight": 0.20},
    "local_dominant": {"organic_weight": 0.05, "local_weight": 0.35},
}

def resolve_strategy_weights(profile, signals=None):
    """
    Returns (organic_weight, local_weight) for composite scoring.
    For 'auto' profile, dynamically adjusts based on SERP structure.
    """
    if profile != "auto":
        p = STRATEGY_PROFILES[profile]
        return p["organic_weight"], p["local_weight"]
    
    # Auto mode: detect SERP structure per metro
    if signals is None:
        return STRATEGY_PROFILES["balanced"].values()
    
    if not signals.local_pack_present:
        # No local pack — organic is the only game
        return 0.30, 0.05
    
    if signals.local_pack_position <= 3:
        # Local pack is above fold — it dominates user attention
        return 0.08, 0.27
    
    # Local pack exists but is below fold — balanced approach
    return 0.15, 0.20
```

### 3.2 Metro/MSA Resolution

We use the U.S. Census Bureau's CBSA (Core-Based Statistical Area) definitions as our metro unit. Each CBSA maps to a set of principal cities that we use for SERP collection.

**Metro database schema:**

```
metros
├── cbsa_code: string (e.g., "38060" for Phoenix-Mesa-Chandler)
├── cbsa_name: string
├── state: string
├── region: string
├── population: int
├── principal_cities: list[string]  # cities used for SERP geo-targeting
└── dataforseo_location_codes: list[int]  # mapped DFS location codes
```

**City-to-metro aggregation rule:** We pull SERP data at the principal city level (because Google localizes results by city), then aggregate signals up to the metro level. For metros with multiple principal cities (e.g., Dallas-Fort Worth), we average signals across cities, weighted by city population.

### 3.3 Geo Scope Expansion

| Scope | Expansion Logic |
|-------|----------------|
| `state` | All CBSAs with principal city in that state, filtered to top N by population |
| `region` | Predefined region-to-state mapping, then same as state |
| `custom` | User-provided CBSA codes or city names resolved to CBSAs |

For `standard` depth: top 20 MSAs by population within scope.
For `deep` depth: all MSAs with population > 50,000 within scope.

---

## 4. Phase 1 — Keyword Expansion + Intent Classification

### 4.1 Overview

Since niches are open-ended, we cannot rely on curated modifier maps. We use a hybrid approach: LLM-powered expansion validated and enriched by DataForSEO's keyword suggestion endpoints. **V1.1 addition:** Each keyword is now classified by search intent, which determines its weight in demand scoring and its AI resilience profile.

### 4.2 Expansion Pipeline

```
niche_keyword
    │
    ├── Step 1: LLM Expansion (Claude)
    │   Prompt: "Given the local service niche '{niche_keyword}', generate:
    │     a) 3-5 core service terms (the primary things customers search for)
    │     b) 3-5 high-intent modifiers (emergency, 24 hour, affordable, best, near me)
    │     c) 3-5 specific sub-services (the most commonly needed jobs)
    │   For each keyword, classify the search intent as one of:
    │     - transactional: searcher wants to hire/buy NOW (e.g., 'emergency plumber near me')
    │     - commercial: searcher is evaluating options (e.g., 'best plumber in phoenix')
    │     - informational: searcher wants to learn (e.g., 'how to fix a leaky faucet')
    │   Output as JSON. Only include terms a real customer would search.
    │   Do not include business-side terms (franchise, training, certification).
    │   EXCLUDE informational queries — they are vulnerable to AI Overviews
    │   and do not generate leads for rank-and-rent sites."
    │
    ├── Step 2: DataForSEO Keyword Suggestions
    │   Endpoint: /v3/dataforseo_labs/google/keyword_suggestions/live
    │   Input: niche_keyword + top 3 LLM-generated terms
    │   Filter: only keywords with local/transactional intent signals
    │
    ├── Step 3: Merge, Deduplicate, & Intent-Filter
    │   Combine LLM + DFS suggestions
    │   Remove duplicates by normalized form
    │   Remove informational queries (how to, what is, DIY, etc.)
    │   Flag any remaining informational keywords for AIO risk tracking
    │
    └── Step 4: Classify by Tier AND Intent
        Assign each keyword to:
        ├── Tier: Head (1), Service (2), or Long-tail (3)
        └── Intent: transactional, commercial, or informational
```

### 4.3 Keyword Classification Rules

| Tier | Pattern | Example (plumber) | Demand Weight |
|------|---------|-------------------|---------------|
| Head | `{niche}`, `{niche} near me`, `{niche} {city}` | "plumber", "plumber near me" | 40% |
| Service | `{sub-service}`, `{modifier} {niche}` | "drain cleaning", "emergency plumber" | 40% |
| Long-tail | `{problem description}`, `{specific job}` | "water heater leaking", "toilet won't flush" | 20% |

### 4.4 Intent Classification & AI Vulnerability

| Intent | AIO Trigger Rate (Research) | Demand Weight Multiplier | Include in SERP Analysis? |
|--------|---------------------------|-------------------------|--------------------------|
| Transactional | ~2.1% | 1.0x (full value) | Yes |
| Commercial | ~4.3% | 0.9x | Yes |
| Informational | ~43%+ | 0.3x (heavily discounted) | No — exclude from SERP pulls |

**Research basis:** Ahrefs 146M-SERP study found informational queries account for 99.9% of AI Overviews. Transactional queries trigger AIOs only 2.1% of the time.

### 4.5 Expansion Output Schema

```json
{
  "niche": "plumber",
  "expanded_keywords": [
    {
      "keyword": "plumber near me",
      "tier": 1,
      "intent": "transactional",
      "source": "input",
      "aio_risk": "low"
    },
    {
      "keyword": "emergency plumber",
      "tier": 2,
      "intent": "transactional",
      "source": "llm",
      "aio_risk": "low"
    },
    {
      "keyword": "best plumber in phoenix",
      "tier": 2,
      "intent": "commercial",
      "source": "llm",
      "aio_risk": "low"
    },
    {
      "keyword": "how to unclog a drain",
      "tier": 3,
      "intent": "informational",
      "source": "dataforseo_suggestions",
      "aio_risk": "high",
      "note": "excluded from SERP analysis, included only for volume tracking"
    }
  ],
  "total_keywords": 15,
  "actionable_keywords": 12,
  "informational_keywords_excluded": 3,
  "expansion_confidence": "high"
}
```

### 4.6 Confidence Flag

If the LLM and DataForSEO suggestions diverge significantly (< 30% overlap in top terms), flag the expansion as `low_confidence`. This likely means the niche is unusual or the keyword doesn't map cleanly to a local service vertical. The report should include a warning.

---

## 5. Phase 2 — Data Collection

### 5.1 API Call Matrix

For each metro (M) and each keyword in the expanded set (K):

| API | Endpoint | Calls | Queue | Est. Cost/Call |
|-----|----------|-------|-------|----------------|
| SERP (Organic + Local Pack + SERP Features) | `/v3/serp/google/organic/task_post` | M × K_tier1 (head terms only) | Standard | $0.0006 |
| SERP (Maps) | `/v3/serp/google/maps/task_post` | M × 1 (head term only) | Standard | $0.0006 |
| Keyword Volume + CPC | `/v3/keywords_data/google/search_volume/task_post` | ceil(total_keywords / 700) per metro | Standard | $0.05/task |
| Business Listings | `/v3/business_data/business_listings/search/live` | M × 1 (niche category) | Live | $0.01 + $0.0003/row |
| **Google Reviews** | `/v3/business_data/google/reviews/task_post` | M × 3 (top 3 local pack businesses) | Standard | ~$0.005/task |
| **Google My Business Info** | `/v3/business_data/google/my_business_info/live` | M × 5 (top 5 GBP listings) | Live | ~$0.004/task |
| Backlinks Summary | `/v3/backlinks/summary/live` | M × 5 (top 5 organic domains per metro) | Live | ~$0.002 |
| OnPage Lighthouse | `/v3/on_page/lighthouse/task_post` | M × 5 (top 5 organic URLs per metro) | Standard | ~$0.002 |

**V1.1 additions (bolded):** Google Reviews and Google My Business Info endpoints. These provide the review velocity and GBP optimization signals that the Whitespark research identifies as the #1 local ranking factor.

**Important optimization:** SERP collection is only on Tier 1 (head) and Tier 2 (service) keywords with transactional/commercial intent. Informational keywords get volume + CPC data only (for demand breadth tracking) but not SERP analysis. This keeps API costs manageable while focusing SERP analysis on the keywords that actually generate leads.

**SERP Feature Extraction:** DataForSEO's SERP API returns structured SERP feature data including `ai_overview`, `local_pack`, `featured_snippet`, `people_also_ask`, `ads_top`, `local_services_ads`, etc. We now explicitly parse these for the AI Resilience score.

### 5.2 Collection Order & Dependencies

```
Step 1 (parallel):
├── Keyword Volume/CPC for ALL keywords × ALL metros
└── SERP pulls for Tier 1+2 transactional/commercial keywords × ALL principal cities

Step 2 (depends on Step 1 SERP results):
├── Extract top 5 unique domains from each metro's organic SERPs
├── Extract top 3 businesses from each metro's local pack
├── Backlink summary for each unique domain (deduplicated globally)
├── Lighthouse audit for top 5 URLs per metro
├── Google My Business Info for top 5 GBP listings per metro
└── Google Reviews for top 3 local pack businesses per metro

Step 3 (parallel with Step 2):
└── Business Listings for niche category × ALL metros
```

### 5.3 Cost Model (20-metro standard report)

| Layer | Calculation | Cost |
|-------|------------|------|
| SERP Organic | 20 metros × avg 2 cities × 5 keywords (T1+T2) = 200 calls | $0.12 |
| SERP Maps | 20 metros × avg 2 cities × 1 = 40 calls | $0.024 |
| Keyword Volume | 20 metros × 1 task (up to 700 kw) = 20 tasks | $1.00 |
| Business Listings | 20 tasks × ~20 rows avg | $0.32 |
| **Google Reviews** | 20 metros × 3 businesses = 60 tasks | $0.30 |
| **Google My Business Info** | 20 metros × 5 listings = 100 calls | $0.40 |
| Backlinks | ~60 unique domains (deduplicated) | $0.12 |
| Lighthouse | 100 URLs | $0.20 |
| **Total** | | **~$2.48** |

**Deep report (50 metros):** ~$6.20.

**V1.1 cost delta:** +$0.70 per standard report for review + GBP data. At $29-49 price point, margins remain 85-95%.

---

## 6. Phase 3 — Signal Extraction

Raw API responses are transformed into standardized signals per metro. Each signal is a numeric value normalized to a consistent scale.

### 6.1 Demand Signals

| Signal | Source | Derivation | Scale |
|--------|--------|-----------|-------|
| `total_search_volume` | Keyword Volume API | Sum of monthly search volume across all expanded keywords for the metro | Raw count |
| `effective_search_volume` | Derived | Volume adjusted for AIO exposure: `Σ(keyword_volume × intent_weight × (1 - aio_trigger_rate × 0.59))` | Raw count |
| `head_term_volume` | Keyword Volume API | Volume of Tier 1 keywords only | Raw count |
| `volume_breadth` | Keyword Volume API | Count of keywords with volume > 0 / total keywords | 0.0 - 1.0 |
| `avg_cpc` | Keyword Volume API | Weighted average CPC across all keywords (weighted by volume) | USD |
| `max_cpc` | Keyword Volume API | Highest CPC among Tier 1-2 keywords | USD |
| `cpc_volume_product` | Derived | `effective_search_volume × avg_cpc` — proxy for total addressable market value | USD |
| `transactional_ratio` | Derived | % of total volume from transactional intent keywords | 0.0 - 1.0 |

**V1.1 change:** `effective_search_volume` replaces raw `total_search_volume` as the primary demand input. The AIO discount formula is:

```python
def effective_volume(keyword_volume, intent, aio_detected_in_serp):
    """
    Discount volume based on AI Overview exposure.
    Research basis: AIOs reduce organic CTR by ~59% (Seer Interactive, SISTRIX).
    Intent-based AIO rates from Ahrefs 146M SERP study.
    """
    AIO_CTR_REDUCTION = 0.59

    # If we actually detected an AIO in the SERP for this keyword, use that
    if aio_detected_in_serp:
        return keyword_volume * (1 - AIO_CTR_REDUCTION)

    # Otherwise, use intent-based expected AIO rate
    INTENT_AIO_RATES = {
        "transactional": 0.021,
        "commercial": 0.043,
        "informational": 0.436,
    }
    expected_aio_rate = INTENT_AIO_RATES.get(intent, 0.10)
    return keyword_volume * (1 - expected_aio_rate * AIO_CTR_REDUCTION)
```

### 6.2 Organic Competition Signals

These signals measure how hard it is to rank in traditional organic (blue link) results.

| Signal | Source | Derivation | Scale |
|--------|--------|-----------|-------|
| `avg_top5_da` | Backlinks API | Average domain authority of top 5 organic results | 0 - 100 |
| `min_top5_da` | Backlinks API | Lowest DA in top 5 — indicates the "entry point" | 0 - 100 |
| `da_spread` | Derived | `max_top5_da - min_top5_da` — high spread = uneven competition | 0 - 100 |
| `aggregator_count` | SERP parsing | Count of known aggregator domains in top 10 | 0 - 10 |
| `local_biz_count` | SERP parsing | Count of actual local business sites in top 10 | 0 - 10 |
| `avg_lighthouse_performance` | Lighthouse API | Average performance score of top 5 URLs | 0 - 100 |
| `schema_adoption_rate` | Lighthouse/OnPage | % of top 5 URLs with LocalBusiness schema markup | 0.0 - 1.0 |
| `title_keyword_match_rate` | SERP parsing | % of top 10 results with exact niche keyword in title tag | 0.0 - 1.0 |

### 6.3 Local Competition Signals (V1.1 — NEW)

These signals measure how hard it is to rank in the local pack (3-pack) and Google Maps results. **Whitespark 2026 research identifies GBP signals as the #1 driver of local pack visibility and reviews as the single most impactful factor across all local result types.**

| Signal | Source | Derivation | Scale |
|--------|--------|-----------|-------|
| `local_pack_present` | SERP parsing | Does local 3-pack appear in SERP? | 0 or 1 |
| `local_pack_position` | SERP parsing | Where in the SERP does the local pack appear? (above fold = harder) | 1 - 10+ |
| `local_pack_review_count_avg` | Google Reviews API | Average review count of top 3 local pack businesses | Raw count |
| `local_pack_review_count_max` | Google Reviews API | Highest review count in local pack (the "bar to clear") | Raw count |
| `local_pack_rating_avg` | Google Reviews API / SERP Maps | Average star rating in local pack | 1.0 - 5.0 |
| `review_velocity_avg` | Google Reviews API | Average reviews per month for top 3 local pack businesses (computed from review timestamps) | Reviews/month |
| `gbp_completeness_avg` | Google My Business Info API | Average GBP optimization level of top 5 listings. Scoring: has_phone (+1), has_hours (+1), has_website (+1), has_photos (+1), has_description (+1), has_services (+1), has_attributes (+1) = 0-7 scale, normalized to 0-1 | 0.0 - 1.0 |
| `gbp_photo_count_avg` | Google My Business Info API | Average photo count on top 5 GBP listings | Raw count |
| `gbp_posting_activity` | Google My Business Info API | % of top 5 GBPs with recent posts (within 30 days) | 0.0 - 1.0 |
| `citation_consistency` | Business Listings API | For top 3 local pack businesses: NAP (name, address, phone) consistency across listings | 0.0 - 1.0 |

### 6.4 AI Resilience Signals (V1.1 — NEW)

These signals measure how vulnerable this niche+metro is to AI-driven traffic erosion.

| Signal | Source | Derivation | Scale |
|--------|--------|-----------|-------|
| `aio_trigger_rate` | SERP parsing | % of analyzed SERPs that contain an AI Overview feature | 0.0 - 1.0 |
| `featured_snippet_rate` | SERP parsing | % of SERPs with featured snippets (correlated with AIO presence) | 0.0 - 1.0 |
| `transactional_keyword_ratio` | Keyword expansion | % of keywords classified as transactional intent | 0.0 - 1.0 |
| `local_fulfillment_required` | LLM classification | Does this niche require physical presence / in-person service? (binary, set during keyword expansion) | 0 or 1 |
| `paa_density` | SERP parsing | Average count of "People Also Ask" boxes per SERP (high PAA = Google sees the query as informational = AIO risk) | Raw count |

### 6.5 Monetization Signals

| Signal | Source | Derivation | Scale |
|--------|--------|-----------|-------|
| `avg_cpc` | Keyword Volume API | Higher CPC = businesses pay more for leads | USD |
| `business_density` | Business Listings API | Count of businesses in niche category within metro | Raw count |
| `gbp_completeness_avg` | (shared with Local Competition) | High completeness = businesses invest in online presence = more likely to pay for leads | 0.0 - 1.0 |
| `lsa_present` | SERP parsing | Are Google Local Service Ads present in SERP? | 0 or 1 |
| `aggregator_presence` | (shared with Organic Competition) | Aggregators in SERP validate the lead-gen model | 0 - 10 |
| `ads_present` | SERP parsing | Are Google Ads (paid search) present in SERP? | 0 or 1 |

### 6.6 Aggregator Domain List (Maintained)

```python
KNOWN_AGGREGATORS = {
    "yelp.com",
    "homeadvisor.com",
    "angi.com",
    "angieslist.com",
    "thumbtack.com",
    "bbb.org",
    "bark.com",
    "houzz.com",
    "expertise.com",
    "chamberofcommerce.com",
    "mapquest.com",
    "yellowpages.com",
    "superpages.com",
    "manta.com",
    "nextdoor.com",
    "porch.com",
    "networx.com",
    "topratedlocal.com",
    "buildzoom.com",
    "fixr.com",
}

KNOWN_NATIONAL_BRANDS = {
    # Populated per-niche. E.g., for plumbing:
    # "rotorooter.com", "mrplumber.com", "benjaminfranklinplumbing.com"
    # For V1 with open-ended niches: classify as national if
    # domain appears in SERPs for 5+ metros (cross-metro dedup signal)
}
```

### 6.7 Cross-Metro Dedup Signal

When the same domain ranks in 5+ metros, it's almost certainly a national brand or directory — not a local business:

```python
domain_metro_count = {}
for metro in all_metros:
    for result in metro.serp_results:
        domain = extract_domain(result.url)
        domain_metro_count[domain] = domain_metro_count.get(domain, set())
        domain_metro_count[domain].add(metro.cbsa_code)

# Domains appearing in 30%+ of analyzed metros are likely national/directory
DETECTED_NATIONAL = {
    domain for domain, metros in domain_metro_count.items()
    if len(metros) / total_metros >= 0.30
}
```

---

## 7. Phase 4 — Scoring

Each metro receives five sub-scores (up from three in V1), each normalized to 0-100.

### 7.1 Demand Score (0-100)

Measures: Is there enough search demand to justify building a site here?

```python
def demand_score(signals, all_metro_signals):
    # V1.1: Use effective_search_volume (AIO-discounted) instead of raw volume
    volume_percentile = percentile_rank(
        signals.effective_search_volume,
        [m.effective_search_volume for m in all_metro_signals]
    )

    # CPC as value multiplier — high CPC niches get a boost
    cpc_multiplier = min(signals.avg_cpc / MEDIAN_LOCAL_SERVICE_CPC, 2.0)
    # MEDIAN_LOCAL_SERVICE_CPC = $5.00 (calibrated from historical data)

    # Breadth bonus — more keyword variants with volume = more content opportunities
    breadth_bonus = signals.volume_breadth * 15  # max 15 point bonus

    # V1.1: Transactional intent bonus — higher ratio of transactional keywords = better quality demand
    intent_bonus = signals.transactional_ratio * 10  # max 10 point bonus

    raw = (volume_percentile * 0.60 * cpc_multiplier) + (breadth_bonus * 0.20) + (intent_bonus * 0.20)
    return clamp(raw, 0, 100)
```

### 7.2 Organic Competition Score (0-100)

Measures: How easy is it to rank in traditional organic results? **Higher score = LESS competition = better opportunity.**

**V1.1 change:** Reduced weight from 40% of composite to 20%. Organic signals (DA, backlinks) are secondary to local signals for local search rankings per Whitespark research.

```python
def organic_competition_score(signals):
    # Domain authority component — lower DA = easier to compete
    da_score = inverse_scale(signals.avg_top5_da, floor=0, ceiling=60)

    # Local business ratio — more local biz in SERP = beatable competitors
    local_ratio = signals.local_biz_count / 10
    local_score = local_ratio * 100

    # Technical quality — low lighthouse + no schema = weak competitors
    tech_weakness = (
        inverse_scale(signals.avg_lighthouse_performance, 0, 100) * 0.5 +
        (1 - signals.schema_adoption_rate) * 100 * 0.5
    )

    # Title optimization — if competitors aren't targeting the keyword, easy win
    title_weakness = (1 - signals.title_keyword_match_rate) * 100

    # Aggregator saturation penalty
    agg_penalty = signals.aggregator_count * 8

    raw = (
        da_score * 0.35 +
        local_score * 0.20 +
        tech_weakness * 0.20 +
        title_weakness * 0.15 -
        agg_penalty * 0.10
    )
    return clamp(raw, 0, 100)
```

### 7.3 Local Competition Score (0-100) — V1.1 NEW

Measures: How easy is it to rank in the local pack and Google Maps? **Higher score = LESS competition = better opportunity.**

**This is the most important competition signal for rank-and-rent.** The Whitespark 2026 survey ranks GBP signals as #1 and reviews as the single most impactful factor.

```python
def local_competition_score(signals):
    # Review barrier — how many reviews do incumbents have?
    # < 20 avg reviews: very weak (score 80-100)
    # 20-50: weak (score 50-80)
    # 50-150: moderate (score 20-50)
    # 150+: strong (score 0-20)
    review_barrier = inverse_scale(signals.local_pack_review_count_avg, floor=0, ceiling=200)

    # Review velocity — how fast are incumbents accumulating reviews?
    # < 2/month: stagnant (score 80-100) — easy to catch up
    # 2-5/month: moderate (score 40-80)
    # 5-15/month: active (score 10-40)
    # 15+/month: aggressive (score 0-10) — very hard to compete
    velocity_score = inverse_scale(signals.review_velocity_avg, floor=0, ceiling=20)

    # GBP optimization level — how well are incumbents managing their profiles?
    gbp_weakness = (1 - signals.gbp_completeness_avg) * 100

    # Photo engagement — GBP listings with many photos signal investment
    photo_weakness = inverse_scale(signals.gbp_photo_count_avg, floor=0, ceiling=50)

    # Posting activity — active GBPs are harder to displace
    posting_weakness = (1 - signals.gbp_posting_activity) * 100

    # Local pack presence — if no local pack shows, organic-only play (different strategy)
    if not signals.local_pack_present:
        # No local pack = local competition is effectively zero
        # but also means the GBP opportunity is limited
        return 75  # default to "moderate-easy" — organic competition score will govern

    raw = (
        review_barrier * 0.30 +
        velocity_score * 0.25 +
        gbp_weakness * 0.20 +
        photo_weakness * 0.10 +
        posting_weakness * 0.15
    )
    return clamp(raw, 0, 100)
```

### 7.4 Monetization Score (0-100)

Measures: If you rank, can you actually make money?

```python
def monetization_score(signals):
    # CPC as lead value proxy
    cpc_score = scale(signals.avg_cpc, floor=1.0, ceiling=30.0)

    # Business density — enough businesses to rent leads to?
    density_score = scale(signals.business_density, floor=5, ceiling=100)

    # Active market signals — LSA, ads, aggregators = businesses spending on leads
    active_market = (
        signals.lsa_present * 30 +
        signals.ads_present * 20 +
        min(signals.aggregator_presence, 3) * 10  # cap at 3, diminishing returns
    )

    # GBP engagement — high completeness = businesses invest in online, more likely to pay
    gbp_score = signals.gbp_completeness_avg * 100

    raw = (
        cpc_score * 0.35 +
        density_score * 0.25 +
        active_market * 0.25 +  # already 0-80 scale, needs normalization
        gbp_score * 0.15
    )
    return clamp(raw, 0, 100)
```

### 7.5 AI Resilience Score (0-100) — V1.1 NEW

Measures: How protected is this niche from AI-driven traffic erosion? **Higher score = MORE resilient = better long-term opportunity.**

**Research basis:** Local/visit-in-person queries trigger AI Overviews only 7.1-7.9% of the time (Ahrefs, 146M SERPs). AIOs reduce organic CTR by 59% (Seer Interactive). This score quantifies how much of the opportunity is "AI-proof."

```python
def ai_resilience_score(signals):
    # AIO exposure — lower trigger rate = more resilient
    # Local services typically 5-10%, so we score this generously
    aio_safety = inverse_scale(signals.aio_trigger_rate, floor=0, ceiling=0.50)
    # 0% AIO = score 100, 50%+ AIO = score 0

    # Transactional intent ratio — higher = more resilient
    intent_safety = signals.transactional_keyword_ratio * 100

    # Local fulfillment requirement — physical services can't be replaced by AI
    fulfillment_bonus = signals.local_fulfillment_required * 20

    # PAA density as risk indicator — high PAA suggests Google sees query as informational
    paa_risk = inverse_scale(signals.paa_density, floor=0, ceiling=8)

    raw = (
        aio_safety * 0.40 +
        intent_safety * 0.25 +
        fulfillment_bonus * 0.15 +  # already 0-20 scale, effective weight ~3pts
        paa_risk * 0.20
    )
    return clamp(raw, 0, 100)
```

### 7.6 Composite Opportunity Score (0-100)

**V1.1 change:** Now incorporates five components. Organic vs. local competition weights are **configurable via strategy_profile** (see §3.4), reflecting different practitioner approaches. All other weights are fixed.

```python
def opportunity_score(demand, organic_comp, local_comp, monetization, ai_resilience,
                      strategy_profile="balanced", signals=None):
    """
    Weight structure:
    - Demand:           0.25 (fixed)
    - Competition:      0.35 total (split between organic + local per strategy_profile)
    - Monetization:     0.20 (fixed)
    - AI Resilience:    0.15 (fixed)
    - Buffer:           0.05 (assigned to whichever competition dimension the profile favors)
    
    Strategy profiles redistribute ONLY the competition allocation:
      organic_first:  organic=0.25, local=0.10
      balanced:       organic=0.15, local=0.20
      local_dominant: organic=0.05, local=0.35
      auto:           dynamic based on SERP structure per metro
    """
    org_w, loc_w = resolve_strategy_weights(strategy_profile, signals)
    
    raw = (
        demand * 0.25 +
        organic_comp * org_w +
        local_comp * loc_w +
        monetization * 0.20 +
        ai_resilience * 0.15
    )

    # Apply minimum threshold gates:
    # If ANY component is below 15, cap the composite at 40
    all_scores = [demand, organic_comp, local_comp, monetization, ai_resilience]
    if min(all_scores) < 5:
        raw = min(raw, 20)
    elif min(all_scores) < 15:
        raw = min(raw, 40)

    # V1.1: AI resilience hard floor — if AIO trigger rate > 40%, cap at 50
    # regardless of other scores (the niche is structurally at risk)
    if ai_resilience < 20:
        raw = min(raw, 50)

    return clamp(raw, 0, 100)
```

### 7.7 Confidence Score

```python
def confidence_score(metro, expansion):
    penalties = []

    # Keyword expansion quality
    if expansion.expansion_confidence == "low":
        penalties.append(("keyword_expansion_uncertain", -20))

    # Data completeness
    if metro.lighthouse_results_count < 3:
        penalties.append(("incomplete_onpage_data", -10))
    if metro.backlink_results_count < 3:
        penalties.append(("incomplete_backlink_data", -10))
    if metro.serp_results_count == 0:
        penalties.append(("no_serp_data", -40))
    # V1.1: Review data completeness
    if metro.review_results_count < 2:
        penalties.append(("incomplete_review_data", -10))
    if metro.gbp_results_count < 3:
        penalties.append(("incomplete_gbp_data", -10))

    # Low volume warning
    if metro.total_search_volume < 50:
        penalties.append(("very_low_volume", -15))

    # V1.1: High AIO exposure warning
    if metro.aio_trigger_rate > 0.30:
        penalties.append(("high_aio_exposure", -10))

    base = 100
    for _, penalty in penalties:
        base += penalty

    return clamp(base, 0, 100), penalties
```

---

## 8. Phase 5 — Classification

### 8.1 SERP Archetype Classification

**V1.1 change:** Archetypes now incorporate local pack strength as a primary dimension, reflecting Whitespark research on GBP signal dominance.

```python
def classify_serp_archetype(signals):
    agg_ratio = signals.aggregator_count / 10
    local_ratio = signals.local_biz_count / 10
    has_pack = signals.local_pack_present

    if agg_ratio >= 0.5:
        return "AGGREGATOR_DOMINATED"
        # Yelp, HomeAdvisor, etc. own the SERP
        # Strategy: target long-tail keywords, avoid head terms

    elif has_pack and signals.local_pack_review_count_avg > 100 and signals.review_velocity_avg > 5:
        return "LOCAL_PACK_FORTIFIED"
        # Strong local pack with established, actively-reviewed businesses
        # Strategy: Long-term GBP build needed, consider adjacent sub-niches

    elif has_pack and signals.local_pack_review_count_avg > 30:
        return "LOCAL_PACK_ESTABLISHED"
        # Local pack exists with moderate-strength businesses
        # Strategy: GBP-first approach, review generation campaign, 4-8 month timeline

    elif has_pack and signals.local_pack_review_count_avg <= 30:
        return "LOCAL_PACK_VULNERABLE"
        # Local pack exists but businesses are weak
        # Strategy: GBP + site combo, fastest path to leads, 2-4 months

    elif local_ratio >= 0.4 and signals.avg_top5_da < 25:
        return "FRAGMENTED_WEAK"
        # Lots of local sites but all low quality
        # Strategy: classic rank-and-rent, quality site wins

    elif local_ratio >= 0.4 and signals.avg_top5_da >= 25:
        return "FRAGMENTED_COMPETITIVE"
        # Local sites with real authority
        # Strategy: needs link building investment, longer timeline

    elif local_ratio < 0.3 and agg_ratio < 0.3:
        return "BARREN"
        # Nobody is really competing for this SERP
        # Strategy: low-hanging fruit IF demand exists

    else:
        return "MIXED"
        # No dominant pattern
        # Strategy: analyze specific gaps in SERP
```

### 8.2 AI Exposure Classification (V1.1 — NEW)

Orthogonal to SERP archetype — classifies the niche's vulnerability to AI search disruption.

```python
def classify_ai_exposure(signals):
    if signals.aio_trigger_rate < 0.05:
        return "AI_SHIELDED"
        # Almost no AI Overviews — typical for local service queries
        # Long-term organic viability is strong

    elif signals.aio_trigger_rate < 0.15:
        return "AI_MINIMAL"
        # Some AIO exposure but within normal range for local search
        # No material impact on opportunity

    elif signals.aio_trigger_rate < 0.30:
        return "AI_MODERATE"
        # Meaningful AIO presence — likely some informational keywords in the mix
        # Demand score already discounted, but flag for user awareness

    else:
        return "AI_EXPOSED"
        # High AIO trigger rate — unusual for local services
        # Likely an informational-heavy niche or poor keyword targeting
        # Flag prominently in report
```

### 8.3 Difficulty Tier

**Scoring direction:** M7 competition scores use inverse scaling — higher scores indicate *weaker* competition (easier to rank). The `combined_comp` value inherits this direction, so a high value means the competitive landscape is favorable. Thresholds map directly: high combined score → easy tier, low combined score → very hard tier.

```python
def difficulty_tier(organic_comp, local_comp, strategy_profile="balanced", signals=None):
    # Use the same strategy profile weights as the composite score
    # so difficulty and opportunity are internally consistent.
    # organic_comp and local_comp are M7 scores where higher = weaker competition.
    org_w, loc_w = resolve_strategy_weights(strategy_profile, signals)
    total_comp_weight = org_w + loc_w

    # Normalize to proportional blend
    org_proportion = org_w / total_comp_weight
    loc_proportion = loc_w / total_comp_weight

    combined_comp = (local_comp * loc_proportion) + (organic_comp * org_proportion)

    if combined_comp >= 70:
        return "EASY"       # Weak competition — rank within 2-4 months
    elif combined_comp >= 45:
        return "MODERATE"   # Moderate competition — expect 4-8 months
    elif combined_comp >= 25:
        return "HARD"       # Strong competition — 8-12+ months, link building needed
    else:
        return "VERY_HARD"  # Very strong competition — not recommended without existing authority
```

### 8.4 Guidance Generation

**V1.1 change:** Guidance now incorporates GBP/review-specific actions and AI resilience context.

```python
GUIDANCE_TEMPLATES = {
    ("LOCAL_PACK_VULNERABLE", "EASY"): {
        "headline": "Strong opportunity — weak local pack with low review barriers",
        "strategy": "The local pack in {metro} for '{niche}' has businesses averaging only "
                    "{review_count_avg} reviews with {gbp_completeness_pct}% GBP optimization. "
                    "A well-optimized Google Business Profile with a targeted review generation "
                    "strategy should enter the local pack within 2-4 months.",
        "priority_actions": [
            "Set up and fully optimize Google Business Profile (all 7 completeness signals)",
            "Build a site with proper LocalBusiness schema targeting '{niche} in {metro}'",
            "Launch review generation — target 5+ reviews/month to overtake incumbents at {velocity_avg}/month",
            "Create service pages for top sub-services: {top_services}",
            "Get 10-15 citations on major directories for NAP consistency"
        ],
        "ai_resilience_note": None  # omit if AI_SHIELDED or AI_MINIMAL
    },
    ("AGGREGATOR_DOMINATED", "HARD"): {
        "headline": "Validated market, but directories dominate head terms",
        "strategy": "The presence of {agg_count} directories in the top 10 confirms "
                    "businesses pay for leads in '{niche}'. Target long-tail and "
                    "service-specific keywords that aggregators don't optimize for. "
                    "Focus GBP strategy on the local pack, which aggregators can't own.",
        "priority_actions": [
            "Target long-tail keywords: {longtail_examples}",
            "Build a GBP-first strategy — the local pack is your entry point, not organic",
            "Develop deep service pages that outclass thin directory listings",
            "Consider Google LSA as a parallel lead source (validates paid lead economics)"
        ],
        "ai_resilience_note": None
    },
    # ... templates for each archetype × difficulty combination
    # Add ai_resilience_note when classification is AI_MODERATE or AI_EXPOSED:
    # "ai_resilience_note": "Note: {aio_pct}% of keywords in this niche trigger AI Overviews, "
    #     "which can reduce organic click-through rates. Focus on transactional keywords "
    #     "and local pack visibility, which are largely unaffected by AI summaries."
}
```

---

## 9. Phase 6 — Feedback Logging (V1.1 — NEW)

### 9.1 Purpose

Every report generation creates a logged tuple for future contextual bandit optimization. Even in V1 where we don't use this data for scoring, we capture it so that when we have enough observations (target: 500+), we can train a recommendation model that learns from real outcomes.

### 9.2 Feedback Log Schema

```json
{
  "log_id": "uuid",
  "timestamp": "2026-04-03T12:00:00Z",

  "context": {
    "niche_keyword": "plumber",
    "cbsa_code": "38060",
    "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
    "population": 4946145,
    "keyword_count": 15,
    "expansion_confidence": "high",
    "strategy_profile": "balanced",
    "resolved_organic_weight": 0.15,
    "resolved_local_weight": 0.20
  },

  "signals": {
    "effective_search_volume": 10850,
    "avg_cpc": 18.50,
    "avg_top5_da": 22,
    "local_pack_review_count_avg": 35,
    "review_velocity_avg": 3.2,
    "gbp_completeness_avg": 0.57,
    "aio_trigger_rate": 0.04,
    "transactional_ratio": 0.73,
    "business_density": 450,
    "lsa_present": true
  },

  "scores": {
    "demand": 72,
    "organic_competition": 65,
    "local_competition": 58,
    "monetization": 81,
    "ai_resilience": 92,
    "opportunity": 71,
    "confidence": 95
  },

  "classification": {
    "serp_archetype": "FRAGMENTED_WEAK",
    "ai_exposure": "AI_SHIELDED",
    "difficulty_tier": "MODERATE"
  },

  "recommendation_rank": 3,

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

### 9.3 Outcome Collection

Outcomes are collected through optional user reporting:
- **Implicit:** Did the user generate another report for the same niche? (signal of continued interest)
- **Explicit (V2):** In-app prompts at 30/60/90/180 days after report: "Did you build a site for {niche} in {metro}? How's it going?"
- **Integrated (V3/Sonar):** If we build rank tracking, we can automatically detect when a user's site enters the SERP for recommended keywords

### 9.4 Future Bandit Architecture

When sufficient outcome data exists (target: 500+ tuples with non-null outcomes):

```python
# Conceptual — not for V1 implementation
class NicheRecommendationBandit:
    """
    Contextual bandit for niche recommendation.
    Arms: niche+metro combinations
    Context: market signals (volume, CPC, competition, etc.)
    Reward: composite of ranking_velocity + lead_volume + user_satisfaction

    Uses LinUCB or Thompson Sampling with delayed feedback.
    Batched updates weekly from accumulated outcome data.
    """

    def recommend(self, context_features, candidate_niches):
        """
        Returns ranked list of niches, balancing:
        - Exploitation: recommend niches similar to past successes
        - Exploration: occasionally recommend under-explored niches to learn
        """
        pass

    def update(self, context, action, reward):
        """
        Called when outcome data arrives (delayed by weeks/months).
        Updates model weights.
        """
        pass
```

**Research basis:** BayesMAB (ACM CIKM 2024, Tencent) achieved 13% CPM decrease and 12.3% ROI increase using Bayesian multi-armed bandits for bid optimization. The same delayed-reward, batch-update framework applies directly to niche recommendation.

---

## 10. Output Schema

### 10.1 Report Output (Full)

```json
{
  "report_id": "uuid",
  "generated_at": "2026-04-03T12:00:00Z",
  "spec_version": "1.1",
  "input": {
    "niche_keyword": "plumber",
    "geo_scope": "state",
    "geo_target": "AZ",
    "report_depth": "standard",
    "strategy_profile": "balanced",
    "resolved_weights": {
      "demand": 0.25,
      "organic_competition": 0.15,
      "local_competition": 0.20,
      "monetization": 0.20,
      "ai_resilience": 0.15,
      "note": "Weights reflect 'balanced' strategy profile. Organic + local sum to 0.35."
    }
  },
  "keyword_expansion": {
    "total_keywords": 15,
    "actionable_keywords": 12,
    "informational_excluded": 3,
    "tier_1": [
      {"keyword": "plumber", "intent": "transactional"},
      {"keyword": "plumber near me", "intent": "transactional"},
      {"keyword": "plumbing services", "intent": "commercial"}
    ],
    "tier_2": [
      {"keyword": "emergency plumber", "intent": "transactional"},
      {"keyword": "drain cleaning", "intent": "transactional"},
      {"keyword": "water heater repair", "intent": "transactional"},
      {"keyword": "sewer line repair", "intent": "transactional"},
      {"keyword": "leak detection", "intent": "commercial"}
    ],
    "tier_3": [
      {"keyword": "toilet won't flush", "intent": "transactional"},
      {"keyword": "kitchen sink clogged", "intent": "transactional"},
      {"keyword": "water heater leaking", "intent": "transactional"},
      {"keyword": "pipe burst", "intent": "transactional"}
    ],
    "excluded_informational": [
      {"keyword": "how to unclog a drain", "intent": "informational", "aio_risk": "high"},
      {"keyword": "how to fix a leaky faucet", "intent": "informational", "aio_risk": "high"},
      {"keyword": "plumbing cost estimate", "intent": "informational", "aio_risk": "moderate"}
    ],
    "expansion_confidence": "high"
  },
  "metros": [
    {
      "cbsa_code": "38060",
      "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
      "population": 4946145,
      "scores": {
        "demand": 72,
        "organic_competition": 65,
        "local_competition": 58,
        "monetization": 81,
        "ai_resilience": 92,
        "opportunity": 71
      },
      "confidence": {
        "score": 95,
        "flags": []
      },
      "serp_archetype": "LOCAL_PACK_VULNERABLE",
      "ai_exposure": "AI_SHIELDED",
      "difficulty_tier": "MODERATE",
      "signals": {
        "effective_search_volume": 10850,
        "raw_search_volume": 12400,
        "aio_volume_discount": 1550,
        "avg_cpc": 18.50,
        "transactional_ratio": 0.73,
        "avg_top5_da": 22,
        "local_biz_count": 4,
        "aggregator_count": 3,
        "local_pack_present": true,
        "local_pack_review_count_avg": 35,
        "local_pack_review_count_max": 89,
        "review_velocity_avg": 3.2,
        "local_pack_rating_avg": 4.3,
        "gbp_completeness_avg": 0.57,
        "gbp_photo_count_avg": 12,
        "gbp_posting_activity": 0.20,
        "aio_trigger_rate": 0.04,
        "lsa_present": true,
        "business_density": 450,
        "schema_adoption_rate": 0.20,
        "avg_lighthouse_performance": 45
      },
      "guidance": {
        "headline": "Strong opportunity — weak local pack with low review barriers",
        "strategy": "...",
        "priority_actions": ["...", "..."],
        "estimated_time_to_rank": "4-6 months",
        "ai_resilience_note": null
      }
    }
  ],
  "meta": {
    "total_api_calls": 482,
    "total_cost_usd": 2.48,
    "processing_time_seconds": 485,
    "feedback_log_id": "uuid-ref"
  }
}
```

---

## 11. Utility Functions

### 11.1 Normalization Functions

```python
def scale(value, floor, ceiling):
    """Linear scale from floor-ceiling to 0-100"""
    if value <= floor:
        return 0
    if value >= ceiling:
        return 100
    return ((value - floor) / (ceiling - floor)) * 100

def inverse_scale(value, floor, ceiling):
    """Inverse linear scale — higher value = lower score"""
    return 100 - scale(value, floor, ceiling)

def percentile_rank(value, all_values):
    """Percentile rank within a distribution, returned as 0-100"""
    sorted_vals = sorted(all_values)
    rank = sum(1 for v in sorted_vals if v < value)
    return (rank / len(sorted_vals)) * 100

def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))
```

### 11.2 Domain Extraction

```python
from urllib.parse import urlparse

def extract_domain(url):
    """Extract registrable domain from URL"""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname
```

### 11.3 Review Velocity Calculation

```python
from datetime import datetime, timedelta

def calculate_review_velocity(reviews, lookback_months=6):
    """
    Calculate average reviews per month over the lookback period.
    Uses review timestamps from Google Reviews API.
    """
    cutoff = datetime.now() - timedelta(days=lookback_months * 30)
    recent_reviews = [r for r in reviews if r.timestamp >= cutoff]
    if lookback_months == 0:
        return 0
    return len(recent_reviews) / lookback_months
```

### 11.4 GBP Completeness Scoring

```python
def gbp_completeness(gbp_info):
    """
    Score GBP optimization level on a 0-1 scale.
    Based on Whitespark's identified GBP ranking signals.
    """
    signals = [
        bool(gbp_info.get("phone")),           # has phone number
        bool(gbp_info.get("work_hours")),       # has business hours
        bool(gbp_info.get("domain")),           # has website
        bool(gbp_info.get("description")),      # has business description
        len(gbp_info.get("images", [])) >= 3,   # has 3+ photos
        bool(gbp_info.get("category")),         # has primary category set
        bool(gbp_info.get("attributes", [])),   # has service attributes
    ]
    return sum(signals) / len(signals)
```

---

## 12. Testing & Validation Framework

### 12.1 Unit Tests

| Test | Input | Expected |
|------|-------|----------|
| Keyword expansion produces Tier 1 terms | "plumber" | Contains "plumber near me" |
| Intent classification: transactional | "emergency plumber near me" | intent = "transactional" |
| Intent classification: informational | "how to fix a leaky faucet" | intent = "informational", excluded from SERP |
| AIO volume discount | volume=1000, intent=transactional | effective ≈ 988 (1000 × (1 - 0.021 × 0.59)) |
| AIO volume discount | volume=1000, intent=informational | effective ≈ 743 (1000 × (1 - 0.436 × 0.59)) |
| Aggregator detection | SERP with yelp.com at #1 | `aggregator_count >= 1` |
| Cross-metro dedup | Same domain in 10/20 metros | Domain in `DETECTED_NATIONAL` |
| Review velocity calculation | 12 reviews in 6 months | velocity = 2.0 reviews/month |
| GBP completeness: full | All 7 signals present | score = 1.0 |
| GBP completeness: minimal | Only phone + category | score = 0.29 |
| Confidence penalty: missing review data | Metro with 0 review results | Confidence ≤ 90 |
| Confidence penalty: high AIO | aio_trigger_rate = 0.35 | Confidence ≤ 90 |
| Opportunity cap: weak component | Any score < 5 | Opportunity ≤ 20 |
| AI resilience hard floor | ai_resilience < 20 | Opportunity ≤ 50 |
| Feedback log created | Any report generation | Non-null log_id in meta |

### 12.2 Integration Tests (Known Markets)

| Test Case | Niche | Metro | Expected Outcome |
|-----------|-------|-------|------------------|
| Known easy market | "plumber" | Small city with weak SERPs | Opportunity > 70, Difficulty EASY |
| Known hard market | "plumber" | NYC/LA | Opportunity < 40, Difficulty HARD/VERY_HARD |
| Known aggregator market | "lawyer" | Any major metro | Archetype = AGGREGATOR_DOMINATED |
| Niche niche | "septic tank pumping" | Rural MSA | Low volume but low competition |
| AI-exposed niche | "how to" heavy niche | Any metro | AI exposure = AI_MODERATE or AI_EXPOSED |
| Review fortress | Niche with 200+ review incumbents | Major metro | Local competition score < 30 |
| GBP desert | Niche with incomplete GBP profiles | Smaller metro | Local competition score > 70 |

### 12.3 Scoring Calibration

The biggest risk with this algo is miscalibrated weights. Initial weights are research-informed but still hypotheses. To calibrate:

1. **Generate 50+ scored reports** across diverse niches and metros
2. **Have Luke's community review 10-15 reports** against their own market knowledge
3. **Specific calibration questions:**
   - Does the local competition score match practitioners' intuitive assessment of difficulty?
   - Does the AI resilience score identify any false positives (niches flagged as risky that practitioners know are safe)?
   - Does the organic vs. local competition weight (10/30) feel right, or should organic get more credit?
4. **Adjust weights** based on feedback
5. **Track prediction accuracy** as outcomes accumulate in the feedback log

### 12.4 Scoring Sensitivity Analysis

For each scoring function, test the impact of ±20% weight changes on the final ranking order. If small weight changes cause large rank changes, the scoring is too sensitive and needs more robust normalization.

### 12.5 AI Resilience Validation

Specific validation for the new AI resilience score:
1. Pull SERPs for 100 known local service keywords and verify AIO trigger rates match Ahrefs research (expect <10% for local services)
2. Pull SERPs for 100 known informational keywords and verify rates are 30%+ (control group)
3. Re-run quarterly as Google expands/contracts AIO deployment — the `INTENT_AIO_RATES` constants may need updating

---

## 13. Known Limitations & Future Work

### V1.1 Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| No temporal data | Can't detect trends (growing/declining niches) | Add SERP history tracking in V2 |
| LLM keyword expansion is non-deterministic | Same niche may produce different keywords on re-run | Cache expansions per niche, use temperature=0 |
| No backlink depth analysis | DA alone doesn't capture link quality | Add referring domain diversity in V1.2 |
| Single-point-in-time SERP snapshot | SERP volatility not captured | Track SERPs weekly in V2 for trend data |
| Population-weighted city aggregation may mask suburb opportunities | A suburb could be easy while the core city is hard | Add city-level drill-down in V1.2 |
| Open-ended niches have no calibrated baselines | Scoring is relative within a single report | Build niche-specific calibration tables as data accumulates |
| AIO trigger rates are based on aggregate research | Per-niche rates may vary | Validate with actual SERP feature data per report |
| Review velocity requires timestamp data | DataForSEO review timestamps may have gaps | Fall back to review count / account age as proxy |
| GBP completeness scoring is heuristic | Not all 7 signals are equally weighted by Google | Refine weights via practitioner feedback |
| Feedback loop requires outcome data we don't have yet | Bandit optimization is future-state | Logging schema is in place from day one |

### Future Enhancements (Prioritized)

1. **Temporal SERP tracking** — Weekly snapshots to detect competition trends and SERP volatility
2. **Niche-specific keyword modifier maps** — As data accumulates, replace LLM expansion with curated + LLM hybrid for top niches
3. **Lead value estimation** — Partner with call tracking providers to get actual lead-to-close data
4. **User feedback loop activation** — When 500+ outcome tuples exist, train contextual bandit model
5. **Cross-niche comparison** — "Plumber in Phoenix vs. electrician in Phoenix" on the same scale
6. **GEO optimization signals** — Track visibility in ChatGPT/Perplexity/Gemini for local queries (12% of LLM-cited URLs rank in Google top 10, per research)
7. **Strategy breakout product** — Detailed competitive playbook for a specific niche+metro (different buyer persona)
8. **AI Overview monitoring** — Track AIO trigger rate changes per niche over time as Google expands/contracts deployment
9. **Conversion quality layer** — LLM-referred traffic converts 3-5x higher; build this into lead value modeling when data available

---

## 14. DataForSEO API Reference (Quick Ref)

### Authentication
```
Base URL: https://api.dataforseo.com/v3/
Auth: HTTP Basic (login:password from app.dataforseo.com)
Rate limit: 2000 calls/minute
```

### Key Endpoints Used

| Purpose | Endpoint | Method | V1.1 Status |
|---------|----------|--------|-------------|
| Google Organic SERP + SERP Features | `/serp/google/organic/task_post` + `/task_get` | Standard Queue | Core |
| Google Maps SERP | `/serp/google/maps/task_post` + `/task_get` | Standard Queue | Core |
| Keyword Volume + CPC | `/keywords_data/google/search_volume/task_post` + `/task_get` | Standard Queue | Core |
| Keyword Suggestions | `/dataforseo_labs/google/keyword_suggestions/live` | Live | Core |
| Business Listings | `/business_data/business_listings/search/live` | Live | Core |
| **Google My Business Info** | `/business_data/google/my_business_info/live` | Live | **V1.1 New** |
| **Google Reviews** | `/business_data/google/reviews/task_post` + `/task_get` | Standard Queue | **V1.1 New** |
| Backlinks Summary | `/backlinks/summary/live` | Live | Core |
| OnPage Lighthouse | `/on_page/lighthouse/task_post` + `/task_get` | Standard Queue | Core |

### SERP Feature Keys to Parse

DataForSEO returns SERP features in a structured array. The following keys are critical for V1.1:

```python
SERP_FEATURES_TO_TRACK = {
    "ai_overview": "aio_present",           # AI Overview / SGE box
    "local_pack": "local_pack_present",     # Local 3-pack
    "featured_snippet": "snippet_present",  # Featured snippet
    "people_also_ask": "paa_present",       # People Also Ask
    "top_stories": "news_present",          # Top Stories
    "ads_top": "ads_top_present",           # Google Ads above organic
    "local_services_ads": "lsa_present",    # Local Service Ads (Google Guaranteed)
    "knowledge_panel": "kp_present",        # Knowledge panel
}
```

### Queue Modes
- **Standard Queue**: POST task → poll/GET results (up to 5 min). Cheapest.
- **Priority Queue**: POST task → poll/GET results (up to 1 min). 2x cost.
- **Live Mode**: POST → instant response. 3.3x cost.

Use Standard Queue for SERP, Keywords, Reviews, Lighthouse. Use Live for Business Listings, GMB Info, Backlinks (per-metro requests where latency matters less than cost).

---

## 15. Appendix: MSA/CBSA Data Source

Use Census Bureau CBSA delineation files: https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html

Map each CBSA to DataForSEO location codes via their location database endpoint:
`/v3/serp/google/locations`

Pre-build and cache this mapping. It changes rarely (Census updates every ~2 years).

---

## 16. Appendix: Research Constants

These constants are derived from research and should be periodically validated:

```python
# AIO Impact Constants
AIO_CTR_REDUCTION = 0.59          # Source: Seer Interactive (2025), SISTRIX
INTENT_AIO_RATES = {
    "transactional": 0.021,       # Source: Ahrefs 146M SERP study
    "commercial": 0.043,          # Source: Ahrefs 146M SERP study
    "informational": 0.436,       # Source: Ahrefs 146M SERP study
}
LOCAL_QUERY_AIO_RATE = 0.079      # Source: Ahrefs — local/visit-in-person queries

# Scoring Calibration Constants
MEDIAN_LOCAL_SERVICE_CPC = 5.00   # To be calibrated from first 50 reports

# Composite Score Weights (fixed components)
FIXED_WEIGHTS = {
    "demand": 0.25,
    "monetization": 0.20,
    "ai_resilience": 0.15,
    # competition total = 0.35, split per strategy_profile (see §3.4)
    # buffer = 0.05, allocated within competition split
}

# Strategy Profile Weights (configurable — organic + local must sum to 0.35)
STRATEGY_PROFILES = {
    "organic_first":  {"organic_weight": 0.25, "local_weight": 0.10},
    "balanced":       {"organic_weight": 0.15, "local_weight": 0.20},
    "local_dominant": {"organic_weight": 0.05, "local_weight": 0.35},
    # "auto": dynamic, see resolve_strategy_weights() in §3.4
}

# Validation Schedule
# Re-validate AIO rates quarterly (Google is actively changing deployment)
# Re-validate CPC median after first 100 reports
# Re-validate competition weights after first practitioner feedback cycle
# Re-validate strategy profile defaults after Luke's community provides feedback
```