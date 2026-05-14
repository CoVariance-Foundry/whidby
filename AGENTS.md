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

# [whidby/whidby] recent context, 2026-05-13 10:15pm PDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (22,609t read) | 468,046t work | 95% savings

### Apr 26, 2026
S188 Run pilot benchmark (scripts.benchmarks.run_pilot) against DataForSEO and Anthropic APIs for two niches across 200 metro slots (Apr 26 at 7:11 PM)
S203 Phase 6 CI Enforcement — implement domain layer import guardrails via lint script, CI job, pre-push hook, and pytest architecture tests (Apr 26 at 7:30 PM)
### Apr 29, 2026
S205 Phase 6 CI Enforcement Branch Entering Finishing Workflow (Apr 29 at 2:57 PM)
S213 vitest Fix Verified Stable After Root package.json Cleanup (Apr 29 at 2:59 PM)
252 3:04p 🔵 vitest Missing from Root node_modules After npm install in Monorepo
253 3:05p 🔵 vitest Listed in package-lock.json but Not Installed in node_modules
254 " 🔵 Root node_modules Has 304 Packages but No vitest; No .npmrc Present
255 3:06p 🔴 Clean Root npm Install Attempted to Resolve Missing vitest Module
256 " 🔵 vitest Installed Only in Worktree node_modules, Not in Main Project
257 3:07p 🔵 Root node_modules Has 312 Packages But vitest Is Not Among Them
258 " 🔵 Root Cause: NODE_ENV=production Caused npm to Omit devDependencies
259 " 🔴 Fixed "Cannot find module 'vitest'" — Tests Now Passing
260 " ✅ vitest Removed from Monorepo Root package.json devDependencies
261 " 🔴 vitest Fix Verified Stable After Root package.json Cleanup
S215 Fix "Cannot find module 'vitest'" TypeScript error in apps/app/src/app/api/agent/health/route.test.ts (Apr 29 at 3:07 PM)
S233 Execute Phase 7 Data Providers implementation plan (18 tasks across 4 task groups: Census ACS, Census CBP, BLS Wages, DataForSEO Trends) using the executing-plans skill (Apr 29 at 3:07 PM)
262 3:11p ✅ Phase 7 Data Providers — Plan Execution Initiated
263 4:19p 🔵 Phase 6 Already Committed to Dev Branch
264 " 🟣 DataForSEO Google Trends API Research Initiated for Phase 7
266 " 🔵 DataForSEO Google Trends Explore Live API Contract Documented
267 " 🔵 DataForSEO Google Trends Explore Task POST API Contract Documented
268 4:24p 🟣 Phase 7 Data Providers Implementation Plan Written
270 " ✅ Phase 7 Plan Corrected: DataForSEO Trends Response Parsing Fixed
271 4:25p ✅ Phase 7 Plan: FakeTrendsClient Test Fixture Corrected to Match Real API Structure
S238 Phase 6 CI Enforcement Planning Session Initiated (Apr 29 at 4:28 PM)
### May 13, 2026
272 1:09p ✅ Phase 6 CI Enforcement Planning Session Initiated
S239 Phase 6 CI Enforcement — Plan and implement architecture enforcement tooling from spec (May 13 at 1:09 PM)
S268 V2 Scoring — Repository Boundary for seo_benchmarks Access Planned (May 13 at 1:10 PM)
277 1:26p ⚖️ V2 Scoring — Repository Boundary for seo_benchmarks Access Planned
S269 V2 scoring repository boundary plan — orientation phase for writing a formal implementation plan (May 13 at 1:26 PM)
278 7:19p ✅ Explore Refresh Control — Canonical Docs Updated (DATA-MODEL, ARCHITECTURE, TEST-SPEC)
279 7:20p ✅ Explore Refresh Control — Canonical Docs Update (Task 1)
280 7:21p ✅ Explore Refresh Control — Canonical Docs Updated (DATA-MODEL, ARCHITECTURE, TEST-SPEC)
281 " 🔵 Explore Refresh Control Doc Verification — git diff --check Clean, docguard-cli Hung
283 7:22p 🔵 Whidby Sandbox Blocks `ps` Command — Operation Not Permitted
284 " 🔵 docguard-cli Never Spawned — Not Found in Process List; Only MCP Servers Running via npx
285 " 🔵 docguard-cli Fails with ENOTFOUND — npm Registry Unreachable in Whidby Sandbox
287 7:23p 🔵 DocGuard v0.9.11 Full Guard Run — 124/191 Passed, All HIGH Checks Clean, 97 MEDIUM Warnings
288 7:24p 🔵 Explore Refresh Control — Task 1 Spec-Compliance Review Findings
289 " 🔵 Explore Refresh Control — Task 1 Doc Review: Diff and Schema Cross-Check
290 7:25p ✅ Explore Refresh Control — Task 1 Spec-Compliance Review Initiated
291 7:26p 🔵 Explore Refresh Control — Canonical Doc Review: Version Metadata and Placeholder Audit Results
292 " 🔵 Whidby Explore Component and Test File Inventory (as of codex/explore-refresh-control)
293 7:27p 🔵 docguard-cli Sandbox Hang Confirmed: Process Tracker Shows Running But No OS Process Exists
294 7:28p 🔵 Explore Refresh Control — Planned API Route and Test File Structure Confirmed
295 7:30p ✅ Explore Refresh Control — Canonical Docs Updated (Task 1)
296 " 🔵 Whidby Sandbox Blocks npm Registry, ps Syscall, and pgrep Without Escalation
297 7:31p 🔵 Primary Key Naming Discrepancy Between DATA-MODEL.md and Migration SQL Plan
298 " ✅ DATA-MODEL.md Refresh Entity Schemas Reconciled with Migration SQL Plan
299 " ✅ TEST-SPEC.md Explore Refresh Test Obligation Expanded with Two Additional Test Files
300 7:32p 🔵 Supabase `reports` Table Uses `id` as PK, Not `report_id` — Application Layer Translates
301 " ✅ Explore Refresh Control Task 1 Canonical Docs — Final Verified State
302 " ✅ Explore Refresh Control Task 1 — Canonical Docs Complete at DONE_WITH_CONCERNS
304 7:33p 🔵 docguard-cli Exact Failure: ENOTFOUND registry.npmjs.org + npm Log Write Blocked
305 7:34p 🔵 Explore Refresh Control — Task 1 Spec-Compliance Review Criteria Established
306 " ⚖️ Explore Refresh Control — Task 1 Doc-Quality Review Criteria Established
307 7:35p 🔵 Explore Refresh Control Task 1 — Spec-Compliance Review Result: PASS
308 " 🔵 Explore Refresh Control — Canonical Docs Verified Against SQL Contract
309 " 🔵 Explore Refresh Control — Git Diff Confirms Prior Session Fixed Stale reports.report_id PK
310 7:37p 🔵 Explore Refresh Control — DATA-MODEL.md Task 1 Spec Compliance Verified

Access 468k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>