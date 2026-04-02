# System Design: Autonomous Geo × Industry Niche Viability Research Engine

**Version:** 0.1 — Draft
**Date:** 2026-03-29
**Author:** Kael × Antwoine
**Status:** Design Review

---

## 1. Problem Statement

We want to systematically identify viable niche opportunities across combinations of geographic markets (cities) and industry verticals. The research process — keyword discovery, SERP competition analysis, viability scoring — is mechanical enough to automate but large enough (potentially 1,000+ combinations) that doing it manually is not practical. The goal is a system that runs autonomously, respects API rate limits, stores all results durably, and surfaces ranked opportunities in a reviewable format.

---

## 2. Requirements

### 2.1 Functional Requirements

- Accept a configurable city list (N metros) and industry list (M verticals) as input
- Generate and manage the full N × M combination matrix
- For each combination:
  - Discover seed keywords using Ahrefs (matching terms, related terms)
  - Pull keyword metrics: monthly volume, Keyword Difficulty (KD), CPC, trend direction
  - Pull geo-constrained SERP data via SerpAPI (competitor DR, SERP features, rankings)
  - Compute a composite viability score
- Store all raw data and scores durably for reproducibility and re-analysis
- Output ranked results as an HTML dashboard, CSV, and Databricks notebook

### 2.2 Non-Functional Requirements

| Requirement | Target |
|---|---|
| Resumability | If a run fails at combo 400/1000, restart from combo 401 — not from scratch |
| Rate limit compliance | Never exceed Ahrefs or SerpAPI plan limits |
| Cost efficiency | Cache results; skip re-fetching combos completed within 30 days |
| Parallelism | Configurable concurrency (default: 5 parallel workers) |
| Auditability | Every score traceable to the raw keyword and SERP data that produced it |
| Latency | Full 1,000-combo run completes within 24 hours on a paid SerpAPI plan |

### 2.3 Constraints

- Python as the primary implementation language
- Databricks for production data infrastructure (Delta Lake)
- SQLite for local dev/testing (zero setup)
- No NeMo — see framework decision below
- SerpAPI requires a paid plan for meaningful scale (see rate limit section)

---

## 3. Framework Decision: Orchestration

### What was considered

**NVIDIA NeMo** — Not the right tool. NeMo is a toolkit for training, fine-tuning, and serving large language models. It has no relevance to API pipeline orchestration. If the reference was to NeMo Guardrails specifically, that is a safety/control layer for LLM applications — useful as an optional guardrails wrapper on Claude-driven decisions, but not an orchestration framework.

**LangGraph** — Good choice if adaptive agent behavior is required (e.g., Claude dynamically deciding to expand keyword seeds on a promising combo mid-run). Adds complexity and non-determinism. Right call for V2.

**Temporal** — Enterprise-grade durable workflow execution. Excellent resumability and fault tolerance. Operationally heavy — requires running a Temporal server. Overkill for this scale.

**Prefect 3** — The right call for V1. Python-native, async-first, built-in `rate_limit()` primitive, task-level retry with backoff, native state persistence, and a monitoring UI. Deploys locally or to Prefect Cloud. Works natively with Databricks.

**Databricks Workflows** — Valid alternative if we want everything in one ecosystem. Lower operational overhead than Prefect Cloud but less flexible orchestration logic. Consider for V2 if Prefect adds friction.

### Decision

**Primary orchestrator: Prefect 3**

**Optional V2 addition: LangGraph** as an agent layer over Prefect, enabling Claude to make adaptive research decisions (e.g., "this city × HVAC combo looks promising — expand keyword seeds before scoring").

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        INPUT LAYER                           │
│   cities.json (N metros) × industries.json (M verticals)    │
│   seeds.json (3–5 seed keywords per industry)               │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                       MATRIX LAYER                           │
│   Combination Generator → N × M combo list                   │
│   Priority Queue → sorted by city population / market size   │
│   Deduplication → skip combos completed within 30 days       │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│              ORCHESTRATION LAYER — Prefect 3                 │
│                                                              │
│   Flow Controller    Rate Limiter      Retry Handler         │
│   resumable          token bucket      exp backoff           │
│   stateful           per API           max 3 attempts        │
│   checkpointed       (Ahrefs / SERP)   then mark failed      │
└──────────┬─────────────────┬───────────────────────────────-┘
           │                 │
┌──────────▼──────┐  ┌───────▼──────────────────────────────┐
│  KEYWORD AGENT  │  │           SERP AGENT                  │
│  Ahrefs MCP     │  │           SerpAPI REST                │
│─────────────────│  │──────────────────────────────────────│
│ matching-terms  │  │ geo-constrained SERP fetch            │
│ volume-history  │  │ location param (city string / lat+lon)│
│ KD, CPC, trend  │  │ competitor Domain Rating              │
│                 │  │ SERP feature detection (PAA, snippets)│
└──────────┬──────┘  └───────┬──────────────────────────────┘
           │                 │
┌──────────▼─────────────────▼───────────────────────────────┐
│               STORAGE LAYER — Delta Lake / SQLite            │
│                                                              │
│   combos          keyword_data       serp_results            │
│   (run tracking)  (Ahrefs output)    (SerpAPI output)        │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                     SCORING AGENT — Python                   │
│   Reads raw keyword + SERP data for each combo               │
│   Computes composite viability score                         │
│   Writes to viability_scores table                           │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                       OUTPUT LAYER                           │
│   HTML Dashboard (city × industry heatmap)                   │
│   CSV Export (top N opportunities)                           │
│   Databricks Notebook (deep-dive analysis)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Data Model

### 5.1 Schema

```sql
-- Tracks every city × industry combination and its processing state
CREATE TABLE combos (
    id            UUID PRIMARY KEY,
    city          VARCHAR NOT NULL,
    state         VARCHAR,
    industry      VARCHAR NOT NULL,
    seed_keywords TEXT[],   -- input seeds for this industry
    status        VARCHAR CHECK (status IN (
                    'pending', 'keyword_done', 'serp_done', 'scored', 'failed'
                  )) DEFAULT 'pending',
    started_at    TIMESTAMP,
    completed_at  TIMESTAMP,
    error_msg     TEXT,
    run_id        UUID      -- links to a specific research run
);

-- Raw keyword data from Ahrefs per combo
CREATE TABLE keyword_data (
    id               UUID PRIMARY KEY,
    combo_id         UUID REFERENCES combos(id),
    keyword          VARCHAR NOT NULL,
    monthly_volume   INT,
    kd               FLOAT,   -- keyword difficulty 0–100
    cpc              FLOAT,   -- cost per click in USD
    trend_direction  FLOAT,   -- % change: 3mo avg vs prior 3mo avg
    volume_3mo_avg   INT,
    fetched_at       TIMESTAMP
);

-- Raw SERP data from SerpAPI per keyword per combo
CREATE TABLE serp_results (
    id               UUID PRIMARY KEY,
    combo_id         UUID REFERENCES combos(id),
    keyword          VARCHAR NOT NULL,
    position         INT,
    url              VARCHAR,
    domain           VARCHAR,
    domain_rating    FLOAT,   -- pulled via Ahrefs site-explorer after SERP fetch
    traffic_estimate INT,
    serp_features    TEXT[],  -- e.g. ['featured_snippet', 'paa', 'local_pack']
    geo_location     VARCHAR, -- the location string used in the SerpAPI call
    fetched_at       TIMESTAMP
);

-- Composite viability scores per combo
CREATE TABLE viability_scores (
    id                    UUID PRIMARY KEY,
    combo_id              UUID REFERENCES combos(id),
    city                  VARCHAR,
    industry              VARCHAR,
    volume_score          FLOAT,       -- normalized 0–1
    competition_score     FLOAT,       -- normalized 0–1 (higher = less competition)
    monetization_score    FLOAT,       -- normalized 0–1
    trend_score           FLOAT,       -- normalized 0–1
    serp_weakness_score   FLOAT,       -- normalized 0–1 (higher = weaker incumbents)
    composite_score       FLOAT,       -- weighted sum, 0–1
    is_viable             BOOLEAN,     -- composite_score > 0.65
    top_keywords          TEXT[],      -- top 3 keywords driving the score
    ranked_at             TIMESTAMP
);
```

### 5.2 State Machine for Combo Processing

```
pending → keyword_done → serp_done → scored
                                ↘
                              failed (at any stage)
```

Failed combos are logged with `error_msg` and skipped on subsequent runs unless explicitly retried.

---

## 6. Viability Scoring Model

### 6.1 Formula

```python
def compute_viability_score(keyword_data: list, serp_data: list) -> float:
    """
    Composite viability score: weighted sum of normalized signals.
    All inputs normalized to [0, 1] relative to the full dataset.
    """
    volume_score       = normalize(median(kw.monthly_volume for kw in keyword_data))
    competition_score  = 1 - normalize(median(kw.kd for kw in keyword_data))
    monetization_score = normalize(median(kw.cpc for kw in keyword_data))
    trend_score        = normalize(median(kw.trend_direction for kw in keyword_data))
    serp_weakness      = 1 - normalize(mean(r.domain_rating for r in serp_data[:3]))

    return (
        0.25 * volume_score       +   # demand signal
        0.25 * competition_score  +   # competition gap
        0.20 * monetization_score +   # buyer intent proxy
        0.15 * trend_score        +   # growth direction
        0.15 * serp_weakness          # incumbent strength
    )
```

### 6.2 Viability Threshold

A combo is marked `is_viable = True` when `composite_score > 0.65`. This threshold is configurable via environment variable (`VIABILITY_THRESHOLD`).

### 6.3 Normalization

All normalization is computed against the full combo dataset for a given run, not globally. This means scores are relative to the batch — useful for ranking, not for absolute benchmarking across runs.

---

## 7. API Contracts (Internal)

```python
# Keyword Agent
class KeywordAgent:
    def fetch(self, city: str, industry: str, seeds: list[str]) -> list[KeywordResult]:
        """
        Calls Ahrefs MCP: matching-terms + volume-history per seed.
        Returns deduplicated keyword list with volume, KD, CPC, trend.
        Filters: KD < 40, volume > 200/mo.
        """

# SERP Agent
class SERPAgent:
    def fetch(self, keyword: str, location: str) -> list[SERPResult]:
        """
        Calls SerpAPI with geo-constrained location string.
        Returns top 10 SERP results with domain, URL, SERP features.
        Domain Rating enriched via Ahrefs site-explorer post-fetch.
        """

# Scoring Agent
class ScoringAgent:
    def score(self, combo_id: str) -> ViabilityScore:
        """
        Reads keyword_data + serp_results from storage for combo_id.
        Computes and writes viability_scores row.
        Returns ViabilityScore object.
        """
```

---

## 8. Rate Limit Strategy

### 8.1 API Limits (Approximate)

| API | Free Tier | Paid Entry | Notes |
|---|---|---|---|
| SerpAPI | 100 searches/mo | ~$50/mo (5K searches) | 1,000 combos × ~10 keywords = 10K calls minimum |
| Ahrefs | N/A (MCP plan) | Varies by plan | Row-based limits per report; batch efficiently |

### 8.2 Implementation

**Prefect native rate limiting** for SerpAPI:

```python
from prefect.concurrency.asyncio import rate_limit

@task
async def fetch_serp(keyword: str, location: str):
    await rate_limit("serpapi")  # named limit configured in Prefect
    return serpapi_client.search({"q": keyword, "location": location})
```

**Token bucket** configuration:
- SerpAPI $50 plan: 5,000 searches/month → ~167/day → configure limit at 150/day with headroom
- Ahrefs: batch keyword lookups into single requests where possible (use `batch-analysis` tool)

### 8.3 Caching Strategy

Before fetching, check if `combo_id` has `status = 'scored'` and `completed_at > NOW() - 30 days`. If yes, skip the entire combo and use existing scores. This makes re-runs nearly free.

---

## 9. Scale Estimation

| Variable | Value |
|---|---|
| Cities | 50 |
| Industries | 20 |
| Total combos | 1,000 |
| Keywords per combo (Ahrefs) | ~10 |
| SerpAPI calls per combo (10 keywords) | 10 |
| Total SerpAPI calls | ~10,000 |
| Required SerpAPI plan | ~$100–150/mo |
| Estimated run time (5 parallel workers, 150 calls/day limit) | ~3–4 days cold; ~hours on warm cache |
| Storage (Delta Lake) | < 1 GB for full run |

**Cost optimization levers:** reduce city or industry list, increase KD filter to reduce keywords per combo, increase parallel workers on a higher-tier API plan.

---

## 10. Error Handling

| Error Type | Behavior |
|---|---|
| 429 Rate Limit | Exponential backoff: 10s, 20s, 40s. After 3 attempts, mark combo `failed` and continue |
| 500 Server Error | Same as 429 |
| Empty SERP response | Log warning, use available data, proceed to scoring |
| Ahrefs no results | Log, mark `keyword_done` with empty set, skip SERP + scoring for this combo |
| Unhandled exception | Log stack trace to `error_msg`, mark `failed`, continue to next combo |

Prefect handles retry logic at the task level via `@task(retries=3, retry_delay_seconds=exponential_backoff(backoff_factor=2))`.

---

## 11. Prefect Flow Skeleton

```python
from prefect import flow, task
from prefect.concurrency.asyncio import rate_limit

@task(retries=3, retry_delay_seconds=[10, 20, 40])
async def run_keyword_agent(combo: Combo) -> list[KeywordResult]:
    await rate_limit("ahrefs")
    return KeywordAgent().fetch(combo.city, combo.industry, combo.seeds)

@task(retries=3, retry_delay_seconds=[10, 20, 40])
async def run_serp_agent(combo: Combo, keyword: str) -> list[SERPResult]:
    await rate_limit("serpapi")
    return SERPAgent().fetch(keyword, location=f"{combo.city}, {combo.state}")

@task
def run_scoring_agent(combo_id: str) -> ViabilityScore:
    return ScoringAgent().score(combo_id)

@flow(name="niche-research-run")
async def niche_research_flow(cities: list, industries: list):
    combos = generate_matrix(cities, industries)
    combos = filter_already_scored(combos, max_age_days=30)  # cache check

    for combo in combos:
        keywords = await run_keyword_agent(combo)
        store_keyword_data(combo.id, keywords)

        serp_tasks = [run_serp_agent(combo, kw.keyword) for kw in keywords]
        serp_results = await asyncio.gather(*serp_tasks)
        store_serp_results(combo.id, serp_results)

        score = run_scoring_agent(combo.id)
        store_score(score)
```

---

## 12. Trade-off Analysis

### Prefect 3 vs Pure asyncio

Prefect adds ~200ms overhead per task and requires a running server for full state persistence. In exchange: full resumability, a monitoring UI, and native rate limiting. For 1,000+ combos running over days, the resumability is non-negotiable. Pure asyncio fails at combo 400 and you restart from zero — that's real money in API credits.

**Decision: Prefect.**

### Ahrefs + SerpAPI vs single tool

Ahrefs has higher-quality keyword volume data and better KD scoring. SerpAPI has better geo-SERP specificity. Using both doubles the API cost surface and adds an integration seam. The alternative — Ahrefs alone — gives country-level geo but not city-level SERP. For a city-level niche finder, that's the entire value proposition.

**Decision: Both tools, by necessity.**

### Static scoring vs Claude-driven scoring

A static formula (section 6.1) is fast, deterministic, and auditable. Claude-driven scoring adds nuance — it can reason about SERP intent, content quality, local market dynamics — but introduces non-determinism and makes scores hard to explain. The hybrid approach: use static scoring as the primary signal, run Claude as a "validation pass" on the top 50 combos to flag anything the formula missed.

**Decision: Static now, hybrid in V2.**

### SQLite vs Delta Lake

SQLite requires zero infrastructure and is fine for development and small runs (< 10K rows). Delta Lake handles scale, supports Spark queries, and fits the existing Databricks stack. The schema is identical — switching is just a connection string change.

**Decision: SQLite for dev, Delta Lake for production.**

---

## 13. What I'd Revisit as the System Grows

**Keyword clustering.** Right now we score individual keywords. The better unit of analysis is a keyword cluster — a group of semantically related terms representing a single user intent. Scoring at cluster level reduces noise and surfaces the actual opportunity more clearly.

**Local market modifiers.** City population and business density affect how much a niche is worth locally. Overlaying census or BLS data (median household income, number of businesses per SIC code per metro) would let us adjust raw viability scores by local market size. A KD=15 keyword in NYC is worth more than the same keyword in Boise.

**Score drift tracking.** Run the same combos monthly and track composite score deltas. A niche that scores 0.55 today but is trending up fast is more interesting than one that scores 0.70 and is declining. The system should surface trajectory, not just point-in-time rank.

**LangGraph adaptive layer (V2).** Let Claude observe early results mid-run and decide to expand seed keywords for promising combos, or deprioritize combos that look saturated after the first few keywords. This turns a static batch job into an adaptive research agent. Pairs with NeMo Guardrails if we need to constrain Claude's decisions to a defined playbook.

---

## 14. Open Questions

1. **City prioritization logic** — what determines the order of the priority queue? Population, GDP, proximity to existing customers, something else?
2. **Seed keyword sourcing** — who defines the 3–5 seeds per industry? Manual curation, or should we auto-generate seeds from Ahrefs `search-suggestions` per industry term?
3. **SerpAPI plan** — 10K+ calls/month means we need the $100–150/month plan minimum. Is this in budget before we start?
4. **Viability threshold** — 0.65 is an assumption. Needs calibration against a set of manually-reviewed combos once we have data.
5. **Output ownership** — who consumes the HTML dashboard? Internal team only, or does this become a product feature?