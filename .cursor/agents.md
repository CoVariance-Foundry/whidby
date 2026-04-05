# Widby — Cursor Agent Instructions

You are building Widby, a niche discovery and scoring platform for local SEO practitioners. This file tells you how to work in this codebase.

## Project Context

Widby helps rank-and-rent SEO practitioners find profitable niches and cities to build lead generation websites. The system collects SERP data, keyword metrics, business listings, and review data from DataForSEO APIs, processes it through a multi-signal scoring algorithm, and outputs ranked niche+metro opportunities with actionable guidance.

There are two interconnected systems:
1. **Niche Scoring Engine** — Analyzes markets and scores opportunities (modules M4-M9)
2. **Outreach Experiment Framework** — Validates scoring by measuring real business response to cold outreach (modules M10-M15)

Both share infrastructure: DataForSEO client (M0), Metro database (M1), Supabase schema (M2), and LLM client (M3).

## Specs Are the Source of Truth

All business logic, data schemas, scoring formulas, and signal definitions live in the spec documents. **Always read the relevant spec before implementing.**

| Spec | Location | Covers |
|------|----------|--------|
| Algo Spec V1.1 | `docs/algo_spec_v1_1.md` | Scoring algorithm, signal definitions, API endpoints, output schema |
| Experiment Framework | `docs/outreach_experiment.md` | Business discovery, site scanning, audit generation, outreach, response tracking |
| Product Breakdown | `docs/product_breakdown.md` | Module decomposition, file structure, input/output contracts, eval criteria |
| Module Dependencies | `docs/module_dependency.md` | Build order, which modules depend on which |
| Data Flow | `docs/data_flow.md` | How data moves between modules |

When implementing a module, find it in `product-breakdown.md` first. It tells you:
- Which spec sections to reference
- The exact input/output contract
- Which files to create
- The eval criteria (which become your tests)
- Dependencies on other modules

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Language | Python 3.11+ | All backend code |
| LLM | `anthropic` Python SDK | Direct API calls, NO agent framework |
| Data APIs | DataForSEO REST API | Custom client wrapper in `src/clients/dataforseo/` |
| Database | Supabase (PostgreSQL) | `supabase-py` for Python, Edge Functions in TypeScript |
| Frontend | Next.js or plain HTML | Eval dashboard only — not customer-facing |
| Hosting | Vercel | Frontend + serverless functions if needed |
| Testing | pytest + pytest-asyncio + pytest-mock | TDD approach |

## No Agent Framework

We deliberately chose NOT to use LangGraph, CrewAI, Claude Agent SDK, or any agent orchestration framework. The pipeline is deterministic with fixed execution order — the LLM is a utility, not the orchestrator. Plain Python async functions handle orchestration.

```python
# This is how our pipeline works. Functions calling functions.
async def run_niche_report(niche, geo_scope, geo_target, strategy_profile):
    keywords = await expand_keywords(niche)            # M4: calls Claude via anthropic SDK
    metros = metro_db.expand_scope(geo_scope, geo_target)  # M1: pure Python
    raw_data = await collect_data(keywords, metros)    # M5: calls DataForSEO
    signals = extract_signals(raw_data)                # M6: pure Python
    scores = compute_scores(signals, strategy_profile) # M7: pure Python
    classification = classify(signals, scores)         # M8: pure Python + Claude for guidance
    report = assemble_report(...)                      # M9: pure Python
    await log_feedback(report)                         # M9: Supabase write
    return report
```

When building Sonar (continuous monitoring — future), we may adopt LangGraph for orchestration. Design modules to be framework-agnostic so they can become LangGraph nodes later.

## Test-Driven Development

**Write tests BEFORE implementation. Always.**

### TDD Workflow

1. Read the module spec in `product-breakdown.md`
2. Create the test file(s) based on the eval criteria
3. Run tests — they should all FAIL (red)
4. Implement the module until tests pass (green)
5. Refactor for clarity without breaking tests
6. Commit

### Test Organization

```
tests/
  unit/                    # Fast, no network, mocked external deps
    test_dataforseo_client.py
    test_metro_db.py
    test_llm_client.py
    test_keyword_expansion.py
    test_signal_extraction.py
    test_scoring_engine.py
    ...
  integration/             # Real API calls, slow, require keys
    test_dataforseo_integration.py
    test_llm_integration.py
    test_pipeline_integration.py
    ...
  fixtures/                # Shared test data
    serp_fixtures.py       # Mock DataForSEO SERP responses
    keyword_fixtures.py    # Mock keyword volume responses
    business_fixtures.py   # Mock business listing responses
    llm_fixtures.py        # Mock Claude responses
    signal_fixtures.py     # Pre-computed signal sets for scoring tests
```

### Test Rules

- **Unit tests** run without API keys or network. Use mocks/fixtures for external dependencies.
- **Integration tests** use `@pytest.mark.integration` and are skipped by default in CI.
- Every public function has at least one unit test.
- Every input/output contract from the spec has a corresponding test.
- Test file names match source file names: `src/scoring/demand_score.py` → `tests/unit/test_demand_score.py`
- Fixtures are explicit — no magic conftest.py inheritance chains. Import what you need.

### Running Tests

```bash
# All unit tests (fast, no network)
pytest tests/unit/ -v

# Specific module
pytest tests/unit/test_scoring_engine.py -v

# Integration tests (requires API keys)
pytest tests/integration/ -v -m integration

# With coverage
pytest tests/unit/ --cov=src --cov-report=term-missing
```

### pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "integration: requires real API calls (deselect with '-m \"not integration\"')",
]
testpaths = ["tests"]
```

## Code Patterns

### DataForSEO Client Usage

```python
from src.clients.dataforseo import DataForSEOClient

client = DataForSEOClient(login="...", password="...")

# Standard queue (batch, cheaper, 5-min turnaround)
task_id = await client.serp_organic_post(keyword="plumber", location_code=1012873)
result = await client.serp_organic_get(task_id)  # polls until ready

# Live mode (instant, more expensive)
result = await client.business_listings_search(
    category="Plumber",
    location_code=1012873,
    limit=100
)
```

### LLM Client Usage

```python
from src.clients.llm import LLMClient

llm = LLMClient()  # reads ANTHROPIC_API_KEY from env

# Structured output (keyword expansion)
expansion = await llm.keyword_expansion(niche="plumber")
# Returns parsed, validated KeywordExpansion object

# Classification (intent)
intent = await llm.classify_intent("emergency plumber near me")
# Returns "transactional" | "commercial" | "informational"

# Free-form generation (audit copy)
copy = await llm.generate_audit_copy(
    business_name="Joe's Plumbing",
    scan_results=scan_data,
    value_prop="competitor_comparison"
)
# Returns string
```

### Scoring Functions

Scoring functions are pure — no side effects, no API calls. Input signals, output numbers.

```python
from src.scoring import demand_score, local_competition_score, opportunity_score

# Individual scores
d = demand_score(metro_signals, all_metro_signals)
lc = local_competition_score(metro_signals)

# Composite with strategy profile
opp = opportunity_score(
    demand=d,
    organic_comp=oc,
    local_comp=lc,
    monetization=m,
    ai_resilience=ai,
    strategy_profile="balanced",
    signals=metro_signals
)
```

### Supabase Usage

```python
from supabase import create_client

supabase = create_client(url, key)

# Write
supabase.table("reports").insert(report_data).execute()

# Read
result = supabase.table("rentability_signals") \
    .select("*") \
    .eq("niche_keyword", "plumber") \
    .eq("cbsa_code", "38060") \
    .execute()
```

## Module Build Order

Build in this sequence. Each module should be fully tested before starting the next.

### Phase 1: Foundation (M0 → M1 → M2 → M3)
These have no dependencies on each other and CAN be built in parallel. But M0 and M3 should be done first since everything else uses them.

### Phase 2: Scoring Pipeline (M4 → M5 → M6 → M7 → M8 → M9)
Sequential — each depends on the previous. M6 and M7 are the algorithmic core.

### Phase 3: Experiment Framework (M10 → M11 → M12 → M13 → M14 → M15)
Sequential. Can start as soon as M0, M1, M3 are done (doesn't need M4-M9).

## How to Implement a Module

When I ask you to implement a module (e.g., "build M4"):

1. **Read** `docs/specs/product-breakdown.md` and find the M4 section
2. **Read** the referenced spec sections (Algo Spec V1.1 §4 for M4)
3. **Create the test files first** using the eval criteria as test cases
4. **Create the source files** listed in the module spec
5. **Implement** until all tests pass
6. **Verify** the input/output contract matches the spec exactly

Do not:
- Add abstractions not in the spec
- Introduce external dependencies without asking
- Skip tests for "simple" functions
- Hardcode values that should come from the spec's research constants
- Use any agent framework (LangGraph, CrewAI, etc.)

Do:
- Use type hints everywhere (dataclasses or Pydantic for data structures)
- Make functions async where they involve I/O (API calls, database)
- Keep scoring functions pure (no side effects)
- Reference spec section numbers in code comments for traceability
- Log API costs to the tracking table
- Handle errors gracefully — never crash the pipeline on a single failed API call

## Key Constants

These come from the algo spec's research constants (§16). Import from a central config, don't hardcode:

```python
# src/config/constants.py

# AIO Impact (Algo Spec V1.1, §16)
AIO_CTR_REDUCTION = 0.59
INTENT_AIO_RATES = {
    "transactional": 0.021,
    "commercial": 0.043,
    "informational": 0.436,
}

# Scoring Weights (Algo Spec V1.1, §3.4, §16)
STRATEGY_PROFILES = {
    "organic_first":  {"organic_weight": 0.25, "local_weight": 0.10},
    "balanced":       {"organic_weight": 0.15, "local_weight": 0.20},
    "local_dominant": {"organic_weight": 0.05, "local_weight": 0.35},
}
FIXED_WEIGHTS = {
    "demand": 0.25,
    "monetization": 0.20,
    "ai_resilience": 0.15,
}

# DataForSEO (Algo Spec V1.1, §14)
DFS_BASE_URL = "https://api.dataforseo.com/v3/"
DFS_RATE_LIMIT = 2000  # calls per minute
DFS_CACHE_TTL = 86400  # 24 hours

# LLM (M3 spec)
DEFAULT_MODEL = "claude-sonnet-4-20250514"
CLASSIFICATION_MODEL = "claude-haiku-4-5-20251001"
```

## Project Files Reference

```
nichefinder/                         # Turborepo root (main/)
├── .cursor/
│   └── agents.md                    ← YOU ARE HERE (one level above main/)
├── docs/
│   ├── algo_spec_v1_1.md
│   ├── outreach_experiment.md
│   ├── product_breakdown.md
│   ├── module_dependency.md
│   ├── data_flow.md
│   └── system_design.md
├── apps/
│   ├── web/                         # Marketing landing page (Next.js)
│   └── app/                         # Product app (M16 eval frontend)
├── src/
│   ├── config/
│   │   └── constants.py
│   ├── clients/
│   │   ├── dataforseo/              # M0
│   │   └── llm/                     # M3
│   ├── data/                        # M1
│   ├── pipeline/                    # M4, M5, M6, M9
│   ├── scoring/                     # M7
│   ├── classification/              # M8
│   └── experiment/                  # M10-M15
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── supabase/
│   ├── migrations/                  # M2
│   └── functions/
├── pyproject.toml
├── package.json                     # Turborepo config
└── CLAUDE.md
```