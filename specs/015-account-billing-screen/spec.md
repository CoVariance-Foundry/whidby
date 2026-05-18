# Feature 015 - Account & Billing Screen

## Problem

Whidby has account-scoped entitlements, Stripe Checkout/Portal routes, subscription webhooks, and quota enforcement, but the consumer app does not yet give users one clear place to understand or manage that account state. Users need to see their current plan, report usage, billing-cycle reset, payment method path, and password/security actions without leaving the product shell or guessing where Stripe-managed billing lives.

## Design Source

- Design artifact: `Account.html` from `https://api.anthropic.com/v1/design/h/J_lxIOcOx-YX0POXZeZYHw?open_file=Account.html`
- Designer prompt: admin/account management screen covering subscription, upgrade/downgrade/cancel, reports run, billing reset, payment method add/change, and password management.
- User correction from design review: keep the existing product convention where the account entry lives in the bottom sidebar user menu, showing the user email and opening a popover with account settings.

The prototype includes a full-page Account & billing screen with a plan hero, usage meter, plan comparison cards, payment method rows, password/security section, cancellation confirmation, and a bottom-sidebar user-menu entry. Treat the prototype as visual/product direction, not production data truth. Its plan prices and quotas drift from Whidby canon; implementation must use the current `free` / `plus` / `pro` rules below.

## Goal

- Add a protected consumer account/settings surface that summarizes the current user's account, subscription, report usage, billing cycle, payment method path, and password/security controls.
- Preserve the existing `UserMenu` entry pattern in the bottom of the sidebar; the trigger should display the user's email and current plan label.
- Use Stripe-hosted billing management for checkout, plan changes, payment method updates, invoice access, downgrade, and cancellation instead of collecting card details in Whidby UI.
- Make usage and entitlement copy consistent with canonical Whidby tiers: `free`, `plus`, and `pro`.

## Canonical Business Rules

| Tier | Price | Fresh report quota | Cached report access |
| --- | ---: | ---: | --- |
| `free` | $0/mo | 0 reports/month | Yes |
| `plus` | $49/mo | 10 reports/month | Yes |
| `pro` | $100/mo | 50 reports/month | Yes |

Free users can browse cached reports and cached discovery surfaces, but cannot generate fresh reports. Plus and Pro users can generate fresh reports until their monthly quota is exhausted. PostHog may hide or disable account UI entry points during rollout, but Supabase entitlement/RLS and Stripe webhook state remain the source of truth.

## User Stories

- As an authenticated consumer user, I want to open account settings from the bottom sidebar menu so that account management stays in the same place as the current product convention.
- As a free user, I want to see that I have cached-report access and 0 fresh reports so that I understand why fresh report actions require an upgrade.
- As a paid user, I want to see my current plan, monthly report usage, remaining reports, and reset date so that I can manage my quota before the cycle ends.
- As a paid user, I want to upgrade, downgrade, or cancel from the account screen so that I can adjust my subscription without contacting support.
- As any user, I want to add or change payment information through a trusted billing flow so that my card data is handled securely.
- As any user, I want to manage my password/security from account settings so that I can keep access secure.

## Requirements

### P0 - Must Have

1. **Account entry follows existing UserMenu convention**
   - Bottom-sidebar `UserMenu` remains the only account/settings entry point in the primary shell.
   - Trigger displays user email, not only full name, plus current plan label.
   - Popover includes Account settings, Admin dashboard, and Sign out.
   - Account settings marks active state when the user is on the account/settings route.

2. **Protected account/settings route**
   - Route is available only to authenticated consumer users.
   - Page resolves Supabase user and account entitlement server-side.
   - Missing entitlement shows an actionable error state, not an empty dashboard.

3. **Subscription summary**
   - Show current plan, price, subscription status, billing cycle start/end, and next reset/renewal date.
   - Copy differs for `free` users: no paid renewal, fresh reports unavailable, cached access available.
   - Paid canceled-at-period-end state must say access continues until period end before dropping to Free.

4. **Report usage meter**
   - Show reports run this cycle, monthly limit, remaining reports, percentage used, and reset date.
   - Use `usage_counters` / entitlement data, not client-only mock state.
   - Near-limit and exhausted states must be visually and textually clear.
   - Free users should not show misleading "remaining fresh reports"; show 0 fresh reports and cached access instead.

5. **Plan actions**
   - Free users see upgrade options for Plus and Pro.
   - Plus users can upgrade to Pro or manage/cancel through Stripe Customer Portal.
   - Pro users can manage/downgrade/cancel through Stripe Customer Portal.
   - Whidby UI must not locally mutate subscription state; Stripe webhook sync updates Supabase.
   - If `billing_checkout_enabled` is false, actions show a disabled/unavailable state with safe copy.

6. **Payment and invoices**
   - Payment method section shows whether Stripe billing customer data exists.
   - Add/change payment method opens Stripe Customer Portal when a billing customer exists; otherwise use Checkout for first paid plan selection.
   - Invoice history opens Stripe Customer Portal; do not build a local invoice table in this slice.
   - Do not render inline card collection forms in production.

7. **Password/security**
   - Provide a password management section with the current supported action.
   - For Supabase email/password users, use Supabase password update or password reset flow.
   - If password management is not fully implemented in this slice, show a clear disabled state and keep the route scoped for a fast follow-up.

### P1 - Nice to Have

1. Show payment method brand/last4/expiry if Stripe customer payment method details are available through a safe server route.
2. Add a "View report history" link from usage to `/reports`.
3. Add success/error toasts after returning from Stripe Checkout or Portal via query params.
4. Include active session and 2FA rows as disabled "coming later" states if Supabase support is not ready.

### P2 - Future Considerations

1. Multi-seat account membership management.
2. Local invoice list synced from Stripe.
3. Self-serve billing email edit outside Stripe Portal.
4. Dedicated passwordless/social-auth account management variants.
5. Admin-side impersonation or support tools.

## Data and API Contracts

Use existing account and billing primitives first:

- `resolveEntitlementContext()` for `account_id`, `plan_key`, `monthly_report_limit`, `subscription_status`, `current_period_start`, and `current_period_end`.
- Supabase `usage_counters` for monthly fresh-report usage.
- Supabase `billing_customers` for Stripe customer presence.
- `POST /api/billing/checkout` for first paid checkout.
- `POST /api/billing/portal` for payment method, invoices, plan management, downgrade, and cancellation.
- Supabase Auth for password update/reset.

If additional account-summary data is needed, add one narrow app route such as `GET /api/account/summary` that returns snake_case JSON:

```json
{
  "account_id": "uuid",
  "email": "user@example.com",
  "plan_key": "plus",
  "plan_label": "Plus",
  "subscription_status": "active",
  "current_period_start": "2026-05-03T00:00:00Z",
  "current_period_end": "2026-06-03T00:00:00Z",
  "monthly_report_limit": 10,
  "fresh_reports_used": 4,
  "stripe_customer_exists": true,
  "billing_management_available": true
}
```

## UX Notes

- Keep the light academic Whidby theme: paper background, restrained cards, serif headings, compact sidebar.
- Account screen should feel like a working settings surface, not a marketing pricing page.
- Use the prototype's page structure: page header, current-plan hero, usage meter, plan comparison area, payment/invoice section, password/security section, and cancellation affordance.
- Keep cards shallow and utilitarian. No nested cards.
- Use existing icon system (`apps/app/src/lib/icons.tsx`) rather than custom SVGs where possible.
- Mobile should stack sections in one column and keep plan actions reachable without horizontal overflow.

## Acceptance Criteria

- Given an authenticated user opens the bottom sidebar user menu, when they click Account settings, then they reach the protected account/settings surface.
- Given the user has no paid subscription, when the page renders, then the plan summary shows Free, 0 fresh reports/month, cached access copy, and upgrade CTAs.
- Given the user has a Plus entitlement with 4 of 10 reports used, when the page renders, then usage shows 4 used, 6 remaining, the billing reset date, and no exhausted-state warning.
- Given the user has exhausted their monthly quota, when the page renders, then the usage meter and copy clearly indicate that fresh reports are unavailable until reset or upgrade.
- Given billing checkout/portal is disabled by feature flag, when the user tries to manage billing, then the UI does not call Stripe and shows a non-destructive disabled state.
- Given a paid user clicks Manage payment method, View invoices, Downgrade, or Cancel, when billing management is available, then the UI starts the Stripe Customer Portal flow and does not directly mutate Supabase subscription rows.
- Given the user returns from Stripe with a success/cancelled query param, when the account page loads, then the page shows a contextual toast or banner and re-reads account state.
- Given a user requests password management, when the current auth provider supports password update/reset, then the action uses Supabase Auth and shows success/error feedback.

## Out of Scope

- Implementing the screen in this spec-writing slice.
- Creating a local billing system that bypasses Stripe-hosted Checkout/Portal.
- Changing the `free` / `plus` / `pro` tier prices, report quotas, or cached-report entitlement rules.
- Building team/member management.
- Writing new schema tables unless implementation discovers a confirmed gap not covered by current account, subscription, billing customer, and usage tables.

## Open Questions

- Should the final route remain the existing `/settings` link from `UserMenu`, or should it become `/settings/account` with `/settings` redirecting there?
- Should password change be inline in v1, or should v1 send a Supabase password reset email to reduce auth edge cases?
- Should plan comparison cards show only current paid tiers, or include a compact Free card for downgrade context?
- Do we want to show Stripe payment method brand/last4 in v1, or keep payment state as "managed in Stripe" until a safe payment-method summary route exists?

## Implementation Plan

1. Update `UserMenu` and `Sidebar` so the trigger can display user email and current entitlement plan label, and can mark Account settings active.
2. Add a protected account/settings page in `apps/app` that resolves entitlement, usage, and billing customer state server-side.
3. Build the Account & billing UI from existing app primitives/styles, matching the prototype layout while using canonical quotas/prices.
4. Wire plan/payment/invoice/cancel actions to existing billing checkout/portal routes with safe disabled/error states.
5. Add password management with Supabase Auth or a clearly disabled/reset-email flow, depending on supported current auth behavior.
6. Add focused tests for entitlement rendering, billing action routing, feature-flag disabled state, and UserMenu entry behavior.
7. Update canonical docs only if implementation changes architecture, data model, or API contracts beyond this spec.

## Verification Targets

- `npm run lint --workspace apps/app -- ...`
- Focused app Vitest tests for account/settings and user-menu behavior.
- Browser smoke on the protected route: unauthenticated redirect, authenticated Free state, authenticated paid state, billing disabled state.
- `npx docguard-cli guard` after doc changes, treated as diagnostic output because this repo has known noisy warnings.
