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

# [whidby/whidby] recent context, 2026-05-16 5:32pm PDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (23,609t read) | 506,580t work | 95% savings

### Apr 29, 2026
S205 Phase 6 CI Enforcement Branch Entering Finishing Workflow (Apr 29 at 2:57 PM)
S213 vitest Fix Verified Stable After Root package.json Cleanup (Apr 29 at 2:59 PM)
S215 Fix "Cannot find module 'vitest'" TypeScript error in apps/app/src/app/api/agent/health/route.test.ts (Apr 29 at 3:07 PM)
S233 Execute Phase 7 Data Providers implementation plan (18 tasks across 4 task groups: Census ACS, Census CBP, BLS Wages, DataForSEO Trends) using the executing-plans skill (Apr 29 at 3:07 PM)
S238 Phase 6 CI Enforcement Planning Session Initiated (Apr 29 at 4:28 PM)
### May 13, 2026
S239 Phase 6 CI Enforcement — Plan and implement architecture enforcement tooling from spec (May 13 at 1:09 PM)
S268 V2 Scoring — Repository Boundary for seo_benchmarks Access Planned (May 13 at 1:10 PM)
S269 V2 scoring repository boundary plan — orientation phase for writing a formal implementation plan (May 13 at 1:26 PM)
S311 Git Worktree Workflow — Cannot Commit to Main Directly (May 13 at 1:26 PM)
### May 14, 2026
341 11:39a ✅ PR #34 All Checks Pass — Docs Sync Gate and Supabase Preview Both Green
342 11:40a ✅ PR #34 Merged to Main — Consumer Billing and Entitlements Now on Main
343 11:41a 🔵 PR #35 Contains 8 Unrelated phase-7-data-providers Commits Plus 3 Explore Refresh Commits
344 11:42a ⚖️ PR #35 Repair Strategy — Cherry-Pick 3 Explore Commits onto Fresh Main, Not Rebase
### May 15, 2026
345 8:45p 🔵 Git Worktree Mental Model — Checkout Conflicts and Merge-Back Strategy
346 8:46p 🔵 Git Worktree Dirty State — AGENTS.md Modified in Two Active Worktrees
347 8:47p 🔵 Git Worktrees — User Confusion Around Checkout Locks and Merging Back to Main
348 8:48p 🔵 niche-surface-hardening-v2 Worktree Branch Has Diverged from Remote
349 " 🔵 Rebase Conflict in scoring/route.ts — account vs report Field in Response
351 " 🔴 scoring/route.ts Rebase Conflict Resolved — Both account and report Fields Preserved
352 8:49p ✅ PRs #38 and #39 Created — Account Billing and Niche Caching Branches
353 8:50p 🔵 Git Worktree Workflow — Cannot Commit to Main Directly
S312 Git fetch vs checkout vs pull — explaining what git fetch does in the fetch/checkout/pull sequence (May 15 at 8:52 PM)
354 8:55p 🔵 Explore Cities Table — Population, Income, Density, Growth Fields Missing from Data Flow
355 8:56p 🔵 Explore Table — business_density_per_1k and establishment_growth_yoy Always Null
356 8:57p 🔵 Supabase Environment Points to eoajvifhbmqmoluiokcj Instance in Both .env Files
357 9:02p 🔵 Explore Cities Data Flow — Historical Context Retrieved from Memory
358 9:05p 🔵 Whidby Repo — On Main Branch with Untracked AGENTS.md Change
360 9:09p ⚖️ Explore Data Model Population — 8-Task Implementation Plan Written
361 " ⚖️ Explore Data Model Fix — Working Directly on Main Branch
362 " 🔵 Git Worktree Creation Blocked by Sandbox Permission Restriction
363 9:10p ✅ Git Worktree Created for Explore Data Model Implementation
364 " 🔵 Explore Worktree Has No node_modules or .venv — Dependencies Need Install
365 9:11p 🔵 Python venv pip install -e .[dev] Fails in Worktree Due to Zsh Glob Expansion
366 " 🔵 Sandbox Has No Network Access — pip Cannot Install Python Build Dependencies
### May 16, 2026
367 8:10a ⚖️ Strategy Discovery System — Canonical Design Formalized in Docs
368 8:11a ✅ Strategy Discovery System — Canonical Docs Updated (Task 1)
369 " ✅ Strategy Discovery System — Canonical Docs Updated (Task 1)
373 8:13a 🔵 docguard-cli Does Not Exist on npm Registry
374 " ✅ Strategy Discovery Canonical Docs Committed on codex/strategy-discovery-system
375 8:14a 🔵 DocGuard v0.9.11 Repo-Wide Baseline — 118/185 Checks Pass, 97 MEDIUM Warnings
376 " ✅ Strategy Discovery Canonical Docs — Exact Diff and Staging Confirmed
377 " ✅ Task 1 Committed — SHA d6c45d8 on codex/strategy-discovery-system
378 " ✅ Task 1 Spec Compliance Review — Strategy Discovery Canonical Docs
379 8:15a ✅ Task 1: Strategy Discovery System — Canonical Design Docs Committed
380 " ✅ Task 1 Spec Compliance Review — Strategy Discovery System Canonical Docs
381 8:16a ✅ Task 1: Strategy Discovery System — Canonical Docs Committed on Branch codex/strategy-discovery-system
382 " 🔵 docguard-cli Is a Phantom npm Package — Not Installable from Public Registry
383 8:17a ✅ Strategy Discovery System — Task 1 Canonical Docs Code Review Initiated
384 8:18a ✅ Strategy Discovery System — Canonical Docs Committed (Task 1) Under Code Review
385 " ✅ Strategy Discovery System — Task 1 Code Review Initiated for Canonical Docs Commit d6c45d8
386 8:19a ✅ Task 1: Canonical Design Update — Strategy Discovery System docs committed on branch codex/strategy-discovery-system
387 8:20a ✅ ARCHITECTURE.md Strategy Discovery Section Refined — Entitlement Gate and Component Map Added
388 8:21a ✅ Task 1 Strategy Discovery Docs — Re-Review After Implementer Fix (Commit 09e345a)
389 " ✅ Strategy Discovery Task 1 — ARCHITECTURE.md Amended After Spec Review
390 8:22a ⚖️ Strategy Discovery System — Task 1 Canonical Docs Re-Review Initiated After Amendments
391 8:24a 🟣 Task 2: Strategy Discovery Schema Migration Initiated
392 " ⚖️ Task 2: Strategy Schema Migration — Implementation Plan Initiated
393 8:25a 🟣 Task 2: Strategy Discovery Schema Migration Created
394 " 🔵 pytest Crashes on Import Due to NumPy 1.x/2.x Compiled Module Conflict
395 " 🟣 Strategy Discovery Schema Migration 016 Written and Tests Passing

Access 507k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>