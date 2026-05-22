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

# [whidby/whidby] recent context, 2026-05-22 12:33pm PDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (22,932t read) | 4,461,985t work | 99% savings

### May 13, 2026
S268 V2 Scoring — Repository Boundary for seo_benchmarks Access Planned (May 13 at 1:10 PM)
S269 V2 scoring repository boundary plan — orientation phase for writing a formal implementation plan (May 13 at 1:26 PM)
S311 Git Worktree Workflow — Cannot Commit to Main Directly (May 13 at 1:26 PM)
### May 15, 2026
S312 Git fetch vs checkout vs pull — explaining what git fetch does in the fetch/checkout/pull sequence (May 15 at 8:50 PM)
S522 Diagnose git branch divergence between origin/dev and origin/main in the whidby project (May 15 at 8:52 PM)
### May 20, 2026
S523 Sync origin/dev with main — merge origin/main into local dev branch and resolve conflicts (May 20 at 12:41 PM)
S524 Sync origin/dev with main — merge, resolve conflict, and push to GitHub (May 20 at 12:45 PM)
S525 Complete Stripe billing integration for PR #51 — add secrets, webhooks, and env configuration so whidby can start taking customers (May 20 at 12:48 PM)
### May 21, 2026
S526 Begin Phase 2 in Linear / Phase 3 planning scope decision for Whidby project (May 21 at 9:45 AM)
### May 22, 2026
S527 Complete Stripe billing integration for PR #51 — add secrets, webhooks, and .env.local config so whidby can start accepting paying customers (May 22 at 10:06 AM)
2233 12:00p 🔵 WHI-9 Parallel Worktree: Other Workers Created Backend and API Layer
2240 12:01p ⚖️ WHI-9 /competitor-intel Paid Page — E2E, Testing & Rollout Planning
2241 " 🟣 Admin Dashboard Menu Item Tests Added to ProtectedLayout
2242 12:02p 🔵 Whidby Test Infrastructure Fully Mapped for WHI-9 Planning
2243 " 🔵 Subagent-Driven Development Skill Pattern Confirmed for WHI-9 Execution Lane
2244 " 🔵 Billing Entitlement Test Pattern Established — Template for /competitor-intel Paid Gate
2245 12:04p ⚖️ WHI-9 Competitor Intel Backend Architecture: BFF + FastAPI Service Slice
2246 " 🔄 JSX Formatting Cleanup in AccountSettingsClient.tsx
2247 12:05p 🟣 WHI-9 Competitor Intel Domain Service and FastAPI Endpoints Implemented
2248 " 🟣 Next.js BFF Competitor Intel Routes with 2-Unit Atomic Quota Enforcement
2249 " 🔵 Parallel Worker A Created Empty Migration and Frontend Directories for WHI-9
2250 " 🔵 Existing Entitlements Pattern: Single-Unit Quota via consume_report_quota Supabase RPC
2251 12:07p ⚖️ Competitor Intel Page - System Design Planning Initiated (WHI-9)
2257 " 🟣 WHI-9 Competitor Intel — Full Stack Implementation Shipped
2258 " ⚖️ Multi-Unit Quota Architecture: Generic consume_usage_quota RPC
2259 " 🟣 CompetitorIntelService — Domain Service Reading Organic + Local Pack Facts
2260 " 🟣 organic_competitor_facts Schema — Extended with Backlink and Schema Signal Columns
2261 " 🟣 CompetitorIntelClient — Six-State React UI with Upgrade Gate and Confirmation Dialog
2262 " 🔵 Initial BFF Worker Used Non-Existent RPC Names for Quota
2263 " ⚖️ Competitor Intel Route is Direct-Link Only; No Navbar Entry Point in This Slice
2252 " 🟣 WHI-9 Competitor Intel Feature Implemented
2253 12:08p 🚨 SSRF Host-Header Cookie Exfiltration Fixed in Settings Page
2254 " 🟣 Settings Page Parallelized: loadAccountSummary + loadSavedReportPreview via Promise.all
2255 " ✅ PR #60 Greptile Review Threads Replied to via GitHub GraphQL
2256 " ✅ Settings Page Tests Expanded for SSRF Fix and Profile/Report Props
2264 12:11p 🔵 Worktree Supabase env vars not loading — DNS resolution failure in audit script
2265 " 🔵 Explore data pipeline requires 9 Supabase tables; seo_benchmarks confidence still below usable coverage
2266 12:13p 🟣 WHI-9 Competitor Intel Feature Implementation Under Code Review
2267 12:16p 🔵 WHI-9 Diff Scope: 12 Modified + 12 New Files, 1,392 Insertions
2268 " 🔵 Multi-Unit Quota RPCs: consume_usage_quota Uses ≤ While Legacy Uses < (Correct But Intentional Divergence)
2269 " 🔵 RLS Safety: organic_competitor_facts Allows All Auth Users to Read NULL-report_id Rows
2270 " 🔵 Next.js BFF Quota Flow: Atomic 2-Unit Consume, Refund on Upstream Failure, Correct Exception Path
2271 " 🔵 CompetitorIntelService: Deterministic Read-Model Returns Three States Based on Durable Fact Availability
2272 " 🔵 SupabasePersistence Extended: Organic and Local Pack Facts Built and Upserted on Report Persist
2273 " 🔵 UI State Machine: Six Distinct View States With Correct Plan-Gate, Confirmation Dialog, and No Null Leakage
2274 " 🔵 Test Coverage: Full-Stack Tests Pass Ruff and ESLint With No Errors; Missing Integration Test for Metro Lookup Ambiguity
2275 " 🔴 Vercel Preview deploys now fail loudly when NEXT_PUBLIC_API_URL is missing
2276 " 🔄 Duplicate URL normalizer functions collapsed into single normalizeBaseUrl helper
2277 12:20p 🚨 SSRF Vulnerability via Untrusted x-forwarded-host Header in Reports Page
2278 " 🔵 WHI-7 PR Branch Worktree Stale by 11 Commits with Dirty AGENTS.md
2279 " 🟣 Reports List Row UI with Opportunity Score Display Added to WHI-7
2280 12:25p 🔵 WHI-9 Competitor Intel Branch — Final Integration Review Scope
2281 12:27p 🔵 WHI-9 Competitor Intel Branch: All Six P1 Issues Verified Fixed
2282 " 🔵 WHI-9: organic_competitor_facts RLS Fully Blocks Authenticated Direct Reads
2283 " 🔵 WHI-9: refund_report_quota Still Granted to authenticated — Acceptable but Noted
2284 12:29p 🔴 PR #59: Nested Interactive Controls Fixed in ReportsTable
2285 12:31p 🔵 Whidby Proto→Production Convergence Epic Landscape Loaded from MEMORY.md
2286 12:32p 🔵 Proto→Production Convergence Live Linear Status Snapshot as of 2026-05-22
2287 " 🔵 WHI-10 Design System Alignment Sub-Issue Tree Fully Enumerated
2288 " 🔵 ACTIVE_WORK.md Reveals Multi-Stream Work State with Key Remaining Gaps

Access 4462k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>