# Research Agent Design

**Version:** 1.0 — Claude-Native Redesign
**Date:** 2026-04-06
**Status:** Implementation Complete

---

## 1. Purpose

The research agent is an autonomous system that systematically improves Widby's niche scoring algorithm. It identifies weaknesses in scoring outputs, generates hypotheses about parameter adjustments, runs controlled experiments using the real M5/M6/M7 scoring pipeline, evaluates results, and produces evidence-based recommendations — all in iterative loops modeled after the Ralph autonomous agent pattern, powered by Claude's native tool-use reasoning.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     RESEARCH AGENT                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ORCHESTRATION                                                   │
│  ├── ClaudeAgent (Anthropic SDK tool-use)                        │
│  ├── PluginRegistry (modular tool loading)                       │
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
│  TOOL PLUGINS                                                    │
│  ├── ScoringPlugin (M5/M6/M7 pipeline for real experiments)     │
│  ├── DataForSEOPlugin (SERP, keywords, business, backlinks)     │
│  ├── MetroDBPlugin (geo scope expansion)                         │
│  └── LLMPlugin (keyword expansion, intent, generation)          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Claude Agent Tool-Use Flow

The experiment runner uses the Anthropic Python SDK's `messages.create()` with the `tools` parameter. Claude reasons about which tools to call for each hypothesis:

```
hypothesis + baseline data
    │
    ▼
ClaudeAgent.run_experiment()
    │
    ├── messages.create(tools=registry.get_tool_definitions())
    │       │
    │       ▼ (stop_reason="tool_use")
    │   PluginRegistry.execute(tool_name, args)
    │       │
    │       ├── ScoringPlugin.rescore_with_modifications → M7 scores
    │       ├── DataForSEOPlugin.fetch_* → raw API data + cost_usd
    │       ├── MetroDBPlugin.expand_geo_scope → metro records
    │       └── LLMPlugin.expand_keywords → keyword set + cost_usd
    │       │
    │       ▼ (tool_result appended to messages)
    │   [loop until end_turn or budget exceeded]
    │
    ▼
ExperimentResult: candidate_scores, cost_usd, tool_calls
```

### Plugin System

The `PluginRegistry` loads self-contained tool plugins at startup. Each plugin declares its tools as Anthropic-compatible schema dicts and handles execution:

| Plugin | Tools | Wraps |
|--------|-------|-------|
| ScoringPlugin | `rescore_with_modifications` | M7 `compute_batch_scores()` |
| DataForSEOPlugin | 8 fetch tools | `DataForSEOClient` |
| MetroDBPlugin | `expand_geo_scope` | `MetroDB` |
| LLMPlugin | `expand_keywords`, `classify_search_intent`, `llm_generate` | `LLMClient` |

Plugins are registered via `registry.register_safe()` which isolates failures — if one plugin fails to load (e.g. missing credentials), others continue.

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
│     ClaudeAgent reasons + calls tools        │
│     via PluginRegistry                       │
│                    │                         │
│                    ▼                         │
│  3. EVALUATE                                 │
│     Compare baseline vs candidate scores     │
│     (real non-zero deltas from M7)           │
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
  experiment_results/      # per-experiment snapshots with real scores
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

### Experiment Runner Output

The `claude_experiment_runner` returns:

```python
{
    "experiment_id": str,
    "cost_usd": float,           # 0.0 for fast mode, real cost for full mode
    "modifications": list[dict],
    "candidate_scores": {
        "metros": [
            {"scores": {"demand": float, "organic_competition": float, ...
                         "opportunity": float}, "cbsa_code": str},
        ]
    },
    "tool_calls": list[dict],    # audit log of all tool invocations
    "plan": dict,                # experiment plan
}
```

### Experiment Modes

**Fast mode (parameter-only, zero API cost):** Claude calls `rescore_with_modifications` which applies signal overrides to baseline data and re-scores via M7's `compute_batch_scores()`.

**Full mode (data refresh, real API cost):** Claude calls DataForSEO tools to gather fresh data, then scores via the M5 → M6 → M7 pipeline. Cost is tracked from each tool call.

---

## 7. Tool Contracts

### Plugin: DataForSEOPlugin

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

### Plugin: ScoringPlugin

| Tool | Wraps | Purpose |
|------|-------|---------|
| rescore_with_modifications | `compute_batch_scores()` (M7) | Re-score baseline with parameter changes |

### Plugin: MetroDBPlugin

| Tool | Wraps | Purpose |
|------|-------|---------|
| expand_geo_scope | `MetroDB.expand_scope()` | Geographic scope expansion |

### Plugin: LLMPlugin

| Tool | Wraps | Purpose |
|------|-------|---------|
| expand_keywords | `LLMClient.keyword_expansion()` | LLM-powered keyword expansion |
| classify_search_intent | `LLMClient.classify_intent()` | Search intent classification |
| llm_generate | `LLMClient.generate()` | Free-form LLM generation |

---

## 8. Failure Modes

| Failure | Behavior |
|---------|----------|
| API rate limit | Tool returns error; agent decides to retry or skip; loop continues |
| Experiment runner exception | Hypothesis marked `failed`; loop continues |
| Evaluation exception | Hypothesis marked `eval_failed`; loop continues |
| Budget exceeded | Agent stops tool calls; loop exits with `BUDGET_EXCEEDED` |
| Tool execution failure | Agent logs error, continues with available data |
| Plugin load failure | `register_safe()` logs error; other plugins still load |
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
# Plugin system tests
pytest tests/unit/test_plugin_registry.py -v
pytest tests/unit/test_scoring_plugin.py -v

# Claude agent tests (mocked Anthropic client, no API key needed)
pytest tests/unit/test_claude_agent.py -v

# Experiment runner tests
pytest tests/unit/test_experiment_runner.py -v

# Existing research agent tests
pytest tests/unit/test_research_agent_loop.py -v
pytest tests/unit/test_hypothesis_generator.py -v
pytest tests/unit/test_recommendation_engine.py -v
pytest tests/unit/test_graph_memory_store.py -v

# Full unit test suite
pytest tests/unit/ -v
```

All unit tests run without API keys. The Anthropic client is mocked in `test_claude_agent.py` and `test_experiment_runner.py`.

---

## 11. Docker Setup

The API runs in Docker for consistent environments.

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

The FastAPI research agent API deploys as a Docker web service on Render. Two Next.js apps consume it on Vercel: **`apps/admin`** (research-agent dashboard at `app.thewidby.com`, Vercel project `whidby-agent`) and **`apps/app`** (consumer product, separate Vercel project). Both apps proxy the same FastAPI bridge via `NEXT_PUBLIC_API_URL`.

**Verified production (Render API, Whidby workspace):** Web service **`whidby-1`**, public URL **`https://whidby-1.onrender.com`**, Docker **`./Dockerfile.api`**, context **`.`**, region **Oregon**, branch **`main`**, repo **`CoVariance-Foundry/whidby`**, latest deploy **live**. Dashboard: `https://dashboard.render.com/web/srv-d78t9ruuk2gs73e177u0`.

```
Browser → Vercel (apps/admin or apps/app) → /api/agent/* proxy → Render (whidby-1.onrender.com) → FastAPI
                                                                       │
                                                                       ├──→ MetroDB seed (autocomplete)
                                                                       └──→ M4-M9 orchestrator → SupabasePersistence → Supabase
```

The FastAPI `/api/niches/score` endpoint runs the end-to-end orchestrator (`src/pipeline/orchestrator.py::score_niche_for_metro`) and writes the M9 report to Supabase via `src/clients/supabase_persistence.py`. Consumer `/reports` reads the same `reports` table via SSR Supabase client (RLS policy from migration 005 grants authenticated SELECT).

Optional later: custom domain **`api.thewidby.com`** (DNS + Render custom domain) — then set `NEXT_PUBLIC_API_URL` to that URL instead.

### Deploy to Render

1. Create a **Web Service** on Render, connect your GitHub repo (production uses **`CoVariance-Foundry/whidby`**; local monorepo clones may use a different remote name).
2. Set the following:
   - **Environment:** Docker
   - **Dockerfile Path:** `Dockerfile.api`
   - **Docker Context:** `.` (repository root)
   - **Instance Type:** Starter (or as needed)
3. Add a **Persistent Disk** mounted at **`/data`** (recommended 1GB+) so `research_runs` and the knowledge graph survive restarts. Align with `RESEARCH_RUNS_DIR` / `RESEARCH_GRAPH_PATH` below.
4. Set environment variables:
   - `ANTHROPIC_API_KEY`
   - `DATAFORSEO_LOGIN`
   - `DATAFORSEO_PASSWORD`
   - `RESEARCH_RUNS_DIR=/data/research_runs`
   - `RESEARCH_GRAPH_PATH=/data/research_graph.json`
5. **HTTP health check:** In the Render Dashboard, set the health check path to **`/health`** (returns `200` with `{"status": "ok"}`).
6. Optionally add a custom domain: `api.thewidby.com`

### Connect Frontend to API

On Vercel, set the environment variable on **both** the admin project (`whidby-agent` serving `app.thewidby.com`) and the consumer project (separate Vercel project, apps/app). Apply to Production and Preview as needed:

```
NEXT_PUBLIC_API_URL=https://whidby-1.onrender.com
```

If this is **unset**, Route Handlers fall back to `http://localhost:8000`, which fails on Vercel — either UI will return **502** for `/api/agent/*` even when Render is healthy.

The Next.js proxy routes in both `apps/admin/src/app/api/agent/` and `apps/app/src/app/api/agent/` forward requests to this URL. Admin carries the full set (sessions/chat/graph/experiments/scoring/exploration/exploration-chat/metros-suggest/health); consumer carries the scoring subset (scoring, metros/suggest, health).

### Example `render.yaml` (Blueprint)

Keep this in a repo root **`render.yaml`** and connect it from the Render Dashboard so infrastructure matches docs. **Do not** commit secret values; use `sync: false` and set keys in the Dashboard.

```yaml
version: "1"
services:
  - type: web
    name: whidby-1
    runtime: docker
    region: oregon
    plan: starter
    branch: main
    dockerfilePath: ./Dockerfile.api
    dockerContext: .
    healthCheckPath: /health
    envVars:
      - key: PYTHONUNBUFFERED
        value: "1"
      - key: RESEARCH_RUNS_DIR
        value: /data/research_runs
      - key: RESEARCH_GRAPH_PATH
        value: /data/research_graph.json
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: DATAFORSEO_LOGIN
        sync: false
      - key: DATAFORSEO_PASSWORD
        sync: false
    disk:
      name: widby-research-data
      mountPath: /data
      sizeGB: 1
```

### Required Environment Variables (Production)

| Variable | Where | Purpose |
|----------|-------|---------|
| `ANTHROPIC_API_KEY` | Render | Claude API for agent reasoning and LLM tools |
| `DATAFORSEO_LOGIN` | Render | DataForSEO API auth |
| `DATAFORSEO_PASSWORD` | Render | DataForSEO API auth |
| `RESEARCH_RUNS_DIR` | Render | Path to persistent volume for run artifacts |
| `RESEARCH_GRAPH_PATH` | Render | Path to persistent graph JSON |
| `NEXT_PUBLIC_API_URL` | Vercel | Public base URL of the Render API (e.g. `https://whidby-1.onrender.com`) |
| `PORT` | Render | Injected by Render; Docker image must bind uvicorn to this port (see `Dockerfile.api`) |

---

## 13. Source Code Layout

```
src/research_agent/
├── __init__.py
├── deep_agent.py              # Session orchestrator (run_research_session)
├── run_research_agent.py      # CLI entrypoint
├── api.py                     # FastAPI bridge
├── agent/                     # Claude-native agent
│   ├── __init__.py            # claude_experiment_runner
│   ├── claude_agent.py        # ClaudeAgent tool-use loop
│   └── prompts.py             # System prompt
├── plugins/                   # Plugin system
│   ├── __init__.py
│   ├── base.py                # ToolPlugin ABC + PluginRegistry
│   ├── scoring_plugin.py      # M7 re-scoring
│   ├── dataforseo_plugin.py   # DataForSEO tools
│   ├── metro_plugin.py        # MetroDB tools
│   └── llm_plugin.py          # LLM tools
├── tools/
│   └── api_tools.py           # Plain adapter functions (no framework deps)
├── hypothesis/
│   ├── generator.py           # Weakness pattern detection
│   └── experiment_planner.py  # Structured experiment plans
├── evaluation/
│   └── evaluator.py           # Baseline vs candidate comparison
├── recommendations/
│   └── recommender.py         # Prioritized improvement synthesis
├── loop/
│   └── ralph_loop.py          # Iterative research loop
└── memory/
    ├── filesystem_store.py    # Per-run artifact persistence
    ├── graph_store.py         # NetworkX knowledge graph
    └── models.py              # Typed graph node/edge schemas
```
