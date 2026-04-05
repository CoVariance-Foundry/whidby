# Widby — Product Breakdown & Spec-Driven Development Guide

> **Canonical notice:** Architecture, requirements, and test obligations from this file
> have been migrated to `docs-canonical/ARCHITECTURE.md`, `docs-canonical/REQUIREMENTS.md`,
> and `docs-canonical/TEST-SPEC.md`. This file is retained as detailed reference.
> Update canonical docs first when making structural changes.

**Purpose:** Decompose the full Widby product into buildable, testable modules with clear boundaries. Each module has its own spec slice, eval criteria, and a minimal frontend surface for experimentation.

**Stack:** Python (backend) · Supabase (database + auth + storage) · Vercel (frontend hosting) · Next.js or simple HTML (eval frontend) · DataForSEO (data APIs) · Anthropic Python SDK (`anthropic`) for LLM inference

**Development approach:** Spec-driven, test-driven development (TDD). Each module has a reference spec section, input/output contract, and eval suite. **Write tests first, then implement until tests pass.** Build and validate one module at a time. Modules compose into the full pipeline.

### Framework Decision: No Framework (Plain Python + Claude API)

**Decision:** We are NOT using LangGraph, CrewAI, Claude Agent SDK, or any agent orchestration framework for V1.

**Rationale:** Widby's pipeline is 80% deterministic data processing (API calls, signal extraction, scoring math) and 20% LLM calls (keyword expansion, audit generation, reply classification). Agent frameworks are designed for the inverse — systems where the LLM decides what to do next. Our pipeline has a fixed execution order defined by the spec. The LLM is a utility called at specific points, not the orchestrator.

**What we use instead:**
- `anthropic` Python SDK for all Claude API calls
- `asyncio` for concurrent API call orchestration
- Plain Python functions with explicit dependency ordering
- Supabase for state persistence
- MCP-compatible tool interfaces (future-proofing for Sonar)

**When we'll reconsider:** When building Sonar (continuous monitoring agent), we'll evaluate LangGraph for orchestration. Our modules will become LangGraph nodes without rewriting business logic. Building framework-agnostic modules now is the deliberate strategy.

### Test-Driven Development Protocol

Every module follows TDD:

1. **Read the spec slice** for the module (referenced in each module section below)
2. **Write the test file first** based on the eval criteria table
3. **Run tests — confirm they fail** (red)
4. **Implement the module** until all tests pass (green)
5. **Refactor** for clarity without breaking tests
6. **Add the eval frontend page** for manual experimentation

**Test structure per module:**
```
tests/
  unit/
    test_{module}.py           # Unit tests — pure function behavior, no external calls
  integration/
    test_{module}_integration.py  # Integration tests — real API calls (DataForSEO, Claude)
  fixtures/
    {module}_fixtures.py       # Shared test data, mock responses
```

**Test rules:**
- Unit tests must run without API keys or network access (use fixtures/mocks)
- Integration tests are tagged `@pytest.mark.integration` and skipped in CI by default
- Every public function has at least one unit test
- Every input/output contract from the spec has a corresponding test
- Use `pytest` with `pytest-asyncio` for async code
- Use `pytest-mock` for mocking external dependencies
- Fixtures live alongside tests, not buried in conftest.py

---

## Product Architecture Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WIDBY PRODUCT                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  SHARED INFRASTRUCTURE                                              │
│  ├── M0: DataForSEO Client (API wrapper + rate limiting + caching)  │
│  ├── M1: Metro Database (CBSA data + DFS location mapping)          │
│  ├── M2: Supabase Schema (tables, RLS, Edge Functions scaffold)     │
│  └── M3: LLM Client (Claude API wrapper + prompt management)        │
│                                                                     │
│  NICHE SCORING ENGINE (Algo Spec V1.1)                              │
│  ├── M4: Keyword Expansion + Intent Classification                  │
│  ├── M5: Data Collection Pipeline (SERP + Keywords + Business)      │
│  ├── M6: Signal Extraction                                          │
│  ├── M7: Scoring Engine (5 scores + composite)                      │
│  ├── M8: Classification + Guidance                                  │
│  └── M9: Report Generation + Feedback Logging                       │
│                                                                     │
│  OUTREACH EXPERIMENT FRAMEWORK                                      │
│  ├── M10: Business Discovery + Qualification                        │
│  ├── M11: Site Scanning + Weakness Scoring                          │
│  ├── M12: Audit Generation (HTML audit pages)                       │
│  ├── M13: Outreach Delivery + Sequencing                            │
│  ├── M14: Response Tracking + Reply Classification                  │
│  └── M15: Experiment Analysis + Rentability Signal                  │
│                                                                     │
│  EVAL FRONTEND                                                      │
│  └── M16: Internal dashboard for running and reviewing all modules  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Build Sequence

Modules are ordered by dependency and value. Each phase produces something you can use and evaluate before moving to the next.

### Phase 1: Foundation (Week 1-2)
Build the shared infrastructure that everything depends on.

```
M0 → M1 → M2 → M3 → M16 (scaffold)
```

### Phase 2: Core Scoring Pipeline (Week 3-5)
Build the niche scoring engine end-to-end, one phase at a time.

```
M4 → M5 → M6 → M7 → M8 → M9
```

### Phase 3: Experiment Framework (Week 6-8)
Build the outreach experiment pipeline, reusing shared infra and scoring signals.

```
M10 → M11 → M12 → M13 → M14 → M15
```

---

## Module Specifications

---

### M0: DataForSEO Client

**Spec reference:** Algo Spec V1.1, §14 (API Reference)

**What it does:** Unified Python client for all DataForSEO API interactions. Handles authentication, rate limiting, request queuing (standard vs. live), response caching, error handling, and cost tracking.

**Input/Output contract:**
```python
# Input: API endpoint + parameters
client.serp_organic(keyword="plumber", location_code=1012873, depth=10)

# Output: Standardized response object
{
  "status": "ok",
  "data": { ... },  # parsed API response
  "cost": 0.0006,
  "cached": False,
  "latency_ms": 1250
}
```

**Key implementation details:**
- Standard queue endpoints: POST task, poll for results (max 5 min)
- Live endpoints: single POST, immediate response
- Rate limit: 2000 calls/minute (enforce client-side)
- Response caching: cache SERP and keyword data for 24 hours (configurable TTL)
- Cost tracking: log every API call cost to `api_usage_log` table
- Retry logic: 3 retries with exponential backoff on 5xx errors

**Files to create:**
```
src/
  clients/
    dataforseo/
      __init__.py
      client.py          # Main client class
      endpoints.py       # Endpoint definitions (SERP, Keywords, Business, etc.)
      queue_manager.py   # Standard queue polling logic
      cache.py           # Response caching layer
      cost_tracker.py    # Per-call cost logging
      types.py           # Response type definitions
  tests/
    test_dataforseo_client.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Authentication | Live API call to `/v3/serp/google/locations` | Returns 200 with location data |
| SERP pull (standard queue) | Query "plumber" in Phoenix | Returns organic results within 5 minutes |
| SERP pull (live) | Business listings for "plumber" in Phoenix | Returns results within 10 seconds |
| Rate limiting | Fire 100 concurrent requests | No 429 errors, requests properly queued |
| Caching | Same query twice within TTL | Second call returns cached result, cost = 0 |
| Cost tracking | Run 10 API calls | `api_usage_log` table has 10 rows with correct costs |
| Error handling | Query with invalid location code | Returns error object, no crash |

**Eval frontend surface:**
- Text input for endpoint selection (dropdown: SERP Organic, SERP Maps, Keywords, Business Listings, etc.)
- Parameter form (keyword, location, depth)
- "Send Request" button
- Raw JSON response viewer
- Cost and latency display
- Cache hit indicator

---

### M1: Metro Database

**Spec reference:** Algo Spec V1.1, §3.2-3.3 (Metro/MSA Resolution, Geo Scope Expansion), §15 (Appendix: CBSA Data Source)

**What it does:** Static database of U.S. metropolitan areas mapped to DataForSEO location codes. Supports geo scope expansion (state → metros, region → metros). Provides the geographic backbone for all queries.

**Input/Output contract:**
```python
# Input: geo scope
metros = metro_db.expand_scope(scope="state", target="AZ", depth="standard")

# Output: List of metro objects
[
  {
    "cbsa_code": "38060",
    "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
    "state": "AZ",
    "population": 4946145,
    "principal_cities": ["Phoenix", "Mesa", "Chandler", "Scottsdale", "Tempe"],
    "dataforseo_location_codes": [1012873, ...]
  },
  ...
]
```

**Key implementation details:**
- Source: Census Bureau CBSA delineation file (download and parse once)
- DFS location mapping: call `/v3/serp/google/locations` once, build lookup table, store in Supabase
- Region definitions: predefined (Southwest = AZ, NM, NV, UT, CO; etc.)
- Standard depth: top 20 metros by population in scope
- Deep depth: all metros with population > 50,000

**Files to create:**
```
src/
  data/
    metro_db.py              # Metro database class
    cbsa_loader.py           # Census file parser
    dfs_location_mapper.py   # DataForSEO location code mapping
    regions.py               # Region-to-state definitions
  data/seed/
    cbsa_delineation.csv     # Census source file
  tests/
    test_metro_db.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| State expansion | expand_scope("state", "AZ", "standard") | Returns Phoenix, Tucson, Mesa CBSAs (top 20 by pop) |
| Region expansion | expand_scope("region", "Southwest", "standard") | Returns metros across AZ, NM, NV, UT, CO |
| Custom expansion | expand_scope("custom", ["38060", "46060"]) | Returns Phoenix + Tucson exactly |
| DFS location mapping | Look up Phoenix CBSA | Returns valid DataForSEO location codes |
| Population ordering | Any state expansion | Results sorted by population descending |
| Deep vs standard | Compare counts for CA | Deep returns significantly more metros than standard |

**Eval frontend surface:**
- Dropdown: State / Region / Custom
- Input for target (state code, region name, or CBSA codes)
- Toggle: Standard / Deep
- "Expand" button
- Table showing returned metros: name, CBSA code, population, principal cities
- Map visualization (optional, stretch goal) showing metro locations

---

### M2: Supabase Schema

**Spec reference:** Algo Spec V1.1 (all phases produce data that needs storage), Experiment Framework §10 (Data Model)

**What it does:** Database schema, Row-Level Security policies, and Edge Function scaffolding. This is the data layer everything writes to and reads from.

**Key implementation details:**
- All tables from both specs (algo + experiment)
- RLS policies for internal-only access
- Edge Functions scaffold for async operations
- Migrations managed via Supabase CLI

**Files to create:**
```
supabase/
  migrations/
    001_core_schema.sql          # Report, keyword, signal tables
    002_experiment_schema.sql    # Experiment, business, event tables
    003_shared_tables.sql        # Metro cache, API usage log, suppression list
    004_rls_policies.sql         # Row-level security
  functions/
    _shared/
      supabase_client.ts         # Shared Supabase client
    placeholder/
      index.ts                   # Scaffold for future Edge Functions
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Schema creation | Run all migrations | No errors, all tables created |
| RLS enforcement | Query experiments table without auth | Returns empty / 403 |
| Insert + read cycle | Insert a test report row, read it back | Data round-trips correctly |
| Foreign keys | Insert event with invalid experiment_id | Rejected by FK constraint |
| Unique constraints | Insert duplicate rentability signal (same niche+metro) | Upsert works correctly |

**Eval frontend surface:**
- None needed — validate via Supabase dashboard and SQL tests
- Optional: simple "DB Health" page showing table row counts and last-modified timestamps

---

### M3: LLM Client

**Spec reference:** Algo Spec V1.1 §4.2 (Keyword Expansion), Experiment Framework §6.4 (Audit Copy), §8.3 (Reply Classification)

**What it does:** Thin wrapper around the `anthropic` Python SDK for all LLM inference tasks. Handles prompt management, structured output parsing (JSON mode), retry logic, token tracking, and cost estimation. This is NOT an agent framework — it's a utility library.

**Input/Output contract:**
```python
# Input: task type + parameters
result = await llm.keyword_expansion(niche="plumber")

# Output: Parsed, validated response
{
  "keywords": [...],
  "expansion_confidence": "high",
  "tokens_used": 1250,
  "cost_usd": 0.004
}
```

**Key implementation details:**
- Uses `anthropic` Python SDK directly (`pip install anthropic`)
- Prompt templates stored as versioned files (not hardcoded strings)
- JSON mode via `response_format={"type": "json_object"}` for structured outputs
- Temperature=0 for keyword expansion (deterministic), 0.3 for audit copy (slight creativity)
- Token budget enforcement per call
- Fallback: if Claude API fails, return graceful error (don't crash the pipeline)
- Model default: `claude-sonnet-4-20250514` for most tasks, `claude-haiku-4-5-20251001` for classification

**Files to create:**
```
src/
  clients/
    llm/
      __init__.py
      client.py            # Thin anthropic SDK wrapper
      prompts/
        keyword_expansion.py
        intent_classification.py
        audit_generation.py
        reply_classification.py
        guidance_generation.py
      output_parsers.py    # JSON parsing + validation
      token_tracker.py     # Usage and cost tracking
tests/
  unit/
    test_llm_client.py
    test_output_parsers.py
    test_prompts.py
  integration/
    test_llm_client_integration.py
  fixtures/
    llm_fixtures.py        # Mock Claude responses for unit tests
```

**TDD sequence — write these tests FIRST:**
```python
# tests/unit/test_llm_client.py

class TestLLMClient:
    def test_keyword_expansion_returns_valid_schema(self, mock_anthropic):
        """Parsed output matches KeywordExpansion schema."""
        mock_anthropic.return_value = FIXTURE_KEYWORD_RESPONSE
        result = await llm.keyword_expansion(niche="plumber")
        assert "expanded_keywords" in result
        assert all("tier" in kw and "intent" in kw for kw in result["expanded_keywords"])

    def test_intent_classification_transactional(self, mock_anthropic):
        """'emergency plumber near me' classified as transactional."""
        mock_anthropic.return_value = FIXTURE_INTENT_TRANSACTIONAL
        result = await llm.classify_intent("emergency plumber near me")
        assert result == "transactional"

    def test_intent_classification_informational(self, mock_anthropic):
        """'how to fix a leaky faucet' classified as informational."""
        mock_anthropic.return_value = FIXTURE_INTENT_INFORMATIONAL
        result = await llm.classify_intent("how to fix a leaky faucet")
        assert result == "informational"

    def test_malformed_json_response_handled(self, mock_anthropic):
        """LLM returns invalid JSON — client returns error, doesn't crash."""
        mock_anthropic.return_value = "not valid json {{"
        result = await llm.keyword_expansion(niche="plumber")
        assert result.error is not None

    def test_token_tracking(self, mock_anthropic):
        """Token usage and cost logged after each call."""
        await llm.keyword_expansion(niche="plumber")
        assert llm.tracker.total_tokens > 0
        assert llm.tracker.total_cost_usd > 0

# tests/integration/test_llm_client_integration.py

@pytest.mark.integration
class TestLLMClientIntegration:
    async def test_real_keyword_expansion(self):
        """Live Claude call returns parseable keyword expansion."""
        result = await llm.keyword_expansion(niche="plumber")
        assert result["total_keywords"] >= 5
        assert result["expansion_confidence"] in ("high", "medium", "low")

    async def test_determinism_at_temp_zero(self):
        """Same input twice at temp=0 produces identical output."""
        r1 = await llm.keyword_expansion(niche="plumber")
        r2 = await llm.keyword_expansion(niche="plumber")
        assert r1["expanded_keywords"] == r2["expanded_keywords"]
```

---

### M4: Keyword Expansion + Intent Classification

**Spec reference:** Algo Spec V1.1, §4 (Phase 1)

**What it does:** Takes a niche keyword, expands it into a classified keyword set with tier and intent labels, validates via DataForSEO keyword suggestions, and flags informational keywords for exclusion from SERP analysis.

**Dependencies:** M0 (DataForSEO Client), M3 (LLM Client)

**Input/Output contract:**
```python
# Input
expansion = expand_keywords(niche="plumber")

# Output: KeywordExpansion object matching algo spec §4.5
{
  "niche": "plumber",
  "expanded_keywords": [
    {"keyword": "plumber near me", "tier": 1, "intent": "transactional", "source": "llm", "aio_risk": "low"},
    ...
  ],
  "total_keywords": 15,
  "actionable_keywords": 12,
  "informational_keywords_excluded": 3,
  "expansion_confidence": "high"
}
```

**Files to create:**
```
src/
  pipeline/
    keyword_expansion.py     # Main expansion pipeline
    intent_classifier.py     # Intent classification logic
    keyword_deduplication.py # Normalize + dedup
  tests/
    test_keyword_expansion.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Head term generation | expand("plumber") | Contains "plumber" and "plumber near me" |
| Service term generation | expand("plumber") | Contains sub-services (drain cleaning, water heater, etc.) |
| Intent classification | All returned keywords | Each has valid intent label |
| Informational filtering | expand("plumber") | "how to" queries marked as excluded |
| DFS validation | LLM terms checked against DFS suggestions | expansion_confidence reflects overlap |
| Tier assignment | All returned keywords | Each has tier 1, 2, or 3 |
| Niche variety | expand("mobile dog grooming") | Returns relevant, non-generic keywords |
| Determinism | Same niche twice | Identical results (temp=0) |
| AIO risk labeling | All returned keywords | Informational = high, transactional = low |
| Edge case: obscure niche | expand("septic tank pumping") | Returns reasonable keywords, confidence may be "low" |

**Eval frontend surface:**
- Text input for niche keyword
- "Expand" button
- Results table: keyword, tier, intent, source, AIO risk
- Summary stats: total, actionable, excluded, confidence
- Side panel: raw LLM response + DFS suggestions for debugging

---

### M5: Data Collection Pipeline

**Spec reference:** Algo Spec V1.1, §5 (Phase 2)

**What it does:** Orchestrates all DataForSEO API calls for a given set of keywords and metros. Manages the dependency chain (SERP results needed before backlink/lighthouse calls), batching, parallel execution, and cost tracking.

**Dependencies:** M0 (DataForSEO Client), M1 (Metro Database), M4 (Keyword Expansion output)

**Input/Output contract:**
```python
# Input
raw_data = collect_data(
    keywords=keyword_expansion,
    metros=[metro_1, metro_2, ...],
    strategy_profile="balanced",
    client=dataforseo_client
)

# Output: RawCollectionResult — organized raw API responses per metro
{
  "metros": {
    "38060": {
      "serp_organic": [{...}, ...],     # per keyword
      "serp_maps": [{...}],             # per metro
      "keyword_volume": [{...}, ...],   # per keyword
      "business_listings": [{...}, ...],
      "google_reviews": [{...}, ...],   # per top-3 local pack business
      "gbp_info": [{...}, ...],         # per top-5 GBP listing
      "backlinks": [{...}, ...],        # per top-5 domain
      "lighthouse": [{...}, ...],       # per top-5 URL
    }
  },
  "meta": {
    "total_api_calls": 482,
    "total_cost_usd": 2.48,
    "collection_time_seconds": 312,
    "errors": [
      {
        "task_id": "dep-00001",
        "task_type": "google_reviews",
        "metro_id": "38060",
        "message": "google_reviews failed",
        "is_retryable": true
      }
    ]
  }
}
```

**Files to create:**
```
src/
  pipeline/
    data_collection.py        # Main orchestrator
    collection_plan.py        # Generates the API call plan from keywords + metros
    task_graph.py             # Dependency graph validation + ordering
    batch_executor.py         # Executes calls with dependency ordering
    errors.py                 # Normalized failure record helpers
    types.py                  # Request/task/result contracts
    result_assembler.py       # Organizes raw responses by metro
tests/
  unit/
    test_collection_plan.py
    test_batch_executor.py
    test_result_assembler.py
    test_data_collection.py
  fixtures/
    m5_collection_fixtures.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Single metro collection | Collect for "plumber" in Phoenix | All 8 data types returned |
| Multi-metro collection | Collect for "plumber" in 3 metros | Data organized correctly per metro |
| Dependency ordering | Backlink calls | Only fire after SERP results identify top domains |
| Cost tracking | Any collection run | total_cost_usd matches sum of individual call costs |
| Error resilience | Simulate one failed API call | Other calls complete, error logged |
| SERP feature parsing | Parse real SERP response | ai_overview, local_pack, ads correctly detected |
| Keyword filtering | Informational keywords | Not sent to SERP endpoint (only to keyword volume) |
| Batch efficiency | 700 keywords in one volume call | Single API task, not 700 separate calls |

**Eval frontend surface:**
- Input: niche keyword + metro selector (from M1)
- "Collect Data" button (with cost estimate before execution)
- Progress tracker: which API calls are pending / complete / failed
- Raw data browser: expandable tree view of results per metro per data type
- Cost summary: total cost, calls by endpoint type, cache hit rate

---

### M6: Signal Extraction

**Spec reference:** Algo Spec V1.1, §6 (Phase 3)

**What it does:** Transforms raw API responses into standardized, normalized signals per metro. This is the core analytical layer — turning messy API data into clean numbers the scoring engine can consume.

**Dependencies:** M5 (Data Collection output)

**Input/Output contract:**
```python
# Input: raw collection data for one metro
signals = extract_signals(raw_data["metros"]["38060"], keyword_expansion)

# Output: MetroSignals object matching algo spec §6.1-6.5
{
  "demand": {
    "total_search_volume": 12400,
    "effective_search_volume": 10850,
    "head_term_volume": 4200,
    "volume_breadth": 0.80,
    "avg_cpc": 18.50,
    "max_cpc": 32.00,
    "cpc_volume_product": 200750,
    "transactional_ratio": 0.73
  },
  "organic_competition": {
    "avg_top5_da": 22,
    "min_top5_da": 8,
    "da_spread": 35,
    "aggregator_count": 3,
    "local_biz_count": 4,
    "avg_lighthouse_performance": 45,
    "schema_adoption_rate": 0.20,
    "title_keyword_match_rate": 0.40
  },
  "local_competition": {
    "local_pack_present": true,
    "local_pack_position": 2,
    "local_pack_review_count_avg": 35,
    "local_pack_review_count_max": 89,
    "local_pack_rating_avg": 4.3,
    "review_velocity_avg": 3.2,
    "gbp_completeness_avg": 0.57,
    "gbp_photo_count_avg": 12,
    "gbp_posting_activity": 0.20,
    "citation_consistency": 0.65
  },
  "ai_resilience": {
    "aio_trigger_rate": 0.04,
    "featured_snippet_rate": 0.10,
    "transactional_keyword_ratio": 0.73,
    "local_fulfillment_required": 1,
    "paa_density": 1.8
  },
  "monetization": {
    "avg_cpc": 18.50,
    "business_density": 450,
    "gbp_completeness_avg": 0.57,
    "lsa_present": true,
    "aggregator_presence": 3,
    "ads_present": true
  }
}
```

**Files to create:**
```
src/
  pipeline/
    signal_extraction.py          # Main extractor
    extractors/
      demand_signals.py           # Volume, CPC, breadth, intent ratio
      organic_competition.py      # DA, aggregators, technical quality
      local_competition.py        # Reviews, GBP, local pack
      ai_resilience.py            # AIO detection, SERP features
      monetization.py             # CPC, density, active market signals
    serp_parser.py                # Parse SERP features from raw responses
    domain_classifier.py          # Aggregator / national / local classification
    effective_volume.py           # AIO-discounted volume calculator
    review_velocity.py            # Review velocity computation
    gbp_completeness.py           # GBP completeness scorer
  tests/
    test_signal_extraction.py
    test_serp_parser.py
    test_domain_classifier.py
    test_effective_volume.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Demand extraction | Real SERP + keyword data | All 8 demand signals populated with valid values |
| Effective volume discount | Transactional keyword | Discount < 2% (0.021 × 0.59) |
| Effective volume discount | Informational keyword | Discount ~26% (0.436 × 0.59) |
| AIO detection | SERP with AI Overview present | aio_trigger_rate > 0 |
| Aggregator detection | SERP with yelp.com result | aggregator_count >= 1 |
| Cross-metro dedup | Same domain in 8/20 metros | Domain classified as national |
| Review velocity | Reviews with timestamps | Correct reviews/month calculation |
| GBP completeness | GBP with 5/7 fields | Score = 0.71 |
| Local pack parsing | SERP with local 3-pack | local_pack_present = true, review counts extracted |
| Missing data handling | Metro with no local pack | local_competition signals have sensible defaults |

**Eval frontend surface:**
- Input: select a completed data collection run
- Select a metro from the run
- "Extract Signals" button
- Signal dashboard: card per signal category (demand, organic comp, local comp, AI resilience, monetization)
- Each card shows all signals with values and visual indicators (green/yellow/red)
- Drill-down: click a signal to see the raw data it was derived from

---

### M7: Scoring Engine

**Spec reference:** Algo Spec V1.1, §7 (Phase 4)

**What it does:** Takes extracted signals and computes the five sub-scores (demand, organic competition, local competition, monetization, AI resilience) plus the composite opportunity score. Strategy profile-aware.

**Dependencies:** M6 (Signal Extraction output)

**Input/Output contract:**
```python
# Input: signals for one metro + all metro signals (for percentile ranking) + config
scores = compute_scores(
    metro_signals=signals,
    all_metro_signals=[signals_1, signals_2, ...],
    strategy_profile="balanced"
)

# Output: MetroScores object
{
  "demand": 72,
  "organic_competition": 65,
  "local_competition": 58,
  "monetization": 81,
  "ai_resilience": 92,
  "opportunity": 71,
  "confidence": {"score": 95, "flags": []},
  "resolved_weights": {"organic": 0.15, "local": 0.20}
}
```

**Files to create:**
```
src/
  scoring/
    engine.py                 # Main scoring orchestrator
    demand_score.py
    organic_competition_score.py
    local_competition_score.py
    monetization_score.py
    ai_resilience_score.py
    composite_score.py        # Opportunity score + threshold gates
    confidence_score.py
    strategy_profiles.py      # Profile definitions + weight resolver
    normalization.py          # scale, inverse_scale, percentile_rank, clamp
  tests/
    test_scoring_engine.py
    test_each_score.py        # Individual score function tests
    test_strategy_profiles.py
    test_normalization.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Demand score range | 20 diverse metros | All scores between 0-100 |
| Competition inversion | Low DA metro vs high DA metro | Low DA metro scores higher (less competition) |
| Local comp: review barrier | Metro with 200+ review avg | Local competition score < 30 |
| Local comp: no local pack | Metro without local pack | Returns 75 (default) |
| Monetization: CPC scaling | $1 CPC vs $25 CPC | $25 CPC scores significantly higher |
| AI resilience: local services | Plumber (low AIO) | Score > 80 |
| AI resilience: informational niche | High AIO trigger rate | Score < 40 |
| Composite: threshold gate | One score < 5 | Opportunity capped at 20 |
| Composite: AI floor | AI resilience < 20 | Opportunity capped at 50 |
| Strategy profile: organic_first | Same metro, different profiles | Organic weight shifts from 0.15 to 0.25 |
| Strategy profile: auto | Metro without local pack | Auto-resolves to organic-heavy weights |
| Confidence: missing data | Metro with 0 review results | Confidence penalty applied |
| Percentile ranking | Demand score across 20 metros | Distribution spans 0-100 range |
| Score reproducibility | Same input twice | Identical scores |

**Eval frontend surface:**
- Input: select extracted signals (from M6) or load a saved signal set
- Strategy profile selector (organic_first / balanced / local_dominant / auto)
- "Score" button
- Score dashboard: 5 sub-scores + composite as visual gauges (0-100)
- Weight visualization: shows how strategy profile distributes competition weight
- Sensitivity slider: adjust one signal value and see score change in real-time
- Comparison view: score same metro under different strategy profiles side by side

---

### M8: Classification + Guidance

**Spec reference:** Algo Spec V1.1, §8 (Phase 5)

**What it does:** Classifies each metro into a SERP archetype and AI exposure level, assigns a difficulty tier, and generates actionable guidance text.

**Dependencies:** M6 (Signals), M7 (Scores)

**Files to create:**
```
src/
  classification/
    serp_archetype.py        # 8 archetype classifier
    ai_exposure.py           # 4-level AI exposure classifier
    difficulty_tier.py       # EASY / MODERATE / HARD / VERY_HARD
    guidance_generator.py    # Template-based + LLM guidance
    templates/
      guidance_templates.py  # Per archetype × difficulty templates
  tests/
    test_classification.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Archetype: aggregator dominated | SERP with 5+ aggregators | Returns AGGREGATOR_DOMINATED |
| Archetype: local pack vulnerable | Pack with <30 avg reviews | Returns LOCAL_PACK_VULNERABLE |
| Archetype: barren | Low local biz count, low aggregators | Returns BARREN |
| AI exposure: shielded | AIO rate < 5% | Returns AI_SHIELDED |
| AI exposure: exposed | AIO rate > 30% | Returns AI_EXPOSED |
| Difficulty: strategy profile | Same metro, organic_first vs local_dominant | May produce different difficulty tiers |
| Guidance: readable | Generated guidance for any archetype | Plain language, no jargon, actionable |
| Guidance: niche-specific | Plumber vs lawyer | Different priority actions |

**Eval frontend surface:**
- Input: select a scored metro (from M7)
- Display: archetype badge, AI exposure badge, difficulty badge
- Guidance panel: headline, strategy text, priority actions list
- Override panel: manually adjust signals and see classification change

---

### M9: Report Generation + Feedback Logging

**Spec reference:** Algo Spec V1.1, §10 (Output Schema), §9 (Feedback Logging)

**What it does:** Assembles all scored and classified metros into the final report JSON. Ranks metros by opportunity score. Writes the feedback log entry.

**Dependencies:** M4-M8 (full pipeline output)

**Files to create:**
```
src/
  pipeline/
    report_generator.py      # Assemble full report
    feedback_logger.py       # Write bandit training tuple
  tests/
    test_report_generator.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Report schema | Generate full report | Validates against JSON schema from spec §10.1 |
| Metro ordering | 20 metros | Sorted by opportunity score descending |
| Meta accuracy | Check total_cost_usd | Matches sum of all API calls in the run |
| Feedback log | Generate report | Row created in feedback_log table with correct context + signals + scores |
| Feedback log: null outcomes | Check outcome fields | All null (to be filled later) |

**Eval frontend surface:**
- Full report viewer: ranked metro list with expandable detail per metro
- Comparison mode: select 2-3 metros and see scores side by side
- Export: download report as JSON
- Feedback log viewer: shows the bandit training tuple that was logged

---

### M10: Business Discovery + Qualification

**Spec reference:** Experiment Framework, §4 (Phase E1), §5.3 (Qualification Gates)

**What it does:** Discovers businesses in a niche+metro via DataForSEO Business Listings, discovers contact emails, and qualifies businesses for outreach eligibility.

**Dependencies:** M0 (DataForSEO Client), M1 (Metro Database)

**Files to create:**
```
src/
  experiment/
    business_discovery.py      # Pull + filter businesses
    email_discovery.py         # Scrape + API email lookup
    business_qualification.py  # Qualification gates
  tests/
    test_business_discovery.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Discovery | Plumber in Phoenix | Returns 50+ businesses with name, URL, reviews, rating |
| Chain filtering | Results include Roto-Rooter | Chain is excluded |
| Email discovery | Business with contact page | Email extracted correctly |
| Qualification | Business with no website | Marked ineligible, reason = "no_website" |
| Qualification | Business with high-quality site | Marked ineligible, reason = "site_already_good" |
| Stratified sampling | 100 businesses into 3 buckets | Roughly proportional representation |

**Eval frontend surface:**
- Input: niche + metro + sample size + filters
- "Discover" button
- Business table: name, URL, reviews, rating, email found (y/n), qualified (y/n), disqualification reason
- Funnel visualization: total → with website → with email → qualified

---

### M11: Site Scanning + Weakness Scoring

**Spec reference:** Experiment Framework, §5 (Phase E2)

**What it does:** Runs Lighthouse, on-page, schema, and content analysis on each business's website. Computes an SEO weakness score.

**Dependencies:** M0 (DataForSEO Client), M10 (Business Discovery output)

**Files to create:**
```
src/
  experiment/
    site_scanner.py           # Orchestrate all scans
    weakness_scorer.py        # Compute weakness score from scan results
    quality_bucketing.py      # Assign nascent/developing/established
  tests/
    test_site_scanner.py
    test_weakness_scorer.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Lighthouse scan | Real business URL | Returns performance, SEO, accessibility scores |
| Schema detection | Site with LocalBusiness schema | has_local_business_schema = true |
| Schema detection | Site without schema | has_local_business_schema = false |
| Weakness scoring | Site with many issues | Score > 60 |
| Weakness scoring | Well-optimized site | Score < 20 |
| Quality bucketing | Scored businesses | Each assigned to nascent/developing/established |
| Content analysis | Real site | word_count, service pages detected correctly |

**Eval frontend surface:**
- Input: select a discovered business (from M10) or enter a URL directly
- "Scan" button
- Scan results dashboard: Lighthouse scores, schema status, content analysis, CWV
- Weakness score with issue breakdown (which issues contribute how many points)
- Quality bucket assignment

---

### M12: Audit Generation

**Spec reference:** Experiment Framework, §6 (Phase E3)

**What it does:** Generates personalized HTML audit pages hosted at unique URLs. Three depth tiers (minimal, standard, visual_mockup). Includes tracking pixels.

**Dependencies:** M3 (LLM Client), M11 (Site Scanning output)

**Files to create:**
```
src/
  experiment/
    audit_generator.py        # Main generation pipeline
    audit_templates/
      minimal.html
      standard.html
      visual_mockup.html
    audit_hosting.py          # Deploy to Supabase Storage or Vercel
    screenshot_capture.py     # Headless browser screenshots (for visual_mockup)
  tests/
    test_audit_generator.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Minimal audit | Generate for a scanned business | Valid HTML, <200 words, 3-5 issues listed |
| Standard audit | Generate for a scanned business | Valid HTML, scored sections, prioritized fixes |
| Visual mockup | Generate with screenshots | Includes before/after screenshots, comparison layout |
| Personalization | Audit for "Joe's Plumbing" in Phoenix | Business name, city, niche appear throughout |
| Hosting | Generated audit | Accessible at unique URL, loads in browser |
| Tracking | Load hosted audit | Tracking pixel fires, event logged |
| LLM copy quality | Review generated text | No hallucinated issues (all claims match scan data) |

**Eval frontend surface:**
- Input: select a scanned business (from M11) + audit depth tier
- "Generate Audit" button
- Audit preview: rendered HTML in an iframe
- Side panel: LLM prompt used, raw LLM response, scan data that informed the audit
- Hosted URL display + "open in new tab" link

---

### M13: Outreach Delivery + Sequencing

**Spec reference:** Experiment Framework, §7 (Phase E4)

**What it does:** Sends personalized outreach emails with audit links, manages follow-up sequences, handles bounces and unsubscribes. Integrates with email delivery platform.

**Dependencies:** M12 (Audit Generation output), email platform (TBD)

**Files to create:**
```
src/
  experiment/
    outreach_manager.py       # Sequence orchestration
    email_templates/
      problem_focused_v1.py
      competitor_comparison_v1.py
      revenue_loss_v1.py
      follow_up_soft.py
      follow_up_value_add.py
    email_sender.py           # Platform-agnostic sender interface
    email_adapters/
      resend_adapter.py       # Resend integration
      instantly_adapter.py    # Instantly integration
    compliance.py             # CAN-SPAM checks, suppression list
  tests/
    test_outreach_manager.py
    test_compliance.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Email rendering | Render template with merge fields | All fields populated, no {placeholders} visible |
| Suppression check | Email on suppression list | Send blocked |
| CAN-SPAM compliance | Any rendered email | Physical address present, unsubscribe link present |
| Sequence scheduling | Initial + 2 follow-ups | Correct day spacing (0, 3, 7) |
| Stop condition: reply | Business replied | Follow-ups cancelled |
| Stop condition: bounce | Email bounced | Marked ineligible, no follow-ups |
| Daily limit | 50 emails queued, limit = 30 | Only 30 sent today, 20 queued for tomorrow |
| Adapter interface | Switch from Resend to Instantly | Same outreach_manager code works |

**Eval frontend surface:**
- Input: select experiment + batch of businesses
- Email preview: rendered email per business per variant
- "Send Test" button (sends to your own email for review)
- "Start Sending" button (with daily limit and confirmation)
- Send queue: pending / sent / bounced / suppressed
- Sequence tracker: which follow-up stage each business is at

---

### M14: Response Tracking + Reply Classification

**Spec reference:** Experiment Framework, §8 (Phase E5)

**What it does:** Ingests email events (open, click, bounce, reply) via webhooks. Classifies replies using LLM. Computes engagement scores per business.

**Dependencies:** M3 (LLM Client), M13 (Outreach Delivery — event webhooks)

**Files to create:**
```
src/
  experiment/
    event_tracker.py           # Webhook handler for email events
    reply_classifier.py        # LLM-based reply classification
    engagement_scorer.py       # Per-business engagement score
  supabase/
    functions/
      track-email-event/
        index.ts               # Edge Function: receive email platform webhooks
      track-audit-view/
        index.ts               # Edge Function: receive audit page tracking events
  tests/
    test_event_tracker.py
    test_reply_classifier.py
    test_engagement_scorer.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Open tracking | Simulate open webhook | Event logged with correct business_id |
| Click tracking | Simulate click webhook | Event logged, audit URL extracted |
| Reply: positive | "Yes I'd love to learn more about fixing my SEO" | POSITIVE_INTENT, confidence > 0.8 |
| Reply: negative | "Stop emailing me" | NEGATIVE, confidence > 0.8 |
| Reply: already handled | "We already work with an SEO company" | ALREADY_HANDLED |
| Engagement score | Business that opened + clicked + replied positively | Score > 70 |
| Engagement score | Business with no events | Score = 0 |
| Audit page tracking | Load hosted audit | page_load event logged |

**Eval frontend surface:**
- Event feed: real-time stream of incoming events per experiment
- Per-business timeline: all events for one business in chronological order
- Reply inbox: classified replies with LLM confidence scores
- Override: manually correct a misclassified reply
- Engagement leaderboard: businesses ranked by engagement score

---

### M15: Experiment Analysis + Rentability Signal

**Spec reference:** Experiment Framework, §9 (Phase E6)

**What it does:** Analyzes completed experiments. Computes variant-level metrics, A/B comparisons, and the rentability signal that feeds back into Widby's scoring model.

**Dependencies:** M14 (Response Tracking output), M2 (Supabase — writes rentability_signals table)

**Files to create:**
```
src/
  experiment/
    experiment_analyzer.py     # Compute all experiment-level metrics
    ab_analysis.py             # Bayesian A/B comparison
    rentability_signal.py      # Compute + write rentability signal
  tests/
    test_experiment_analyzer.py
    test_ab_analysis.py
    test_rentability_signal.py
```

**Eval criteria:**
| Test | Method | Pass Criteria |
|------|--------|--------------|
| Metric computation | Completed experiment | All rates computed correctly (open, click, reply, intent) |
| A/B comparison | Two-variant experiment | Bayesian probability computed, significance flagged at >90% |
| Breakdown by segment | Experiment with varied businesses | reply_rate_by_review_bucket populated |
| Rentability score | Experiment with 5% response rate, 2% intent rate | Score between 40-70 |
| Rentability score: shrinkage | Experiment with only 10 businesses | Score pulled toward 50 (uncertain) |
| Signal write | Analysis complete | Row upserted in rentability_signals table |
| Widby integration | Load rentability signal in scoring engine | Monetization score incorporates behavioral data |

**Eval frontend surface:**
- Experiment selector: pick a completed experiment
- Results dashboard: funnel metrics (delivered → opened → clicked → replied → positive intent → referral)
- A/B comparison panel: side-by-side variant metrics with significance indicator
- Segment breakdown: response rates by review bucket, site quality, GBP completeness
- Rentability score display with confidence level
- "Push to Widby" button: writes the rentability signal to the scoring model

---

### M16: Eval Frontend

**Spec reference:** All modules

**What it does:** Unified internal dashboard that provides eval surfaces for every module. Not a customer-facing product — this is your experiment and evaluation workbench.

**Architecture:** Simple Next.js app (or even plain HTML + JS if faster to build) deployed on Vercel. Calls Supabase directly for data and Python backend for pipeline operations.

**Pages:**
```
/                          # Dashboard: system health, recent runs, costs
/data/serp-explorer        # M0: Manual API call tester
/data/metros               # M1: Metro browser + geo scope expansion
/pipeline/keywords         # M4: Keyword expansion tester
/pipeline/collection       # M5: Data collection runner + browser
/pipeline/signals          # M6: Signal extraction viewer
/pipeline/scoring          # M7: Scoring engine + sensitivity analysis
/pipeline/classification   # M8: Archetype + guidance viewer
/pipeline/report           # M9: Full report viewer
/experiment/discovery      # M10: Business discovery + qualification
/experiment/scanning       # M11: Site scanner
/experiment/audits         # M12: Audit generator + preview
/experiment/outreach       # M13: Outreach delivery manager
/experiment/tracking       # M14: Event feed + reply inbox
/experiment/analysis       # M15: Experiment results + rentability
```

**Build approach:** Scaffold the shell with navigation in Phase 1. Add page content as each module is built. Each module's eval section above describes the frontend surface for its corresponding page.

---

## Development Docs Package

To begin spec-driven development in Cursor, you need these files in your project:

```
docs/
  specs/
    algo-spec-v1.1.md                    # Full algo spec (already written)
    outreach-experiment-framework.md      # Full experiment spec (already written)
    product-breakdown.md                  # This document
  
  architecture/
    module-dependency-graph.md            # Which modules depend on which
    data-flow.md                          # How data flows between modules
    supabase-schema.sql                   # Complete schema (from spec)
  
  api-reference/
    dataforseo-endpoints.md              # Quick reference for all DFS endpoints used
    claude-prompts.md                    # All LLM prompts collected in one place
  
  eval/
    eval-criteria-master.md              # All eval criteria from all modules in one list
    test-fixtures.md                     # Expected inputs/outputs for key test cases

.cursor/
  agents.md                              # Cursor agent instructions (how to build with these specs)

src/                                     # Python backend
  clients/                               # External service wrappers (DataForSEO, Claude)
  pipeline/                              # Scoring pipeline modules (M4-M9)
  experiment/                            # Outreach experiment modules (M10-M15)
  scoring/                               # Scoring engine (M7)
  classification/                        # Classification + guidance (M8)
  data/                                  # Metro database + seed data (M1)

tests/
  unit/                                  # Fast tests, no network, mock external deps
  integration/                           # Real API calls, tagged @pytest.mark.integration
  fixtures/                              # Shared mock data and expected outputs
  conftest.py                            # Shared pytest config, markers, base fixtures

supabase/
  migrations/                            # SQL migration files
  functions/                             # Edge Functions (TypeScript)

frontend/                                # Eval frontend (Next.js or HTML)

pyproject.toml                           # Python project config with pytest settings
```