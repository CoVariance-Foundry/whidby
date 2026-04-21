# Environment & Configuration

<!-- docguard:version 1.0.2 -->
<!-- docguard:status approved -->
<!-- docguard:last-reviewed 2026-04-06 -->
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
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` | Yes | — | Supabase publishable key (replaces legacy anon key) | Supabase Dashboard → Settings → API Keys |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | — | Supabase service role key (server-only) | Supabase Dashboard → Settings → API |
| `DATAFORSEO_LOGIN` | Yes | — | DataForSEO API login | app.dataforseo.com |
| `DATAFORSEO_PASSWORD` | Yes | — | DataForSEO API password | app.dataforseo.com |
| `DATAFORSEO_BASE_URL` | No | `https://api.dataforseo.com` | DataForSEO API base URL | — |
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key | console.anthropic.com |
| `ACTIVECAMPAIGN_API_URL` | Yes (web app) | — | ActiveCampaign API base URL | ActiveCampaign → Settings → Developer |
| `ACTIVECAMPAIGN_API_KEY` | Yes (web app) | — | ActiveCampaign API key | ActiveCampaign → Settings → Developer |
| `VERCEL_PROJECT_ID` | No | — | Vercel project ID for deployments | Vercel Dashboard |
| `VERCEL_ORG_ID` | No | — | Vercel organization ID | Vercel Dashboard |
| `NEXT_PUBLIC_API_URL` | Yes (both UI apps in production) | `http://localhost:8000` | Base URL of the FastAPI research agent bridge used by `/api/agent/*` Route Handlers in both `apps/admin` and `apps/app`. **Not** used for auth redirects. | Render web service URL, e.g. `https://whidby-1.onrender.com` |
| `NEXT_PUBLIC_APP_FRONTEND_URL` | Yes (both UI apps in production) | `http://localhost:3001` (admin) / `http://localhost:3002` (consumer) | Frontend origin used for Supabase email/password sign-in callback redirects. Must point to the Vercel-hosted app, **not** the API. | Vercel project URL (e.g. `https://app.thewidby.com` for admin; separate consumer project URL). |
| `NEXT_PUBLIC_NICHE_DRY_RUN` | No | — | When set to `"1"`, the admin and consumer `/api/agent/scoring` + `/api/agent/exploration` proxies forward `dry_run: true` to FastAPI so the orchestrator loads from fixtures instead of calling DataForSEO / Anthropic. Used by Playwright E2E. | Local or Playwright webServer env only |

### Research agent API (Render)

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | Yes (Render) | Injected by Render; uvicorn must listen on this port (`Dockerfile.api`). |
| `RESEARCH_RUNS_DIR` | Recommended | Directory for per-run artifacts; use `/data/research_runs` with a disk mounted at `/data`. |
| `RESEARCH_GRAPH_PATH` | Recommended | Path to knowledge graph JSON; e.g. `/data/research_graph.json` with same disk. |
| `ANTHROPIC_API_KEY` | Yes | Claude / agent tool-use. |
| `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` | Yes | DataForSEO when plugins call live SEO APIs. |

See `docs/research_agent_design.md` §12 for production architecture, verified service name/URL, and an example `render.yaml`.

## Configuration Files

| File | Purpose | Template |
|------|---------|----------|
| `.env` / `.env.local` | Local dev secrets (root) | `.env.example` |
| `apps/admin/.env.local` | Admin dashboard local secrets | `apps/admin/.env.example` (if present; otherwise root `.env.example`) |
| `apps/app/.env.local` | Consumer app local secrets | `apps/app/.env.example` (if present; otherwise root `.env.example`) |
| `pyproject.toml` | Python build config, ruff, pytest settings | — |
| `package.json` | Turborepo workspace config | — |
| `apps/web/next.config.ts` | Marketing Next.js config (redirects) | — |
| `apps/admin/next.config.ts` | Admin Next.js config | — |
| `apps/app/next.config.ts` | Consumer Next.js config | — |
| `src/config/constants.py` | Scoring engine constants (AIO rates, weights, thresholds) | — |

### Vercel deployment checklist (`whidby-agent` — admin dashboard)

The admin research-agent dashboard (`apps/admin/`, port 3001 locally) deploys to Vercel as project `whidby-agent` and serves `app.thewidby.com`. The consumer product (`apps/app/`, port 3002 locally) is a separate Vercel project — apply the same env-var checklist there with the consumer's own origin substituted into `NEXT_PUBLIC_APP_FRONTEND_URL`. The middleware requires these env vars at edge runtime — missing or invalid values cause `MIDDLEWARE_INVOCATION_FAILED`. Set them in the Vercel project settings for **both Production and Preview** environments:

| Variable | Required | Notes |
|----------|----------|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Must be a valid `https://<project>.supabase.co` URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` | Yes | Publishable (anon) key from Supabase Dashboard |
| `NEXT_PUBLIC_API_URL` | Yes (production) | Render API URL, e.g. `https://whidby-1.onrender.com` |
| `NEXT_PUBLIC_APP_FRONTEND_URL` | Yes (production) | App frontend origin for auth redirects, e.g. `https://app.thewidby.com` |

### E2E test accounts (Supabase `whidby` project)

Login uses email + password (`signInWithPassword`). These accounts are seeded directly in `auth.users`.

| Account | Email | Password | Purpose |
|---------|-------|----------|---------|
| Personal | `antwoine@covariance.studio` | `WidbyDev2026!` | Dev/admin login |
| E2E Test | `e2e-test@widby.dev` | `WidbyTest2026!` | Playwright automation |

For Vercel preview E2E, set these env vars in the project's **Preview** environment:

| Variable | Value |
|----------|-------|
| `E2E_AUTH_EMAIL` | `e2e-test@widby.dev` |
| `E2E_AUTH_PASSWORD` | `WidbyTest2026!` |

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
| `npm run dev:admin` | Admin research-agent dashboard (port 3001) |
| `npm run dev:app` | Consumer product (port 3002) |
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

## Supabase Migrations

Run in order from `supabase/migrations/`:

| # | File | Notes |
|---|------|-------|
| 001 | `001_core_schema.sql` | `reports`, `report_keywords`, `metro_signals`, `metro_scores`, `feedback_log` — core M9 output tables |
| 002 | `002_experiment_schema.sql` | Experiment framework (M10–M15) tables |
| 003 | `003_shared_tables.sql` | `metro_location_cache`, `api_usage_log`, `suppression_list` |
| 004 | `004_rls_policies.sql` | RLS enabled on all tables; `service_role` FOR ALL policies |
| 005 | `005_authenticated_read_reports.sql` | Grants `authenticated` users SELECT on the four report-facing tables so the consumer `/reports` page can read via the publishable key. Writes remain `service_role`. Added in PR #25. |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-04-05 | DocGuard Init | Initial template |
| 1.0.0 | 2026-04-05 | Migration | Populated from CLAUDE.md, apps/web/CLAUDE.md, .env.example |
| 1.0.1 | 2026-04-05 | Render alignment | `NEXT_PUBLIC_API_URL`, Render research API env table, pointer to research_agent_design §12 |
| 1.0.2 | 2026-04-06 | Middleware fix | Added Vercel deployment checklist, `apps/app` config files, `NEXT_PUBLIC_API_URL` to root `.env.example` |
| 1.1.0 | 2026-04-21 | Apps reorg + operational wiring | Distinguish `apps/admin` (3001) vs `apps/app` (3002), drop magic-link language for email/password, add `NEXT_PUBLIC_NICHE_DRY_RUN`, document migration 005 |
