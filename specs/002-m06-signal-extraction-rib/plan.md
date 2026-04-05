# Implementation Plan: M6 Signal Extraction

**Branch**: `002-m06-signal-extraction-rib` | **Date**: 2026-04-04 | **Spec**: `specs/002-m06-signal-extraction-rib/spec.md`  
**Input**: Feature specification from `specs/002-m06-signal-extraction-rib/spec.md` with source context from `.specify/specs/M06-signal-extraction/spec.md`

## Summary

Implement M6 as a pure transformation layer that converts one metro's M5 raw collection payload plus M4 keyword metadata into a normalized `MetroSignals` object with five categories. The plan decomposes M6 into small deterministic extractors (demand, organic competition, local competition, AI resilience, monetization) and shared utility modules (SERP feature parsing, domain classification, effective volume, review velocity, GBP completeness) so M7 receives stable, complete, null-safe signal contracts.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `pydantic>=2`, existing pipeline types/utilities, `src/config/constants.py` constants (`AIO_CTR_REDUCTION`, `INTENT_AIO_RATES`, `KNOWN_AGGREGATORS`)  
**Storage**: N/A (in-memory signal derivation from provided M5 payloads)  
**Testing**: `pytest`, `pytest-asyncio` (where needed), fixture-driven unit tests; optional integration tests remain separate  
**Target Platform**: Linux/macOS developer machines and CI Python runtime  
**Project Type**: Backend pipeline module in monorepo  
**Performance Goals**: Deterministic extraction over a 20-metro batch should complete within normal pipeline stage budget (seconds to low minutes depending on fixture size), with no network latency dependence  
**Constraints**: No external API calls; preserve exact signal keys/scales from Algo §6.1-6.5; null-safe defaults for missing local/GBP/review data; cross-metro classification logic must be deterministic  
**Scale/Scope**: One `MetroSignals` output per metro, each built from keyword-level and SERP-level inputs spanning tens to hundreds of keywords per metro

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Spec-Driven + TDD**: PASS — artifacts are created first and implementation sequencing remains test-first by extractor.
- **II. Module-First Architecture**: PASS — changes are scoped to M6 boundaries (M5 input contract, M7 output contract).
- **III. No Agent Framework in V1 Pipeline**: PASS — plain deterministic Python functions only.
- **IV. Code Quality Standards**: PASS — typed Python modules, ruff-compliant style, unit-test-first approach.
- **V. Documentation as Code**: PASS — plan includes `research.md`, `data-model.md`, `quickstart.md`, and explicit contracts.
- **VI. Simplicity and Determinism**: PASS — fixed extractor composition and explicit defaults avoid implicit behavior.

Post-design re-check: PASS (Phase 1 artifacts preserve deterministic module design, no constitution violations introduced).

## Project Structure

### Documentation (this feature)

```text
specs/002-m06-signal-extraction-rib/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── signal-extraction-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── config/
│   └── constants.py
└── pipeline/
    ├── signal_extraction.py
    ├── serp_parser.py
    ├── domain_classifier.py
    ├── effective_volume.py
    ├── review_velocity.py
    ├── gbp_completeness.py
    └── extractors/
        ├── demand_signals.py
        ├── organic_competition.py
        ├── local_competition.py
        ├── ai_resilience.py
        └── monetization.py

tests/
├── fixtures/
│   └── m6_signal_extraction_fixtures.py
└── unit/
    ├── test_signal_extraction.py
    ├── test_serp_parser.py
    ├── test_domain_classifier.py
    ├── test_effective_volume.py
    ├── test_review_velocity.py
    ├── test_gbp_completeness.py
    └── test_signal_extractors.py
```

**Structure Decision**: Use the existing single-project Python pipeline layout with a focused `extractors` subpackage for category-specific derivations and top-level shared utilities for reusable computations.

## Complexity Tracking

No constitution violations requiring exception tracking.

## Implementation Validation

- Lint: `python3 -m ruff check src/pipeline tests/fixtures/m6_signal_extraction_fixtures.py tests/unit/test_signal_extraction.py tests/unit/test_serp_parser.py tests/unit/test_domain_classifier.py tests/unit/test_effective_volume.py tests/unit/test_review_velocity.py tests/unit/test_gbp_completeness.py tests/unit/test_signal_extractors.py` -> **passed**
- Unit tests: `python3 -m pytest tests/unit/test_signal_extraction.py tests/unit/test_serp_parser.py tests/unit/test_domain_classifier.py tests/unit/test_effective_volume.py tests/unit/test_review_velocity.py tests/unit/test_gbp_completeness.py tests/unit/test_signal_extractors.py -v` -> **23 passed**
- Contract checks: M6 output categories and key counts validated in `tests/unit/test_signal_extraction.py` and extractor-level assertions in `tests/unit/test_signal_extractors.py`
