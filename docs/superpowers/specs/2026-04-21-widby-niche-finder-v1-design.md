# Widby Niche Finder — Foundation + Phased Roadmap

**Date:** 2026-04-21
**Target branch:** `015-niche-finder-product-v1` (to be created)
**Status:** design approved, implementation planning next

## Problem

The Niche Finder product (consumer-facing, `apps/app`) is currently inert. The `(protected)/` route tree redirects to `/reports` and no home, niche-search, or exploration UI ships today.

Separately, while building the 012 recipe-reports feature a conflation emerged: Claude-orchestrated "recipes" (via the research agent's hand-rolled tool-use loop) got treated as product features when they should have been clearly separated. The correct separation has two parts:

1. **Deterministic product features** — composable pipelines that wrap the scoring engine (`src/scoring/`, `src/pipeline/`) and surface results to users. No Claude in the execution path. Example: the niche search that returns a score + evidence.
2. **Agentic features** — open-ended Claude-powered surfaces where the tool sequence isn't fixed in advance. Exploration assistants, cross-referenced recipe reports, research experiments. Run on Anthropic's Managed Agents service so we don't hand-roll session state, plugin registries, or tool-use loops.

Parallel agents on `.worktrees/013-niche-operational-wiring` and `.worktrees/014-consumer-niche-finder-wiring` have already landed the backend product surface (`POST /api/niches/score`, `GET /api/niches/{id}`, `GET /api/metros/suggest`), Supabase persistence, and a simple consumer `/niche-finder` page. The design mockups bundle (Home, Niche Search as command-center Variation B, Reports with archetype chip filter) has been provided via Claude Design and is committed at [docs/designs/widby-niche-finder-v1/](docs/designs/widby-niche-finder-v1/).

This spec ships the **Foundation** (three consumer pages + deterministic backend wiring) and names the **phased advanced features** that follow. Agentic features from Phase 2 onward use [Anthropic Managed Agents](https://platform.claude.com/docs/en/managed-agents/agent-setup) as the runtime.

## Architecture

Three lanes; no runtime crosstalk between the first two:

- **Product lane** — customer-facing. `apps/app` talks to `/api/niches/*`, `/api/metros/*`. Deterministic: M4 → M9 chain via `src/pipeline/orchestrator.py::score_niche_for_metro`, persisted to Supabase. No Claude.
- **Research lane** — internal. `apps/admin` talks to `/api/sessions`, `/api/experiments`, `/api/chat`, `/api/graph`. The Ralph loop, `ClaudeAgent`, `PluginRegistry`, knowledge graph. Refines scoring weights in `src/scoring/` asynchronously. Currently uses the plain `anthropic.Anthropic` SDK; future refactor may port it to Managed Agents as its own agent configuration.
- **Agentic-product lane (new, phased in after Foundation)** — customer-facing Claude-powered surfaces. Consumer Exploration assistant, strategy search, cross-referenced recipe reports. Each feature is one **Managed Agent configuration** (system prompt + tools + MCP servers + skills), invoked by our FastAPI endpoints via the Anthropic Managed Agents beta API (`managed-agents-2026-04-01` header). Our code is a thin proxy: start session → stream events → persist output. No uvicorn-side tool-use loop, no plugin packaging on disk, no hand-rolled registry.

The shared substrate across all three lanes is `src/scoring/` and `src/pipeline/` — and that is correct, because the whole point of the research lane is to refine that engine, and the Claude-powered lanes should build on the same scoring primitives.

### Managed Agents — the Claude runtime for Widby

All new Claude-powered features from Phase 2 onward are Managed Agent configurations. Rationale:

- **No infrastructure to manage.** Anthropic stores the agent (system prompt + tools + `mcp_servers` + `skills`), versions it, runs sessions on their side. Our FastAPI is a session orchestrator, not a host.
- **Composable by design.** Each recipe = one agent. Want cross-referenced reports? Create a "cross_reference_report" agent. Want a competitor gap analyzer? Create a "competitor_gap" agent. They share MCP servers (DataForSEO, SerpAPI, etc.) through the agent registry, not through a local `PluginRegistry`.
- **Skills are first-class.** A SKILL.md file tells Claude how to behave; Managed Agents loads it as part of the agent's configuration. The ad-hoc "recipe playbook" concept from 012 maps cleanly onto skills.
- **Versioned agent configs.** Updating an agent mints a new version; existing sessions continue on their pinned version. Ops story is clean.

The dormant 012 code (`src/research_agent/recipes/*`, `src/research_agent/templates/*`, `/api/reports/*`) stays in the tree as **legacy**, not as a future path. When we ship the cross-referenced reports feature (Phase 4), it'll be a new Managed Agent configuration — not a revival of the hand-rolled 012 runtime. The 012 Jinja templates are still useful reference material for the HTML output format.

`ANTHROPIC_API_KEY` is already in `.env`. Managed Agents uses the same auth with the added `anthropic-beta: managed-agents-2026-04-01` header.

## Foundation scope — what ships on this branch

Three pages on `apps/app/src/app/(protected)/`, matching the Widby design bundle at [docs/designs/widby-niche-finder-v1/project/](docs/designs/widby-niche-finder-v1/project/) in the existing light academic theme ([apps/app/src/app/globals.css](apps/app/src/app/globals.css)). Zero Claude calls in the Foundation — this is the deterministic product skeleton.

### Page 1: Home — `(protected)/page.tsx`

Replaces the current redirect stub. Dashboard layout per `Widby Home.html`:

- Greeting header with user context
- 4 stat cards: niches scored, watchlist size, average opportunity score, total reports count
- Hero quick-search strip (collapsed command bar) — links to `/niche-finder`
- Recommended metros grid — Foundation: top 6 recent reports from Supabase; real recommendation algorithm lives in a later phase
- Recent activity feed — Foundation: last 10 reports, newest first
- Saved-searches block — Foundation: empty state with "coming soon" copy

### Page 2: Niche finder — `(protected)/niche-finder/page.tsx`

Upgrades the 014 simple version to Variation B (command center) per `Niche Search.html`:

- Top tabs: **Niche & city** (default, active) and **Strategy** (visible but stubbed — click shows "coming soon" toast; the real strategy search lands in Phase 3)
- Hero search row: `CityAutocomplete` + niche (service) input + submit button
- Strategy preset rail: the 8 archetype cards (`AGGREGATOR_DOMINATED`, `LOCAL_PACK_FORTIFIED`, `LOCAL_PACK_ESTABLISHED`, `LOCAL_PACK_VULNERABLE`, `FRAGMENTED_WEAK`, `FRAGMENTED_COMPETITIVE`, `BARREN`, `MIXED`) from `niche-shared.jsx`. Visible but non-functional in Foundation.
- Result section: single `StandardSurfaceResponse` card after a successful submit — classification pill + opportunity score (0–100) + short signal summary
- Right rail: pinned + recent queries. Foundation: LocalStorage persistence.

Backend: existing `POST /api/niches/score` via the consumer proxy at `apps/app/src/app/api/agent/scoring/route.ts` (landed in 014).

### Page 3: Reports — `(protected)/reports/page.tsx`

Re-skins the 014 basic version per `Widby Reports.html`:

- Summary stats row (total reports, strategy distribution)
- Search input (client-side filter over titles / cities / services)
- **Archetype chip filter** — multi-select, 8 chips + "All strategies" clear action; filters the table by archetype
- Sortable table: ID / strategy (archetype short name) / metros / top opportunity score / status pill / owner / date
- Empty state when filters return no rows
- SSR from Supabase `reports` table; client-side filter and sort

Report detail pages at `/reports/{id}` are Phase 2 scope.

### Sidebar

Stays scoped to consumer product: **Home · Niche finder · Recommendations (stub) · Reports** (+ Saved once Phase 3 ships). No research-graph / experiments / research-chat — those live in `apps/admin` only.

## Explicit non-goals for the Foundation

These are called out so scope doesn't creep. Each gets its own phase below.

- **Consumer Exploration surface** (US2 from [specs/011-niche-exploration-ui/spec.md](specs/011-niche-exploration-ui/spec.md)) — raw-evidence drill-down. Admin has it; consumer ships in **Phase 2**.
- **Exploration assistant** (US3 from 011 spec) — Claude tool-use follow-up. Ships in **Phase 2** as a Managed Agent.
- **Strategy search backend** — endpoint like `GET /api/niches/by-archetype`. Stubbed in Foundation UI; backend ships in **Phase 3**.
- **Saved searches feature** — new Supabase table + save/unsave UI + list retrieval. Empty state in Foundation; ships in **Phase 3**.
- **Report detail pages** — `/reports/{id}` on either app. Ships in **Phase 2**.
- **Recommended metros algorithm** — product decision + endpoint. Foundation uses last N reports as placeholder. Real algorithm in **Phase 3**.
- **Cross-referenced recipe reports** — the 012 vision, rebuilt as Managed Agents. Ships in **Phase 4**.
- **Managed Agents plumbing** — agent configuration management, session proxy, streaming event handling. Introduced in **Phase 2** when the first Claude-powered feature lands.
- **Multi-user RLS** — 014 notes current policies grant `authenticated` users full read across reports. Acceptable for internal/dev phase.
- **`src/product_api/` module extraction** — pure refactor. Non-blocking.

## Phased roadmap (after Foundation)

The phases below are not part of this spec. They're named here so the Foundation's design choices don't preclude them.

### Phase 2 — Exploration surface + assistant (Managed Agents introduction)

- Build `apps/app/src/app/(protected)/niche-finder/exploration/page.tsx` per 011 spec US2: same score card + evidence panel below
- Build `apps/app/src/app/(protected)/reports/[id]/page.tsx` — report detail view
- **First Managed Agent configuration**: `widby-exploration-assistant`
  - System prompt: "You are a niche-research assistant. The user is looking at a niche score for {service, city}. Help them investigate edge cases using the tools available."
  - Tools: DataForSEO MCP, SerpAPI MCP (or custom tools wrapping our existing clients if MCP wrappers aren't ready yet)
  - Skills: a `niche-investigation` skill that teaches Claude how to reason about SERP archetypes and signal evidence
- **Backend plumbing**: a new `src/product_api/managed_agents.py` module that creates/updates agents by name, starts sessions against stored agent IDs, streams events back to the FastAPI response, persists transcripts. Small surface area — it wraps `client.beta.agents.*` + `client.beta.sessions.*`.
- **FastAPI endpoint**: `POST /api/niches/exploration/chat` — body `{niche_query, message}`, response is SSE stream of agent events
- **Consumer UI**: chat panel on the exploration page wired to the SSE endpoint

### Phase 3 — Strategy search + saved searches + recommendations

- **Strategy search**: new endpoint `GET /api/niches/by-archetype?archetype=X&limit=Y`. Could be a pure Supabase query OR a Managed Agent that orchestrates multiple score lookups — TBD at phase scoping
- Wire the Niche Finder's Strategy tab to the new endpoint (replace the "coming soon" toast)
- **Saved searches**: new Supabase table, save/unsave UI, list retrieval; integrate into Home + Niche Finder pinned rail
- **Recommendations algorithm**: product decision + endpoint; home page recommended-metros grid switches off the placeholder

### Phase 4 — Cross-referenced recipe reports (the 012 vision, rebuilt on Managed Agents)

- Each recipe from the [covariance SEO intelligence map](seo-api-intelligence.html) becomes a Managed Agent configuration (`rank-difficulty-estimator`, `lead-value-estimator`, `competitor-gap-analyzer`, `app-idea-validator`, `content-market-fit-finder`, `ai-visibility-tracker`, etc.)
- Each agent loads a SKILL.md that encodes the recipe's playbook
- Shared MCP servers: DataForSEO, SerpAPI, Firecrawl, Apify
- **Consumer surface**: a new page `(protected)/recipes/` with recipe cards; selecting one starts a Managed Agent session and renders the output as HTML (reusing the 012 Jinja templates as reference output formats)
- **Research lane integration**: some of these agents (e.g. `competitor-gap-analyzer`) could also be invoked from `apps/admin` for research workflows — same agent, different surface

### Phase 5 — Research agent migration (optional)

- Port `src/research_agent/` from plain Anthropic SDK + hand-rolled `PluginRegistry` to Managed Agents
- The Ralph loop becomes a loop of Managed Agent sessions with a "research-experimenter" agent configuration
- Hypotheses, experiment runs, knowledge graph persistence stay on our side; only the Claude orchestration moves
- This is a cleanup; the research agent works fine today, no urgency

## Critical files

### New (to be created for Foundation)
- `apps/app/src/app/(protected)/page.tsx` — rewrite the redirect stub into the Home dashboard
- `apps/app/src/components/home/StatCardRow.tsx`
- `apps/app/src/components/home/HeroQuickSearch.tsx`
- `apps/app/src/components/home/RecommendedMetros.tsx`
- `apps/app/src/components/home/RecentActivityFeed.tsx`
- `apps/app/src/components/home/SavedSearchesBlock.tsx`
- `apps/app/src/components/niche-finder/NicheFinderTabs.tsx`
- `apps/app/src/components/niche-finder/StrategyPresetRail.tsx`
- `apps/app/src/components/niche-finder/PinnedRecentRail.tsx`
- `apps/app/src/components/reports/ArchetypeChipFilter.tsx`
- `apps/app/src/components/reports/ReportsTable.tsx`
- `apps/app/src/lib/archetypes.ts` — the 8-archetype registry (id, short name, tint CSS var, blurb), shared across niche-finder + reports

### Modified (rewrites on Foundation scaffolding from 014 merge)
- `apps/app/src/app/(protected)/niche-finder/page.tsx` — upgrade to Variation B layout
- `apps/app/src/app/(protected)/reports/page.tsx` — replace with chip-filtered table layout
- `apps/app/src/components/Sidebar.tsx` — confirm no research links leak in

### Reused as-is (from 013/014 merge)
- `apps/app/src/components/niche-finder/CityAutocomplete.tsx`
- `apps/app/src/app/api/agent/scoring/route.ts`
- `apps/app/src/app/api/agent/metros/suggest/route.ts`
- `apps/app/src/app/api/agent/health/route.ts`
- `apps/app/src/lib/niche-finder/*` — types, request-validation, metro-suggest, reports-mapper

### Untouched (research lane)
- All of `src/research_agent/` — no changes in Foundation
- All of `apps/admin/` — no changes in Foundation

### Legacy (leave in place, reference only)
- `src/research_agent/recipes/*` (from 012) — will be superseded by Phase 4 Managed Agents, not revived
- `src/research_agent/templates/*` (from 012) — retained as HTML output reference for Phase 4

## Build sequence

Five phases for Foundation. Each produces a shippable increment.

**Phase A — Foundation integration**
1. Create branch `015-niche-finder-product-v1` off `main`
2. Merge `013-niche-operational-wiring` (backend routes + Supabase schema + admin proxies)
3. Merge `014-consumer-niche-finder-wiring` (consumer proxies + Supabase RLS + CityAutocomplete + scaffolded niche-finder + basic reports)
4. Resolve merge conflicts; run full test suite + `ruff check` + `tsc --noEmit` across both apps. Baseline green.

**Phase B — Home page**
1. Archetypes registry (`src/lib/archetypes.ts`) — single source of truth for the 8 archetypes' ids, short names, CSS tint vars, blurbs
2. StatCardRow + mock-data prop first, wire to Supabase queries once layout matches mock
3. HeroQuickSearch as a read-only preview that links to `/niche-finder`
4. RecommendedMetros + RecentActivityFeed — both backed by `reports` table via server component
5. SavedSearchesBlock — static empty-state
6. Assemble `(protected)/page.tsx`; remove the redirect

**Phase C — Niche Finder upgrade**
1. NicheFinderTabs component (niche-&-city / strategy)
2. StrategyPresetRail — pure presentation, click → "coming soon" toast
3. PinnedRecentRail — LocalStorage state, useEffect hydration
4. Rewrite page.tsx as command-center layout using existing CityAutocomplete + niche input
5. Keep existing form-submit wiring (posts to `/api/agent/scoring`, renders `StandardSurfaceResponse`)

**Phase D — Reports re-skin**
1. ArchetypeChipFilter — multi-select chips, "All" + "Clear" actions
2. ReportsTable — sortable columns, empty state, ellipsis-with-title-hover on long cells
3. Rewrite page.tsx as SSR list + client-side filter + sort
4. Map report rows to include `archetype_id` (check Supabase `metro_scores` first; add mapper if missing)

**Phase E — Polish**
1. Playwright E2E: login → home → niche finder submit → reports list shows new entry → filter by archetype → empty state
2. Accessibility: keyboard nav, focus states, ARIA on tabs / chips / autocomplete
3. Update `apps/app/CLAUDE.md` to describe the Foundation consumer state
4. Changelog entry

## Verification

Per-phase acceptance:

**Foundation integration (A)** — `pytest tests/unit/ -q` green; `cd apps/app && npx tsc --noEmit && npx vitest run` green; `cd apps/admin && npx tsc --noEmit && npx vitest run` green; `ruff check src/ tests/` green. No dropped tests, no regressions.

**Home (B)** — Playwright navigates to `/`, sees greeting + 4 stat cards + quick search + 6 metro cards + recent activity rows; Source Serif headings, warm paper background, ink text. Lighthouse a11y ≥ 95.

**Niche Finder (C)** — Playwright: type city in autocomplete, select from results, type "roofing", submit with dry-run env var; score card renders with classification pill + score number. Click Strategy tab; click preset card; "coming soon" toast appears; no navigation.

**Reports (D)** — Playwright: reports page shows summary stats + chips + table; click "Pack vulnerable" chip, table filters; click "Clear"; all rows return. Sort by date desc confirmed.

**E2E (E)** — full flow: login → home → quick-search → niche-finder → submit → navigate to reports → see new entry at top → click "Pack vulnerable" chip → empty or filtered.

## Open questions (for implementation planning)

1. **Archetype on `reports` table**: the 013 backend persists a scoring result; does the Supabase `metro_scores` row already carry an archetype id, or do we derive it at read-time from `serp_archetype`? Decided in Phase A; add mapper if missing.
2. **Recommended metros query**: Phase B ships "top 6 recent reports" as placeholder. Real algorithm owner + date belong on the Phase 3 spec, not this one.
3. **Saved searches table**: Phase 3 scope; flagged now so Home's empty state copy doesn't drift.
4. **Strategy search endpoint shape**: Phase 3; probably `GET /api/niches/by-archetype?archetype=X&limit=Y`. Decide at Phase 3 scoping whether pure Supabase query or Managed Agent-orchestrated.
5. **Managed Agents session lifecycle** (Phase 2): are exploration-assistant sessions single-turn or multi-turn? Does each message open a new session or continue one? Affects how we persist transcripts.
6. **Managed Agents cost/rate budget** (Phase 2+): need an envelope before we turn the assistant on for end users. Exploration assistant is invoked from the consumer product; a chatty user could rack up calls. Budget and rate-limit per user/session at Phase 2 scoping.
