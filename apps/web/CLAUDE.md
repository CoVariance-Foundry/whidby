# CLAUDE.md

> **Canonical docs** for project-wide architecture, requirements, and environment live in
> `docs-canonical/` at the repo root. This file covers app-specific guidance for `apps/web/`.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Whidby** (branded as "Widby") is a pre-launch landing page for an AI market intelligence tool targeting rank-and-rent SEO practitioners. The site collects waitlist signups via a multi-step onboarding modal and tracks visitor analytics. There is no authenticated app yet — this is a marketing/waitlist site.

## Commands

```bash
npm run dev      # Start Next.js dev server (localhost:3000)
npm run build    # Production build
npm run start    # Serve production build
npm run lint     # ESLint (flat config, core-web-vitals + typescript)
```

No test framework is configured.

## Architecture

### Stack
- **Next.js 16** (App Router, `src/` directory)
- **Tailwind CSS v4** (uses `@theme` in globals.css, not tailwind.config)
- **Supabase** for data persistence (waitlist signups, analytics events, onboarding responses)
- **ActiveCampaign** for email marketing CRM (contact sync, tagging)
- **Framer Motion** for animations
- **Lucide React** for icons

### Path alias
`@/*` maps to `./src/*`

### Data flow

The entire page (`src/app/page.tsx`) is a single `'use client'` component tree. All marketing sections are composed here with a shared `openWaitlist(source)` callback that opens the `WaitlistModal`.

**Waitlist signup flow:**
1. User clicks CTA → `WaitlistModal` opens (4-step onboarding wizard)
2. Step 1: email → `POST /api/waitlist` → inserts into Supabase `waitlist_signups` + syncs contact to ActiveCampaign
3. Steps 2-4: business size, sites managed, use cases → `POST /api/onboarding` → inserts into Supabase `onboarding_responses` + tags contact in ActiveCampaign

**Analytics pipeline:**
- `AnalyticsProvider` wraps the page and tracks: page views, scroll depth milestones (25/50/75/100%), section visibility (via IntersectionObserver), CTA clicks
- All events → `POST /api/events` → Supabase `analytics_events` table
- UTM params are captured from URL and persisted in sessionStorage (`rr_utm` key)
- Session IDs are generated per browser session (`rr_session_id` key)

### API routes
| Route | Purpose |
|---|---|
| `/api/waitlist` | Email signup → Supabase + ActiveCampaign |
| `/api/events` | Analytics event ingestion → Supabase |
| `/api/onboarding` | Post-signup survey → Supabase + ActiveCampaign tags |

### Key libraries (`src/lib/`)
- `supabase.ts` — Singleton Supabase client (uses `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY`)
- `activecampaign.ts` — AC API wrapper (uses `ACTIVECAMPAIGN_API_URL` + `ACTIVECAMPAIGN_API_KEY`). Respects AC's 5 req/s rate limit by tagging sequentially.
- `analytics.ts` — Client-side event tracking functions
- `utm.ts` — UTM param capture/storage utilities

### Design system
Defined via Tailwind `@theme` in `globals.css`:
- **Fonts:** Inter (sans), DM Serif Display (serif headings), JetBrains Mono (mono)
- **Accent:** emerald green (`#10B981`) with light/dark/bg variants
- **Dark:** near-black (`#141414`) with card/alt variants
- Custom CSS classes: `.score-circle`, `.progress-track`, `.progress-fill`, `.card-gradient-border`

### Environment variables

Required server-side:
- `ACTIVECAMPAIGN_API_URL`
- `ACTIVECAMPAIGN_API_KEY`

Required (public):
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY`

### Routing config
`next.config.ts` has a redirect from `/podcast` → `/?utm_source=podcast&utm_medium=audio&utm_campaign=launch_2026`
