# Widby Architecture Rework — Agent Execution Guide

**Purpose:** This document is the master instruction set for Claude Code agents executing the Widby architecture redesign. Read this FIRST, then pick up the specific phase plan you're assigned.

---

## What This Rework Is

Widby's scoring engine works. The M4→M9 pipeline, pure scoring functions, and two-tier caching are solid. But business logic is trapped in the API handler (~150 lines of mixed concerns), there's no service layer, and testing requires mocking infrastructure. As the product grows toward 8 strategy modes, city/service filtering, and new data providers, this becomes load-bearing.

The rework introduces a clean three-layer architecture: **API → Domain → Infrastructure**. It is NOT a rewrite — it's a series of incremental, independently shippable changes.

**Read `widby-architecture-redesign.md` for the full rationale, domain model, and trade-off analysis.**

---

## The Three Core Entities

Everything centers on three entities and their relationships:

- **City** — geographic market with demographics, economics, competitive profile
- **Service** — local service category with ACV, seasonality, NAICS code
- **Market** — the intersection of City × Service, where signals live and scores are computed

Strategies are lenses (weight configurations), not entities. Queries are filters + sort + score over these three types. The data model is stable; the access patterns vary.

---

## Layer Rules (Hard Constraints)

These rules are non-negotiable. Phase 6 adds automated enforcement, but every phase must respect them:

1. **`src/domain/` NEVER imports from `src/clients/`, `src/research_agent/`, or `src/data/`.** It defines Protocol interfaces in `ports.py` and receives implementations via constructor injection.
2. **`src/pipeline/` is called BY `src/domain/`, never the reverse.**
3. **`src/scoring/` and `src/classification/` are leaf-level pure functions.** Called by pipeline, never call outward.
4. **`src/research_agent/api.py` imports ONLY from `src/domain/`.** Constructs infrastructure at startup, passes to domain services.
5. **Infrastructure adapters** (`src/clients/*/adapter.py`) are the only place where domain and infrastructure knowledge coexist.
6. **No `os.environ` or `os.getenv` in `src/domain/`.** Environment config is resolved at startup in the API layer.

Quick self-check before committing:
```bash
grep -r "from src.clients" src/domain/ && echo "VIOLATION" || echo "CLEAN"
grep -r "from src.research_agent" src/domain/ && echo "VIOLATION" || echo "CLEAN"
grep -r "import os" src/domain/ && echo "VIOLATION" || echo "CLEAN"
```

---

## Phase Dependency Graph

```
Phase 1: Domain Entities & Ports        ← START HERE (no dependencies)
    │
    ├──► Phase 2: Extract Geo Resolution
    │        │
    │        └──► Phase 3: Create MarketService    ← HIGHEST RISK
    │                 │
    │                 ├──► Phase 4: Lens-Based Scoring
    │                 │        │
    │                 │        └──► Phase 5: DiscoveryService + /api/discover
    │                 │
    │                 └──► Phase 6: CI Layer Enforcement  (can run after Phase 1-5)
    │
    └──► Phase 7: New Data Providers  (4 parallel sub-phases, after Phase 5)
             ├── 7A: Census ACS (city demographics)
             ├── 7B: Census CBP (business density)
             ├── 7C: BLS Wages (ACV estimates)
             └── 7D: Google Trends (seasonality)
```

**Critical path:** 1 → 2 → 3 → 4 → 5
**Parallel after Phase 5:** Phase 6 + all Phase 7 sub-phases

---

## How to Execute a Phase

Each phase plan (`phase-N-*.md`) follows this structure:

### 1. Step 0: Read existing code
Every plan starts with specific files to read. **Do not skip this.** The plans reference line numbers and function names from the architecture doc, but the actual codebase may have drifted. Read the real files and adjust.

### 2. Create/modify files
Each plan specifies exact files to create, with code templates. These templates are starting points — adapt them to what you find in Step 0. The templates capture the *intent* and *interfaces*; the implementation details come from the actual codebase.

### 3. Write tests
Every phase includes test specs with in-memory fakes. The pattern is consistent:
- Domain logic is tested with fake implementations of Protocol interfaces
- No mocking, no patching, no `os.environ`
- Infrastructure adapters get separate integration tests

### 4. Validate
Every phase ends with explicit validation commands. Run ALL of them before marking the phase complete. The validations check:
- New tests pass
- Existing tests still pass (no regressions)
- Architecture rules are respected
- API contracts are unchanged (for Phases 2-4)

---

## Key Files in the Current Codebase

Before starting any phase, orient yourself:

| File | What it does | Phases that touch it |
|------|-------------|---------------------|
| `src/research_agent/api.py` | HTTP handlers (the ~150-line handler we're extracting from) | 3, 5 |
| `src/pipeline/orchestrator.py` | M4→M9 pipeline composition + geo resolution | 2, 3 |
| `src/scoring/engine.py` | Pure scoring math | 4 |
| `src/config/constants.py` | `FIXED_WEIGHTS`, `STRATEGY_PROFILES`, scoring constants | 4 |
| `src/clients/supabase_persistence.py` | Report persistence | 3 |
| `src/clients/kb_persistence.py` | Knowledge base operations | 3 |
| `src/clients/dataforseo/client.py` | DataForSEO API client | 3 |
| `src/clients/llm/client.py` | LLM client for keyword expansion | 3 |
| `src/data/metro_db.py` | Metro/city lookup database | 2 |
| `src/scoring/canonical_key.py` | Entity identity normalization | 2 |

---

## What Each Phase Produces

| Phase | New files created | Existing files modified | Risk |
|-------|------------------|------------------------|------|
| 1 | `src/domain/` package (7 files) | None | Zero |
| 2 | `geo_resolver.py`, `metro_db_adapter.py` | `orchestrator.py` (removes inline geo logic) | Low |
| 3 | `market_service.py`, 4 adapter files | `api.py` (gutted to thin handler) | **Medium** |
| 4 | Updated `scoring.py` | `engine.py` or `composite_score.py` (accepts weight dict) | Low-Med |
| 5 | `discovery_service.py`, new API endpoints | `api.py` (adds endpoints) | Low |
| 6 | `check_domain_imports.py`, CI config | CI/Makefile | Zero |
| 7 | 4 client packages, 4 adapters, 3 SQL migrations | None (pure additive) | Low each |

---

## Backward Compatibility Contracts

These MUST hold after every phase:

1. **`POST /api/niches/score`** — Same request shape, same response shape, same behavior. The `strategy_profile` parameter continues to work. Existing callers notice nothing.
2. **Pipeline output** — `orchestrator.score_niche_for_metro` returns the same structure. Phases 2-3 refactor *how* it's called, not *what* it returns.
3. **Scoring math** — The `BALANCED` lens (Phase 4) must produce scores identical to the current `balanced` strategy profile on the same input signals. A regression test enforces this.
4. **Caching** — The two-tier `PersistentResponseCache` is untouched in all phases.

---

## When You're Stuck

- **Can't find a function the plan references?** The plan was written from the architecture doc, not the live codebase. Search for the *behavior* described, not the exact name.
- **Types don't match?** The entity/port definitions in Phase 1 are the source of truth. If existing code returns a different shape, the adapter (Phase 3) is where you reconcile.
- **Tests fail after a change?** Check backward compat first. If the existing API test suite breaks, the refactor leaked a behavior change.
- **Architecture lint fails?** You probably imported a client directly in `src/domain/`. Use the port interface and inject the adapter.

---

## File Inventory

```
docs/architecture-rework/
├── ARCHITECTURE-REWORK.md          ← You are here (master guide)
├── widby-architecture-redesign.md  ← Full rationale & domain model
├── phase-1-domain-entities.md      ← Entities, ports, lenses, queries
├── phase-2-geo-resolver.md         ← Geo resolution extraction
├── phase-3-market-service.md       ← MarketService + adapters
├── phase-4-lens-scoring.md         ← Lens-based scoring refactor
├── phase-5-discovery-service.md    ← DiscoveryService + /api/discover
├── phase-6-ci-enforcement.md       ← Architectural lint & CI
└── phase-7-data-providers.md       ← Census, BLS, Trends integrations
```
