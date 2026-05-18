# Environment & Configuration

<!-- docguard:version 1.4.0 -->
<!-- docguard:status approved -->
<!-- docguard:last-reviewed 2026-05-17 -->
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
| `MAPBOX_ACCESS_TOKEN` | Yes (places autocomplete) | — | Mapbox Geocoding API token for global city autocomplete (`/api/places/suggest`). Endpoint returns 503 if missing. Uses permanent geocoding mode. | account.mapbox.com → Tokens |
| `SERPAPI_KEY` | Yes (recipe reports) | — | SerpAPI API key for Google + Google Maps engines | serpapi.com → Dashboard |
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key | console.anthropic.com |
| `ACTIVECAMPAIGN_API_URL` | Yes (web app) | — | ActiveCampaign API base URL | ActiveCampaign → Settings → Developer |
| `ACTIVECAMPAIGN_API_KEY` | Yes (web app) | — | ActiveCampaign API key | ActiveCampaign → Settings → Developer |
| `VERCEL_PROJECT_ID` | No | — | Vercel project ID for deployments | Vercel Dashboard |
| `VERCEL_ORG_ID` | No | — | Vercel organization ID | Vercel Dashboard |
| `NEXT_PUBLIC_API_URL` | Yes (both UI apps in production) | `http://localhost:8000` | Base URL of the FastAPI research agent bridge used by `/api/agent/*` Route Handlers in both `apps/admin` and `apps/app`. **Not** used for auth redirects. | Render web service URL, e.g. `https://whidby-1.onrender.com` |
| `STRATEGY_DISCOVERY_INTERNAL_TOKEN` | Yes for production strategy discovery | — | Shared server-to-server token. Consumer app `/api/strategies/discover` forwards it to FastAPI; FastAPI requires it when `ENVIRONMENT=production` before reading service-role cached strategy data. | Generate a long random secret and set the same value in Vercel and Render |
| `NEXT_PUBLIC_APP_FRONTEND_URL` | Yes (both UI apps in production) | `http://localhost:3001` (admin) / `http://localhost:3002` (consumer) | Frontend origin used for Supabase email/password sign-in callback redirects. Must point to the Vercel-hosted app, **not** the API. | Vercel project URL (e.g. `https://app.thewidby.com` for admin; separate consumer project URL). |
| `NEXT_PUBLIC_NICHE_DRY_RUN` | No | — | When set to `"1"`, the admin and consumer `/api/agent/scoring` + `/api/agent/exploration` proxies forward `dry_run: true` to FastAPI so the orchestrator loads from fixtures instead of calling DataForSEO / Anthropic. Used by Playwright E2E. | Local or Playwright webServer env only |
| `STRIPE_SECRET_KEY` | Yes (consumer billing) | — | Server-side Stripe API key for Checkout, Customer Portal, and webhook subscription retrieval | Stripe Dashboard |
| `STRIPE_WEBHOOK_SECRET` | Yes (consumer billing) | — | Stripe webhook signing secret for `/api/billing/webhook` | Stripe Dashboard webhook endpoint |
| `STRIPE_PLUS_PRICE_ID` | Yes (consumer billing) | — | Recurring monthly Stripe Price for Plus ($49/mo) | Stripe Dashboard product catalog |
| `STRIPE_PRO_PRICE_ID` | Yes (consumer billing) | — | Recurring monthly Stripe Price for Pro ($100/mo) | Stripe Dashboard product catalog |
| `NEXT_PUBLIC_POSTHOG_KEY` | No | — | PostHog project key for consumer feature flags. If absent, secure defaults are used. | PostHog project settings |
| `NEXT_PUBLIC_POSTHOG_HOST` | No | `https://us.i.posthog.com` | PostHog ingestion/feature flag host | PostHog project settings |

### Research agent API (Render)

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | Yes (Render) | Injected by Render; uvicorn must listen on this port (`Dockerfile.api`). |
| `RESEARCH_RUNS_DIR` | Recommended | Directory for per-run artifacts; use `/data/research_runs` with a disk mounted at `/data`. |
| `RESEARCH_GRAPH_PATH` | Recommended | Path to knowledge graph JSON; e.g. `/data/research_graph.json` with same disk. |
| `ANTHROPIC_API_KEY` | Yes | Claude / agent tool-use. |
| `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` | Yes | DataForSEO when plugins call live SEO APIs. |
| `MAPBOX_ACCESS_TOKEN` | Yes | Mapbox Geocoding for `/api/places/suggest` global autocomplete. |
| `ENVIRONMENT` | Recommended | `production` or `staging`. Controls CORS: staging allows `*.vercel.app` preview origins. |
| `STRATEGY_DISCOVERY_INTERNAL_TOKEN` | Required in production | Shared token required by `/api/discover` when `ENVIRONMENT=production`; must match the consumer app server route env value. |
| `CORS_EXTRA_ORIGINS` | No | Comma-separated extra CORS origins (e.g. custom staging domains). |

### Operational notes

- **2026-04-22:** Confirmed Render API env now includes `MAPBOX_ACCESS_TOKEN`; `/api/places/suggest` resolves small metros/cities (e.g., Tuskegee, AL and Macon, GA) through Mapbox-backed autocomplete.

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
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Yes (consumer billing) | Required only on the consumer app project |
| `STRIPE_PLUS_PRICE_ID` / `STRIPE_PRO_PRICE_ID` | Yes (consumer billing) | Plus and Pro monthly recurring price IDs |
| `NEXT_PUBLIC_POSTHOG_KEY` / `NEXT_PUBLIC_POSTHOG_HOST` | No | Consumer feature flags; server handlers fall back to secure defaults when unset |

### E2E test accounts (Supabase `whidby` project)

Login uses email + password (`signInWithPassword`). These accounts are seeded directly in `auth.users`.

| Account | Email | Password | Purpose |
|---------|-------|----------|---------|
| Personal | `antwoine@covariance.studio` | Local `.env` value only | Dev/admin login |
| E2E Test | `e2e-test@widby.dev` | `E2E_AUTH_PASSWORD` | Playwright automation |

For Vercel preview E2E, set these env vars in the project's **Preview** environment:

| Variable | Value |
|----------|-------|
| `E2E_AUTH_EMAIL` | `e2e-test@widby.dev` |
| `E2E_AUTH_PASSWORD` | GitHub/Vercel preview secret value, never committed |

Any previously committed test-account passwords should be treated as exposed and rotated before reuse.

## Staging Environment

The project uses a `dev` branch as a staging/integration gate. Feature branches PR into `dev`; verified work on `dev` PRs into `main` for production.

### Staging stack

| Layer | Service | Branch | URL |
|-------|---------|--------|-----|
| Frontend | Vercel preview deploys (all 3 apps) | any non-`main` push | auto-generated `*.vercel.app` URLs |
| API | `whidby-staging` (Render, Starter) | `dev` | `https://whidby-staging.onrender.com` |
| Database | `whidby-staging` (Supabase, free tier) | — | `https://wuybidpvqhhgkukpyyhq.supabase.co` |

### Env var scoping

Vercel env vars for **Preview** environment point at the staging backend:

| Variable | Preview Value |
|----------|--------------|
| `NEXT_PUBLIC_API_URL` | `https://whidby-staging.onrender.com` |
| `NEXT_PUBLIC_SUPABASE_URL` | staging Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` | staging Supabase anon key |

Production env vars are unchanged and only apply to `main` deploys.

The staging Render service (`whidby-staging`) has `ENVIRONMENT=staging`, which enables CORS for all `*.vercel.app` preview origins. The production Render service (`whidby-1`) has `ENVIRONMENT=production`, which restricts CORS to the explicit allowlist.

### Benchmark Runner Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `BENCHMARK_SUPABASE_URL` | Recommended | Supabase project URL for benchmark writes. Defaults to `whidby-staging`. |
| `BENCHMARK_SUPABASE_KEY` | Recommended | Service-role key for the benchmark Supabase project. The runner requires either `BENCHMARK_SUPABASE_KEY` or `SUPABASE_SERVICE_ROLE_KEY`; this variable falls back to `SUPABASE_SERVICE_ROLE_KEY`. |

### Benchmark Commands

| Command | Purpose |
|---------|---------|
| `.venv/bin/python -m scripts.benchmarks.recompute_benchmarks 120` | Rebuild staging `seo_benchmarks` from recent `seo_facts` |

### Supabase staging migrations

Staging migrations deploy from `dev` to Supabase project `whidby-staging` (`wuybidpvqhhgkukpyyhq`) through `.github/workflows/supabase-staging.yml`. The workflow runs manually through `workflow_dispatch` and automatically on `dev` pushes that change `supabase/migrations/**` or the workflow file. Manual runs must choose branch `dev`; the deploy job is guarded to skip any other branch.

1. Write migration in `supabase/migrations/`
2. Merge the feature branch into `dev`
3. Let `.github/workflows/supabase-staging.yml` install Supabase CLI `2.98.2` with `supabase/setup-cli@v2`, initialize `supabase/config.toml` when the checkout only has migrations, link `whidby-staging`, list pending migrations, run `supabase db push`, and list migration status again
4. Test end-to-end on staging (Vercel preview + staging Render + staging Supabase)
5. On merge to `main`, apply the same migration to production Supabase

### Staging test-account seeding

Staging test accounts are seeded manually through `.github/workflows/supabase-seed-test-accounts.yml` after the migrations that create account, entitlement, and internal user entitlement objects exist in staging. Manual runs must choose branch `dev`; the seed job is guarded to skip any other branch because it uses staging service-role credentials. Do not run this workflow on every push; it curates Auth users and account entitlements with operational credentials.

Default staging personas:

| Email | Member role | Plan | Quota exemption |
|-------|-------------|------|-----------------|
| `admin-test@widby.dev` | `admin` | `free` | yes |
| `user-test@widby.dev` | `owner` | `free` | no |
| `henock@covariance.studio` | `admin` | `free` | yes |
| `antwoine@covariance.studio` | `admin` | `free` | yes |
| `lm13vand@gmail.com` | `owner` | `pro` | no |

This staging setup is not Terraform. Supabase migrations manage schema, RLS, and RPCs. GitHub Environment secrets and local env files store operational credentials. `scripts/supabase/seed_test_accounts.py` manages curated Auth users and entitlements.

### GitHub Environment `staging` secrets

Create these secrets on the GitHub Environment named `staging`:

| Secret | Used by |
|--------|---------|
| `SUPABASE_ACCESS_TOKEN` | `.github/workflows/supabase-staging.yml` |
| `STAGING_DB_PASSWORD` | `.github/workflows/supabase-staging.yml` |
| `STAGING_SUPABASE_SERVICE_ROLE_KEY` | `.github/workflows/supabase-seed-test-accounts.yml` |
| `WHIDBY_TEST_ADMIN_PASSWORD` | `.github/workflows/supabase-seed-test-accounts.yml` |
| `WHIDBY_TEST_USER_PASSWORD` | `.github/workflows/supabase-seed-test-accounts.yml` |
| `WHIDBY_BETA_HENOCK_PASSWORD` | `.github/workflows/supabase-seed-test-accounts.yml` |
| `WHIDBY_BETA_ANTWOINE_PASSWORD` | `.github/workflows/supabase-seed-test-accounts.yml` |
| `WHIDBY_BETA_LUKE_PASSWORD` | `.github/workflows/supabase-seed-test-accounts.yml` |

For manual local runs of `python scripts/supabase/seed_test_accounts.py`, store staging-only values in a local `.env` file:

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | `https://wuybidpvqhhgkukpyyhq.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Staging service-role key |
| `WHIDBY_TEST_ADMIN_PASSWORD` | Password for `admin-test@widby.dev` |
| `WHIDBY_TEST_USER_PASSWORD` | Password for `user-test@widby.dev` |
| `WHIDBY_BETA_HENOCK_PASSWORD` | Password for `henock@covariance.studio` |
| `WHIDBY_BETA_ANTWOINE_PASSWORD` | Password for `antwoine@covariance.studio` |
| `WHIDBY_BETA_LUKE_PASSWORD` | Password for `lm13vand@gmail.com` |

Never commit `.env`, service-role keys, or test-account passwords. Redirect URL pattern `https://*.vercel.app/**` must be added to the staging project's Auth settings.

## AI Review, Preview, and Visual QA Environments

| Stage | Git branch | Frontend | API | Database | Review gates |
|-------|------------|----------|-----|----------|--------------|
| Feature Preview | `codex/*`, `feature/*`, `fix/*` PRs into `dev` | Vercel Preview | Render staging API by default | Supabase preview branch for schema-changing PRs, otherwise staging Supabase | Quality Gates, Greptile, Playwright smoke, optional visual QA |
| Integration | `dev` | Vercel staging custom environment or branch-scoped Preview | `whidby-staging` Render service | persistent staging Supabase project or persistent Supabase branch | Full Quality Gates, visual QA, staging smoke |
| Production | `main` | Vercel Production | `whidby-1` Render service | production Supabase project | protected merge from `dev`, production migration approval |

Feature branches must not receive production service-role credentials. Schema-changing PRs should use Supabase preview branches seeded with deterministic test data. UI-only PRs may use staging Supabase with E2E test accounts.

Supabase preview branches are data-less by default. Preview seed data must be deterministic, minimal, and free of production customer data. Auth users for E2E should be created through the approved staging/preview auth setup, not by committing real passwords into migrations.

Secret-bearing Visual QA runs only from trusted `dev` or `main` workflow dispatches. Use the `visual-qa` PR label to request review, wait for the Vercel preview URL, then dispatch the workflow from `dev` or `main` with that URL. Manual preview URLs must be HTTPS and must match `VISUAL_QA_ALLOWED_HOSTS` or `VISUAL_QA_ALLOWED_HOST_SUFFIXES`; if no allowlist vars are set, only `*.vercel.app` previews are accepted.

Environment sync scripts are dry-run planners in this branch. Use `npm run env:plan:preview`, `npm run env:plan:vercel -- --environment <env>`, `npm run env:plan:github -- --environment <env>`, or `npm run env:plan:supabase -- --environment <env> --branch <name>` to audit required names without applying provider changes.

### PR AI Review Policy

Greptile is the code-review AI for PR-level source review. It runs through the GitHub App and is accessed locally through Greptile MCP in Cursor, Codex, or Claude Code. Visual QA is separate: Playwright captures user-flow artifacts and an optional local/CI agent reviews the rendered experience for product and design issues.

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
| 006 | `006_authenticated_delete_reports.sql` | Grants authenticated users scoped report deletion support. |
| 007 | `007_kb_schema.sql` | Knowledge base tables: `kb_entities`, `kb_snapshots`, `kb_evidence_artifacts`, `api_response_cache`, `feedback_events` — canonical geo+industry entities, versioned snapshots with supersedence, raw evidence persistence, persistent API cache, and runtime feedback |
| 008 | `008_kb_rls_and_lifecycle.sql` | RLS on KB tables, authenticated SELECT on entities/snapshots/feedback, soft-delete governance (`archived_at` + `entity_id` + `snapshot_id` columns on `reports`) |
| 009 | `009_metros_and_census.sql` | Explore metro/census source tables and metro read-model support. |
| 010 | `010_v2_benchmarks.sql` | V2 benchmark tables for city-size and business-type scoring inputs. |
| 011 | `011_data_provider_tables.sql` | Data-provider persistence tables for external evidence ingestion. |
| 012 | `012_recompute_seo_benchmarks.sql` | Benchmark recompute SQL for SEO benchmark refreshes. |
| 013 | `013_sonar_slice_lite.sql` | Sonar Slice Lite schema support. |
| 014 | `014_user_management_billing.sql` | Consumer accounts, memberships, subscriptions, usage counters, billing customer mapping, report ownership columns, account-scoped report RLS, and quota RPCs |
| 015 | `015_explore_refresh_control.sql` | Explore refresh policies, targets, runs, run items, report snapshots, latest/trend views, and read/service-role RLS policies |
| 016 | `016_consumer_onboarding.sql` | Consumer onboarding profiles, target selection state, and onboarding lifecycle support. |
| 017 | `017_strategy_discovery_system.sql` | Strategy discovery system tables, cached strategy data, and protected discovery runtime support. |
| 018 | `018_internal_user_entitlements.sql` | Internal user entitlement overrides for curated accounts and quota exemptions. |
| 019 | `019_explore_refresh_grants.sql` | Forward-only Data API grants for environments that applied refresh control before explicit grants were added. |
| 020 | `020_explore_market_cells.sql` | Derived Explore market-cell materialized read model for city-first discovery. |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-04-05 | DocGuard Init | Initial template |
| 1.0.0 | 2026-04-05 | Migration | Populated from CLAUDE.md, apps/web/CLAUDE.md, .env.example |
| 1.0.1 | 2026-04-05 | Render alignment | `NEXT_PUBLIC_API_URL`, Render research API env table, pointer to research_agent_design §12 |
| 1.0.2 | 2026-04-06 | Middleware fix | Added Vercel deployment checklist, `apps/app` config files, `NEXT_PUBLIC_API_URL` to root `.env.example` |
| 1.1.0 | 2026-04-21 | Apps reorg + operational wiring | Distinguish `apps/admin` (3001) vs `apps/app` (3002), drop magic-link language for email/password, add `NEXT_PUBLIC_NICHE_DRY_RUN`, document migration 005 |
| 1.2.0 | 2026-04-22 | Mapbox autocomplete | Added `MAPBOX_ACCESS_TOKEN` to both root and Render env tables |
| 1.3.0 | 2026-04-25 | Staging environment | Added staging stack docs, `ENVIRONMENT`/`CORS_EXTRA_ORIGINS` vars, migration workflow, env scoping |
| 1.4.0 | 2026-05-17 | Supabase staging workflows | Added staging migration and test-account seeding workflow docs, required `staging` secrets, local env handling, pinned Supabase CLI workflow setup, dev-branch guards, and missing migration rows through 018 |
