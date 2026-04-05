# Implementation Plan: M8 Classification + Guidance

**Branch**: `008-m08-classification-guidance-g3j` | **Date**: 2026-04-05 | **Spec**: `specs/008-m08-classification-guidance-g3j/spec.md`  
**Input**: Feature specification from `specs/008-m08-classification-guidance-g3j/spec.md` with source context from `.specify/specs/M08-classification-guidance/spec.md`

## Summary

Implement M8 as a deterministic classification stage over M6 signals and M7 scores that emits one SERP archetype, one AI exposure level, and one difficulty tier per metro, then layers template-driven LLM guidance that stays consistent with structured outputs. The implementation keeps rule logic pure and testable, isolates prompt/template assets, and adds explicit fallback behavior for LLM failure so guidance never silently contradicts classification.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `pydantic>=2`, existing M3 `LLMClient`, M6/M7 typed outputs, shared constants/utilities in `src/config/constants.py`  
**Storage**: N/A (in-memory derivation and text generation; persistence handled downstream by M9/reporting)  
**Testing**: `pytest` with fixture-driven unit tests and LLM client mocking/stubbing for guidance flows  
**Target Platform**: Linux/macOS developer machines and CI Python runtime  
**Project Type**: Backend pipeline module in monorepo  
**Performance Goals**: Classification should be O(1) per metro and guidance generation should complete within existing M3 timeout/retry envelopes without blocking deterministic classification output  
**Constraints**: No score recomputation in M8; enforce exact enum outputs per Algo §8 and spec FR-001..FR-006; fail-safe guidance fallback on LLM timeout/error; prompts/templates versioned in module files  
**Scale/Scope**: One classification bundle per metro across typical 20-metro runs, with support for diverse niche/metro contexts and boundary-case fixtures

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Spec-Driven + TDD**: PASS — plan artifacts and contract are defined before implementation; tasks will enforce test-first rule coverage per acceptance scenarios.
- **II. Module-First Architecture**: PASS — scope remains strictly M8 boundaries consuming M6/M7 and producing outputs for M9.
- **III. No Framework for V1 Pipeline**: PASS — deterministic Python classifiers plus existing M3 utility client only; no orchestration framework introduced.
- **IV. Code Quality Standards**: PASS — typed Python modules, explicit error handling, and unit coverage across normal and edge/failure paths.
- **V. Documentation as Code (Canonical-First)**: PASS — plan defines artifacts and contract; any interface/schema drift to canonical docs is flagged before implementation.
- **VI. Simplicity and Determinism**: PASS — rules are ordered and explicit, with deterministic precedence and bounded fallback behavior for non-deterministic LLM calls.

Post-design re-check: PASS (Phase 1 artifacts preserve deterministic classification contracts and isolate non-deterministic guidance generation behind explicit safeguards).

## Project Structure

### Documentation (this feature)

```text
specs/008-m08-classification-guidance-g3j/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── classification-guidance-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
└── classification/
    ├── serp_archetype.py
    ├── ai_exposure.py
    ├── difficulty_tier.py
    ├── guidance_generator.py
    └── templates/
        └── guidance_templates.py

tests/
├── fixtures/
│   └── m8_classification_fixtures.py
└── unit/
    ├── test_serp_archetype.py
    ├── test_ai_exposure.py
    ├── test_difficulty_tier.py
    ├── test_guidance_generator.py
    └── test_classification_pipeline.py
```

**Structure Decision**: Use the existing single-project Python module layout, with one file per classification responsibility and a separate templates module to keep prompt/guidance content structured, testable, and easy to version.

## Complexity Tracking

No constitution violations requiring exception tracking.

## Implementation Validation

- Lint: `python3 -m ruff check src/classification tests/fixtures/m8_classification_fixtures.py tests/unit/test_serp_archetype.py tests/unit/test_ai_exposure.py tests/unit/test_difficulty_tier.py tests/unit/test_guidance_generator.py tests/unit/test_classification_pipeline.py` -> **passed**
- Unit tests: `python3 -m pytest tests/unit/test_serp_archetype.py tests/unit/test_ai_exposure.py tests/unit/test_difficulty_tier.py tests/unit/test_guidance_generator.py tests/unit/test_classification_pipeline.py -v` -> **18 passed**
- Contract checks: output bundle shape, enum validity, fallback metadata, and guidance status transitions are validated in `tests/unit/test_classification_pipeline.py` and `tests/unit/test_guidance_generator.py`
