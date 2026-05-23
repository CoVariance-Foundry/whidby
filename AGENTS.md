# Agent Instructions

> This project follows **Canonical-Driven Development (CDD)** alongside **Spec-Kit** workflows.
> Read canonical docs before making changes. Log drift when deviating.

---

## Project Overview

**Widby** is a niche discovery and scoring platform for rank-and-rent SEO practitioners. Three subsystems: a Python scoring engine (`src/`), an experiment framework (`src/experiment/`), and a Next.js marketing site (`apps/web/`).

## Project Documentation (CDD + Spec-Kit)

This project uses a hybrid documentation strategy:

- **Canonical docs** (maintained source of truth): `docs-canonical/`
  - `ARCHITECTURE.md` — system overview, module map, dependency graph, tech stack
  - `REQUIREMENTS.md` — functional/non-functional requirements, success criteria
  - `DATA-MODEL.md` — entity schemas, data flow, research constants
  - `TEST-SPEC.md` — test obligations, coverage rules, quality gates
  - `ENVIRONMENT.md` — prerequisites, env vars, setup steps, commands
- **Detailed reference docs**: `docs/` — algo spec, product breakdown, data flow (read for deep context)
- **Spec-Kit artifacts**: `specs/` and `.specify/` — per-feature spec/plan/tasks
- **Constitution**: `.specify/memory/constitution.md` — non-negotiable engineering principles
- **Drift tracking**: `DRIFT-LOG.md` (when code deviates from canonical docs)

## Build & Dev Commands

| Command | Purpose |
|---------|---------|
| `npm install` | Install Node dependencies |
| `pip install -e ".[dev]"` | Install Python dependencies |
| `npm run dev` | Dev all apps (Turborepo) |
| `npm run dev:web` | Marketing site (port 3000) |
| `npm run dev:app` | Research dashboard (port 3001) |
| `pytest tests/unit/ -v` | Python unit tests |
| `ruff check src tests` | Python lint |
| `npm run lint` | JS/TS lint |

## Production App Gotchas

- The authenticated production app is `app.thewidby.com` on Vercel project `whidby-agent`; the marketing site is the separate `whidby` project on `www.thewidby.com`. When debugging app/dashboard/reports outages, verify the project before changing Vercel env.
- If `/` shows "Reports are temporarily unavailable" or `/reports` fails with `reports list: HTTP 401`, check both:
  - `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` on the `whidby-agent` Production environment. Stale/mismatched publishable keys make Supabase Auth/PostgREST return `401 Invalid API key`.
  - `WIDBY_APP_BASE_URL=https://app.thewidby.com` on `whidby-agent` Production. Server-side self-fetches must use the public app domain; falling back to `VERCEL_URL` can hit a protected deployment URL and return Vercel SSO `401` before `/api/agent/reports` runs.
- After Vercel env changes, redeploy production and verify with an authenticated smoke test against `https://app.thewidby.com`; env changes alone do not update already-built serverless functions.

## DocGuard — Documentation Enforcement

This project uses **DocGuard** for CDD compliance:

```bash
npx docguard-cli diagnose # Run diagnostic summary + remediation prompts
npx docguard-cli guard    # Validate compliance
npx docguard-cli score    # CDD maturity score
npx docguard-cli diff     # Show documentation/code drift details
```

## Workflow Rules

1. **Read canonical docs first** — Check `docs-canonical/` before suggesting changes
2. **Fall back to reference docs** — Use `docs/` for algorithm details and per-module I/O contracts
3. **Follow spec-kit lifecycle** — Use `/speckit.*` commands for module delivery
4. **Confirm before implementing** — Show a plan, wait for approval
5. **Match existing patterns** — Search codebase for similar implementations
6. **Document drift** — If deviating from canonical docs, add `// DRIFT: reason`
7. **Update canonical docs first** — When changing architecture/requirements/schemas, update `docs-canonical/` before code
8. **Run DocGuard** — After documentation changes, run `npx docguard-cli guard`

## Code Conventions

- Python: PEP 8 via ruff, type annotations required, Google-style docstrings
- TypeScript: ESLint with core-web-vitals + typescript
- **API contract casing**: All JSON payloads at service boundaries use **snake_case** keys (Next.js route handlers, FastAPI endpoints, spec contracts). No camelCase in wire payloads.
- Test file names mirror source: `src/pipeline/keyword_expansion.py` → `tests/unit/test_keyword_expansion.py`
- Constants in `src/config/constants.py`, never hardcoded
- Prompt templates in versioned files under `src/clients/llm/prompts/`

## File Change Rules

- Changes to >3 files require explicit approval
- Schema/data model changes require `docs-canonical/DATA-MODEL.md` update
- New dependencies require justification
- Architecture changes require `docs-canonical/ARCHITECTURE.md` update
- Documentation changes must pass `docguard-cli guard` before commit


<claude-mem-context>
# Memory Context

# [whidby] recent context, 2026-05-22 10:27pm PDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (18,478t read) | 938,169t work | 98% savings

### Apr 29, 2026
S233 Execute Phase 7 Data Providers implementation plan (18 tasks across 4 task groups: Census ACS, Census CBP, BLS Wages, DataForSEO Trends) using the executing-plans skill (Apr 29 at 3:07 PM)
S238 Phase 6 CI Enforcement Planning Session Initiated (Apr 29 at 4:28 PM)
### May 13, 2026
S239 Phase 6 CI Enforcement — Plan and implement architecture enforcement tooling from spec (May 13 at 1:09 PM)
S311 Git Worktree Workflow — Cannot Commit to Main Directly (May 13 at 1:10 PM)
### May 15, 2026
S312 Git fetch vs checkout vs pull — explaining what git fetch does in the fetch/checkout/pull sequence (May 15 at 8:50 PM)
S522 Diagnose git branch divergence between origin/dev and origin/main in the whidby project (May 15 at 8:52 PM)
### May 20, 2026
S523 Sync origin/dev with main — merge origin/main into local dev branch and resolve conflicts (May 20 at 12:41 PM)
S524 Sync origin/dev with main — merge, resolve conflict, and push to GitHub (May 20 at 12:45 PM)
S525 Complete Stripe billing integration for PR #51 — add secrets, webhooks, and env configuration so whidby can start taking customers (May 20 at 12:48 PM)
### May 22, 2026
S527 Complete Stripe billing integration for PR #51 — add secrets, webhooks, and .env.local config so whidby can start accepting paying customers (May 22 at 10:06 AM)
2692 9:19p 🟣 Niche Finder Strategy Playbook Published as Linear Core Strategy Document
2693 " 🟣 Added next/link mock and Competitor Intel CTA link test to ReportDetailModal
2694 9:22p 🔵 Greptile Bot Review Findings on PR #76 Tier Upgrade E2E Tests
2695 " 🔴 Fixed Three Greptile Review Issues in Tier Upgrade E2E Tests
2696 " 🔵 Competitor Intelligence Report Page Missing CTA from New Prototype
2697 9:23p 🟣 Added "Next Moves" CTA Section to ReportDetailModal with Competitor Intel Link
2698 " ✅ Tier Upgrade E2E Test File Final State Confirmed Post-Patch
2699 " ✅ ESLint Passed on Patched E2E File; Dev Server Started for E2E Re-run
2700 9:24p 🟣 All 3 Tier Upgrade E2E Tests Pass After Review Fix
2701 " ✅ E2E Request Traces Confirm All Three Tier Scenarios Exercised Billing Routes
2702 " 🔄 Cosmetic Line-Wrap Reformatting Applied to verifyPortalPathOrMissingBillingProfile
2703 " ✅ Final Patch Verified — 16 Insertions / 7 Deletions Ready to Commit on codex/tier-upgrade-e2e
2704 9:25p ✅ Review Fix Committed and Pushed to codex/tier-upgrade-e2e
2705 " ✅ Commit baf3dbc Successfully Pushed to GitHub — PR #76 Updated
2706 " 🔵 GitHub API PR Comment Reply Returns 404 for greptile-apps Bot Comment
2707 " 🔵 All Three greptile-apps Review Comment Reply Attempts Failed With 404
2708 " ✅ All Three greptile Review Thread Replies Posted Successfully to PR #76
2709 9:26p 🔵 PR #76 Post-Push CI Status: Quality Gates Passing, CodeQL and Greptile Review In Progress
2710 " 🔵 chatgpt-codex-connector Bot Left 3 Additional Unaddressed Review Comments on PR #76
2711 " 🔴 Refactored Env Loading to Fix Global Mutation and Load-Order Override Bug
2712 " 🔴 testEnv Refactor Patch Applied and Lint Passed Clean
2713 9:27p ✅ All 3 Tier Upgrade E2E Tests Pass After testEnv Refactor
2714 9:28p ✅ Env Isolation Refactor Committed and Pushed — PR #76 Branch Advanced to caef353
2718 " 🔵 WHI-2 App Frame Navbar Branch Exists Unmerged with Scans/Plan UI
2719 " 🔵 Sidebar Plan Label Falls Back to "Free plan" on Any Entitlement Error
2720 " 🔵 Luke's Staging Account Seeded as Pro but Staging Publishable Key May Be Invalid
2715 " ✅ Two chatgpt-codex-connector Review Thread Replies Posted on PR #76
2716 " ✅ All 6 PR #76 Inline Review Threads Now Have Exactly One Reply Each
2717 " 🔵 PR #76 CI Status Post-caef353: All Quality Gates Pass, CodeQL and Greptile Still Pending
2721 9:29p ✅ All CI Checks Pass on PR #76 After caef353 — Greptile Review and CodeQL Green
2723 " 🔵 Luke's Staging Subscription Has Correct Pro Plan but Null Period Dates
2724 " 🔵 Origin/Main Has Navbar Architecture with Shared ProtectedLayout — Not Local Main
2722 " 🔵 Greptile Review Check Remains Pending After 30+ Seconds on caef353
2725 9:30p 🔵 get_account_entitlement RPC Correctly Returns Pro for Luke — App Connection Is the Blocker
2726 " 🔵 PR #76 mergeStateStatus BLOCKED Due to Greptile Review IN_PROGRESS
2727 " 🔵 Root Cause Found: Luke Is Free/Admin in Production Supabase, Not Pro
2732 9:37p 🔵 Orphaned gh pr checks watcher process detected and kill requested
2738 9:47p 🔵 AGENTS.md Local Memory Update Blocking Git Fast-Forward Merge
2739 " 🟣 Tier Upgrade E2E Playwright Coverage Shipped — PR #76 Merged to Branch
2740 " 🟣 Niche Finder Strategy Playbook Published as Linear Core Strategy Document
2744 9:50p 🔵 Git Worktree Rebase Permission Error on whidby PR Branch
2745 9:53p 🟣 Navbar usage pill handles quota-exempt users with "Unlimited scans" label
2746 " ⚖️ Quota-exempt test coverage scoped to Navbar.test.tsx only, not layout integration test
2747 " ✅ Navbar quota-exempt patch finalized: layout.test.tsx fully reverted, 4 files in final diff
2758 9:56p ⚖️ Trading Strategies Gated Behind PostHog Feature Flags
2763 9:57p 🔵 Existing PostHog Flag Infrastructure in Whidby
2764 " 🔵 Strategy Discovery Route Architecture and Entitlement Model
2816 10:26p ✅ PR Pushed Including agents.md
2817 " 🟣 Navbar Quota-Exempt Users Now Show "Unlimited Scans"
2818 " 🔵 Git Branch Creation Requires Escalated Sandbox Permissions in whidby Repo

Access 938k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>
