# Implementation Plan: M07 Scoring Engine

**Branch**: `007-m07-scoring-engine` | **Date**: 2026-04-05 | **Spec**: `/.specify/specs/M07-scoring-engine/spec.md`  
**Input**: Feature specification from `/.specify/specs/M07-scoring-engine/spec.md`

## Summary

Build a pure, deterministic scoring module that consumes M6 `metro_signals`, `all_metro_signals`, and `strategy_profile`, then emits `MetroScores` with five 0-100 sub-scores, an `opportunity` composite, `confidence` (score + flags), and `resolved_weights`. Implementation is decomposed by score domain and shared normalization/profile utilities, with TDD coverage for all required gates and invariants.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `pydantic>=2`, existing M6 schemas/contracts, constants in `src/config/constants.py`  
**Storage**: N/A (pure functions only)  
**Testing**: `pytest`, `pytest-asyncio` (if needed), fixture-driven unit tests  
**Target Platform**: Python scoring engine runtime under `src/`  
**Project Type**: Deterministic backend pipeline module  
**Performance Goals**: Linear batch scoring by metro count and reproducible outputs for fixed inputs  
**Constraints**: No side effects/no network calls; strict rule parity with Algo Spec V1.1 §7; clamp all emitted scores to 0-100  
**Scale/Scope**: M07 module files under `src/scoring/` and mirrored tests under `tests/unit/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Spec-driven + TDD**: PASS - test-first implementation from M07 spec acceptance criteria.
- **II. Module-first architecture**: PASS - M07 consumes M6 outputs without crossing module boundaries.
- **III. No framework for V1 pipeline**: PASS - plain Python deterministic functions only.
- **IV. Code quality standards**: PASS - typed APIs, docstrings, ruff/pytest gates.
- **V. Documentation as code**: PASS - update canonical/detailed docs if contracts change.
- **VI. Simplicity and determinism**: PASS - centralized constants and deterministic calculations.

## Project Structure

### Documentation (this feature)

```text
.specify/specs/M07-scoring-engine/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
src/scoring/
├── engine.py
├── demand_score.py
├── organic_competition_score.py
├── local_competition_score.py
├── monetization_score.py
├── ai_resilience_score.py
├── composite_score.py
├── confidence_score.py
├── strategy_profiles.py
└── normalization.py

tests/
├── unit/
│   └── test_m07_*.py
└── fixtures/
    └── m07_*_fixtures.py
```

**Structure Decision**: Keep M07 logic isolated in `src/scoring/` by concern (one file per score domain plus orchestration/composition utilities), with deterministic unit tests mirrored under `tests/unit/`.

## Complexity Tracking

No constitution violations requiring justification.