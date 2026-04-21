# Architecture

<!-- docguard:version 1.0.2 -->
<!-- docguard:status approved -->
<!-- docguard:last-reviewed 2026-04-07 -->
<!-- docguard:owner @widby-team -->

> **Canonical document** — Design intent. This file describes WHAT the system is designed to be.
> Changes to this file require team review. Update `DRIFT-LOG.md` if code deviates.

| Metadata | Value |
|----------|-------|
| **Status** | approved |
| **Version** | `1.0.2` |
| **Last Updated** | 2026-04-07 |
| **Owner** | @widby-team |

---

## System Overview

**Widby** is a niche discovery and scoring platform for rank-and-rent SEO practitioners. The system collects SERP, keyword, business, and review data via DataForSEO, runs it through a multi-signal scoring algorithm, and outputs ranked niche + metro opportunities with actionable guidance.

Three subsystems compose the platform:

1. **Niche Scoring Engine** (`src/`) — Python 3.11+ deterministic pipeline (M0–M9)
2. **Outreach Experiment Framework** (`src/`) — Validation pipeline (M10–M15)
3. **Marketing Site** (`apps/web/`) — Next.js 16 pre-launch landing page
4. **Research Agent Dashboard** (`apps/app/`) — Next.js 16 eval UI

**Production split:** The dashboard is hosted on **Vercel** (`app.thewidby.com`). The FastAPI bridge (`src/research_agent/api.py`) is hosted on **Render** as a Docker web service (e.g. `https://whidby-1.onrender.com`). Vercel server routes under `apps/app/src/app/api/agent/` proxy to the Render URL via **`NEXT_PUBLIC_API_URL`**. Auth magic-link callbacks redirect to the dashboard frontend via **`NEXT_PUBLIC_APP_FRONTEND_URL`** (the Vercel origin, not the API). Supabase backs auth and product data for the app. Details: `docs/research_agent_design.md` §12.

### Niche Finder Dual-Surface Interface

The Research Agent Dashboard includes a dual-surface niche finder flow:

- **Standard surface**: city + service input returns an opportunity score for quick triage.
- **Exploration surface**: same input and score pathway, plus evidence categories that explain score rationale.
- **Exploration assistant**: follow-up query panel that uses approved scoring/search plugin capabilities to retrieve deeper evidence while preserving active city/service context.

Both surfaces are contractually bound to shared query normalization and score parity so operators can trust that exploration explains the same score seen on the standard surface.

## Component Map

| Component | Responsibility | Location | Tests |
|-----------|---------------|----------|-------|
| DataForSEO Client (M0) | API auth, rate limiting, caching, cost tracking | `src/clients/dataforseo/` | `tests/unit/test_dataforseo_client.py` |
| Metro Database (M1) | MSA/CBSA lookup, geo resolution | `src/data/` | `tests/unit/test_metro_db.py` |
| Supabase Schema (M2) | Database migrations, RLS policies | `supabase/migrations/` | `tests/unit/test_supabase_schema.py` |
| LLM Client (M3) | Anthropic SDK wrapper, structured output, token tracking | `src/clients/llm/` | `tests/unit/test_llm_client.py` |
| Keyword Expansion (M4) | Niche → keyword set with intent/tier/AIO risk | `src/pipeline/` | `tests/unit/test_keyword_expansion.py` |
| Data Collection (M5) | Batch SERP + keyword + business data pull per metro | `src/pipeline/` | `tests/unit/test_data_collection.py` |
| Signal Extraction (M6) | Raw responses → derived signals per metro | `src/pipeline/` | `tests/unit/test_signal_extraction.py` |
| Scoring Engine (M7) | Signals → demand/competition/monetization/AI scores | `src/scoring/` | `tests/unit/test_scoring_engine.py` |
| Classification (M8) | Scores → SERP archetype, AI exposure, difficulty tier | `src/classification/` | `tests/unit/test_classification.py` |
| Report Generation (M9) | Assembly + Supabase persistence + feedback logging | `src/pipeline/` | `tests/unit/test_report_generation.py` |
| Business Discovery (M10) | DataForSEO business listings + email discovery | `src/experiment/` | `tests/unit/test_business_discovery.py` |
| Site Scanning (M11) | Lighthouse + schema + CWV analysis | `src/experiment/` | `tests/unit/test_site_scanning.py` |
| Audit Generation (M12) | Personalized HTML audit pages | `src/experiment/` | `tests/unit/test_audit_generation.py` |
| Outreach Delivery (M13) | Email sequencing + compliance | `src/experiment/` | `tests/unit/test_outreach_delivery.py` |
| Response Tracking (M14) | Event collection + reply classification | `src/experiment/` | `tests/unit/test_response_tracking.py` |
| Experiment Analysis (M15) | A/B analysis + rentability signal | `src/experiment/` | `tests/unit/test_experiment_analysis.py` |
| Eval Frontend (M16) | Dashboard pages per module | `apps/app/` | — |
| Research Agent | Claude-native tool-use agent + Ralph loop for autonomous scoring improvement | `src/research_agent/` | `tests/unit/test_research_agent_loop.py`, `test_claude_agent.py`, `test_plugin_registry.py`, `test_scoring_plugin.py`, `test_experiment_runner.py` |
| Marketing Site | Waitlist signup + analytics | `apps/web/` | — |

## Module Dependency Graph

```
M0 (DataForSEO Client) ──┐
M1 (Metro Database) ──────┤
M2 (Supabase Schema) ─────┼──→ M4 (Keyword Expansion) ──→ M5 (Data Collection) ──→ M6 (Signal Extraction) ──→ M7 (Scoring) ──→ M8 (Classification) ──→ M9 (Report)
M3 (LLM Client) ──────────┘                                                                                       ↑
                                                                                                                    │
                           ┌──→ M10 (Business Discovery) ──→ M11 (Site Scanning) ──→ M12 (Audit Gen) ──→ M13 (Outreach) ──→ M14 (Tracking) ──→ M15 (Analysis) ──┘
                           │                                                                                                                         │
M0 ────────────────────────┤                                                                                                          (rentability signal
M1 ────────────────────────┤                                                                                                           feeds back into M7)
M3 ────────────────────────┘

M16 (Eval Frontend): scaffolded in Phase 1, pages added as each module is built
```

### Dependency Matrix

| Module | Depends On | Depended On By |
|--------|-----------|----------------|
| M0: DataForSEO Client | — | M4, M5, M10, M11 |
| M1: Metro Database | — | M5, M10 |
| M2: Supabase Schema | — | M9, M14, M15 |
| M3: LLM Client | — | M4, M8, M12, M14 |
| M4: Keyword Expansion | M0, M3 | M5 |
| M5: Data Collection | M0, M1, M4 | M6 |
| M6: Signal Extraction | M5 | M7 |
| M7: Scoring Engine | M6 | M8, M9, M15 |
| M8: Classification | M6, M7, M3 | M9 |
| M9: Report Generation | M4-M8, M2 | — |
| M10: Business Discovery | M0, M1 | M11 |
| M11: Site Scanning | M0, M10 | M12 |
| M12: Audit Generation | M3, M11 | M13 |
| M13: Outreach Delivery | M12 | M14 |
| M14: Response Tracking | M3, M13, M2 | M15 |
| M15: Experiment Analysis | M14, M2 | M7 (feedback loop) |
| M16: Eval Frontend | All modules | — |

## Layer Boundaries

| Layer | Can Import From | Cannot Import From |
|-------|----------------|-------------------|
| `src/pipeline/` (M4-M6, M9) | `src/clients/`, `src/config/`, `src/data/` | `src/scoring/`, `src/classification/`, `src/experiment/` |
| `src/scoring/` (M7) | `src/config/` | `src/clients/`, `src/pipeline/`, `src/experiment/` |
| `src/classification/` (M8) | `src/config/`, `src/clients/llm/` | `src/pipeline/`, `src/experiment/` |
| `src/experiment/` (M10-M15) | `src/clients/`, `src/config/`, `src/data/` | `src/pipeline/`, `src/scoring/` |
| `src/research_agent/` | `src/clients/`, `src/config/`, `src/scoring/`, `src/pipeline/`, `src/data/` | `src/experiment/` |
| `apps/web/` | Own `src/` only | `src/` (Python engine) |
| `apps/app/` | Own `src/`, FastAPI bridge | `src/` (Python engine) directly |

## Tech Stack

| Category | Technology | Version | Notes |
|----------|-----------|---------|-------|
| Language (Backend) | Python | 3.11+ | `asyncio`, `pydantic>=2`, `httpx` |
| Language (Frontend) | TypeScript | 5.x | Next.js App Router |
| LLM | Anthropic Python SDK | latest | `claude-sonnet-4-20250514` default, `claude-haiku-4-5-20251001` for classification |
| Data APIs | DataForSEO | v3 | Rate limited to 2000 calls/min client-side |
| Database | Supabase | — | PostgreSQL + RLS + Edge Functions |
| Frontend Framework | Next.js | 16 | Tailwind CSS v4 |
| Monorepo | Turborepo | latest | `npm` workspaces |
| Hosting | Vercel | — | Marketing site + eval dashboard |
| Research Agent | Anthropic SDK tool-use + NetworkX + Plugin Registry | — | Same SDK as pipeline; no framework exception |
| Linting (Python) | ruff | — | line-length 100, target py311 |
| Linting (JS/TS) | ESLint | — | core-web-vitals + typescript |
| Testing | pytest + pytest-asyncio + pytest-mock | — | Unit + integration |

## External Dependencies

| Service | Purpose | Rate Limit | Fallback |
|---------|---------|------------|----------|
| DataForSEO | SERP, keyword, business, review, backlink, lighthouse data | 2000 calls/min | Response cache (24h TTL) + retry with backoff |
| Anthropic Claude API | Keyword expansion, intent classification, audit copy, guidance | Per-model limits | Temperature=0 determinism; fallback defaults on failure |
| Supabase | Data persistence (reports, feedback, experiments) | — | — |
| ActiveCampaign | Email CRM for waitlist/marketing | 5 req/s | Sequential tagging |

## Build Sequence

### Phase 1: Foundation (M0, M1, M2, M3, M16 scaffold)

Teams build the four foundation modules in parallel and scaffold M16 in the same phase.

### Phase 2: Scoring Pipeline (M4 → M5 → M6 → M7 → M8 → M9)

This phase follows strict sequential dependencies, and each module consumes the output of the previous module.

### Phase 3: Experiment Framework (M10 → M11 → M12 → M13 → M14 → M15)

Teams can start this phase as soon as M0 + M1 + M3 are complete because it is independent of M4-M9.

### Parallel Opportunities

- M0, M1, M2, M3 can all be built in parallel (Week 1)
- M10-M12 can start as soon as M0 + M1 + M3 are done (independent of M4-M9)
- M8 and M9 can be built in parallel (M8 needs M6+M7; M9 needs M4-M8 but can be built alongside M8)
- Research Agent modules can be built after M0, M1, M3 (independent of scoring pipeline)

## Repository Config Surfaces

| Path | Role |
|------|------|
| `.docguard.json` | DocGuard profile, required canonical files, and validator toggles |
| `.mcp.json` | MCP server configuration used by local coding agents |
| `.githooks/` | Project-managed git hook scripts used by quality gates |
| `.agent/` | Generated DocGuard/agent skills and local agent metadata |
| `.claude/` | Claude plugin and local assistant configuration cache |
| `turbo.json` | Turborepo task graph and workspace pipeline configuration |
| `.turbo/` | Local Turborepo cache/output artifacts (generated) |
| `.venv/` | Local Python virtual environment (generated) |
| `.pytest_cache/` | Local pytest cache/state (generated) |
| `.ruff_cache/` | Local ruff cache/state (generated) |

## Processing Pipeline

```
INPUT                  COLLECTION              TRANSFORMATION          SCORING                  OUTPUT
─────                  ──────────              ──────────────          ───────                  ──────
Niche keyword    →     Keyword Expansion   →   Signal Extraction   →  Demand Score          →  Ranked Metro List
Geographic scope →     SERP Collection     →   SERP Parsing        →  Organic Competition   →  Opportunity Scores
                       Keyword Data Pull   →   Competitor Profiling →  Local Competition     →  SERP Archetypes
                       Business Data Pull  →   GBP Analysis        →  Monetization Score    →  AI Resilience Flags
                       Reviews Data Pull   →   Review Analysis     →  AI Resilience Score   →  Guidance Labels
                       Backlink/OnPage     →   Authority Mapping   →  Composite Score       →  Confidence Flags
                                                                      Confidence Level      →  Feedback Log Entry
```

### Phase Latency Targets

| Phase | Name | Input | Output | Latency Target |
|-------|------|-------|--------|----------------|
| 0 | Configuration | User input | Validated params | <1s |
| 1 | Keyword Expansion | Niche keyword | Expanded keyword set with intent labels | 5-15s |
| 2 | Data Collection | Keywords + Metros | Raw API responses | 2-8 min |
| 3 | Signal Extraction | Raw responses | Derived signals per metro | <30s |
| 4 | Scoring | Signals | Scores per metro | <5s |
| 5 | Classification | Scores + signals | Archetypes + guidance | <5s |
| 6 | Feedback Logging | Scores + input context | Logged tuple | <1s |

**Total target: <10 minutes per report.**

## Canonical Source Mapping

| `docs/` Source | Status | Content Migrated To |
|----------------|--------|---------------------|
| `docs/product_breakdown.md` | canonicalized | `docs-canonical/ARCHITECTURE.md`, `docs-canonical/REQUIREMENTS.md`, `docs-canonical/TEST-SPEC.md` |
| `docs/module_dependency.md` | canonicalized | `docs-canonical/ARCHITECTURE.md` |
| `docs/data_flow.md` | canonicalized | `docs-canonical/DATA-MODEL.md` |
| `docs/algo_spec_v1_1.md` | canonicalized | `docs-canonical/ARCHITECTURE.md`, `docs-canonical/REQUIREMENTS.md`, `docs-canonical/DATA-MODEL.md`, `docs-canonical/TEST-SPEC.md` |
| `docs/outreach_experiment.md` | reference-only | pending-phase-2 |
| `docs/research_agent_design.md` | reference-only | pending-phase-2 |
| `docs/spec_workflow_guide.md` | reference-only | pending-phase-2 |
| `docs/module_spec_map.md` | reference-only | pending-phase-2 |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-04-05 | DocGuard Init | Initial template |
| 1.0.0 | 2026-04-05 | Migration | Populated from `docs/product_breakdown.md`, `docs/module_dependency.md`, `docs/algo_spec_v1_1.md` |
| 1.0.1 | 2026-04-05 | Render alignment | Production split Vercel / Render / Supabase in system overview |
| 1.0.2 | 2026-04-07 | Doc alignment pass | Added repository config surfaces and tightened active voice in build sequencing |
