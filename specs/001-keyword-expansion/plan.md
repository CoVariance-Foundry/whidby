# Implementation Plan: M04 Keyword Expansion

**Branch**: `001-keyword-expansion` | **Date**: 2026-04-04 | **Spec**: `/specs/001-keyword-expansion/spec.md`  
**Input**: Feature specification from `/specs/001-keyword-expansion/spec.md`

## Summary

Implement M4 as a deterministic pipeline module that expands one niche keyword into a normalized, deduplicated keyword set with tier, intent, actionability, source traceability, AIO risk label, and expansion confidence. The module orchestrates LLM-based candidate generation and DataForSEO suggestion enrichment, then applies deterministic merge, classification, and quality accounting rules so M5 and M6 can consume a stable `KeywordExpansion` contract.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Existing `LLMClient` (M3), `DataForSEOClient` (M0), `pydantic>=2`, `httpx`, shared constants in `src/config/constants.py`  
**Storage**: N/A for M4 runtime output (in-memory object passed downstream; persistence handled by later modules)  
**Testing**: `pytest`, `pytest-asyncio`, mock/fixture-driven unit tests; optional `@pytest.mark.integration` tests for live API behavior  
**Target Platform**: Python pipeline runtime on Linux/macOS CI and developer machines  
**Project Type**: Backend data-processing pipeline module  
**Performance Goals**: Single expansion run typically completes within 5-15 seconds for a standard niche input  
**Constraints**: Deterministic output for identical input and config; no network in unit tests; temperature=0 for expansion/classification calls; DataForSEO rate limits respected by M0  
**Scale/Scope**: One niche input per invocation; expected output size roughly 10-60 keywords including informational terms

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Gate Check

- **Spec-driven + TDD required**: PASS — spec exists and implementation is planned with test-first task sequencing.
- **Module-first boundaries**: PASS — M4 scope isolated to keyword expansion output consumed by M5/M6.
- **No framework for V1**: PASS — design uses plain Python orchestration with existing SDK wrappers only.
- **Code quality standards**: PASS — plan uses typed functions, deterministic logic, explicit exception handling, and pytest coverage expectations.
- **Documentation as code**: PASS — this plan plus research/data-model/contracts/quickstart artifacts are included.
- **Simplicity and determinism**: PASS — deterministic merge + classification policy with fixed ordering.

### Post-Design Gate Check

- **No constitutional violations introduced by design artifacts**: PASS
- **All technical clarifications resolved before implementation**: PASS (see `research.md`)
- **Testability of every contract guaranteed**: PASS (unit + integration strategy documented in `quickstart.md` and contracts)

## Project Structure

### Documentation (this feature)

```text
specs/001-keyword-expansion/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── keyword-expansion.schema.json
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── pipeline/
│   ├── keyword_expansion.py
│   ├── intent_classifier.py
│   └── keyword_deduplication.py
├── clients/
│   ├── llm/
│   │   └── client.py
│   └── dataforseo/
│       └── client.py
└── config/
    └── constants.py

tests/
├── unit/
│   ├── test_keyword_expansion.py
│   ├── test_intent_classifier.py
│   └── test_keyword_deduplication.py
└── integration/
    └── test_keyword_expansion_integration.py
```

**Structure Decision**: Reuse the existing monorepo Python pipeline layout by adding M4-specific modules under `src/pipeline/` and mirrored tests under `tests/unit/` and `tests/integration/`. No new package or service boundary is needed.

## Complexity Tracking

No constitution violations requiring justification.
