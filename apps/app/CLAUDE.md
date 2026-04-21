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
      layout.tsx               Light-theme root, Source Serif 4 + Inter + JetBrains Mono
      login/                   Email/password sign-in (same Supabase project as admin)
      auth/callback/           OAuth callback
      (protected)/
        layout.tsx             Sidebar + Topbar shell
        page.tsx               Home; currently redirects to /reports
        niche-finder/          City+service scoring page with CityAutocomplete
        reports/
          page.tsx             Server component — SSR Supabase fetch from `reports`
          ReportsView.tsx      Client table (props-driven, no mock data)
        recommendations/       "Coming soon" stub so sidebar link stops 404-ing
      api/
        agent/
          scoring/route.ts     POST → FastAPI /api/niches/score
          metros/suggest/      GET → FastAPI /api/metros/suggest (autocomplete)
          health/route.ts      GET → FastAPI /health
    components/
      niche-finder/
        CityAutocomplete.tsx   Mirror of apps/admin/ component, light-themed
      Sidebar.tsx / Topbar.tsx / StatusPill.tsx
    lib/
      niche-finder/            Mirrors of apps/admin/src/lib/niche-finder/ (types,
                               request-validation, metro-suggest, reports-mapper)
      archetypes.ts / icons.tsx / utils.ts / supabase/
    middleware.ts              Auth guard
```

## Niche-finder flow on consumer

1. User visits `/niche-finder`, types a city → `CityAutocomplete` hits `/api/agent/metros/suggest` for suggestions.
2. User selects a suggestion → form populates both `city` AND `state`.
3. Submit sends `POST /api/agent/scoring` with `{city, service, state}`; state is optional (the orchestrator resolves via `MetroDB.find_by_city` if missing).
4. FastAPI runs M4 → M9, persists to Supabase, returns `{report_id, opportunity_score, classification_label, evidence, report}`.
5. Success card links to `/reports/{report_id}` (detail page is a future PR; for now the list view is the only Supabase read).

## RLS

Migration `supabase/migrations/005_authenticated_read_reports.sql` grants `authenticated` users SELECT on `reports`, `report_keywords`, `metro_signals`, `metro_scores`. Writes remain service_role only (via the Python scoring engine). If you add new tables the consumer reads, add matching SELECT-for-authenticated policies.

## Mirror-lib convention

`apps/app/src/lib/niche-finder/*` and `apps/app/src/components/niche-finder/CityAutocomplete.tsx` are verbatim mirrors of their `apps/admin/` counterparts with a `// Mirror of ...` header. Keep them in sync until extracted to `packages/niche-finder/` in a dedicated PR.

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

Will also need (once scoring wires in):

- `NEXT_PUBLIC_API_URL` — FastAPI bridge base
- `NEXT_PUBLIC_NICHE_DRY_RUN` — dev/E2E override

## Design conventions

- **Light academic theme** — Source Serif 4 for headings, Inter for body, JetBrains Mono for data/code. Respect the visual contrast with admin's dark theme; these are intentionally separate design systems.
- **Display-layer first** — pages should feel fast even before backend wiring lands. Use skeletons / sample data where appropriate, but label mock state clearly in component-internal comments.
- **Shared Supabase auth** — same users auth against both apps. Sign-out on one app signs out the other via shared cookies.
