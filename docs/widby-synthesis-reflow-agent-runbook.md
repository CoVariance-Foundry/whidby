# Widby Synthesis Reflow Agent Runbook

This runbook is the execution contract for the `Widby Synthesis Reflow` Linear project. It keeps autonomous agents aligned with the accepted A2 dashboard plus B2 strategies/path synthesis while preserving the existing entitlement, quota, and report access boundaries.

## Context Order

Read context in this order before implementing a child issue:

1. Repo instructions: `AGENTS.md`, then any nested instructions for touched files.
2. Canonical docs: `docs-canonical/ARCHITECTURE.md`, `docs-canonical/REQUIREMENTS.md`, `docs-canonical/DATA-MODEL.md`, `docs-canonical/TEST-SPEC.md`.
3. Linear project source of truth: `Widby Synthesis Reflow`, its source-of-truth document, the active issue, and issue comments.
4. Prototype and notes artifacts referenced by the Linear source-of-truth document.
5. Current repo code, tests, git status, and open PR state.
6. Live providers only when making readiness, deployment, auth, billing, Supabase, Vercel, Render, or smoke-test claims.

Memory can help locate prior work, but it is not proof. Do not claim current readiness from memory.

## Product Invariants

- This is a full production replacement, not a parallel experiment.
- Segment first surfaces are `find_first -> /`, `scale -> /strategies`, `coach_agency -> /agency`, and `researching -> /explore`.
- Visible catalog is Easy Win, GBP Blitz, Expand & Conquer, Keyword Hijack, and locked Portfolio Builder only.
- Cross-metro plays other than locked Portfolio Builder are deferred.
- Scan completion advances Easy Win to GBP Blitz.
- Ranked-site declaration unlocks Expand & Conquer.
- Keyword Hijack requires feasibility/compliance preflight before spend.
- GBP Blitz must stay soft on address dependency.
- Report V1.1 is in scope as the durable detail surface.
- Preserve entitlement, quota consumption/refund, and cached/account-owned report visibility exactly unless a later issue explicitly changes those contracts.

## Work Loop

For every child issue:

1. Fetch the Linear issue and related comments.
2. Inspect likely files and existing local patterns before editing.
3. Check `git status --short --branch`; preserve unrelated user or agent changes.
4. Make the smallest complete change that satisfies the issue.
5. Update canonical docs before code when behavior, architecture, schema, or test obligations change.
6. Add or update focused tests for the touched behavior.
7. Run the standard approval gates below.
8. Capture screenshots/traces for every touched frontend state.
9. Open or update a non-draft PR linked to the Linear issue when implementation code changes.
10. Post a concise Linear handoff with evidence and residual risk.

## Standard Approval Gates

Run the gates that match the touched surface. Do not mark a ticket done with missing gates; record blockers in Linear instead.

| Surface | Required gates |
| --- | --- |
| Canonical docs | `npx docguard-cli guard`, `npx docguard-cli diff` |
| Python/backend | `ruff check src tests`, focused `python -m pytest ...`, broader unit suite when shared contracts change |
| Consumer app TypeScript | `npm --workspace apps/app test -- <focused files>`, `cd apps/app && npx --no-install tsc --noEmit`, `npm run lint` or affected workspace lint |
| Admin app TypeScript | `npm --workspace apps/admin test -- <focused files>`, `cd apps/admin && npx --no-install tsc --noEmit`, `npm run lint` or affected workspace lint |
| Frontend UI | Playwright E2E for the touched flow plus screenshot evidence for desktop and mobile states |
| Deployment/live readiness | Provider-specific live evidence from Vercel, Supabase, Render, GitHub checks, or authenticated smoke tests |

Docs-only tickets must still run DocGuard and must explicitly state when no frontend surface changed.

## Visual Evidence Rules

Frontend tickets must include screenshots or traces for all states touched by the issue, including loading, empty, error, locked/upgrade, and success states when the implementation changes them. Use existing Playwright configs and artifact locations where possible.

Preferred commands:

```bash
npm run test:e2e:app:local -- <spec>
npm run qa:visual:app
npm run qa:visual:admin
```

If local authenticated visual QA is blocked by environment or provider credentials, do not fake it. Record the blocker, the route/state that remains unverified, and the next live/preview smoke needed.

## Handoff Template

Post this shape as a Linear issue comment before moving an issue out of implementation:

```text
Implemented:
- ...

Files changed:
- ...

Verified:
- command: result
- Playwright/screenshots/traces: path(s)

Not verified:
- ...

No frontend surface changed:
- yes/no; if no, list visual evidence.

Risks / follow-ups:
- ...
```

## Closeout Rules

- Keep planned, implemented, tested, visually verified, PR-reviewed, merged, and live-ready separate.
- Do not mark a Linear issue done until required local gates pass or the blocker is recorded and accepted.
- Do not mark the project ready until Wave 6 has local seeded E2E, screenshot/trace evidence, and deployed smoke with a test account.
- Do not bulk-close stale proto-convergence issues; treat them as historical reference unless explicitly pulled into this project.
