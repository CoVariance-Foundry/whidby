# Deep Agent Deployment Audit

**Date:** 2026-04-06
**Scope:** Research agent deployment workflows, runtime architecture, service dependencies, and observability posture.
**Status:** Updated post-implementation of Claude-native agent (009-claude-native-agent branch).

---

## 1. Core Executable Workflows

### 1.1 CLI -- Direct Research Session

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
3. For each hypothesis, `claude_experiment_runner` creates a `ClaudeAgent` with all plugins, which reasons about tools and produces real candidate scores via M7.
4. Writes the final markdown report to `--output` (or stdout).
5. Logs session summary (iterations, stop reason, cost) to stderr via `logging.INFO`.

**Artifacts produced:** `research_runs/{run_id}/` directory with `progress.jsonl`, `backlog.json`, `loop_state.json`, `snapshots/`, `experiment_results/` (now containing real non-zero scores).

---

### 1.2 FastAPI Bridge -- Docker Dev

**Command:**
```bash
npm run dev:api          # docker compose up api --build
# OR
docker compose up api --build
```

**Entrypoint:** `src/research_agent/api.py` mounted as `src.research_agent.api:app`.

**Docker setup:**
- `Dockerfile.api`: Python 3.11-slim, installs from `pyproject.toml` (no LangChain/DeepAgents deps), runs uvicorn.
- `docker-compose.yml`: Builds from `Dockerfile.api`, maps ports `8000:8000`, mounts `./src` and `./research_runs` for hot-reload + artifact persistence, passes `.env` file.
- Named volume `research_graph` mounted at `/data` for graph persistence across container restarts.

---

### 1.3 FastAPI Bridge -- Local (No Docker)

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
| POST | `/api/sessions` | Start a new research session | Calls `run_research_session()` with Claude agent |
| GET | `/api/sessions` | List all session run IDs with summaries | Reads `loop_state.json` from each run |
| GET | `/api/sessions/{run_id}` | Full session detail (outcome, progress, backlog) | Reads all artifacts via `FilesystemStore` |
| POST | `/api/chat` | Chat-based hypothesis generation (V1 simplified) | Calls `generate_novel_hypothesis()` |
| GET | `/api/graph` | Full knowledge graph for visualization | Reads `GRAPH_PATH` via `ResearchGraphStore` |
| GET | `/api/graph/{node_id}/neighborhood` | Neighborhood of a graph node | `ResearchGraphStore.neighborhood()` |
| GET | `/api/experiments/{run_id}` | List experiment results for a run | Reads `experiment_results/*.json` via `FilesystemStore` |

**Liveness / health:** **`GET /health`** returns `{"status": "ok"}` (200). Use this for Render health checks and external monitoring.

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

---

### 1.6 Production Deployment

**Target architecture:**
```
Browser -> Vercel (app.thewidby.com) -> /api/agent/* proxy -> Render (whidby-1.onrender.com) -> FastAPI
```

**Render (verified via Render MCP, Whidby workspace):** Web service **`whidby-1`**, URL **`https://whidby-1.onrender.com`**, Docker **`./Dockerfile.api`**, internal port **10000** (Render sets **`PORT`**; image must listen on it). Repo **`CoVariance-Foundry/whidby`**, branch **`main`**, region **Oregon**, latest deploy **live**. Service dashboard: `https://dashboard.render.com/web/srv-d78t9ruuk2gs73e177u0`.

**Vercel:** Set **`NEXT_PUBLIC_API_URL=https://whidby-1.onrender.com`** for `nichefinder-app`. Without it, proxies default to `localhost:8000` and return **502**.

**Render setup checklist:**
1. Web Service with Docker, `Dockerfile.api` at repo root.
2. Persistent disk at **`/data`** (confirm in Dashboard; MCP service payload may omit disk details).
3. Env vars: `ANTHROPIC_API_KEY`, `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`, `RESEARCH_RUNS_DIR=/data/research_runs`, `RESEARCH_GRAPH_PATH=/data/research_graph.json`.
4. Optional: commit **`render.yaml`** at repo root — example embedded in `docs/research_agent_design.md` §12.
5. Set **Health Check Path** in Render to **`/health`** (returns `200` with `{"status": "ok"}`).

---

### 1.7 CI -- Quality Gates

**Trigger:** Pull request to `main` (`.github/workflows/quality-gates.yml`).

**Jobs:**
| Job | What It Runs |
|-----|-------------|
| `python-quality` | `ruff check src/ tests/` + `pytest tests/unit/ -v --tb=short` |
| `web-quality` | `npm ci` + `npm run lint` |
| `spec-artifact-check` | Custom bash script validating spec artifacts for module changes |
| `docs-sync-check` | Custom bash script checking architecture docs updated for interface changes |

---

### 1.8 Unit Tests

```bash
# Plugin system + Claude agent (36 new tests)
pytest tests/unit/test_plugin_registry.py tests/unit/test_scoring_plugin.py \
       tests/unit/test_claude_agent.py tests/unit/test_experiment_runner.py -v

# Existing research agent tests
pytest tests/unit/test_research_agent_loop.py tests/unit/test_hypothesis_generator.py \
       tests/unit/test_recommendation_engine.py tests/unit/test_graph_memory_store.py -v

# Full suite: 217 tests
pytest tests/unit/ -v
```

All run without API keys. The Anthropic client is mocked in agent tests.

---

## 2. Runtime Design and Implementation

### 2.1 Orchestration Path

The runtime path uses the Claude-native agent with plugin registry:

```
run_research_session() [deep_agent.py]
  |
  +-- generate_hypotheses() [hypothesis/generator.py]
  |     Rule-based: analyze scoring results, identify weak proxies,
  |     produce structured hypothesis dicts.
  |     Checks graph for previously invalidated hypotheses.
  |
  +-- RalphResearchLoop.run() [loop/ralph_loop.py]
  |     For each iteration:
  |       1. select_task() — highest-priority pending hypothesis
  |       2. claude_experiment_runner() [agent/__init__.py]:
  |          a. Creates PluginRegistry with 4 plugins (Scoring,
  |             DataForSEO, Metro, LLM)
  |          b. Creates ClaudeAgent with registry
  |          c. Agent reasons about tools, calls them via registry
  |          d. ScoringPlugin calls M7 compute_batch_scores()
  |          e. Returns real candidate_scores with cost tracking
  |       3. evaluator() — compares baseline vs candidate with
  |          real non-zero deltas
  |       4. record learning to filesystem + promote to graph
  |       5. reprioritize backlog based on evidence
  |
  +-- synthesize_recommendations() [recommendations/recommender.py]
  |     Filters validated results, generates prioritized recommendations.
  |
  +-- generate_improvement_report() [recommendations/recommender.py]
        Formats a markdown report with real evidence.
```

### 2.2 Persistence Model

**Filesystem Store** (`src/research_agent/memory/filesystem_store.py`):

```
research_runs/{run_id}/
  progress.jsonl           <- append-only, one JSON line per event
  backlog.json             <- overwritten each iteration
  loop_state.json          <- overwritten each iteration (crash recovery)
  experiment_results/
    {experiment_id}.json   <- real candidate scores + tool call audit log
  tool_outputs/
    {step}_{tool}.json     <- tool responses for replay
  snapshots/
    baseline.json          <- set once before loop
```

**Graph Store** (`src/research_agent/memory/graph_store.py`):

- NetworkX `DiGraph` with JSON persistence via `nx.node_link_data`.
- Persists on every add/update operation (eager write).
- Graph nodes now carry real delta values as confidence weights.

---

## 3. Systems and Services Inventory

### 3.1 External Services

| Service | Client | Used For | Env Vars | Live in Default Path? |
|---------|--------|----------|----------|----------------------|
| **Anthropic Claude API** | `src/clients/llm/client.py` (`LLMClient`) + `ClaudeAgent` | Agent reasoning (tool-use), keyword expansion, intent classification | `ANTHROPIC_API_KEY` | **Yes** -- ClaudeAgent calls it for every experiment |
| **DataForSEO API** | `src/clients/dataforseo/client.py` (`DataForSEOClient`) | SERP, keyword, business, review, backlink, Lighthouse data | `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` | **Yes** -- via DataForSEOPlugin when Claude requests data |

### 3.2 Internal Components

| Component | Location | Role |
|-----------|----------|------|
| `ClaudeAgent` | `src/research_agent/agent/claude_agent.py` | Anthropic SDK tool-use loop for experiment reasoning |
| `PluginRegistry` | `src/research_agent/plugins/base.py` | Modular tool loading and dispatch |
| `ScoringPlugin` | `src/research_agent/plugins/scoring_plugin.py` | Wraps M7 `compute_batch_scores()` for re-scoring |
| `DataForSEOPlugin` | `src/research_agent/plugins/dataforseo_plugin.py` | Wraps 8 DataForSEO API tools |
| `MetroDBPlugin` | `src/research_agent/plugins/metro_plugin.py` | Wraps geographic scope expansion |
| `LLMPlugin` | `src/research_agent/plugins/llm_plugin.py` | Wraps keyword/intent/generation tools |
| `HypothesisGenerator` | `src/research_agent/hypothesis/generator.py` | Rule-based weakness detection |
| `ExperimentPlanner` | `src/research_agent/hypothesis/experiment_planner.py` | Structured experiment plans |
| `Evaluator` | `src/research_agent/evaluation/evaluator.py` | Baseline vs candidate comparison |
| `Recommender` | `src/research_agent/recommendations/recommender.py` | Prioritized improvement synthesis |
| `FilesystemStore` | `src/research_agent/memory/filesystem_store.py` | Per-run artifact persistence |
| `ResearchGraphStore` | `src/research_agent/memory/graph_store.py` | NetworkX knowledge graph |
| `MetroDB` | `src/data/metro_db.py` | Static CBSA seed data |

### 3.3 Dependencies (Post-Cleanup)

Removed: `deepagents`, `langgraph`, `langchain-core`, `langchain-anthropic`.

Remaining in `pyproject.toml`:
- `anthropic` -- Claude SDK for agent reasoning and LLM tools
- `httpx` -- async HTTP for DataForSEO
- `supabase` -- database persistence
- `pydantic>=2` -- data validation
- `networkx` -- knowledge graph
- `fastapi` -- API bridge
- `uvicorn[standard]` -- ASGI server

---

## 4. Logging and Observability

### 4.1 Log Points

**`claude_agent.py`:**
- `INFO` -- Tool executed: name, latency, cost.
- `INFO` -- Budget exhausted, stopping agent.
- `ERROR` with `exc_info=True` -- Tool execution failure.

**`ralph_loop.py`:**
- `INFO` -- Iteration start/complete with delta, validated, cost.
- `ERROR` with `exc_info=True` -- Experiment/evaluation failures.

**`plugins/base.py`:**
- `ERROR` with `exc_info=True` -- Plugin registration failure (via `register_safe`).

### 4.2 Structured Telemetry

| Artifact | Format | Written By |
|----------|--------|------------|
| `progress.jsonl` | Append-only JSONL with timestamps | `FilesystemStore` |
| `experiment_results/*.json` | Full experiment result with tool_calls audit log | `claude_experiment_runner` |
| `loop_state.json` | Current loop state for crash recovery | `RalphResearchLoop` |

### 4.3 Remaining Gaps

| Capability | Status | Impact |
|------------|--------|--------|
| Structured logging (JSON to stdout) | Missing | Cloud log aggregators can't parse easily |
| Request-ID correlation | Missing | No tracing across API request -> loop -> agent |
| Health check endpoint | Done | **`GET /health`** returns `{"status": "ok"}` with test in `test_research_agent_api.py` |
| Deployment IaC | Done | **`render.yaml`** at repo root matches production service; example also in `docs/research_agent_design.md` §12 |
| Docker build in CI | Missing | `quality-gates.yml` does not test Docker |

---

## 5. Summary

### What Works Now

1. **Real scoring experiments** -- The Claude agent calls M7 `compute_batch_scores()` via the ScoringPlugin, producing real non-zero score deltas. Budget tracking is effective.
2. **AI-powered reasoning** -- Claude reasons about which tools to call for each hypothesis, preferring fast-mode re-scoring for parameter-only experiments.
3. **Modular plugin system** -- Four plugins (Scoring, DataForSEO, Metro, LLM) load independently with failure isolation.
4. **Clean dependency footprint** -- LangChain/DeepAgents removed. Docker builds are faster and cleaner.
5. **Full test coverage** -- 217 unit tests pass, 36 new tests for the agent/plugin system, all without API keys.
6. **Unchanged API surface** -- All FastAPI endpoints, CLI commands, and dashboard proxy routes work without contract changes.

### Resolved Gaps (from initial audit)

| Gap | Resolution |
|-----|-----------|
| Deep Agent was dead code | Replaced with Claude-native `ClaudeAgent` using Anthropic SDK tool-use |
| Experiment runner was a stub | `claude_experiment_runner` produces real candidate scores via M7 |
| Tools were never called | All tools active via plugin registry, called by Claude agent |
| Budget tracking was inert | Real `cost_usd` tracked from tool calls, budget guard effective |
| Unused framework dependencies | `deepagents`, `langgraph`, `langchain-core`, `langchain-anthropic` removed |
