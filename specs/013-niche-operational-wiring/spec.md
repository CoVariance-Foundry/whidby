# Feature 013 — Niche Scoring Operational Wiring

## Problem

M4 through M9 of the scoring engine were fully implemented and tested, but nothing called them end-to-end. The Next.js admin surface's `/api/agent/scoring` and `/api/agent/exploration` returned hash-based synthetic scores from `apps/admin/src/lib/niche-finder/response-adapter.ts`. The research-agent exploration-chat proxy swallowed FastAPI errors as a generic "could not complete." There was no persisted niche report anywhere.

## Goal

Wire the existing pipeline into production paths so the user-facing flow — enter city + service, see a real score with real signals — actually executes M4 → M5 → M6 → M7 → M8 → M9 against live APIs, persists the report to Supabase, and renders from that data.

## Out of scope

- Multi-user RLS on the `reports` table (currently service-role only)
- M10-M15 outreach experiment tables (`experiments`, `outreach_events`, etc.)
- Consumer product (`apps/app`) exploration UI — niche scoring flow still lives on admin in this PR; consumer wiring is a follow-up
- "Recent niche scores" dashboard widget

## What shipped

1. **`src/pipeline/orchestrator.py::score_niche_for_metro`** — composes M4-M9 for a single `(niche, city, state)` pair. Supports `dry_run=True` for fast, free UI/CI runs using fixtures.
2. **`src/clients/supabase_persistence.py`** — writes the M9 report into `reports` / `report_keywords` / `metro_signals` / `metro_scores`.
3. **FastAPI routes** `POST /api/niches/score` and `GET /api/niches/{id}` on `src/research_agent/api.py`.
4. **Next.js admin proxies** rewritten: `/api/agent/scoring`, `/api/agent/exploration` now hit FastAPI. `response-adapter.ts` deleted.
5. **Diagnostic routes** `/api/agent/health`. `/api/agent/exploration-chat` now surfaces upstream status + body.
6. **Loading + error UI** on the admin exploration and home pages for the synchronous live scoring path. Customer first-report latency and durability are governed by Feature 016 rather than the former elapsed-time estimate.
7. **Playwright E2E** at `apps/admin/e2e/niche-scoring.spec.ts` using `NEXT_PUBLIC_NICHE_DRY_RUN=1` on the Playwright `webServer`.

## Dependencies

- `supabase-py ≥ 2.7` (added to `pyproject.toml`)
- `SUPABASE_SERVICE_ROLE_KEY` (added to `.env.example`)
- Existing `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` / `ANTHROPIC_API_KEY` for live path

## Acceptance

- `pytest tests/unit/ -q` — 290+ tests pass (baseline + new)
- `ruff check src/ tests/` — clean
- `cd apps/admin && npx vitest run src/app/api/agent/` — all route tests pass
- Live acceptance is superseded by `specs/016-first-report-performance/spec.md`: the production-image gate must complete a successful scoring POST plus immediate schema-valid GET of the same durable report in `<= 60.0` seconds, without `persist_warning`, under the `500000000`-byte cgroup limit. The former 30-90-second allowance is retired.

## Plan

See `docs/superpowers/plans/2026-04-20-niche-finder-operational-wiring.md`.
