# CLAUDE.md

## Project Overview

**Widby** is a niche discovery and scoring platform for rank-and-rent SEO practitioners. It has three main systems:

1. **Marketing site** (`apps/web/`) — Next.js 16 pre-launch landing page collecting waitlist signups via Supabase + ActiveCampaign
2. **Niche Scoring Engine** (`src/`) — Python 3.11+ pipeline that collects SERP/keyword/business data from DataForSEO, runs it through a multi-signal scoring algorithm, and outputs ranked niche+metro opportunities
3. **Research Agent** (`src/research_agent/`) — LangChain Deep Agents + Ralph loop for autonomous scoring improvement via hypothesis-driven experiments

## Monorepo Structure

This is a Turborepo monorepo. The git root is this directory.

```
apps/
  web/              — Marketing landing page (Next.js 16, deployed as "whidby" on Vercel)
  app/              — Research Agent Dashboard (Next.js 16, port 3001, deploys to app.thewidby.com)
src/                — Python scoring engine (modules M0–M15)
  research_agent/   — Autonomous research agent (Deep Agents + Ralph loop)
tests/              — pytest: unit/, integration/, fixtures/
docs/               — Algo spec, product breakdown, data flow specs
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
pytest tests/unit/test_research_agent_loop.py tests/unit/test_graph_memory_store.py -v  # Agent tests
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

## Specs Are the Source of Truth

| Spec | Location | Covers |
|------|----------|--------|
| Algo Spec V1.1 | `docs/algo_spec_v1_1.md` | Scoring algorithm, signal definitions, API endpoints, output schema |
| Experiment Framework | `docs/outreach_experiment.md` | Business discovery, site scanning, audit generation, outreach, response tracking |
| Product Breakdown | `docs/product_breakdown.md` | Module decomposition, file structure, input/output contracts, eval criteria |
| Module Dependencies | `docs/module_dependency.md` | Build order, which modules depend on which |
| Data Flow | `docs/data_flow.md` | How data moves between modules |
| Research Agent Design | `docs/research_agent_design.md` | Loop semantics, tool contracts, memory architecture, failure modes |

## Environment Variables

Required (see `.env.example`):
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` — Supabase
- `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` — DataForSEO API
- `ANTHROPIC_API_KEY` — Claude API for LLM client
- `ACTIVECAMPAIGN_API_URL`, `ACTIVECAMPAIGN_API_KEY` — Email CRM (web app only)

## TDD Workflow

Tests are written **before** implementation. For each module:
1. Read the module spec in `docs/product_breakdown.md`
2. Create test files from eval criteria
3. Run tests (expect red) → implement → green → refactor → commit

## App-Specific Guidance

See `apps/web/CLAUDE.md` for marketing site details.
