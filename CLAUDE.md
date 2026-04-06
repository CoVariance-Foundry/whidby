# CLAUDE.md

## Project Overview

**Widby** is a niche discovery and scoring platform for rank-and-rent SEO practitioners. It has three main systems:

1. **Marketing site** (`apps/web/`) — Next.js 16 pre-launch landing page collecting waitlist signups via Supabase + ActiveCampaign
2. **Niche Scoring Engine** (`src/`) — Python 3.11+ pipeline that collects SERP/keyword/business data from DataForSEO, runs it through a multi-signal scoring algorithm, and outputs ranked niche+metro opportunities
3. **Research Agent** (`src/research_agent/`) — Claude-native tool-use agent + Ralph loop for autonomous scoring improvement via hypothesis-driven experiments

## Monorepo Structure

This is a Turborepo monorepo. The git root is this directory.

```
apps/
  web/              — Marketing landing page (Next.js 16, deployed as "whidby" on Vercel)
  app/              — Research Agent Dashboard (Next.js 16, port 3001, deploys to app.thewidby.com)
src/                — Python scoring engine (modules M0–M15)
  research_agent/   — Autonomous research agent (Anthropic SDK tool-use + Ralph loop)
tests/              — pytest: unit/, integration/, fixtures/
docs-canonical/     — Canonical docs (architecture, requirements, data model, tests, env) — maintained source
docs/               — Detailed reference specs (algo spec, product breakdown, data flow, experiment spec)
packages/           — (none yet)
```

## Commands

### JavaScript (Turborepo)

```bash
npm run dev          # Dev all apps
npm run build        # Build all apps
npm run dev:web      # Marketing site only (port 3000)
npm run dev:app      # Research agent dashboard (port 3001)
```

### Python (Scoring Engine)

```bash
pytest tests/unit/ -v                            # Unit tests (no network)
pytest tests/integration/ -v -m integration      # Integration tests (needs API keys)
pytest tests/unit/ --cov=src --cov-report=term-missing  # With coverage
```

Linting: `ruff` (configured in `pyproject.toml`, line-length 100, target py311).

### Research Agent

```bash
python -m src.research_agent.run_research_agent              # Run with demo data
python -m src.research_agent.run_research_agent --scoring-input scores.json  # Run with real data
npm run dev:api     # FastAPI bridge on port 8000 (run in separate terminal alongside dev:app)
pytest tests/unit/test_plugin_registry.py tests/unit/test_claude_agent.py \
       tests/unit/test_scoring_plugin.py tests/unit/test_experiment_runner.py -v  # Agent + plugin tests
pytest tests/unit/test_research_agent_loop.py tests/unit/test_graph_memory_store.py -v  # Loop + memory tests
```

## Architecture: Scoring Engine

The pipeline is **deliberately not using any agent framework** for V1 scoring (no LangGraph, CrewAI, etc.). It's deterministic Python async functions with fixed execution order. The LLM (Anthropic SDK) is a utility, not an orchestrator.

### Module build order (sequential dependencies)

- **Phase 1 — Foundation:** M0 (DataForSEO client) → M1 (Metro DB) → M2 (Supabase schema) → M3 (LLM client)
- **Phase 2 — Scoring Pipeline:** M4 (keyword expansion) → M5 (data collection) → M6 (signal extraction) → M7 (scoring) → M8 (classification) → M9 (report assembly)
- **Phase 3 — Experiment Framework:** M10–M15 (outreach validation, can start after Phase 1)

### Key design rules

- Scoring functions are **pure** — no side effects, no API calls
- All business logic, schemas, and formulas live in spec docs under `docs/` — read the relevant spec before implementing
- `docs/product_breakdown.md` is the module decomposition reference — it defines file structure, I/O contracts, and eval criteria per module
- Research constants (AIO rates, scoring weights, rate limits) live in `src/config/constants.py`, never hardcoded
- Test file names mirror source: `src/scoring/demand_score.py` → `tests/unit/test_demand_score.py`

## Architecture: Research Agent

The research agent uses **Claude-native tool-use** (Anthropic SDK `messages.create()` with `tools=`) — no agent frameworks. A **plugin registry** loads modular tool plugins (DataForSEO, MetroDB, LLM, Scoring), and a **ClaudeAgent** reasons about which tools to call for each experiment.

### Key components

- `src/research_agent/agent/claude_agent.py` — Tool-use loop: send hypothesis → Claude calls tools → real scores via M7
- `src/research_agent/plugins/base.py` — `ToolPlugin` ABC + `PluginRegistry` with failure isolation
- `src/research_agent/plugins/scoring_plugin.py` — Calls M7 `compute_batch_scores()` for parameter re-scoring
- `src/research_agent/deep_agent.py` — Session orchestrator wiring `claude_experiment_runner` into the Ralph loop

### Design rules

- The Ralph loop is the deterministic outer structure; Claude is a tool within it, not the orchestrator
- Plugins are self-contained: each declares tool schemas and handles execution independently
- Plugin load failures are isolated via `register_safe()` — one failure doesn't break others
- All tool invocations are logged with inputs, outputs, cost, and latency for auditability
- No LangChain, no DeepAgents — same Anthropic SDK as the rest of the pipeline

## Documentation (Canonical-First)

**Read canonical docs first**, then fall back to detailed reference docs for deep context.

### Canonical Docs (`docs-canonical/`)

| Document | Covers |
|----------|--------|
| `docs-canonical/ARCHITECTURE.md` | System overview, module map, dependency graph, tech stack, build sequence |
| `docs-canonical/REQUIREMENTS.md` | Functional/non-functional requirements, success criteria, traceability matrix |
| `docs-canonical/DATA-MODEL.md` | Entity schemas, data flow diagrams, research constants |
| `docs-canonical/TEST-SPEC.md` | Test obligations, coverage rules, quality gates, validation commands |
| `docs-canonical/ENVIRONMENT.md` | Prerequisites, env vars, setup steps, commands |

### Detailed Reference Docs (`docs/`)

| Spec | Location | Covers |
|------|----------|--------|
| Algo Spec V1.1 | `docs/algo_spec_v1_1.md` | Full scoring algorithm, signal definitions, formulas, output schema |
| Experiment Framework | `docs/outreach_experiment.md` | Business discovery, site scanning, audit generation, outreach |
| Product Breakdown | `docs/product_breakdown.md` | Per-module I/O contracts, eval criteria, file trees |
| Module Dependencies | `docs/module_dependency.md` | Full dependency graph and parallel build opportunities |
| Data Flow | `docs/data_flow.md` | Detailed data flow diagrams between all modules |
| Research Agent Design | `docs/research_agent_design.md` | Loop semantics, tool contracts, memory architecture |


## Environment Variables

Required (see `.env.example`):

- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY`, `SUPABASE_SERVICE_ROLE_KEY` — Supabase
- `NEXT_PUBLIC_API_URL` — Research agent FastAPI base URL for `apps/app` proxies (production: Render, e.g. `https://whidby-1.onrender.com`; local: `http://localhost:8000`)
- `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` — DataForSEO API
- `ANTHROPIC_API_KEY` — Claude API for LLM client
- `ACTIVECAMPAIGN_API_URL`, `ACTIVECAMPAIGN_API_KEY` — Email CRM (web app only)

## TDD Workflow

Tests are written **before** implementation. For each module:

1. Read the module spec in `docs/product_breakdown.md`
2. Create test files from eval criteria
3. Run tests (expect red) → implement → green → refactor → commit

## Pre-Commit Quality Gates (MANDATORY)

Before every `git commit && git push` on module code (`src/`), you **must** run the same checks CI enforces:

1. **Lint**: `ruff check src/ tests/` — must pass with zero errors
2. **Unit tests**: `pytest tests/unit/ -v` — all tests must pass
3. **Docs sync**: If any files under `src/pipeline/`, `src/scoring/`, `src/classification/`, `src/experiment/`, `src/clients/`, or `src/data/` are changed, at least one of these docs must also be updated in the same commit:
   - `docs/product_breakdown.md` (I/O contracts, file trees)
   - `docs/module_dependency.md` (dependency changes)
   - `docs/data_flow.md` (data shape changes)
   - If no doc changes are needed, add `[docs-sync-skip]` to the commit message to bypass
4. **Spec artifacts**: If the branch name matches a feature pattern (`NNN-*`), a corresponding `specs/` directory must exist

Skipping these gates results in CI failure on push. Run them locally first.

## Spec-Kit (Spec-Driven Development)

This project uses [github/spec-kit](https://github.com/github/spec-kit) v0.5.0 for all remaining module delivery. The spec-kit workspace lives in `.specify/` and Cursor commands are in `.cursor/commands/speckit.*.md`.

**Mandatory lifecycle for every module (M4-M15, M16 pages):**

1. `/speckit.specify` — Define scope and acceptance criteria
2. `/speckit.clarify` — Resolve ambiguity
3. `/speckit.plan` — Technical implementation plan
4. `/speckit.tasks` — TDD-first task breakdown
5. `/speckit.implement` — Build with hard CI gates

See `docs/spec_workflow_guide.md` for the full workflow, naming conventions, and gate definitions. The project constitution is in `.specify/memory/constitution.md`.

## App-Specific Guidance

See `apps/web/CLAUDE.md` for marketing site details.