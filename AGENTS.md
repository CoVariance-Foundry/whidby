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

# [whidby/whidby] recent context, 2026-05-23 3:24pm PDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (20,098t read) | 446,582t work | 95% savings

### May 13, 2026
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
S527 Complete Stripe billing integration for PR #51 — add secrets, webhooks, and .env.local config so whidby can start accepting paying customers (May 21 at 10:23 PM)
### May 22, 2026
S528 Continue the 12x8 scoring pilot — bulk scoring 12 metros × 8 services for rank-and-rent strategy analysis (May 22 at 10:06 AM)
### May 23, 2026
S529 Strategy feature flag design — modeling PostHog rollout controls for the Strategies surface in the Whidby app (May 23 at 6:27 AM)
2906 8:25a 🔵 Large Bucket: Greenville SC Confirmed as CBSA 24860
2907 8:35a 🟣 Bulk Scoring Pilot — Metro Bucket Execution (Post-PR-78)
2908 8:42a 🟣 Metro bucket bulk scoring completed successfully for Phoenix, AZ pilot
2909 " 🟣 Mega bucket bulk scoring command awaiting approval for mega_5m_plus pilot
2910 8:49a 🟣 Bounded 96-pair Pilot Scoring Run Completed Successfully Across All Population Classes
2911 8:53a ✅ WHI-102 Progress Docs Updated: Pilot Complete, Audit Gates Still Blocking
2912 " 🔵 DocGuard CLI Unavailable in Codex Sandbox Due to Network DNS Failure
2913 8:57a ✅ WHI-102 Pilot Closeout Documented and PR #80 Opened
2914 2:31p ✅ Next-slice implementation plan initiated in whidby project
2915 " 🔵 PR #80 (docs-only, WHI-102) was already merged before slice start
2918 " 🔵 Local AGENTS.md changes blocked git pull/merge in worktree 6aa7
2916 " ✅ WHI-102 Pilot Closeout PR #80 Opened and All Checks Green
2917 " 🔵 WHI-102 Pilot Audit: DA/Lighthouse and Benchmark Coverage Gaps Quantified
2919 " 🔵 Whidby worktree is a linked worktree rooted at Desktop development path
2920 2:32p 🔵 WHI-102 Linear history: audit gates still closed, next slice targets DA/Lighthouse data acquisition
2921 " 🔵 New worktree created for WHI-102 data-acquisition-gates branch at /private/tmp
2922 " 🔵 DA/Lighthouse audit gap traced: run_pilot.py never calls backlinks_summary or lighthouse endpoints
2923 2:33p 🔵 Extractor API contract and SERP maps gap identified for local difficulty inputs
2924 " 🔵 DFS endpoint cost map and seo_facts schema contract fully mapped for acquisition planning
2925 2:34p 🔵 Review velocity for benchmark facts uses DFS serp_maps reviews_per_month field, not timestamp computation
2926 " ✅ Implementation phase started: opt-in DA/Lighthouse and review-velocity acquisition in run_pilot.py
2927 2:35p 🟣 Opt-in DA/Lighthouse and review-velocity acquisition added to run_pilot.py
2928 2:36p 🟣 Unit tests written for all new acquisition functions in run_pilot.py and DataForSEO client
2929 " 🟣 Opt-in Organic Telemetry and Review Velocity Collection Added to Benchmark Pilot Runner
2930 " 🔄 DataForSEO `google_reviews()` Client Method Generalized to Support cid, place_id, and sort_by
2931 " 🔵 DataForSEO Backlinks Summary Returns `rank`/`domain_rank` Not `domain_authority`; Lighthouse Performance Score May Be 0–1 or 0–100
2932 " 🔵 Test run failed: mocker fixture unavailable with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
2933 " 🔴 Ruff F402 lint errors fixed: loop variable 'field' shadowed dataclasses import
2934 2:37p 🔴 parse_serp_items counted empty-URL organic items as local_biz — fixed with domain guard
2935 " ✅ All new acquisition tests passing and ruff clean — implementation verified
2936 2:38p 🔵 TEST-SPEC and DATA-MODEL confirm opt-in telemetry approach aligns with canonical contracts
2937 2:42p 🟣 WHI-102: Opt-in Benchmark Acquisition Added to Pilot Runner
2938 " 🟣 DataForSEO Client: Google Reviews Supports `place_id` Targeting and `sort_by` Parameter
2939 " ✅ TEST-SPEC.md: Benchmark Acquisition Tests Section Added
2940 " ⚖️ DocGuard Skill Auto-Update Side Effect Reverted from Branch
2941 2:45p ✅ Benchmark Acquisition Docs Updated to Pass CI Docs-Sync Gate
2942 2:50p 🟣 WHI-102 Data Acquisition Slice — PR #81 Opened with Opt-in Flags
2943 2:55p 🔴 Three Data Acquisition Review Issues Patched in WHI-102
2944 " 🔵 docguard-cli Requires Network Access; Blocked in Sandbox
2945 2:58p 🔴 Backlinks DA parser now prioritizes specific rank keys over generic `rank`
2946 3:01p 🔵 PR #81 (whidby-whi102-data-acquisition) All CI Checks Passing Except Greptile
2947 3:22p 🔵 Linear Skill Capabilities Reviewed for Post-PR Workflow
2948 " ✅ PR #81 (WHI-102 Data Acquisition Gates) Merged to Main
2949 3:23p ✅ WHI-102 Closeout Comment Posted to Linear with Detailed Summary
2950 " 🟣 WHI-102: PR #81 Merged — Benchmark Acquisition Gates
2951 " ✅ Post-Merge: Linear Update and Next Work Item Handoff Initiated
2952 " 🔵 Scoring Coverage & Benchmark Hardening Backlog State Mapped
2953 " 🔵 Coverage Experiment Reports Exist in Main Worktree for WHI-103 Analysis
2954 3:24p 🔵 Scoring Audit Results: Near-Total Coverage Failure Across All Components
2955 " 🔵 Git Fetch Fails in Codex Worktree Due to FETCH_HEAD Permission Error

Access 447k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>
