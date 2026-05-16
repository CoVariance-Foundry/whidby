# Consumer Onboarding Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Implemented in `codex/consumer-onboarding-flow` on 2026-05-16. Closeout context lives in `.Codex/ACTIVE_WORK.md` and `.Codex/project_context.md`; canonical architecture, data model, and test obligations were updated in `docs-canonical/`.

**Goal:** Build production consumer onboarding that persists signup intent, recommends a starter strategy, captures a service + geography target, resumes cleanly, and hands first-report generation to the existing entitlement-protected scoring path.

**Architecture:** Onboarding state lives in Supabase tables scoped to the authenticated user and account. Strategy routing is deterministic TypeScript code under `apps/app/src/lib/onboarding/`, while Next.js route handlers persist profile/target state and reuse existing account entitlement behavior. Fresh report generation must go through `apps/app/src/app/api/agent/scoring/route.ts`; onboarding does not create a parallel scoring or report system.

**Tech Stack:** Next.js App Router, TypeScript, Supabase SSR/client SDK, Supabase SQL migrations/RLS, Vitest + Testing Library, Playwright smoke, DocGuard.

---

## Prototype Inputs

Use these prototype files directly as the UX and interaction reference:

- `/Users/antwoineflowers/Desktop/development/covariance/whidby-ux-proto/src/app/signup/page.tsx`
- `/Users/antwoineflowers/Desktop/development/covariance/whidby-ux-proto/src/app/onboarding/page.tsx`
- `/Users/antwoineflowers/Desktop/development/covariance/whidby-ux-proto/src/lib/strategies.ts`
- `/Users/antwoineflowers/Desktop/development/covariance/whidby-ux-proto/src/components/LocationCombobox.tsx`
- `/Users/antwoineflowers/Desktop/development/covariance/whidby-ux-proto/src/components/StateMultiselect.tsx`
- `/Users/antwoineflowers/Desktop/development/covariance/whidby-ux-proto/src/components/StrategyCard.tsx`
- `/Users/antwoineflowers/Desktop/development/covariance/whidby-ux-proto/src/components/StrategyResultHeader.tsx`

Do not copy prototype local state behavior (`useApp`, local scan counts, static report id). Port the interaction shape into production APIs and existing quota/report contracts.

## File Structure

- `supabase/migrations/016_consumer_onboarding.sql`: create onboarding profile/target tables, RLS policies, and profile upsert/read RPCs.
- `apps/app/src/lib/onboarding/strategy-routing.ts`: production-safe version of prototype `routeOnboardingToStrategy`.
- `apps/app/src/lib/onboarding/types.ts`: shared request/response/status types.
- `apps/app/src/app/api/onboarding/profile/route.ts`: GET/POST route for profile answers and resume state.
- `apps/app/src/app/api/onboarding/target/route.ts`: POST route for selected service + geography target.
- `apps/app/src/app/api/onboarding/start-report/route.ts`: route that validates the saved target and delegates to existing scoring behavior.
- `apps/app/src/app/onboarding/page.tsx`: server page that loads profile state and renders the client flow.
- `apps/app/src/app/onboarding/OnboardingClient.tsx`: production port of prototype onboarding UI.
- `apps/app/src/components/onboarding/ServicePicker.tsx`: service category/custom service step.
- `apps/app/src/components/onboarding/TargetPicker.tsx`: city/state target step using production `CityAutocomplete`.
- `apps/app/src/components/onboarding/OnboardingSummary.tsx`: confirmation and entitlement-aware CTA.
- Tests beside each route/component.
- Update `.Codex/ACTIVE_WORK.md` and `.Codex/project_context.md` only after implementation starts/completes.

---

### Task 1: Add Onboarding Schema and RLS

**Files:**
- Create: `supabase/migrations/016_consumer_onboarding.sql`
- Modify: `docs-canonical/DATA-MODEL.md` only if fields drift from this plan.

- [ ] **Step 1: Write the migration**

Create `supabase/migrations/016_consumer_onboarding.sql`:

```sql
-- 016_consumer_onboarding.sql
-- Durable consumer onboarding state for strategy routing, target capture,
-- resume behavior, and first-report handoff.

CREATE TABLE IF NOT EXISTS onboarding_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES user_profiles(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    intent TEXT CHECK (intent IN ('find_first', 'scale', 'coach_agency', 'researching')),
    focus TEXT,
    coach_or_agency TEXT CHECK (coach_or_agency IN ('coaching', 'agency', 'both')),
    referral_source TEXT,
    recommended_strategy_id TEXT,
    available_strategy_ids TEXT[] NOT NULL DEFAULT '{}',
    next_route TEXT,
    status TEXT NOT NULL DEFAULT 'profile_started' CHECK (
        status IN (
            'profile_started',
            'profile_completed',
            'strategy_recommended',
            'target_selected',
            'report_queued',
            'cached_route_selected',
            'upgrade_required',
            'report_ready'
        )
    ),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_onboarding_profiles_account
    ON onboarding_profiles (account_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS onboarding_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    onboarding_profile_id UUID NOT NULL REFERENCES onboarding_profiles(id) ON DELETE CASCADE,
    strategy_id TEXT NOT NULL,
    niche_keyword TEXT NOT NULL CHECK (length(trim(niche_keyword)) > 0),
    service_category_id TEXT,
    geo_scope TEXT NOT NULL CHECK (geo_scope IN ('city', 'state', 'region', 'nationwide')),
    city TEXT,
    state TEXT,
    cbsa_code TEXT REFERENCES metros(cbsa_code),
    place_id TEXT,
    dataforseo_location_code INTEGER,
    resolved_label TEXT,
    metadata_source TEXT CHECK (
        metadata_source IN ('typed', 'mapbox_selected', 'recent_history', 'fallback_cbsa')
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (onboarding_profile_id, strategy_id)
);

CREATE INDEX IF NOT EXISTS idx_onboarding_targets_profile
    ON onboarding_targets (onboarding_profile_id, updated_at DESC);

ALTER TABLE onboarding_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE onboarding_targets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Account members can read onboarding profiles"
    ON onboarding_profiles FOR SELECT
    TO authenticated
    USING (public.is_account_member(account_id));

CREATE POLICY "Users can update own onboarding profile"
    ON onboarding_profiles FOR UPDATE
    TO authenticated
    USING (user_id = (SELECT auth.uid()) AND public.is_account_member(account_id))
    WITH CHECK (user_id = (SELECT auth.uid()) AND public.is_account_member(account_id));

CREATE POLICY "Users can insert own onboarding profile"
    ON onboarding_profiles FOR INSERT
    TO authenticated
    WITH CHECK (user_id = (SELECT auth.uid()) AND public.is_account_member(account_id));

CREATE POLICY "Account members can read onboarding targets"
    ON onboarding_targets FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM onboarding_profiles op
            WHERE op.id = onboarding_targets.onboarding_profile_id
              AND public.is_account_member(op.account_id)
        )
    );

CREATE POLICY "Users can upsert own onboarding targets"
    ON onboarding_targets FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM onboarding_profiles op
            WHERE op.id = onboarding_targets.onboarding_profile_id
              AND op.user_id = (SELECT auth.uid())
              AND public.is_account_member(op.account_id)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM onboarding_profiles op
            WHERE op.id = onboarding_targets.onboarding_profile_id
              AND op.user_id = (SELECT auth.uid())
              AND public.is_account_member(op.account_id)
        )
    );

CREATE POLICY "Service role full access on onboarding_profiles"
    ON onboarding_profiles FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on onboarding_targets"
    ON onboarding_targets FOR ALL
    USING (auth.role() = 'service_role');
```

- [ ] **Step 2: Verify migration text**

Run:

```bash
git diff --check -- supabase/migrations/016_consumer_onboarding.sql
```

Expected: no trailing whitespace errors.

- [ ] **Step 3: Add schema test coverage**

Add assertions to `tests/unit/test_supabase_schema.py` that the migration includes `onboarding_profiles`, `onboarding_targets`, RLS enablement, and policies using `public.is_account_member`.

- [ ] **Step 4: Run schema tests**

Run:

```bash
pytest tests/unit/test_supabase_schema.py -v
```

Expected: PASS.

### Task 2: Add Shared Strategy Routing

**Files:**
- Create: `apps/app/src/lib/onboarding/strategy-routing.ts`
- Create: `apps/app/src/lib/onboarding/strategy-routing.test.ts`
- Create: `apps/app/src/lib/onboarding/types.ts`

- [ ] **Step 1: Write routing tests**

Create tests for the core prototype routing cases:

```ts
import { describe, expect, it } from "vitest";
import { routeOnboardingToStrategy } from "./strategy-routing";

describe("routeOnboardingToStrategy", () => {
  it("routes researching users to Explore", () => {
    expect(routeOnboardingToStrategy({ intent: "researching" })).toMatchObject({
      starter: "easy_win",
      next_route: "/explore",
    });
  });

  it("routes agency-focused users to Multi-market", () => {
    expect(routeOnboardingToStrategy({
      intent: "coach_agency",
      focus: "agency",
    })).toMatchObject({
      starter: "cash_cow",
      next_route: "/agency",
    });
  });

  it("routes first-niche users to Easy Win by default", () => {
    expect(routeOnboardingToStrategy({
      intent: "find_first",
      focus: "niche",
    })).toMatchObject({
      starter: "easy_win",
      next_route: "/strategies",
    });
  });
});
```

- [ ] **Step 2: Implement production routing**

Port the deterministic logic from prototype `src/lib/strategies.ts`, but use snake_case response keys for route/API contracts:

```ts
export type OnboardingIntent = "find_first" | "scale" | "coach_agency" | "researching";
export type StrategyId =
  | "easy_win"
  | "cash_cow"
  | "blue_ocean"
  | "gbp_blitz"
  | "portfolio_builder"
  | "expand_conquer"
  | "seasonal_arbitrage";

export interface OnboardingStrategyRouting {
  starter: StrategyId;
  available: StrategyId[];
  rationale: string;
  next_route: "/strategies" | "/explore" | "/agency";
}
```

- [ ] **Step 3: Run focused app tests**

Run:

```bash
npm --workspace apps/app test -- apps/app/src/lib/onboarding/strategy-routing.test.ts
```

Expected: PASS.

### Task 3: Add Onboarding Profile API

**Files:**
- Create: `apps/app/src/app/api/onboarding/profile/route.ts`
- Create: `apps/app/src/app/api/onboarding/profile/route.test.ts`
- Modify: `apps/app/src/lib/onboarding/types.ts`

- [ ] **Step 1: Write route tests**

Cover:

- unauthenticated requests return `401`.
- `POST` calls `resolveEntitlementContext`, computes strategy routing, and upserts one `onboarding_profiles` row.
- `GET` returns profile plus latest target when present.

- [ ] **Step 2: Implement route handler**

Use `createClient()` and `resolveEntitlementContext()` from existing production auth/account code. Keep response keys snake_case:

```ts
export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const { user, entitlement } = await resolveEntitlementContext(supabase);
  const body = await req.json();
  const routing = routeOnboardingToStrategy({
    intent: body.intent,
    focus: body.focus,
  });

  const { data, error } = await supabase
    .from("onboarding_profiles")
    .upsert({
      user_id: user.id,
      account_id: entitlement.account_id,
      intent: body.intent,
      focus: body.focus ?? null,
      coach_or_agency: body.coach_or_agency ?? null,
      referral_source: body.referral_source ?? null,
      recommended_strategy_id: routing.starter,
      available_strategy_ids: routing.available,
      next_route: routing.next_route,
      status: "strategy_recommended",
      completed_at: new Date().toISOString(),
    }, { onConflict: "user_id" })
    .select()
    .single();

  if (error) {
    return NextResponse.json({ status: "error", message: error.message }, { status: 500 });
  }
  return NextResponse.json({ status: "success", profile: data, routing });
}
```

- [ ] **Step 3: Run route tests**

Run:

```bash
npm --workspace apps/app test -- apps/app/src/app/api/onboarding/profile/route.test.ts
```

Expected: PASS.

### Task 4: Add Target API and First-Report Handoff

**Files:**
- Create: `apps/app/src/app/api/onboarding/target/route.ts`
- Create: `apps/app/src/app/api/onboarding/target/route.test.ts`
- Create: `apps/app/src/app/api/onboarding/start-report/route.ts`
- Create: `apps/app/src/app/api/onboarding/start-report/route.test.ts`

- [ ] **Step 1: Implement target validation tests**

Validate that `niche_keyword`, `strategy_id`, and `geo_scope` are required; city targets must include `city` or `resolved_label`.

- [ ] **Step 2: Implement target upsert**

The target route should find the user's onboarding profile, upsert the selected target, and update profile status to `target_selected`.

- [ ] **Step 3: Implement start-report tests**

Cover:

- free entitlement returns `403` with `fresh_reports_not_included`.
- state or region targets return cached route guidance instead of calling scoring.
- city targets call the existing scoring route contract with `city`, `service`, `state`, `place_id`, `dataforseo_location_code`, and `metadata_source`.

- [ ] **Step 4: Implement start-report route**

Delegate fresh city scoring to the same internal logic/contract as `/api/agent/scoring`; do not duplicate quota consumption. If direct function reuse is awkward, extract the scoring implementation into `apps/app/src/lib/niche-finder/scoring-proxy.ts` in this task and have both routes call it.

- [ ] **Step 5: Run focused tests**

Run:

```bash
npm --workspace apps/app test -- apps/app/src/app/api/onboarding/target/route.test.ts apps/app/src/app/api/onboarding/start-report/route.test.ts apps/app/src/app/api/agent/scoring/route.test.ts
```

Expected: PASS.

### Task 5: Build Production Onboarding UI

**Files:**
- Create: `apps/app/src/app/onboarding/page.tsx`
- Create: `apps/app/src/app/onboarding/OnboardingClient.tsx`
- Create: `apps/app/src/app/onboarding/OnboardingClient.test.tsx`
- Create: `apps/app/src/components/onboarding/ServicePicker.tsx`
- Create: `apps/app/src/components/onboarding/TargetPicker.tsx`
- Create: `apps/app/src/components/onboarding/OnboardingSummary.tsx`

- [ ] **Step 1: Port the prototype step flow**

Use prototype `onboarding/page.tsx` as the screen reference: welcome, service, region, confirm. Replace `useApp()` mutations with calls to `/api/onboarding/profile`, `/api/onboarding/target`, and `/api/onboarding/start-report`.

- [ ] **Step 2: Use production location input**

Use `apps/app/src/components/niche-finder/CityAutocomplete.tsx` for city-level targeting. Add state/region support only when the CTA routes to cached Explore or agency workflows.

- [ ] **Step 3: Make CTA entitlement-aware**

The summary step should show:

- plus/pro with quota: generate fresh report.
- free: browse cached opportunities.
- target shape not city: continue to Explore or Multi-market.

- [ ] **Step 4: Run UI tests**

Run:

```bash
npm --workspace apps/app test -- apps/app/src/app/onboarding/OnboardingClient.test.tsx
```

Expected: PASS.

### Task 6: Connect Signup Resume Routing

**Files:**
- Modify or create auth/signup route files under `apps/app/src/app/` based on current auth layout.
- Modify: `apps/app/src/app/auth/callback/route.ts`
- Add route/component tests beside modified files.

- [ ] **Step 1: After auth callback, load onboarding profile**

If no completed onboarding profile exists, route to `/onboarding`. If profile status is `strategy_recommended` or `target_selected`, route to the stored `next_route` or `/onboarding` for resume.

- [ ] **Step 2: Preserve safe-next behavior**

Use existing `apps/app/src/lib/auth/safe-next.ts` rules when honoring redirect params.

- [ ] **Step 3: Run auth/onboarding tests**

Run:

```bash
npm --workspace apps/app test -- apps/app/src/app/auth/callback/route.test.ts apps/app/src/app/onboarding/OnboardingClient.test.tsx
```

Expected: PASS.

### Task 7: Final Verification and Docs

**Files:**
- Modify: `.Codex/ACTIVE_WORK.md`
- Modify: `.Codex/project_context.md`
- Modify: `docs-canonical/ARCHITECTURE.md`, `docs-canonical/DATA-MODEL.md`, `docs-canonical/TEST-SPEC.md` only if implementation differs from the saved design or adds new test obligations.

- [ ] **Step 1: Run focused frontend verification**

Run:

```bash
npm --workspace apps/app test -- apps/app/src/lib/onboarding apps/app/src/app/api/onboarding apps/app/src/app/onboarding
npm --workspace apps/app lint
```

Expected: PASS.

- [ ] **Step 2: Run backend/schema verification**

Run:

```bash
pytest tests/unit/test_supabase_schema.py -v
git diff --check
```

Expected: PASS.

- [ ] **Step 3: Run DocGuard after doc changes**

Run:

```bash
npx docguard-cli guard
```

Expected: PASS or known non-high warnings only. If the sandbox cannot reach npm, record the exact `ENOTFOUND` or network failure in the final handoff.

- [ ] **Step 4: Browser smoke**

Start app:

```bash
npm run dev:app
```

Open `http://localhost:3002/onboarding` and verify:

- unauthenticated users are redirected according to current app auth rules.
- profile answers persist after refresh.
- city selection preserves state/place metadata.
- free users are routed to cached Explore instead of fresh scoring.
- paid/quota-enabled users can submit a city target and land on the generated report route.

---

## Self-Review

- Spec coverage: The plan covers durable profile persistence, strategy routing, target capture, entitlement-aware fresh/cached handoff, resume routing, UI porting from the prototype, and verification.
- Placeholder scan: No task depends on an unspecified new subsystem; any extraction from scoring route is explicitly scoped to `scoring-proxy.ts` if needed.
- Type consistency: Public API payloads use snake_case at service boundaries, matching Whidby conventions.
