# CLAUDE.md

## Monorepo Structure

This is a Turborepo monorepo for the NicheFinder/Widby project.

```
apps/
  web/     — Marketing landing page (Next.js 16, deployed as "whidby" on Vercel)
  app/     — Research Agent Dashboard (Next.js 16, port 3001, deploys to app.thewidby.com)
packages/
  (none yet)
```

## Commands

```bash
npm run dev          # Dev all apps
npm run build        # Build all apps
npm run dev:web      # Dev marketing site only (port 3000)
npm run dev:app      # Dev product app only (port 3001)
```

## Python Scoring Engine

The niche scoring and outreach engine lives in `src/` (Python 3.11+). See `.cursor/agents.md` for full module specs, build order, and TDD workflow.

```bash
pytest tests/unit/ -v              # Unit tests (no network)
pytest tests/integration/ -v -m integration  # Integration tests (requires API keys)
```

## Research Agent

The autonomous research agent lives in `src/research_agent/` (LangChain Deep Agents + Ralph loop). See `docs/research_agent_design.md` for architecture and operating playbook.

```bash
python -m src.research_agent.run_research_agent              # Run with demo data
python -m src.research_agent.run_research_agent --scoring-input scores.json  # Run with real data
pytest tests/unit/test_research_agent_loop.py tests/unit/test_graph_memory_store.py -v  # Agent tests
```

## Research Agent Dashboard (apps/app)

Interactive frontend for the research agent: chat interface, dashboard, experiments, graph explorer, and recommendations.

```bash
npm run dev:app     # Next.js frontend on port 3001
npm run dev:api     # FastAPI bridge on port 8000 (run in separate terminal)
```

Pages: `/chat` (primary), `/dashboard`, `/experiments`, `/graph`, `/recommendations`

## App-Specific Guidance

See `apps/web/CLAUDE.md` for marketing site details.
