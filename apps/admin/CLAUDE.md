# Admin App — Research Dashboard

This is the **research-agent dashboard** + **niche-scoring admin UI**. Dark theme, port 3001, deploys to `app.thewidby.com` on Vercel as `whidby-admin`.

## Purpose

- Internal tool for investigating niche scoring, running research experiments, and viewing the knowledge graph.
- Currently hosts the production niche-finder + exploration flow. The consumer app (`apps/app`) will eventually take over niche-finder; admin retains the experiment / graph / chat surfaces.

## Topology

```
apps/admin/
  src/
    app/
      layout.tsx                  Dark-theme root shell (Inter + JetBrains Mono)
      login/                      Email/password sign-in (supabase-ssr)
      auth/callback/              OAuth / magic-link callback
      (protected)/                All surfaces require an auth session
        layout.tsx                Sidebar + Topbar
        page.tsx                  Home: quick niche score (city + service)
        exploration/page.tsx      Full evidence + follow-up chat for one niche
        chat/page.tsx             Claude agent conversation
        graph/page.tsx            Knowledge graph viewer
        experiments/page.tsx      Experiment run browser
        recommendations/page.tsx  Synthesized recs per session
        dashboard/page.tsx        Session history + aggregate metrics
      api/
        agent/
          scoring/route.ts        POST → FastAPI /api/niches/score (forwards place_id + dataforseo_location_code)
          exploration/route.ts    POST → FastAPI /api/niches/score (returns evidence)
          places/suggest/route.ts GET → FastAPI /api/places/suggest (Mapbox autocomplete)
          exploration-chat/route.ts POST → FastAPI /api/exploration/followup
          sessions/route.ts       Research-session proxy
          sessions/[runId]/route.ts
          experiments/[runId]/route.ts
          chat/route.ts
          graph/route.ts
          health/route.ts         GET → FastAPI /health (diagnostics)
    components/niche-finder/      Shared niche-finder UI components
    lib/
      niche-finder/               Types, validators, session context, service wrappers
      supabase/                   SSR client factories
      archetypes.ts               Niche strategy archetype catalog
    proxy.ts                      Auth guard (redirects to /login)
  e2e/                            Playwright specs (run via playwright.config.ts)
  vitest.config.ts                Vitest excludes e2e/ so Playwright specs don't collide
```

## Niche-finder flow (operational)

1. User types a city → `CityAutocomplete` hits `/api/agent/places/suggest` (Mapbox Geocoding, global coverage); falls back to legacy `/api/agent/metros/suggest` if Mapbox is unavailable.
2. User selects a suggestion → form populates `city`, `state` (if region is a 2-letter code), `place_id`, and `dataforseo_location_code` (if bridge resolved one).
3. User submits `{city, service, state?, place_id?, dataforseo_location_code?}` via `StandardNicheForm` (home) or `ExplorationQueryForm` (exploration).
4. Client calls `/api/agent/scoring` or `/api/agent/exploration`.
5. Proxy route POSTs to `${NEXT_PUBLIC_API_URL}/api/niches/score` with all fields including `place_id` and `dataforseo_location_code` when available (dry_run flag honored via `NEXT_PUBLIC_NICHE_DRY_RUN=1`).
6. When `dataforseo_location_code` is present, the orchestrator uses it directly for DataForSEO targeting (bypasses MetroDB seed lookup). Otherwise falls back to `MetroDB.find_by_city`.
7. FastAPI runs the Python orchestrator M4 → M9, persists the report to Supabase (report metadata includes `place_id` and `dataforseo_location_code`), returns `{report_id, opportunity_score, classification_label, evidence, report}`.
8. UI renders score + evidence; exploration page additionally mounts `ExplorationAssistantPanel` for follow-up Q&A via `/api/agent/exploration-chat`.

**Important:** Both the scoring and exploration proxies hit the same FastAPI endpoint. Do NOT add a double `Promise.all([scoring, exploration])` pattern — that would run M4 → M9 twice and write duplicate Supabase rows. Use one fetch, derive both surfaces from its response.

## Dev commands

```bash
npm run dev:admin             # Next.js on :3001 (from repo root)
npm run dev:api               # FastAPI bridge on :8000 (required for niche-finder)
cd apps/admin && npx vitest run        # Unit / route tests
cd apps/admin && npx tsc --noEmit      # Type check
cd apps/admin && npx playwright test   # E2E (starts its own Next server with dry-run env)
```

## Environment variables

See `docs-canonical/ENVIRONMENT.md`. Required for admin specifically:

- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` — auth
- `NEXT_PUBLIC_API_URL` — FastAPI base (`http://localhost:8000` local, Render URL in prod)
- `NEXT_PUBLIC_APP_FRONTEND_URL` — frontend origin for auth redirects
- `NEXT_PUBLIC_NICHE_DRY_RUN` — set `1` to force all scoring fetches through the orchestrator's fixture path (no DataForSEO / Anthropic spend)

Test accounts are documented in `docs-canonical/ENVIRONMENT.md` under "E2E test accounts."

## Conventions

- Client components marked `"use client"`; data fetching happens in client handlers, not server components (results are async, shown with loading + error banners).
- Loading banner: `role="status"` + `aria-live="polite"`. Error banner: `role="alert"`.
- `data-testid="opportunity-score"` on the score element (required by Playwright spec `e2e/niche-scoring.spec.ts`).
- All proxy routes snake_case on the wire. Do not introduce camelCase into outbound JSON.

## Auth rate limits

Two layers of protection on the login form:

1. **Server-side (Supabase baseline).** Supabase Auth enforces 30 auth requests/hour/IP by default, configurable in the Supabase dashboard. This is the primary defense against credential stuffing. Docs: https://supabase.com/docs/guides/auth/auth-rate-limits

2. **Client-side backoff (UX friction).** The login form applies a progressive lockout after each failed attempt: 1s, 2s, 4s, 8s, 15s (capped). Implemented inline in `src/app/login/page.tsx` via a `failCountRef` (useRef, not state — the counter doesn't need to drive rerenders) and `lockedUntil` state with a 1s `setInterval` countdown. Resets on successful sign-in or full page refresh (no localStorage persistence). This blocks rapid-fire UI submissions but does NOT protect against attackers bypassing the form.

**Future work:** Proper IP-based rate-limiting (e.g., via `@upstash/ratelimit` + Upstash Redis) belongs in middleware or a `/api/auth/login` route handler once we provision Redis. The hook point is marked with a TODO comment above `computeLockMs` in the login page.

## Known footguns

- The FastAPI bridge must be running for any `/api/agent/*` call to succeed. The admin `/api/agent/health` route surfaces bridge state — hit it when debugging "nothing renders."
- The proxy auth guard treats `/api/agent/*` as protected (session required) but `/api/agent/health` is useful uncredentialed for diagnostics; confirm the proxy lets it through if you add health-checking from CI.
