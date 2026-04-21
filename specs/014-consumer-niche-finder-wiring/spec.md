# Feature 014 — Consumer Niche-Finder Wiring + City Autocomplete

## Problem

After PR #23 shipped the admin-side operational wiring (orchestrator, Supabase persistence, FastAPI niche routes), two gaps remained:

1. **Ambiguous city resolution.** The admin proxies defaulted `state` to `"AZ"` when the UI omitted it — but the UI had no state field. Non-AZ cities (Atlanta, Denver, Seattle) were silently broken. A city autocomplete that resolves `{city, state, cbsa_code}` server-side is the right UX fix.
2. **Consumer app inert.** `apps/app/` (the light-theme consumer product scaffolded in commit `8fef1ee`) had no API routes, no niche-finder page, hardcoded mock report data, and dead `/recommendations` / `/niche-finder` nav links.

## Goal

- Ship an autocomplete service end-to-end: FastAPI suggest endpoint → admin proxy → `CityAutocomplete` React component → adopted in both admin forms.
- Mirror the admin's scoring + autocomplete + health proxies onto the consumer app.
- Build the consumer's `/niche-finder` page in the light academic theme.
- Replace the consumer's hardcoded `ReportsView` with a live SSR read from Supabase `reports`.
- Kill the `/recommendations` 404 with a stub page.
- Add the RLS policy needed so authenticated consumer users can read reports.

## Out of scope

- Extracting the duplicated niche-finder lib into a shared `packages/` workspace. The mirrored files carry a `// Mirror of ...` header and wait for a dedicated extraction PR.
- Consumer exploration/evidence surface (full-depth signal drill-down). Admin still owns that for now.
- Report detail pages at `/reports/{id}` on either app. The list view is enough for this PR; detail comes later.
- Multi-user RLS (rows scoped to owner). Current policies grant `authenticated` users full read across all reports — acceptable for the internal/dev phase.

## What shipped

### Backend
- `GET /api/metros/suggest?q=&limit=` on the FastAPI bridge (`src/research_agent/api.py`), scanning `MetroDB` seed by city prefix, returning population-ordered results.
- `MetroDB.find_by_city(city, state=None)` and `MetroDB.all_metros()` public helpers.
- `NicheScoreRequest.state` made optional (server resolves state from city when the caller omits it).
- `http://localhost:3002` added to FastAPI CORS allowlist so consumer dev works.

### Admin (`apps/admin`)
- New `/api/agent/metros/suggest` proxy.
- New `CityAutocomplete` component (combobox, debounce, AbortController, full ARIA, keyboard nav, empty-state row).
- Adopted in `StandardNicheForm` + `ExplorationQueryForm`; `NicheQueryInput` gains `state?: string`.
- RTL + jsdom + jest-dom + user-event added as dev deps for component tests.

### Consumer (`apps/app`)
- `/api/agent/scoring`, `/api/agent/metros/suggest`, `/api/agent/health` proxies (mirrors of admin with a `// Mirror of ...` header).
- `/niche-finder` page with `CityAutocomplete` + result card (light academic theme).
- `/reports` page converted to async server component; SSR Supabase fetch from `reports` table ordered by `created_at DESC limit 50`, with a `ReportsView` client component.
- `/recommendations` stub page (kills dead nav link).
- Mirror lib files under `src/lib/niche-finder/` (types, request-validation, metro-suggest, reports-mapper).

### Database
- `supabase/migrations/005_authenticated_read_reports.sql` — grants `authenticated` users SELECT on `reports`, `report_keywords`, `metro_signals`, `metro_scores`. Writes remain `service_role` only.

### Docs
- `apps/app/CLAUDE.md` rewritten to describe post-PR-#25 state.
- `docs/product_breakdown.md` extended with the new MetroDB methods and `/api/metros/suggest` route.

## Acceptance

- `pytest tests/unit/ -q` → 298 pass (was 291 on PR #23 base, +7 autocomplete tests)
- `ruff check src/ tests/` → clean
- `cd apps/admin && npx tsc --noEmit` → clean; `npx vitest run` → 35 pass (was 17, +18)
- `cd apps/app && npx tsc --noEmit` → clean; `npx vitest run` → 23 pass (was 0, +23)
- No `[docs-sync-skip]` on any commit; no tests suppressed, skipped, or muted
- Manual live smoke: start `npm run dev:api` + `npm run dev:app`, log in, type `phoe` in the niche-finder city input, confirm `Phoenix, AZ` appears and selection populates both city and state. Submit with `roofing` service. Confirm a new row lands in `reports` and the `/reports` page shows it.

## Plan

No written plan file was used for this PR — scope was defined interactively from the PR #23 follow-up audit. The commit log on `014-consumer-niche-finder-wiring` captures the T1–T8 breakdown used during subagent-driven execution.
