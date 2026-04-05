# Deep Agent Deployment Audit

**Date:** 2026-04-04
**Scope:** Research agent deployment workflows, runtime architecture, service dependencies, and observability posture.

---

## 1. Core Executable Workflows

### 1.1 CLI — Direct Research Session

**Command:**
```bash
python -m src.research_agent.run_research_agent
```

**Flags:**
| Flag | Default | Purpose |
|------|---------|---------|
| `--scoring-input` | demo data | Path to JSON file with scoring results |
| `--run-id` | random 8-char UUID | Identifier for the run |
| `--max-iterations` | 10 | Hard loop cap |
| `--budget` | 50.0 | Max API spend in USD |
| `--graph-path` | None | Persistent knowledge graph JSON path |
| `--output` | stdout | File path for the markdown report |

**Entrypoint:** `src/research_agent/run_research_agent.py` -> `run_research_session()` in `src/research_agent/deep_agent.py`.

**What happens:**
1. Parses CLI args, loads scoring JSON (or falls back to hardcoded demo data).
2. Creates a `LoopConfig` and calls `run_research_session()`.
3. Writes the final markdown report to `--output` (or stdout).
4. Logs session summary (iterations, stop reason, cost) to stderr via `logging.INFO`.

**Artifacts produced:** `research_runs/{run_id}/` directory with `progress.jsonl`, `backlog.json`, `loop_state.json`, `snapshots/`, `experiment_results/`.

---

### 1.2 FastAPI Bridge — Docker Dev

**Command:**
```bash
npm run dev:api          # docker compose up api --build
# OR
docker compose up api --build
```

**Entrypoint:** `src/research_agent/api.py` mounted as `src.research_agent.api:app`.

**Docker setup:**
- `Dockerfile.api`: Python 3.11-slim, installs from `pyproject.toml`, runs uvicorn.
- `docker-compose.yml`: Builds from `Dockerfile.api`, maps ports `8000:8000`, mounts `./src` and `./research_runs` for hot-reload + artifact persistence, passes `.env` file, sets `RESEARCH_RUNS_DIR=/data/research_runs` and `RESEARCH_GRAPH_PATH=/data/research_graph.json`.
- Named volume `research_graph` mounted at `/data` for graph persistence across container restarts.

**Env overrides in Docker:**
| Variable | Container Value |
|----------|----------------|
| `PORT` | 8000 |
| `RESEARCH_RUNS_DIR` | `/data/research_runs` |
| `RESEARCH_GRAPH_PATH` | `/data/research_graph.json` |
| `PYTHONUNBUFFERED` | 1 |

---

### 1.3 FastAPI Bridge — Local (No Docker)

**Command:**
```bash
npm run dev:api:local    # uvicorn src.research_agent.api:app --reload --port 8000
```

Uses local Python environment directly. Artifacts write to `./research_runs/` and `./research_graph.json` relative to working directory.

---

### 1.4 API Endpoint Surface

All endpoints served by `src/research_agent/api.py`:

| Method | Path | Purpose | Implementation |
|--------|------|---------|----------------|
| POST | `/api/sessions` | Start a new research session | Calls `run_research_session()` synchronously |
| GET | `/api/sessions` | List all session run IDs with summaries | Reads `loop_state.json` from each `research_runs/{run_id}/` |
| GET | `/api/sessions/{run_id}` | Full session detail (outcome, progress, backlog) | Reads all artifacts via `FilesystemStore` |
| POST | `/api/chat` | Chat-based hypothesis generation (V1 simplified) | Calls `generate_novel_hypothesis()` only (no LLM) |
| GET | `/api/graph` | Full knowledge graph for visualization | Reads `GRAPH_PATH` via `ResearchGraphStore` |
| GET | `/api/graph/{node_id}/neighborhood` | Neighborhood of a graph node | `ResearchGraphStore.neighborhood()` |
| GET | `/api/experiments/{run_id}` | List experiment results for a run | Reads `experiment_results/*.json` via `FilesystemStore` |

**CORS allowlist:** `http://localhost:3001`, `https://app.thewidby.com`, `https://whidby-1.onrender.com`.

---

### 1.5 Next.js Dashboard (Frontend Proxy)

**Command:**
```bash
npm run dev:app    # turbo dev --filter=nichefinder-app (port 3001)
```

**Proxy routes** in `apps/app/src/app/api/agent/`:

| Route File | Proxies To |
|------------|------------|
| `sessions/route.ts` (GET, POST) | `{API_BASE}/api/sessions` |
| `sessions/[runId]/route.ts` (GET) | `{API_BASE}/api/sessions/{runId}` |
| `chat/route.ts` (POST) | `{API_BASE}/api/chat` |
| `graph/route.ts` (GET) | `{API_BASE}/api/graph` |
| `experiments/[runId]/route.ts` (GET) | `{API_BASE}/api/experiments/{runId}` |

**API base resolution:** `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"` (defined in `apps/app/src/lib/utils.ts`).

**Error handling:** All proxy routes catch fetch errors and return `502` with a JSON error body.

---

### 1.6 Production Deployment

**Documented target architecture:**
```
Browser -> Vercel (app.thewidby.com) -> /api/agent/* proxy -> Render (api.thewidby.com) -> FastAPI
```

**Render setup (manual, no `render.yaml` in repo):**
1. Web Service with Docker environment, `Dockerfile.api`.
2. Persistent disk at `/data` (1GB free tier).
3. Env vars: `ANTHROPIC_API_KEY`, `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`, `RESEARCH_RUNS_DIR=/data/research_runs`, `RESEARCH_GRAPH_PATH=/data/research_graph.json`.
4. Optional custom domain: `api.thewidby.com`.

**Vercel setup:**
- `NEXT_PUBLIC_API_URL=https://api.thewidby.com` on the `nichefinder-app` project.

---

### 1.7 CI — Quality Gates

**Trigger:** Pull request to `main` (`.github/workflows/quality-gates.yml`).

**Jobs:**
| Job | What It Runs |
|-----|-------------|
| `python-quality` | `ruff check src/ tests/` + `pytest tests/unit/ -v --tb=short` |
| `web-quality` | `npm ci` + `npm run lint` |
| `spec-artifact-check` | Custom bash script validating spec artifacts for module changes |
| `docs-sync-check` | Custom bash script checking architecture docs updated for interface changes |

**Gap:** CI does not build or smoke-test `Dockerfile.api` or Docker Compose. No integration test job. No deployment pipeline (Render deploys on push are configured externally, not in the repo).

---

### 1.8 Unit Tests

```bash
pytest tests/unit/test_research_agent_loop.py -v
pytest tests/unit/test_hypothesis_generator.py -v
pytest tests/unit/test_recommendation_engine.py -v
pytest tests/unit/test_graph_memory_store.py -v
```

All run without API keys or network access.

---

## 2. Runtime Design and Implementation

### 2.1 Orchestration Path

The **live runtime path** uses a deterministic pipeline, not the LangChain Deep Agent:

```
run_research_session() [deep_agent.py]
  |
  +-- generate_hypotheses() [hypothesis/generator.py]
  |     Rule-based: analyze scoring results, identify weak proxies,
  |     produce structured hypothesis dicts. No LLM calls.
  |     Optionally checks graph for previously invalidated hypotheses.
  |
  +-- RalphResearchLoop.run() [loop/ralph_loop.py]
  |     For each iteration:
  |       1. select_task() — highest-priority pending hypothesis
  |       2. experiment_runner() — default_experiment_runner() creates
  |          an experiment plan via plan_experiment() and saves it;
  |          returns cost_usd: 0.0 (no real scoring re-run yet)
  |       3. evaluator() — evaluate_experiment() compares baseline vs
  |          candidate composite scores; since default runner produces
  |          empty candidate_scores, deltas are effectively 0
  |       4. record learning to filesystem + promote to graph
  |       5. reprioritize backlog based on evidence
  |
  +-- synthesize_recommendations() [recommendations/recommender.py]
  |     Filters validated results, generates prioritized recommendation
  |     dicts, promotes high-confidence ones to graph.
  |
  +-- generate_improvement_report() [recommendations/recommender.py]
        Formats a markdown report with summary stats and per-
        recommendation evidence blocks.
```

**Key finding: `create_research_agent()` is dead code on live paths.** It exists in `deep_agent.py` and imports `deepagents.create_deep_agent`, but nothing in the CLI or API entrypoints calls it. The `RESEARCH_TOOLS` list (combining `ALL_TOOLS` + higher-level tools) is assembled but never invoked by the active pipeline.

### 2.2 Ralph Loop Cycle

Each iteration of `RalphResearchLoop.run()` follows 5 stages with 4 stop conditions:

**Stages:**
1. **Select task** — Sort pending hypotheses by priority descending, pick first.
2. **Run experiment** — Delegate to `experiment_runner` callback. On exception: mark hypothesis `failed`, log `error` with `exc_info=True`, append to `progress.jsonl`, continue.
3. **Evaluate** — Delegate to `evaluator` callback. On exception: mark hypothesis `eval_failed`, continue.
4. **Record learning** — Mark hypothesis validated/invalidated, save to `progress.jsonl`, promote hypothesis + experiment nodes to graph with supports/contradicts edge.
5. **Reprioritize** — Boost priority of hypotheses sharing a target proxy with validated results; demote those related to invalidated ones.

**Stop conditions:**
| Condition | Check | Default |
|-----------|-------|---------|
| `BACKLOG_EMPTY` | No pending hypotheses remain | -- |
| `BUDGET_EXCEEDED` | `cumulative_cost >= budget_limit_usd` | $50 |
| `CONVERGENCE` | Last N iterations all had `abs(delta) < threshold` | 3 iters, delta < 0.01 |
| `MAX_ITERATIONS` | Hard cap | 10 |

**Crash recovery:** `loop_state.json` is written before each experiment with current iteration, hypothesis ID, and cumulative cost. On completion, it is overwritten with full `LoopOutcome`. Actual resume-from-checkpoint logic is not implemented.

### 2.3 Persistence Model

**Filesystem Store** (`src/research_agent/memory/filesystem_store.py`):

```
research_runs/{run_id}/
  progress.jsonl           <- append-only, one JSON line per event
  backlog.json             <- overwritten each iteration
  loop_state.json          <- overwritten each iteration (crash recovery)
  experiment_results/
    {experiment_id}.json   <- one per experiment
  tool_outputs/
    {step}_{tool}.json     <- intended for replay; NOT populated by default runner
  snapshots/
    baseline.json          <- set once before loop
    candidate_{n}.json     <- not populated by default runner
```

**Graph Store** (`src/research_agent/memory/graph_store.py`):

- NetworkX `DiGraph` with JSON persistence via `nx.node_link_data`.
- Nodes: `hypothesis`, `experiment`, `proxy_metric`, `recommendation`, `observation`.
- Edges: `supports`, `contradicts`, `derived_from`, `supersedes`, `tested_by`.
- Persists on every add/update operation (eager write).
- Single file: controlled by `RESEARCH_GRAPH_PATH` env var (default `research_graph.json`).
- API endpoint reads this same file for the graph visualization UI.

**Promotion policy:**
1. All experiment outcomes (validated + invalidated) are promoted to graph as hypothesis + experiment node pairs.
2. Edges are typed `SUPPORTS` (validated) or `CONTRADICTS` (invalidated), weighted by `abs(delta)`.
3. Recommendations with `high` or `medium` confidence are promoted to graph as `recommendation` nodes with `DERIVED_FROM` edges back to hypotheses.

---

## 3. Systems and Services Inventory

### 3.1 External Services

| Service | Client | Used For | Env Vars | Live in Default Path? |
|---------|--------|----------|----------|----------------------|
| **Anthropic Claude API** | `src/clients/llm/client.py` (`LLMClient`) | Keyword expansion, intent classification, free-form generation | `ANTHROPIC_API_KEY` | No -- tools are registered but `default_experiment_runner` never calls them |
| **DataForSEO API** | `src/clients/dataforseo/client.py` (`DataForSEOClient`) | SERP, keyword, business, review, backlink, Lighthouse data | `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` | No -- same as above |

Both clients are instantiated lazily inside tool functions (`api_tools.py`), which are only called if a Deep Agent or external caller invokes the LangChain tools. The default `run_research_session` -> `default_experiment_runner` path makes zero external API calls.

### 3.2 Internal Components

| Component | Location | Role |
|-----------|----------|------|
| `HypothesisGenerator` | `src/research_agent/hypothesis/generator.py` | Rule-based weakness detection from proxy score averages |
| `ExperimentPlanner` | `src/research_agent/hypothesis/experiment_planner.py` | Converts hypothesis to structured experiment plan with modifications |
| `Evaluator` | `src/research_agent/evaluation/evaluator.py` | Baseline vs candidate composite score comparison |
| `Recommender` | `src/research_agent/recommendations/recommender.py` | Synthesizes recommendations, generates markdown report |
| `FilesystemStore` | `src/research_agent/memory/filesystem_store.py` | Per-run artifact persistence |
| `ResearchGraphStore` | `src/research_agent/memory/graph_store.py` | NetworkX knowledge graph with JSON persistence |
| `MetroDB` | `src/data/metro_db.py` | Static CBSA seed data, geographic scope expansion |

### 3.3 Tool Registry (Registered but Not Actively Called)

Defined in `src/research_agent/tools/api_tools.py` and `src/research_agent/deep_agent.py`:

**DataForSEO tools (8):** `fetch_serp_organic`, `fetch_serp_maps`, `fetch_keyword_volume`, `fetch_keyword_suggestions`, `fetch_business_listings`, `fetch_google_reviews`, `fetch_backlinks_summary`, `fetch_lighthouse`.

**MetroDB tools (1):** `expand_geo_scope`.

**LLM tools (3):** `expand_keywords`, `classify_search_intent`, `llm_generate`.

**Research tools (3):** `generate_research_hypotheses`, `plan_research_experiment`, `propose_novel_hypothesis`.

All 15 tools are assembled into `RESEARCH_TOOLS` and passed to `create_research_agent()`, which is the dead-code Deep Agent factory.

### 3.4 Cost Tracking (In-Memory Only)

| Tracker | Location | Scope | Persisted? |
|---------|----------|-------|------------|
| `TokenTracker` | `src/clients/llm/token_tracker.py` | Per `LLMClient` instance | No -- lost when process exits |
| `CostTracker` | `src/clients/dataforseo/cost_tracker.py` | Per `DataForSEOClient` instance | No -- comment says "Future: flush to Supabase" |

The Ralph loop tracks `cumulative_cost` from `experiment_result["cost_usd"]`, but the default experiment runner always returns `cost_usd: 0.0`, so the budget guard is ineffective today.

### 3.5 Infrastructure Dependencies

| System | Purpose | IaC in Repo? |
|--------|---------|-------------|
| **Docker** | API containerization | `Dockerfile.api`, `docker-compose.yml` |
| **Render** | Production API hosting | No -- manual setup per docs |
| **Vercel** | Dashboard hosting + proxy | No `vercel.json` in `apps/app`; relies on defaults |
| **GitHub Actions** | CI quality gates | `.github/workflows/quality-gates.yml` |

---

## 4. Logging and Observability

### 4.1 Logging Configuration

| Entrypoint | Config | Format |
|------------|--------|--------|
| `api.py` | `logging.basicConfig(level=logging.INFO)` | Default stdlib (no timestamp) |
| `run_research_agent.py` | `logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")` | Timestamped with module name |

All modules use `logger = logging.getLogger(__name__)` at the module level.

### 4.2 Log Points by Module

**`ralph_loop.py`:**
- `INFO` — Iteration start: hypothesis title, iteration count.
- `INFO` — Iteration complete: delta, validated, cost.
- `ERROR` with `exc_info=True` — Experiment runner exception.
- `ERROR` with `exc_info=True` — Evaluator exception.

**`run_research_agent.py`:**
- `INFO` — Session start with `run_id`.
- `INFO` — Report written to file (if `--output`).
- `INFO` — Session complete summary (iterations, stop reason, cost).

**`graph_store.py`:**
- `WARNING` — Node added without `provenance_artifact`.

**`src/clients/llm/client.py`:**
- `ERROR` with `exc_info=True` — LLM call failure.

**`src/clients/dataforseo/client.py`:**
- `WARNING` — DFS request retry (attempt N).

**`api.py`, `deep_agent.py`, `filesystem_store.py`:**
- Logger declared but no active log statements beyond basicConfig.

### 4.3 Structured Telemetry (File-Based)

| Artifact | Location | Format | Written By |
|----------|----------|--------|------------|
| `progress.jsonl` | `research_runs/{run_id}/progress.jsonl` | Append-only JSONL, one line per event with UTC timestamp | `FilesystemStore.append_progress()` |
| `loop_state.json` | `research_runs/{run_id}/loop_state.json` | JSON, overwritten each iteration | `FilesystemStore.save_loop_state()` |
| `experiment_results/*.json` | Per-experiment snapshot | JSON | `FilesystemStore.save_experiment_result()` |

The dashboard API reads these artifacts to surface session progress, outcomes, and experiment details.

### 4.4 What Is NOT Present

| Capability | Status | Impact |
|------------|--------|--------|
| **Structured logging** (JSON lines to stdout) | Missing | Render/cloud log aggregators can't parse free-text logs easily |
| **Request-ID correlation** | Missing | No way to trace a single API request through FastAPI -> loop -> tools |
| **OpenTelemetry / distributed tracing** | Missing | No spans or trace IDs across HTTP -> Python -> external APIs |
| **LangSmith / LangChain tracing** | Missing | `deepagents`/LangChain dependencies exist but the deep agent path is dead code |
| **Prometheus / metrics endpoint** | Missing | No `/metrics`, no counters for requests, loop iterations, errors, latency |
| **Health check endpoint** | Missing | No `/health` or `/ready` for Render to probe |
| **Centralized log shipping** | Missing | stdout only; no Datadog, Sentry, or cloud logging integration |
| **API request logging middleware** | Missing | FastAPI has no request/response logging middleware |
| **Cost tracking persistence** | Missing | `TokenTracker` and `CostTracker` are in-memory only, lost on restart |
| **Deployment IaC** | Missing | No `render.yaml` in repo; production deploy is a manual checklist |
| **Docker build in CI** | Missing | `quality-gates.yml` does not build or test `Dockerfile.api` |
| **Integration test job** | Missing | No CI job runs integration tests or smoke tests against the API |

---

## 5. Summary of Findings

### What Works Today

1. **CLI research sessions** run end-to-end with demo data, producing artifacts, a knowledge graph, and a markdown report.
2. **FastAPI bridge** serves all CRUD endpoints for sessions, chat, graph, and experiments.
3. **Docker dev workflow** (`npm run dev:api`) provides hot-reload, volume-mounted artifacts, and env passthrough.
4. **Next.js proxy routes** correctly forward all agent API calls with error handling (502 on failure).
5. **Filesystem persistence** is comprehensive: append-only progress, loop state for crash recovery, experiment results, snapshots.
6. **Graph memory** persists across runs via a shared JSON file with typed nodes/edges and neighborhood queries.
7. **Unit tests** cover the loop, hypothesis generator, recommendation engine, and graph store without needing API keys.
8. **CI quality gates** run linting + unit tests on every PR.

### Critical Gaps

1. **Deep Agent is dead code.** `create_research_agent()` and the 15-tool `RESEARCH_TOOLS` registry are never called by any live entrypoint. The `deepagents`, `langgraph`, `langchain-core`, and `langchain-anthropic` dependencies are unused at runtime.

2. **Default experiment runner is a no-op.** It creates an experiment plan and saves it, but returns `cost_usd: 0.0` and empty `candidate_scores`. This means:
   - Budget tracking is ineffective (always $0).
   - Evaluation always sees zero deltas.
   - All hypotheses converge to "invalidated" after the convergence window.

3. **`/api/chat` is not a real deep agent chat.** It calls `generate_novel_hypothesis()`, which is pure string manipulation (UUID + truncated input), no LLM.

4. **No production observability.** Logging is stdlib INFO to stdout with no structure, no request correlation, no metrics, no tracing.

5. **No deployment IaC.** Production Render deploy is manual. No `render.yaml`, no CI/CD deployment step.

6. **Single global graph file.** `GRAPH_PATH` is shared across all sessions and the API graph endpoint. Concurrent sessions can race or corrupt the JSON file.

7. **CORS allowlist is hardcoded.** Preview/branch deploy URLs from Vercel will be blocked unless manually added to `api.py`.

8. **Crash recovery is write-only.** `loop_state.json` is written but there is no resume logic that reads it and continues from the last checkpoint.
