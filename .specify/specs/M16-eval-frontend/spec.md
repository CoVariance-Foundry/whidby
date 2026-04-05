# Feature: Eval Frontend (M16)

**Feature branch:** `M16-eval-frontend`  
**Status:** Draft  
**Module ID:** M16  
**Spec references:** `docs/product_breakdown.md` (cross-module eval surfaces); `docs/algo_spec_v1_1.md`; `docs/outreach_experiment.md`; `docs/data_flow.md`

## Summary

Delivers a **unified internal dashboard** (not customer-facing) for Widby engineers and operators to exercise, inspect, and evaluate every module from M0 through M15. The app is a Next.js application deployed on Vercel, calling **Supabase** for data and a **Python backend** for pipeline and experiment operations, with a shell scaffolded in Phase 1 and feature pages added as modules ship.

## Dependencies

- **All modules M0–M15:** Each route exposes eval affordances consistent with that module’s contracts (read-only vs triggering jobs per plan).
- **M2 (Supabase):** Auth (internal), data tables, and Edge Functions as needed for secure access from the browser.
- **Python backend:** FastAPI or existing bridge (`npm run dev:api` pattern) serving module-specific eval endpoints without exposing secrets to the client.

## User Scenarios & Acceptance Scenarios

### US-1 — Engineer lands on the eval home dashboard

**Acceptance**

- **AS-1.1 (dashboard):** Route `/` lists modules M0–M15 with status (stub vs live), deep links to each eval page, and links to relevant spec sections.
- **AS-1.2 (internal-only):** Deployment is restricted to internal users (Vercel protection, Supabase auth allowlist, or VPN — mechanism fixed in plan); anonymous public access is blocked.

### US-2 — Data plane eval pages

**Acceptance**

- **AS-2.1 (M0):** `/data/serp-explorer` can run or display cached DataForSEO-backed exploration per M0 contract (keys stay server-side).
- **AS-2.2 (M1):** `/data/metros` browses metro DB records and validates M1 loaders.

### US-3 — Scoring pipeline eval pages

**Acceptance**

- **AS-3.1 (M4–M9):** Routes `/pipeline/keywords`, `/pipeline/collection`, `/pipeline/signals`, `/pipeline/scoring`, `/pipeline/classification`, `/pipeline/report` each expose inputs, sample fixtures, run triggers (where allowed), and structured output viewers aligned with module I/O specs.

### US-4 — Experiment framework eval pages

**Acceptance**

- **AS-4.1 (M10–M15):** Routes `/experiment/discovery`, `/experiment/scanning`, `/experiment/audits`, `/experiment/outreach`, `/experiment/tracking`, `/experiment/analysis` surface the eval hooks for business discovery through rentability signal review, including links to Supabase rows and logs where applicable.

### US-5 — Phased delivery matches module readiness

**Acceptance**

- **AS-5.1 (shell first):** Phase 1 ships navigation shell, auth gate, and placeholder pages with “not wired” states; pages graduate to “live” as modules complete without breaking URLs.

## Requirements

### Functional

- **FR-1:** Implement the Next.js app under `apps/app/` (or path fixed in plan) with App Router, consistent internal layout, and shared components for JSON viewers, run history, and error banners.
- **FR-2:** Integrate Supabase client for reads/writes allowed to internal roles; never embed DataForSEO or Anthropic keys in the browser bundle.
- **FR-3:** Integrate Python backend HTTP calls for operations that must stay server-side (pipeline runs, provider proxies).
- **FR-4:** Implement the route map exactly as follows (titles may vary; paths are stable):
  - `/` — dashboard
  - `/data/serp-explorer` — M0
  - `/data/metros` — M1
  - `/pipeline/keywords` — M4
  - `/pipeline/collection` — M5
  - `/pipeline/signals` — M6
  - `/pipeline/scoring` — M7
  - `/pipeline/classification` — M8
  - `/pipeline/report` — M9
  - `/experiment/discovery` — M10
  - `/experiment/scanning` — M11
  - `/experiment/audits` — M12
  - `/experiment/outreach` — M13
  - `/experiment/tracking` — M14
  - `/experiment/analysis` — M15

### Non-functional

- **NFR-1:** Lighthouse and bundle size appropriate for an internal tool; no marketing SEO requirements.
- **NFR-2:** Audit logging of eval actions (who ran what) stored server-side when mutations are exposed.

### Implementation mapping (from this spec)

- Next.js app (Vercel) — UI shell and pages above
- Supabase — data + auth for internal users
- Python backend — privileged module execution and adapter proxies

## Success Criteria

| ID | Criterion | Pass condition |
|----|-----------|----------------|
| SC-1 | Route completeness | All listed routes exist and render per FR-4 |
| SC-2 | Internal gate | Unauthorized users cannot access per AS-1.2 |
| SC-3 | M0/M1 data pages | AS-2.1 and AS-2.2 acceptance met when backends ready |
| SC-4 | Pipeline pages | M4–M9 pages wired per AS-3.1 as modules land |
| SC-5 | Experiment pages | M10–M15 pages wired per AS-4.1 as modules land |
| SC-6 | Phased rollout | Shell + placeholders in Phase 1 per AS-5.1 |

## Assumptions

- The marketing site (`apps/web/`) remains separate; this dashboard is not linked from public pages.
- Module teams own the backend endpoints each page calls; M16 owns routing, auth, and presentation patterns.
- Some pages may remain fixture-only until upstream modules merge; feature flags or status badges communicate readiness.

## Source documentation

- `docs/product_breakdown.md` — module boundaries and eval criteria (all modules)
- `docs/algo_spec_v1_1.md` — pipeline schemas and scoring context
- `docs/outreach_experiment.md` — experiment phases E1–E6
- `docs/data_flow.md` — end-to-end data movement for UI surfacing
- `docs/module_dependency.md` — build order vs page wiring
- `CLAUDE.md` — monorepo commands (`dev:app`, `dev:api`)
