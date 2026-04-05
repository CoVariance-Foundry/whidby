# Spec-Driven Development Workflow Guide

**Version:** 1.0 | **Date:** 2026-04-04

This document defines how spec-kit governs all remaining module delivery for the Widby project.

## Spec-Kit Integration

The project uses [github/spec-kit](https://github.com/github/spec-kit) v0.5.0 for Spec-Driven Development. All spec-kit artifacts live under `.specify/` and all Cursor slash commands are in `.cursor/commands/speckit.*.md`.

## Mandatory Lifecycle Per Module

Every module (M4-M15, M16 page increments) must follow this sequence. No step may be skipped without documented justification in the PR.

| Step | Command | Produces | Gate |
|------|---------|----------|------|
| 1. Specify | `/speckit.specify` | `.specify/specs/{feature}/spec.md` | -- |
| 2. Clarify | `/speckit.clarify` | Updates to `spec.md` clarifications section | -- |
| 3. Plan | `/speckit.plan` | `.specify/specs/{feature}/plan.md` + supporting artifacts | -- |
| 4. Tasks | `/speckit.tasks` | `.specify/specs/{feature}/tasks.md` | Pre-implementation review |
| 5. Implement | `/speckit.implement` | Source code + tests | CI hard gate |
| 6. Merge | PR merge | -- | All gates green |

## Feature Naming Convention

Each module maps to a spec-kit feature directory:

```
.specify/specs/
  M04-keyword-expansion/
  M05-data-collection/
  M06-signal-extraction/
  M07-scoring-engine/
  M08-classification-guidance/
  M09-report-generation/
  M10-business-discovery/
  M11-site-scanning/
  M12-audit-generation/
  M13-outreach-delivery/
  M14-response-tracking/
  M15-experiment-analysis/
  M16-eval-frontend/
```

## Existing Docs as Authoritative Sources

These existing documents remain the canonical product specs. Spec-kit feature specs reference them:

| Document | Role | Referenced By |
|----------|------|---------------|
| `docs/product_breakdown.md` | Module map, I/O contracts, eval criteria | All feature specs |
| `docs/algo_spec_v1_1.md` | Scoring algorithm spec (Phases 0-6) | M4-M9 specs |
| `docs/outreach_experiment.md` | Outreach experiment framework (E0-E6) | M10-M15 specs |
| `docs/module_dependency.md` | DAG + dependency matrix | Build ordering |
| `docs/data_flow.md` | Inter-module data flow | I/O contract validation |
| `docs/research_agent_design.md` | Research agent architecture | RA integration points |

## Build Sequence (from Dependency Graph)

Modules must be delivered in dependency order:

**Phase 2 (Core Scoring Pipeline):**
```
M4 → M5 → M6 → M7 → M8 → M9
```

**Phase 3 (Experiment Framework):**
```
M10 → M11 → M12 → M13 → M14 → M15
```

**Continuous (Eval Frontend):**
```
M16 pages added as each module completes
```

Parallel opportunities exist per `docs/module_dependency.md`: M10-M12 can start once M0+M1+M3 are done (independent of M4-M9).

## Hard Gates (CI Enforced)

Every PR must pass:

1. **Spec artifact check** -- If code touches a module scope (`src/pipeline/`, `src/scoring/`, etc.), corresponding spec artifacts must exist
2. **Python quality** -- `ruff check src/ tests/` passes
3. **Unit tests** -- `pytest tests/unit/ -v` passes
4. **Web lint** -- `npm run lint` passes for affected workspaces
5. **Docs sync** -- Architecture docs updated when module interfaces change

## Cross-Module Doc Updates

When a module's implementation reveals contract changes, these docs MUST be updated in the same PR:

- `docs/product_breakdown.md` -- If I/O contracts change
- `docs/module_dependency.md` -- If dependency relationships change
- `docs/data_flow.md` -- If data shapes between modules change
