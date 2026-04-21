# Consumer App — Widby Reports

Light academic theme, port 3002. Deploys separately from the admin dashboard. Scaffolded in commit `8fef1ee` (2026-04-20) with **backend wiring deliberately deferred** — the current app is a presentation scaffold.

## Purpose

The user-facing consumer product. Where operators will eventually:
- Submit city + service for a niche score (current: this lives in admin; future: migrates here)
- Review historical reports with filtering by archetype
- Manage saved searches

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
        reports/
          page.tsx             Reports index wrapper
          ReportsView.tsx      Reports table + stats (currently HARDCODED mock data)
    components/
      Sidebar.tsx              Nav: Home, Niche finder, Recommendations, Reports
      Topbar.tsx               Breadcrumb + actions
      StatusPill.tsx           Archetype status badge
    lib/
      archetypes.ts            Catalog of 8 strategy archetypes
      icons.tsx                Light-theme SVG icons
      supabase/                SSR client factories (same shape as admin's)
      utils.ts                 cn() helper (clsx + tailwind-merge)
    middleware.ts              Auth guard (identical to admin's)
```

## Gaps (known work items — do NOT assume these are done)

As of 2026-04-21, the consumer app does not yet have:

- **Any `/api/` routes.** The Sidebar links `/niche-finder` → a page that doesn't exist. Clicking it 404s.
- **A scoring proxy.** `NEXT_PUBLIC_API_URL` is declared in `.env.example` but unused here.
- **Real reports data.** `ReportsView.tsx` lines ~26-37 hardcode 10 fake rows. Needs to read from Supabase `reports` table (populated by the admin's niche-finder via the FastAPI bridge).
- **`/recommendations` page.** Sidebar links to it; page missing.
- **Shared niche-finder lib.** Admin has `apps/admin/src/lib/niche-finder/` with types, validators, session context. Consumer has nothing equivalent. Either lift to `packages/niche-finder/` or duplicate with a Supabase-read-only variant.

When wiring any of the above, follow the patterns in `apps/admin/` — same FastAPI bridge URL, same `NEXT_PUBLIC_NICHE_DRY_RUN` toggle, same snake_case wire format, same loading/error banners.

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
