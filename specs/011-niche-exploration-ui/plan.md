# Implementation Plan: Niche Finder Exploration Interface

**Branch**: `011-niche-exploration-ui` | **Date**: 2026-04-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-niche-exploration-ui/spec.md`

## Summary

Deliver a dual-surface niche finder experience: (1) a standard scoring surface for city/service queries and (2) an exploration surface that exposes the score-driving raw evidence and includes an exploration assistant that can run follow-up SERP/data queries through existing scoring plugin capabilities.

## Technical Context

**Language/Version**: TypeScript (Next.js 16 frontend), Python 3.11+ (scoring and research-agent services)  
**Primary Dependencies**: Next.js app router stack (existing), internal API routes in `apps/app`, existing `src/scoring` engine, existing `src/research_agent` plugin registry + DataForSEO tooling  
**Storage**: Existing platform persistence and in-memory request/session state for UI interactions  
**Testing**: `pytest` for backend/plugin logic, existing JS/TS lint + app-level tests for frontend behavior  
**Target Platform**: Web application (desktop-first) backed by existing API services  
**Project Type**: Monorepo full-stack feature (frontend surface + backend integration contracts)  
**Performance Goals**: Meet spec outcomes, including returning valid score responses for 95% of valid inputs in <=10 seconds  
**Constraints**: Preserve score consistency between standard and exploration surfaces; avoid introducing new orchestration frameworks; reuse existing scoring/plugin capabilities  
**Scale/Scope**: Initial scope is one standard surface, one exploration surface, and one exploration assistant loop bound to city/service context

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-Driven, TDD | PASS | Spec and plan artifacts are present; implementation tasks will require tests before code completion |
| II. Module-First Architecture | PASS | Work composes existing modules (`apps/app`, `src/scoring`, `src/research_agent`) without breaking DAG boundaries |
| III. No Framework for V1 | PASS | Plan reuses existing deterministic scoring + existing Anthropic-native tool-use approach; no new agent framework |
| IV. Code Quality Standards | PASS | Uses existing lint/type/test standards for TS and Python |
| V. Documentation as Code | PASS | This plan includes research/design/contracts artifacts under `specs/011-niche-exploration-ui/` |
| VI. Simplicity and Determinism | PASS | Exploration assistant is constrained to existing plugin capabilities and query context; scoring path remains deterministic |

## Project Structure

### Documentation (this feature)

```text
specs/011-niche-exploration-ui/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── niche-finder-ui-contract.md
│   └── exploration-agent-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/app/
├── src/app/(protected)/
│   ├── page.tsx                    # standard niche finder entry surface (modify)
│   └── ...                         # existing protected routes
├── src/app/api/
│   └── agent/                      # existing agent proxy routes (extend for exploration use)
└── src/components/                 # shared UI components for dual-surface UX (add/modify)

src/
├── scoring/
│   └── engine.py                   # existing score computation path (reuse)
└── research_agent/
    ├── plugins/
    │   ├── scoring_plugin.py       # existing scoring tool surface (reuse/extend)
    │   └── dataforseo_plugin.py    # existing SERP/data query tool surface (reuse/extend)
    └── agent/claude_agent.py       # existing tool-use loop (reuse for exploration assistant mode)

tests/
├── unit/                           # Python unit tests for plugin/service behavior
└── integration/                    # integration coverage for cross-surface consistency as needed
```

**Structure Decision**: Use the existing `apps/app` web surface and existing Python scoring/agent modules. No new top-level package or service is introduced.

## Design Decisions

### D1: Dual-Surface Experience with Shared Query Context

The standard and exploration surfaces both accept city/service and share a normalized query context to guarantee score comparability.

### D2: Score Transparency by Evidence Attribution

Exploration responses must expose score-driving evidence categories and show which evidence supports the presented score interpretation.

### D3: Exploration Assistant Bound to Existing Plugin Tools

The exploration assistant must execute follow-up queries only via approved, existing plugin capabilities and maintain city/service context continuity.

### D4: Consistency as a First-Class Contract

The design introduces explicit contracts for input normalization and score parity checks between surfaces to satisfy SC-005.

## Post-Design Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-Driven, TDD | PASS | Artifacts for implementation (`research`, `data-model`, `contracts`, `quickstart`) are created |
| II. Module-First Architecture | PASS | No new architectural boundary violations |
| III. No Framework for V1 | PASS | Existing native tool-use and pipeline retained |
| IV. Code Quality Standards | PASS | Planned validation includes existing lint/tests across touched areas |
| V. Documentation as Code | PASS | Design outputs created before implementation |
| VI. Simplicity and Determinism | PASS | Deterministic scoring preserved; assistant constrained by contract |

## Complexity Tracking

No constitution violations identified. No complexity exemptions required.
