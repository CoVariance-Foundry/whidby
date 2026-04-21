# Tasks: M16-eval-frontend (Phase 1 — Auth Shell)

**Input**: Design documents from `/specs/M16-eval-frontend/`
**Prerequisites**: plan.md (required), spec.md (required)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 = auth gate per AS-1.2, US2 = shell navigation per AS-5.1)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add dependencies and environment contract

- [x] T001 Add `@supabase/supabase-js` and `@supabase/ssr` to apps/app/package.json
- [x] T002 [P] Create `.env.local.example` documenting `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` in apps/app/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Supabase client utilities and middleware that all auth-dependent routes need

- [x] T003 Create browser Supabase client in apps/app/src/lib/supabase/client.ts
- [x] T004 [P] Create server Supabase client in apps/app/src/lib/supabase/server.ts
- [x] T005 Create middleware.ts in apps/app/src/ for session refresh and auth redirect

**Checkpoint**: Supabase clients and middleware ready — auth routes can now be built

---

## Phase 3: User Story 1 — Auth Gate (Priority: P1, maps to AS-1.2)

**Goal**: Unauthenticated users are blocked from the app; email + password sign-in works end-to-end.

> Originally specified with Supabase magic-link (OTP). Replaced by email/password in PR #22 (`012-auth-password-login`). Tasks below reflect the current implementation; file paths are as shipped in the admin rename (was `apps/app/` pre-reorg, now `apps/admin/`). A mirror login page also ships in the consumer `apps/app/` and shares the same Supabase users.

**Independent Test**: Visit any protected route while logged out → redirected to /login. Enter email + password → redirected to `/` (or original destination).

### Implementation for User Story 1

- [x] T006 [US1] Create login page with email/password form at apps/admin/src/app/login/page.tsx (+ mirror at apps/app/src/app/login/page.tsx)
- [x] T007 [US1] Create auth callback route handler at apps/admin/src/app/auth/callback/route.ts (retained for future OAuth providers)

**Checkpoint**: Auth flow functional — login, callback, session established

---

## Phase 4: User Story 2 — Shell Navigation (Priority: P2, maps to AS-5.1)

**Goal**: Authenticated users see a sidebar with only the agent route; existing pages are gated behind auth

**Independent Test**: Log in → land on /chat with sidebar showing only "Agent". Other routes remain accessible but behind auth.

### Implementation for User Story 2

- [x] T008 [US2] Create protected route group layout at apps/app/src/app/(protected)/layout.tsx with server-side auth check and sidebar
- [x] T009 [US2] Move existing page files into (protected)/ route group (chat, dashboard, experiments, graph, recommendations, root redirect)
- [x] T010 [US2] Update root layout at apps/app/src/app/layout.tsx to remove sidebar (now in protected layout)
- [x] T011 [US2] Update Sidebar.tsx to show only agent nav item and add sign-out button

**Checkpoint**: Protected shell with agent-only sidebar working

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T012 [P] Run `npm run lint` in apps/app and fix any lint errors
- [x] T013 Verify auth redirects work correctly (logged out → /login, logged in → /chat, /login when logged in → /)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Phase 1 (packages installed)
- **US1 (Phase 3)**: Depends on Phase 2 (clients + middleware)
- **US2 (Phase 4)**: Depends on Phase 2 (server client for layout auth check)
- **Polish (Phase 5)**: Depends on Phases 3 + 4

### Parallel Opportunities

- T002 can run in parallel with T001
- T003 and T004 can run in parallel
- US1 and US2 can proceed in parallel after Phase 2

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (auth gate)
4. **STOP and VALIDATE**: Magic-link flow works

### Full Delivery

1. Setup → Foundational → US1 → US2 → Polish
2. Total: 13 tasks across 5 phases
