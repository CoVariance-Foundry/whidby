# Implementation Plan: M16-eval-frontend (Phase 1 — Auth Shell)

**Branch**: `cursor/phase1-scoring-engine-foundation` | **Date**: 2026-04-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/M16-eval-frontend/spec.md`
**Scope**: Phase 1 only — auth gate, login page, simplified sidebar shell (AS-1.2, AS-5.1)

## Summary

Deliver the internal auth gate and navigation shell for the Widby eval frontend. Uses Supabase magic-link (OTP) authentication to restrict access to authenticated users only. The sidebar is scoped to only the agent/chat route for initial dev testing. Other M16 routes remain as placeholders gated behind auth.

## Technical Context

**Language/Version**: TypeScript (Next.js 16 App Router)
**Primary Dependencies**: `@supabase/supabase-js`, `@supabase/ssr`, existing Tailwind v4 + lucide-react
**Storage**: Supabase Auth (managed — no local database for auth)
**Testing**: `next lint` for TypeScript/ESLint; manual flow validation
**Target Platform**: Vercel (app.thewidby.com)
**Project Type**: Web application (internal eval dashboard)
**Constraints**: No secrets in browser bundle; SSR session refresh via middleware

## Constitution Check

| Gate | Status | Notes |
|------|--------|-------|
| Spec artifact presence | PASS | M16 spec.md exists |
| ESLint for TS/JS | WILL VALIDATE | Run `npm run lint` post-implementation |
| Docs-sync validation | N/A | No module interface changes |
| No framework for pipeline | N/A | Frontend only, no pipeline code |
| Spec-driven, test-driven | PASS | Artifacts produced before implementation |

## Project Structure

### Documentation (this feature)

```text
specs/M16-eval-frontend/
├── spec.md
├── plan.md              # This file
└── tasks.md             # Task breakdown
```

### Source Code

```text
apps/app/
├── src/
│   ├── app/
│   │   ├── login/page.tsx           # Magic-link login form
│   │   ├── auth/callback/route.ts   # Code exchange route handler
│   │   ├── (protected)/             # Route group for auth-gated pages
│   │   │   ├── layout.tsx           # Auth check + sidebar layout
│   │   │   ├── page.tsx             # Redirect to /chat
│   │   │   ├── chat/page.tsx        # (existing, moved)
│   │   │   ├── dashboard/page.tsx   # (existing, moved)
│   │   │   ├── experiments/page.tsx # (existing, moved)
│   │   │   ├── graph/page.tsx       # (existing, moved)
│   │   │   └── recommendations/page.tsx # (existing, moved)
│   │   ├── layout.tsx               # Root layout (fonts, globals, no sidebar)
│   │   └── globals.css              # (existing)
│   ├── components/
│   │   └── Sidebar.tsx              # Updated: agent-only nav + sign-out
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts            # Browser client (createBrowserClient)
│   │   │   └── server.ts            # Server client (createServerClient)
│   │   └── utils.ts                 # (existing)
│   └── middleware.ts                 # Supabase session refresh + auth redirect
├── package.json
└── .env.local                       # NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
```

## Auth Flow

```
User visits any route
  → middleware.ts: refreshes session, checks auth
  → If unauthenticated and route is protected → redirect to /login
  → If authenticated and route is /login → redirect to /

Login page (/login):
  → User enters email (prefilled: antwoine@covariance.studio)
  → signInWithOtp({ email, options: { emailRedirectTo: /auth/callback } })
  → "Check your email" confirmation shown

Auth callback (/auth/callback):
  → Exchanges code for session via supabase.auth.exchangeCodeForSession
  → Redirects to /

Protected layout ((protected)/layout.tsx):
  → Server-side: reads session via server client
  → If no session → redirect to /login
  → If session → render sidebar + children
```

## Complexity Tracking

No constitution violations — standard Next.js App Router patterns with Supabase SSR.
