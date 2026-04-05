# Environment & Configuration

<!-- docguard:version 1.0.0 -->
<!-- docguard:status approved -->
<!-- docguard:last-reviewed 2026-04-05 -->
<!-- docguard:owner @widby-team -->

> **Canonical document** — Design intent. This file documents everything needed to run this project.

---

## Prerequisites

| Requirement | Version | Purpose |
|------------|---------|----------|
| Python | 3.11+ | Scoring engine runtime |
| Node.js | 20.x+ | Frontend apps + Turborepo |
| npm | 10.x+ | Package management |
| Supabase CLI | latest | Database migrations |
| ruff | latest | Python linting |

## Environment Variables

| Variable | Required | Default | Description | Where to Get |
|----------|----------|---------|-------------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | — | Supabase project URL | Supabase Dashboard → Settings → API |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | — | Supabase anon/public key | Supabase Dashboard → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | — | Supabase service role key (server-only) | Supabase Dashboard → Settings → API |
| `DATAFORSEO_LOGIN` | Yes | — | DataForSEO API login | app.dataforseo.com |
| `DATAFORSEO_PASSWORD` | Yes | — | DataForSEO API password | app.dataforseo.com |
| `DATAFORSEO_BASE_URL` | No | `https://api.dataforseo.com` | DataForSEO API base URL | — |
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key | console.anthropic.com |
| `ACTIVECAMPAIGN_API_URL` | Yes (web app) | — | ActiveCampaign API base URL | ActiveCampaign → Settings → Developer |
| `ACTIVECAMPAIGN_API_KEY` | Yes (web app) | — | ActiveCampaign API key | ActiveCampaign → Settings → Developer |
| `VERCEL_PROJECT_ID` | No | — | Vercel project ID for deployments | Vercel Dashboard |
| `VERCEL_ORG_ID` | No | — | Vercel organization ID | Vercel Dashboard |

## Configuration Files

| File | Purpose | Template |
|------|---------|----------|
| `.env` / `.env.local` | Local dev secrets | `.env.example` |
| `pyproject.toml` | Python build config, ruff, pytest settings | — |
| `package.json` | Turborepo workspace config | — |
| `apps/web/next.config.ts` | Next.js config (redirects) | — |
| `src/config/constants.py` | Scoring engine constants (AIO rates, weights, thresholds) | — |

## Setup Steps

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in required variables
3. Install Python dependencies: `pip install -e ".[dev]"`
4. Install Node dependencies: `npm install`
5. Run Python tests: `python -m pytest tests/unit/ -v`
6. Run frontend lint: `npm run lint`
7. Start all apps in dev: `npm run dev`

### Individual App Development

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev all apps (Turborepo) |
| `npm run dev:web` | Marketing site only (port 3000) |
| `npm run dev:app` | Research agent dashboard (port 3001) |
| `npm run dev:api` | FastAPI bridge (port 8000) |
| `npm run build` | Production build all apps |

### Python Commands

| Command | Purpose |
|---------|---------|
| `pytest tests/unit/ -v` | Unit tests (no network) |
| `pytest tests/integration/ -v -m integration` | Integration tests (needs API keys) |
| `pytest tests/unit/ --cov=src --cov-report=term-missing` | Coverage report |
| `ruff check src tests` | Python lint |

### Research Agent

| Command | Purpose |
|---------|---------|
| `python -m src.research_agent.run_research_agent` | Run with demo data |
| `python -m src.research_agent.run_research_agent --scoring-input scores.json` | Run with real data |

## DataForSEO API Reference

| Detail | Value |
|--------|-------|
| Base URL | `https://api.dataforseo.com/v3/` |
| Auth | HTTP Basic (login:password) |
| Rate limit | 2000 calls/minute |
| Cache TTL | 24 hours (client-side) |
| Max retries | 3 with exponential backoff |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-04-05 | DocGuard Init | Initial template |
| 1.0.0 | 2026-04-05 | Migration | Populated from CLAUDE.md, apps/web/CLAUDE.md, .env.example |
