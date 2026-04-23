# Consumer App — Widby Reports

Light academic theme, port 3002. Deploys separately from the admin dashboard. Scaffolded in commit `8fef1ee` (2026-04-20); backend wiring landed in PR #24 (`014-consumer-niche-finder-wiring`).

## Purpose

The user-facing consumer product where operators:
- Score a niche by submitting city + service on `/niche-finder` (hits the Python orchestrator via the FastAPI bridge)
- Review their history of scored reports on `/reports` (live Supabase read)

## Topology (current)

```
apps/app/
  src/
    app/
      (protected)/
        page.tsx                 Home dashboard (SSR — loadDashboard)
        niche-finder/
          page.tsx               Variation B command center
        reports/
          page.tsx               SSR Supabase fetch + client shell
          ReportsPageClient.tsx  Client filter/search/summary + table
          ReportsView.tsx        Legacy 014 client table (unused by Foundation)
        recommendations/         Coming-soon stub
        layout.tsx               Sidebar + Topbar shell
      api/agent/                 scoring + places/suggest + metros/suggest + health proxies
      auth/                      Supabase auth callback
      login/                     Sign-in flow
    components/
      home/                      StatCardRow, HeroQuickSearch, RecommendedMetros,
                                  RecentActivityFeed, SavedSearchesBlock
      niche-finder/              CityAutocomplete, NicheFinderTabs,
                                  StrategyPresetRail, PinnedRecentRail
      reports/                   ArchetypeChipFilter, ReportsTable
      Sidebar.tsx / Topbar.tsx / StatusPill.tsx
    lib/
      archetypes.ts              8-archetype registry (id/short/glyph/hint/strat)
      home/load-dashboard.ts     Supabase → DashboardData loader
      niche-finder/              types, request-validation, metro-suggest,
                                  reports-mapper, history-storage, derive-archetype
      supabase/                  Supabase server/client factories
```

## Foundation flow (2026-04-21)

All Foundation pages are deterministic — no Claude calls. Agentic
features (exploration assistant, strategy search, shareable reports)
arrive from Phase 2 onward on Managed Agents. See
`docs/superpowers/specs/2026-04-21-widby-niche-finder-v1-design.md`
for the phased roadmap and the separation-of-concerns rule that
keeps the product lane deterministic.

## Niche-finder flow on consumer

1. User visits `/niche-finder`, types a city → `CityAutocomplete` hits `/api/agent/places/suggest` (Mapbox Geocoding, global coverage). Falls back to legacy `/api/agent/metros/suggest` (CBSA seed, US-only) if Mapbox is unavailable.
2. User selects a suggestion → form populates `city`, `state` (if region is a 2-letter code), `place_id`, and `dataforseo_location_code` (if bridge resolved one).
3. Submit sends `POST /api/agent/scoring` with `{city, service, state?, place_id?, dataforseo_location_code?}`. When `dataforseo_location_code` is present, the orchestrator uses it directly for DataForSEO targeting (bypasses MetroDB seed lookup); otherwise falls back to `MetroDB.find_by_city`.
4. FastAPI runs M4 → M9, persists to Supabase (report metadata includes `place_id` and `dataforseo_location_code` when provided), returns `{report_id, opportunity_score, classification_label, evidence, report}`.
5. Success card links to `/reports/{report_id}`. On success, the entry is pushed to `localStorage` recent history with `place_id` + `dataforseo_location_code` so reruns reuse canonical targeting without re-resolution.
6. Clicking a recent history row restores stored `place_id` / `dataforseo_location_code` / `state` into the form.

## RLS

Migration `supabase/migrations/005_authenticated_read_reports.sql` grants `authenticated` users SELECT on `reports`, `report_keywords`, `metro_signals`, `metro_scores`. Writes remain service_role only (via the Python scoring engine). If you add new tables the consumer reads, add matching SELECT-for-authenticated policies.

## Mirror-lib convention

`apps/app/src/lib/niche-finder/*` and `apps/app/src/components/niche-finder/CityAutocomplete.tsx` are verbatim mirrors of their `apps/admin/` counterparts with a `// Mirror of ...` header. Keep them in sync until extracted to `packages/niche-finder/` in a dedicated PR. Key mirrored files include `place-suggest.ts` (Mapbox client + fallback), `metro-suggest.ts` (legacy), and `types.ts` (includes `place_id` and `dataforseo_location_code` on `NicheQueryInput`).

## Dev commands

```bash
npm run dev:app                # Next.js on :3002 (from repo root)
cd apps/app && npx tsc --noEmit
cd apps/app && npx vitest run  # Once tests are added
```

## Environment variables

Currently uses:

- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` — auth
- `NEXT_PUBLIC_APP_FRONTEND_URL` — auth redirect origin
- `NEXT_PUBLIC_API_URL` — FastAPI bridge base (required for scoring + places autocomplete)
- `NEXT_PUBLIC_NICHE_DRY_RUN` — dev/E2E override

Note: `MAPBOX_ACCESS_TOKEN` is set on the FastAPI side (Render env), not the frontend. The frontend proxies through `/api/agent/places/suggest`.

Operational note (2026-04-22): Render API env has been updated with `MAPBOX_ACCESS_TOKEN`; consumer `/niche-finder` autocomplete now returns small-city suggestions such as Tuskegee, AL and Macon, GA.

## Auth rate limits

Two layers of protection on the login form:

1. **Server-side (Supabase baseline).** Supabase Auth enforces 30 auth requests/hour/IP by default, configurable in the Supabase dashboard. This is the primary defense against credential stuffing. Docs: https://supabase.com/docs/guides/auth/auth-rate-limits

2. **Client-side backoff (UX friction).** The login form applies a progressive lockout after each failed attempt: 1s, 2s, 4s, 8s, 15s (capped). Implemented inline in `src/app/login/page.tsx` via a `failCountRef` (useRef, not state — the counter doesn't need to drive rerenders) and `lockedUntil` state with a 1s `setInterval` countdown. Resets on successful sign-in or full page refresh (no localStorage persistence). This blocks rapid-fire UI submissions but does NOT protect against attackers bypassing the form.

**Future work:** Proper IP-based rate-limiting (e.g., via `@upstash/ratelimit` + Upstash Redis) belongs in middleware or a `/api/auth/login` route handler once we provision Redis. The hook point is marked with a TODO comment above `computeLockMs` in the login page.

## Design conventions

- **Light academic theme** — Source Serif 4 for headings, Inter for body, JetBrains Mono for data/code. Respect the visual contrast with admin's dark theme; these are intentionally separate design systems.
- **Display-layer first** — pages should feel fast even before backend wiring lands. Use skeletons / sample data where appropriate, but label mock state clearly in component-internal comments.
- **Shared Supabase auth** — same users auth against both apps. Sign-out on one app signs out the other via shared cookies.
