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

# [whidby] recent context, 2026-05-13 12:46am PDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (17,724t read) | 366,663t work | 95% savings

### Apr 26, 2026
S181 Merge all pending PRs into dev if their reviews have passed — finishing the Phase 5 development branch (Apr 26 at 6:59 PM)
S183 Benchmark Pilot Fix Plan Written — Three Failure Buckets Identified and Addressed (Apr 26 at 7:04 PM)
S184 Supabase MCP Available via Two Distinct Integrations (Apr 26 at 7:06 PM)
220 7:06p 🔵 Supabase MCP Available via Two Distinct Integrations
S187 dev Branch Pushed to Remote — Phase 3 + Phase 5 Complete (Apr 26 at 7:06 PM)
221 7:10p 🟣 Phase 3 MarketService Domain Extraction — PR #31 Code Review
222 7:11p ✅ PR #31 Phase 3 MarketService Merged to dev
223 " 🔵 Merge Conflict in domain/services/__init__.py Between dev and phase-5-discovery-service
224 " 🔴 Merge Conflict Resolved in domain/services/__init__.py — All 119 Tests Pass
225 " ✅ Phase 5 DiscoveryService Merged into dev — Commit f0505fa
226 " ✅ dev Branch Pushed to Remote — Phase 3 + Phase 5 Complete
S188 Run pilot benchmark (scripts.benchmarks.run_pilot) against DataForSEO and Anthropic APIs for two niches across 200 metro slots (Apr 26 at 7:11 PM)
227 7:20p ✅ Pilot Benchmark Script Launched as Background Task
228 7:30p 🔵 Pilot Benchmark Completed — 62/200 Reports Succeeded, 1667 Facts Inserted
S203 Phase 6 CI Enforcement — implement domain layer import guardrails via lint script, CI job, pre-push hook, and pytest architecture tests (Apr 26 at 7:30 PM)
229 7:31p 🔵 Pilot Failure Mode Is Silent — 138 Reports Started But Never Logged Completion or Error
230 " 🔵 DataForSEO keyword_suggestions/live Endpoint Exhibited 38–62 Second Latency Spikes
231 " 🔵 Pilot Success Rate Varies Significantly by Niche — Concrete Contractor Only 10%, Auto Repair 50%
### Apr 29, 2026
232 2:24p 🔵 Whidby Domain Layer Structure and CI Workflow Mapped
233 " 🔵 Existing CI Enforcement Infrastructure in Widby Repo
234 2:25p 🔵 Phase 6 CI/CD Enforcement Spec Loaded for Planning
235 2:26p 🔵 Domain Layer Has Existing Architecture Violations Before Phase 6 Enforcement
236 2:48p 🔵 Domain Layer Audit — Additional Violation in market_service.py and Clean Results Elsewhere
237 2:49p ✅ Phase 6 CI Enforcement Implementation Plan Written
238 2:52p 🟣 Phase 6 CI Enforcement Plan Written for whidby Domain Layer
239 2:53p 🔵 quality-gates.yml Structure Confirmed — 4 Jobs, PR-Only Trigger
240 2:54p 🟣 Phase 6 CI Enforcement Files Created and Confirmed Working
241 2:55p 🔵 tests/ Directory Structure — No architecture/ Subdirectory Yet
242 " 🟣 pytest Architecture Tests Created and Passing — 2 Tests Green
243 2:56p 🟣 Violation Detection Validated — Both Lint Script and pytest Correctly Fail on Banned Import
244 2:57p 🔵 Full Test Suite: 627 Pass, 3 Pre-existing Failures in test_api_reports.py Unrelated to Phase 6
S205 Phase 6 CI Enforcement Branch Entering Finishing Workflow (Apr 29 at 2:57 PM)
245 2:59p ✅ Phase 6 CI Enforcement Branch Entering Finishing Workflow
S213 vitest Fix Verified Stable After Root package.json Cleanup (Apr 29 at 2:59 PM)
246 " 🔵 Phase 6 CI Enforcement — Uncommitted State Snapshot Before Commit
247 3:03p 🔵 Vitest Module Resolution Error in Agent Health Route Test
248 " 🔵 Vitest Not Installed Despite Being in package.json devDependencies
249 " 🔴 Vitest Installed by Running npm install in apps/app Workspace
250 " 🔵 Running npm install in apps/app Broke React Type Resolution via Monorepo Conflict
251 " 🔵 vitest Still Not Installed After npm install — 25 Test Files Affected Project-Wide
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
262 3:11p ✅ Phase 7 Data Providers — Plan Execution Initiated
263 4:19p 🔵 Phase 6 Already Committed to Dev Branch
264 " 🟣 DataForSEO Google Trends API Research Initiated for Phase 7
266 " 🔵 DataForSEO Google Trends Explore Live API Contract Documented
267 " 🔵 DataForSEO Google Trends Explore Task POST API Contract Documented
268 4:24p 🟣 Phase 7 Data Providers Implementation Plan Written
270 " ✅ Phase 7 Plan Corrected: DataForSEO Trends Response Parsing Fixed
271 4:25p ✅ Phase 7 Plan: FakeTrendsClient Test Fixture Corrected to Match Real API Structure
S233 Execute Phase 7 Data Providers implementation plan (18 tasks across 4 task groups: Census ACS, Census CBP, BLS Wages, DataForSEO Trends) using the executing-plans skill (Apr 29 at 4:28 PM)
**Investigated**: Plan file reviewed: 2,079 lines, 55 checkboxes, 17 main tasks. Plan structure covers 4 independent data provider implementations plus composition and validation. Plan has been finalized with design decisions documented (Census/BLS raw httpx, growth_rate deferred, APIResponse handling patterns confirmed, Trends endpoint specs finalized)

**Learned**: **Design finalization:**
- Census ACS/CBP and BLS clients use raw httpx (no rate-limiting, cost tracking, or caching—free government APIs with annual data)
- DataForSEO Trends reuses existing DataForSEO client infrastructure ($0.05/task, max 5 keywords, time_range parameter simplified)
- APIResponse is a dataclass with `.data` attribute containing raw JSON
- Growth rate computation deferred (would require ~800 API calls on first load—acceptable for v1 with placeholder 0 in vector)
- Architecture lint now requires both check_domain_imports.py script AND pytest tests/architecture/ validation

**Completed**: **Session setup complete:**
- Plan file finalized at docs/superpowers/plans/2026-04-29-phase-7-data-providers.md
- All design decisions documented and corrections incorporated
- Plan structure: Task 0 (feature branch) → Task 1 (numpy dep) → Tasks 2-4 (7A) → Tasks 5-7 (7B) → Tasks 8-11 (7C) → Tasks 12-14 (7D) → Tasks 15-17 (composition/migration) → Task 18 (validation)
- Expected outcome: 20 new files, 3 modified files, 660+ passing tests

**Next Steps**: Begin Task 0 execution: Create feature branch from dev (`git checkout dev && git pull origin dev`, then `git checkout -b phase-7-data-providers`). Then Task 1: Run baseline test suite, add numpy to pyproject.toml, verify architecture lint passes before proceeding to Task Group 7A.


Access 367k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>