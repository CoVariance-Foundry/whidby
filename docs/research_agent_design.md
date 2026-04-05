# Research Agent Design

**Version:** 0.1 — Initial
**Date:** 2026-04-04
**Status:** Implementation Complete

---

## 1. Purpose

The research agent is an autonomous system that systematically improves Widby's niche scoring algorithm. It identifies weaknesses in scoring outputs, generates hypotheses about parameter adjustments, runs controlled experiments, evaluates results, and produces evidence-based recommendations — all in iterative loops modeled after the Ralph autonomous agent pattern.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     RESEARCH AGENT                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ORCHESTRATION                                                   │
│  ├── DeepAgentCoordinator (LangChain Deep Agents SDK)            │
│  ├── RalphResearchLoop (iterative experiment loop)               │
│  └── CLI Entrypoint (run_research_agent.py)                      │
│                                                                  │
│  HYPOTHESIS LAYER                                                │
│  ├── HypothesisGenerator (weak-proxy pattern detection)          │
│  └── ExperimentPlanner (structured experiment design)            │
│                                                                  │
│  EVALUATION LAYER                                                │
│  ├── Evaluator (baseline vs candidate scoring comparison)        │
│  └── Recommender (prioritized improvement synthesis)             │
│                                                                  │
│  MEMORY LAYER                                                    │
│  ├── FilesystemStore (artifacts, progress, replay bundles)       │
│  └── ResearchGraphStore (hypothesis/evidence knowledge graph)    │
│                                                                  │
│  TOOL ADAPTERS                                                   │
│  ├── DataForSEO tools (SERP, keywords, business, backlinks)     │
│  ├── MetroDB tools (geo scope expansion)                         │
│  └── LLM tools (keyword expansion, intent, generation)          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Ralph Loop Semantics

Each research session runs an iterative loop inspired by [snarktank/ralph](https://github.com/snarktank/ralph):

```
┌─────────────────────────────────────────────┐
│            RALPH RESEARCH LOOP               │
│                                              │
│  1. SELECT TASK                              │
│     Pick highest-priority pending hypothesis │
│                    │                         │
│                    ▼                         │
│  2. RUN EXPERIMENT                           │
│     Execute via tools, record artifacts      │
│                    │                         │
│                    ▼                         │
│  3. EVALUATE                                 │
│     Compare baseline vs candidate scores     │
│                    │                         │
│                    ▼                         │
│  4. RECORD LEARNING                          │
│     Persist to filesystem + promote to graph │
│                    │                         │
│                    ▼                         │
│  5. REPRIORITIZE                             │
│     Update backlog based on new evidence     │
│                    │                         │
│                    ▼                         │
│  ── Check stop conditions ──                 │
│     max_iterations? convergence? budget?     │
│     backlog empty?                           │
│                    │                         │
│            (loop or exit)                    │
└─────────────────────────────────────────────┘
```

### Stop Conditions

| Condition | Default | Description |
|-----------|---------|-------------|
| max_iterations | 10 | Hard cap on loop cycles |
| convergence | 3 iterations, delta < 0.01 | No meaningful improvement across recent runs |
| budget_exceeded | $50 USD | Cumulative API cost limit |
| backlog_empty | — | All hypotheses processed |

---

## 4. Hybrid Memory Architecture

### Filesystem Memory (Short/Medium Horizon)

Stores per-iteration operational state:

```
research_runs/{run_id}/
  progress.jsonl           # append-only learning log
  backlog.json             # current hypothesis backlog
  loop_state.json          # crash recovery state
  experiment_results/      # per-experiment snapshots
    {experiment_id}.json
  tool_outputs/            # raw tool responses for replay
    {step}_{tool}.json
  snapshots/               # scoring comparison snapshots
    baseline.json
    candidate_{n}.json
  knowledge_graph.json     # graph memory persistence
```

### Graph Memory (Long Horizon Reasoning)

NetworkX-backed directed graph with JSON persistence:

- **Node types:** hypothesis, experiment, proxy_metric, recommendation, observation
- **Edge types:** supports, contradicts, derived_from, supersedes, tested_by
- **Key queries:**
  - `invalidated_hypotheses()` — avoid repeating failed ideas
  - `strongest_evidence_for(node_id)` — rank supporting evidence
  - `lineage(node_id)` — trace derivation chain
  - `neighborhood(node_id, depth)` — explore related concepts

### Promotion Policy

1. New observations land in filesystem artifacts first
2. Only validated experiment outcomes are promoted to graph memory
3. Every graph write includes a `provenance_artifact` pointer to the filesystem
4. Recommendation generation reads both: fresh run context + historical graph

---

## 5. Hypothesis Generation

The generator identifies scoring weaknesses by analyzing proxy score distributions:

| Proxy | Signals Analyzed | Spec Section |
|-------|-----------------|--------------|
| demand | effective_search_volume, volume_breadth, transactional_ratio | §7.1 |
| organic_competition | avg_top5_da, local_biz_count, lighthouse_performance | §7.2 |
| local_competition | review_counts, review_velocity, gbp_completeness | §7.3 |
| monetization | avg_cpc, business_density, lsa_present | §7.4 |
| ai_resilience | aio_trigger_rate, transactional_keyword_ratio, paa_density | §7.5 |

Weakness patterns generate approach-specific hypotheses:
- `keyword_expansion_tuning` — adjust KD/volume filters
- `da_ceiling_adjustment` — modify DA scoring breakpoints
- `review_barrier_recalibration` — tune review count barriers
- `cpc_floor_adjustment` — recalibrate CPC baseline
- `aio_rate_threshold_tuning` — adjust AIO scoring breakpoints

---

## 6. Experiment Contracts

Every experiment plan includes:

| Field | Description |
|-------|-------------|
| target_proxy | Which scoring dimension is being tested |
| modifications | Specific parameter changes with current/candidate values |
| expected_direction | Whether the change should increase or decrease the score |
| minimum_detectable_change | Minimum delta to consider meaningful |
| rollback_condition | When to revert the modification |
| sample_requirements | Minimum metros, keywords for validity |

---

## 7. Tool Contracts

### DataForSEO Adapters

| Tool | Wraps | Purpose |
|------|-------|---------|
| fetch_serp_organic | DataForSEOClient.serp_organic | Organic SERP data |
| fetch_serp_maps | DataForSEOClient.serp_maps | Maps/local pack data |
| fetch_keyword_volume | DataForSEOClient.keyword_volume | Search volume metrics |
| fetch_keyword_suggestions | DataForSEOClient.keyword_suggestions | Related keywords |
| fetch_business_listings | DataForSEOClient.business_listings | Local business data |
| fetch_google_reviews | DataForSEOClient.google_reviews | Review metrics |
| fetch_backlinks_summary | DataForSEOClient.backlinks_summary | Domain authority data |
| fetch_lighthouse | DataForSEOClient.lighthouse | Performance audits |

### Research-Specific Tools

| Tool | Purpose |
|------|---------|
| generate_research_hypotheses | Analyze scoring results, produce hypothesis backlog |
| plan_research_experiment | Convert hypothesis to structured experiment plan |
| propose_novel_hypothesis | Free-form hypothesis from agent reasoning |
| expand_geo_scope | Metro resolution for geographic targeting |
| expand_keywords | LLM-powered keyword expansion |
| classify_search_intent | Search intent classification |

---

## 8. Failure Modes

| Failure | Behavior |
|---------|----------|
| API rate limit | Tool returns error; loop continues to next hypothesis |
| Experiment runner exception | Hypothesis marked `failed`; loop continues |
| Evaluation exception | Hypothesis marked `eval_failed`; loop continues |
| Budget exceeded | Loop exits with `BUDGET_EXCEEDED` stop reason |
| Graph write failure | Logged as warning; filesystem remains source of truth |
| Crash mid-iteration | `loop_state.json` enables resume from last checkpoint |

---

## 9. Usage

### CLI

```bash
# Run with demo data
python -m src.research_agent.run_research_agent

# Run with real scoring input
python -m src.research_agent.run_research_agent \
    --scoring-input path/to/scores.json \
    --max-iterations 15 \
    --budget 25.0 \
    --graph-path research_graph.json \
    --output report.md

# Custom run ID for tracking
python -m src.research_agent.run_research_agent --run-id my-experiment-01
```

### Programmatic

```python
from src.research_agent.deep_agent import run_research_session
from src.research_agent.loop.ralph_loop import LoopConfig

result = run_research_session(
    scoring_results=my_scoring_data,
    config=LoopConfig(max_iterations=10, budget_limit_usd=25.0),
    graph_path="persistent_graph.json",
)

print(result["report"])
for rec in result["recommendations"]:
    print(f"  {rec['title']} — impact={rec['impact_score']:.3f}")
```

---

## 10. Testing

```bash
# All research agent unit tests (no API keys needed)
pytest tests/unit/test_research_agent_loop.py -v
pytest tests/unit/test_hypothesis_generator.py -v
pytest tests/unit/test_recommendation_engine.py -v
pytest tests/unit/test_graph_memory_store.py -v

# Full unit test suite
pytest tests/unit/ -v
```

---

## 11. Docker Setup

The API runs in Docker to avoid architecture-specific binary issues (e.g., pydantic arm64/x86 mismatch on Apple Silicon).

### Local Dev

```bash
# Start the API in Docker (builds image, mounts source for hot-reload)
npm run dev:api

# Or use docker compose directly
docker compose up api --build

# Fallback: run without Docker (if your local Python env is clean)
npm run dev:api:local
```

Docker Compose mounts `./src` and `./research_runs` so code changes are reflected immediately and run artifacts persist on the host.

### Docker Files

| File | Purpose |
|------|---------|
| `Dockerfile.api` | Production-ready image: Python 3.11-slim, installs from pyproject.toml, runs uvicorn |
| `docker-compose.yml` | Local dev: builds from Dockerfile.api, adds volume mounts, hot-reload, env passthrough |
| `.dockerignore` | Excludes node_modules, apps/, tests/, docs/ from Docker build context |

---

## 12. Production Deployment (Render)

The FastAPI research agent API deploys as a Docker web service on Render. The Next.js frontend stays on Vercel.

```
Browser → Vercel (app.thewidby.com) → /api/agent/* proxy → Render (api.thewidby.com) → FastAPI
```

### Deploy to Render

1. Create a **Web Service** on Render, connect your GitHub repo
2. Set the following:
   - **Environment:** Docker
   - **Dockerfile Path:** `Dockerfile.api`
   - **Instance Type:** Starter ($7/mo)
3. Add a **Persistent Disk** mounted at `/data` (1GB free tier)
4. Set environment variables:
   - `ANTHROPIC_API_KEY`
   - `DATAFORSEO_LOGIN`
   - `DATAFORSEO_PASSWORD`
   - `RESEARCH_RUNS_DIR=/data/research_runs`
   - `RESEARCH_GRAPH_PATH=/data/research_graph.json`
5. Optionally add a custom domain: `api.thewidby.com`

### Connect Frontend to API

On Vercel, set the environment variable for the `nichefinder-app` project:

```
NEXT_PUBLIC_API_URL=https://api.thewidby.com
```

The Next.js proxy routes in `apps/app/src/app/api/agent/` forward requests to this URL.

### Required Environment Variables (Production)

| Variable | Where | Purpose |
|----------|-------|---------|
| `ANTHROPIC_API_KEY` | Render | Claude API for LLM client |
| `DATAFORSEO_LOGIN` | Render | DataForSEO API auth |
| `DATAFORSEO_PASSWORD` | Render | DataForSEO API auth |
| `RESEARCH_RUNS_DIR` | Render | Path to persistent volume for run artifacts |
| `RESEARCH_GRAPH_PATH` | Render | Path to persistent graph JSON |
| `NEXT_PUBLIC_API_URL` | Vercel | URL of the Render API service |
