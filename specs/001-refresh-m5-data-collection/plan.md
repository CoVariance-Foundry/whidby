# Implementation Plan: M5 Data Collection Refresh

**Branch**: `001-refresh-m5-data-collection` | **Date**: 2026-04-04 | **Spec**: `specs/001-refresh-m5-data-collection/spec.md`  
**Input**: Feature specification from `specs/001-refresh-m5-data-collection/spec.md` with source details from `.specify/specs/M05-data-collection/spec.md`

## Summary

Implement M5 as a deterministic async orchestration layer that converts expanded keywords and metros into an execution plan, runs DataForSEO calls with dependency-aware ordering and batching, and assembles normalized per-metro raw outputs plus run metadata (calls, cost, duration, errors). Design centers on four modules: planner, batch executor, result assembler, and top-level collection entrypoint.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `httpx`, `pydantic>=2`, existing `src/clients/dataforseo` client wrappers, `asyncio`  
**Storage**: In-memory assembly for run output; no new persistent storage in M5  
**Testing**: `pytest`, `pytest-asyncio`, fixture-driven unit tests, optional integration tests for live endpoints  
**Target Platform**: Linux/macOS CI and developer machines running Python pipeline jobs  
**Project Type**: Backend pipeline module in monorepo  
**Performance Goals**: Standard 20-metro collection completes in 2-8 minutes; planner avoids per-keyword volume calls when batchable  
**Constraints**: Respect DataForSEO client rate limits, retry behavior, and queue/live endpoint semantics; preserve deterministic processing order for dependency edges  
**Scale/Scope**: Multi-metro runs, keyword-volume batches up to 700 keywords per task per metro, downstream dependent lookups for top local and organic targets

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Spec-Driven + TDD**: PASS — plan includes spec artifacts and test-first delivery for all new public functions.
- **II. Module-First Architecture**: PASS — work is scoped to M5 with explicit M4 input and M6 handoff contract.
- **III. No Agent Framework in V1 Pipeline**: PASS — deterministic async orchestration only; no agent framework usage.
- **IV. Code Quality Standards**: PASS — typed Python modules with `ruff` and pytest gates.
- **V. Documentation as Code**: PASS — plan outputs include `research.md`, `data-model.md`, `quickstart.md`, and contracts.
- **VI. Simplicity and Determinism**: PASS — fixed execution phases and explicit dependencies in planner/executor design.

Post-design re-check: PASS (no constitution violations introduced by data model or contract decisions).

## Project Structure

### Documentation (this feature)

```text
specs/001-refresh-m5-data-collection/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── data-collection-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── clients/
│   └── dataforseo/
│       ├── client.py
│       └── types.py
├── data/
│   └── metro_db.py
└── pipeline/
    ├── data_collection.py
    ├── collection_plan.py
    ├── batch_executor.py
    └── result_assembler.py

tests/
├── fixtures/
│   └── dataforseo_fixtures.py
├── integration/
│   └── test_dataforseo_integration.py
└── unit/
    ├── test_collection_plan.py
    ├── test_batch_executor.py
    ├── test_result_assembler.py
    └── test_data_collection.py
```

**Structure Decision**: Keep a single Python pipeline project layout and add a dedicated `src/pipeline/` package for M5 orchestration boundaries, with mirrored unit tests by module.

## Complexity Tracking

No constitution violations requiring exception handling.

## Implementation Validation

- Unit test suite: `python3 -m pytest tests/unit/test_collection_plan.py tests/unit/test_batch_executor.py tests/unit/test_result_assembler.py tests/unit/test_data_collection.py -v` -> **13 passed**
- Targeted lint checks: `python3 -m ruff check src/pipeline tests/fixtures/m5_collection_fixtures.py tests/unit/test_collection_plan.py tests/unit/test_batch_executor.py tests/unit/test_result_assembler.py tests/unit/test_data_collection.py tests/integration/test_dataforseo_integration.py` -> **passed**
- Optional integration check: `python3 -m pytest tests/integration/test_dataforseo_integration.py -v -m integration` -> **8 skipped** (missing DataForSEO credentials in environment)
