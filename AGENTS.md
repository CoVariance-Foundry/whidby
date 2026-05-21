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

# [whidby] recent context, 2026-05-20 8:55pm PDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (19,633t read) | 816,928t work | 98% savings

### Apr 29, 2026
S213 vitest Fix Verified Stable After Root package.json Cleanup (Apr 29 at 2:59 PM)
S215 Fix "Cannot find module 'vitest'" TypeScript error in apps/app/src/app/api/agent/health/route.test.ts (Apr 29 at 3:07 PM)
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
S524 Sync origin/dev with main — merge, resolve conflict, and push to GitHub (May 20 at 12:48 PM)
1452 7:41p 🔵 PR #50 True Diff Scope is 73 Files vs Main — Far Larger Than PR Description Implies
1453 " 🔵 Code Inspection Confirms metro_score_v2 INSERT Bug; seo_facts Upsert Is Correct but NULL-Vulnerable
1454 " 🟣 New bulk_score.py Script for Populating explore_market_cells Materialized View
1456 7:42p 🔵 PR #50 Supabase Branch Migration Failure: Duplicate Migration Version 021
1457 7:43p 🔵 Earlier 73-File Diff Was Against Stale main; True PR #50 Scope Is 36 Files Matching PR Metadata
1458 " 🔵 NULL snapshot_date Bug in build_seo_fact_rows Confirmed by Source Read
1459 " 🔵 top3_review_data_low_coverage Vacuous True Bug Confirmed in v2.py Lines 61-64
1460 " 🔵 V2 Implementation Plan Fully Completed Except next build Typecheck Blocker
1461 " 🟣 New /api/agent/reports Route Consolidates Report Listing with V2 Detection and Dashboard Assembly
1462 " 🔄 load-explore-data.ts Gutted; Normalization Logic Extracted to normalize-explore-data.ts
1463 " 🔵 persist_report Test Suite Explicitly Validates seo_facts Upsert Requirement and 6-Table Write Path
1464 7:45p 🔴 PR #50 V2 Scoring: Three Bot-Flagged Issues Resolved on codex/v2-scoring-system
1465 " 🔵 Supabase Branch Deployment Failure: Duplicate Migration Version 021
1466 " ✅ PR #50 Review Threads Replied To and Resolved on GitHub
1467 " 🔵 PR #50 Final State: All Review Threads Resolved, Supabase Branch Deployment Successful
1468 " 🔵 PR #50 CI Check Status: Docs Sync Gate Failing, All Other Checks Passing
1469 7:46p ⚖️ Docs Sync Gate Failure Is a Known Recurring Issue — Not a PR Blocker
1470 7:47p 🔵 Docs Sync Gate: How It Works and How to Bypass It
1471 " 🔵 Docs Sync Gate Script Logic and Architecture Doc Coverage of V2 Scoring
1472 " 🔵 Architecture Docs Still Describe V1 Four-Table Persistence — V2 Tables Missing
1473 7:48p ✅ Architecture Docs Updated to Document V2 Scoring Persistence and New Module Dependencies
1474 " 🔵 Docs Sync Gate Script Checks Committed Files Only — Unstaged Changes Not Detected
1475 " ✅ Docs Sync Gate Now Passes Locally and Pushed — PR #50 Branch at d155663
1476 " 🔵 New CI Run Triggered for Commit d155663 — Docs Sync Gate Now Pending on Fresh Run
1477 7:49p 🔵 PR #50 CI Checks All Passing After Doc Update Commit d155663
1478 7:50p 🔵 PR #50 All Automated CI Checks Passing — Only Greptile Review Pending
1479 7:55p 🔵 MarketService Infrastructure Connected but Not Wired in api.py
1480 " 🔵 V2 Local Competition Extractor Still Computes V1.1 Averages
1481 " 🔵 Backlinks and Lighthouse Extractors Only Process First Result Instead of Top-5
1482 7:56p ✅ Architecture Docs Updated for V2 Scoring Persistence Layer
1483 " 🔴 Docs Sync Gate Fixed on PR #50 After V2 Doc Commit
1484 " 🔵 V2 Scoring System PR #50 CI All Green Except Greptile Review Pending
1485 8:42p 🔴 V2 Scoring PR Review Comments Addressed
1486 " 🔵 PR #50 CI Checks Status — All Passing
1487 " 🔴 PR #50 v2 Scoring — Four Issues Fixed in Commit 5641ddb
1488 8:43p 🔵 Greptile Review Check-Run Payload — 39 Files, 0 Comments
1489 8:45p 🔵 Codex Agent Git State Mismatch in whidby Repo
1490 8:46p 🟣 PR #50 "Implement V2 Scoring System Wiring" Merged to Main
1491 " 🔵 dev Branch Has Post-PR-50 Explore Fixes Not Yet in Main
1492 8:47p 🔵 dev Branch Is Behind main Post-PR-50; Needs Merge Before Follow-up PRs
1493 " 🔵 dev Is a Clean Fast-Forward Candidate to origin/main — No Merge Conflicts
1494 8:48p ⚖️ User Chose to Fast-Forward dev to origin/main to Sync PR #50
1495 8:54p ✅ Fast-Forward `dev` Branch to Match Merged PR #50 State
1496 " 🔵 Pre-Merge `dev` Branch State Confirmed in whidby Repo
1497 " 🔵 `git fetch` Blocked by Permissions Error on `.git/FETCH_HEAD`
1498 " 🔵 `git fetch` Succeeded with Escalated Sandbox Permissions
1499 " 🔵 Stripe Integration Resume Point: Keys Added, Prior Architecture Confirmed
1500 8:55p 🔵 Branch Graph Fully Mapped After Fetch — `dev` and `origin/dev` Both 5 Behind
1501 " ✅ Remote `dev` Updated via Direct Refspec Push `origin/main:dev`
1502 " 🔵 Stripe Billing API Routes Fully Implemented — Keys Were the Only Missing Piece

Access 817k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>