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

# [whidby] recent context, 2026-05-17 8:20pm PDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (24,359t read) | 1,796,565t work | 99% savings

### Apr 26, 2026
S188 Run pilot benchmark (scripts.benchmarks.run_pilot) against DataForSEO and Anthropic APIs for two niches across 200 metro slots (Apr 26 at 7:11 PM)
S203 Phase 6 CI Enforcement — implement domain layer import guardrails via lint script, CI job, pre-push hook, and pytest architecture tests (Apr 26 at 7:30 PM)
### Apr 29, 2026
S205 Phase 6 CI Enforcement Branch Entering Finishing Workflow (Apr 29 at 2:57 PM)
S213 vitest Fix Verified Stable After Root package.json Cleanup (Apr 29 at 2:59 PM)
S215 Fix "Cannot find module 'vitest'" TypeScript error in apps/app/src/app/api/agent/health/route.test.ts (Apr 29 at 3:07 PM)
S233 Execute Phase 7 Data Providers implementation plan (18 tasks across 4 task groups: Census ACS, Census CBP, BLS Wages, DataForSEO Trends) using the executing-plans skill (Apr 29 at 3:07 PM)
S238 Phase 6 CI Enforcement Planning Session Initiated (Apr 29 at 4:28 PM)
### May 13, 2026
S239 Phase 6 CI Enforcement — Plan and implement architecture enforcement tooling from spec (May 13 at 1:09 PM)
S311 Git Worktree Workflow — Cannot Commit to Main Directly (May 13 at 1:10 PM)
### May 15, 2026
S312 Git fetch vs checkout vs pull — explaining what git fetch does in the fetch/checkout/pull sequence (May 15 at 8:52 PM)
### May 17, 2026
892 3:39p ✅ Lint Clean — 0 Errors, 2 Pre-existing Warnings Only
895 3:41p 🔵 Settings Route Auth Gate Confirmed — Redirects to /login?next=/settings
897 3:44p 🔵 Dev Server Logs — Local Login Failing with "Invalid Credentials" and Auth Rate Limit
898 3:45p 🔵 Sandbox Network Egress Blocks Live Supabase Probe — fetch failed for All Tables
899 " 🔵 Task 8 Documentation Review — Supabase Staging Accounts Worktree
900 3:46p 🔵 Supabase Staging — Tables Exist but `get_account_entitlement` RPC Missing from Schema Cache
901 " 🔵 Task 8 Documentation Review — All Four Files Approved with One Version Gap Note
902 " 🔵 InternalUserEntitlement — Full Schema and Access Policy Now Canonical
903 " 🔵 Staging Deployment State — Two Blockers Remain After Task 8
904 3:48p 🔵 Migration 014 Not Applied to Staging — Billing Tables and RPCs Are Completely Absent
905 " 🔵 Task 8 Spec Compliance Review — Supabase Staging Docs Audit Initiated
909 3:50p 🟣 Supabase Staging Test Accounts Branch — Full Implementation Complete and Branch-Reviewed
910 " 🔐 GitHub Staging Environment Secrets Blocked — Manual Upload Required
917 3:52p 🟣 Migration 018 — internal_user_entitlements Schema, Admin Bootstrap RPC, and Updated Entitlement Surface
918 " 🟣 App Entitlement Gate — fresh_report_quota_exempt Bypass Added to All Three Fresh-Report Routes
919 " 🟣 seed_test_accounts.py — stdlib-Only Staging Account Seeder with Five Named Personas
920 " 🟣 GitHub Actions Staging Workflows — supabase-staging.yml and supabase-seed-test-accounts.yml
921 " 🔵 Migration 014 get_account_entitlement() Redefined in 018 — Safe Sequential Override Pattern
922 " ✅ Canonical Docs Updated — DATA-MODEL, ENVIRONMENT, TEST-SPEC, ACTIVE_WORK, project_context All Include 018 and Staging Seeding
926 3:55p 🔵 Accounts and Billing — Migration and Hydration Gap Investigation Initiated
927 " 🔵 Migration 014 Confirmed Never Applied — Billing Tables Absent from Staging Supabase
928 " 🔵 ENVIRONMENT.md Migration Table Incomplete — Migrations 006, 009–013, 016, 017 Not Listed
929 4:31p 🔴 Explore API Sort Mapping Gap Fixed — cached_services Now Properly Routed
930 " 🔵 Explore Sort Fix a11e938 Verified — 19 Tests Pass, Worktree Clean
931 " 🔵 Task 5 Explore Cities Proxy — Orientation and Directory Creation
936 4:33p 🟣 Task 5 Initiated — Explore Cities Proxy Routes and Loader Replacement
938 4:34p 🔴 Explore Cities Route — req.nextUrl Unavailable in Vitest, Fixed with new URL(req.url).search
939 " 🟣 Explore Cities Proxy Routes and Loader — All 11 Tests Passing, ESLint Clean
940 " 🔴 explore/page.test.tsx — vi.mock Factory Must Explicitly Export fromSearchParams
942 4:35p 🟣 Task 5 Initiated — Explore Cities Proxy Routes and Backend Loader Replacement
945 " 🟣 Explore Cities Proxy Routes — Implementation Confirmed with Bounded Error Handling
946 " 🟣 Explore Cities Loader — Supabase Removed, Backend DTO Normalization Layer Added
947 " ✅ ExplorePageClient Test Fixtures Updated with New DTO Fields
948 " 🔵 Task 5 Validation — TypeScript Clean, ESLint Warnings Pre-Existing, No Whitespace Errors
950 4:36p 🟣 Task 5 Committed — Explore Cities Proxy Loader on Branch codex/whi-1-explore-cities-refactor
953 4:37p 🔵 Task 5 Spec Compliance Review Initiated — Commit ad7463e
954 " 🔵 Task 5 Commit ad7463e — Scope Confirmed: 10 Files, Net 700-Line Reduction
955 " 🔵 Zsh Glob Expansion Blocks git show for [cbsaCode] Bracket Paths
956 4:38p 🔵 Task 5 Core Deliverables Verified — All Spec Files Present and Structurally Correct
957 " 🔵 Query Param Name Mismatch — Frontend Uses min_population/min_income, Backend Expects population_min/income_min
958 4:39p 🔵 Task 5 Code Quality Review Initiated — Explore Cities Proxy Refactor at Commit ad7463e
974 4:45p 🔴 Explore Cities Loader Contract Fixes — Commit 93dd683
975 4:46p 🔵 Task 5 Re-Review APPROVED — All Four Contract Bugs Verified Fixed in Commit 93dd683
992 4:56p 🔵 Task 6 Spec Compliance Review Initiated — Explore Cities UI Refactor at Commit f65b3f6
996 4:57p 🔵 Explore Cities Proxy Refactor — Code Review Initiated for Commit f65b3f6
1016 5:08p 🔵 Commit 79d8da2 Code Review Initiated — Explore Cities Refactor Branch
1019 5:10p 🔵 Task 7 Spec Compliance Review Initiated — Explore Cities Refactor at Commit 79d8da2
1028 5:16p 🔵 Task 8 Spec Compliance Review Initiated — Commit f44a832 in whi-1-explore-cities-refactor
1031 " 🔵 Task 8 Spec Compliance — APPROVED with One Residual Risk at Commit f44a832
1032 5:17p 🔵 Task 7 Final State Re-Review Initiated — Prior Findings Tracked Through Commit f64e4d1

Access 1797k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>