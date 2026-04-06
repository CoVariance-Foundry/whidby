# Quickstart: M8 Classification + Guidance

## Prerequisites

- Python 3.11+
- Project dependencies installed
- Existing M6 signal fixtures and M7 score fixtures available locally
- M3 LLM client available for mocked and optional live-path tests

## 1) Implement module skeleton

Create or update M8 files:

- `src/classification/serp_archetype.py`
- `src/classification/ai_exposure.py`
- `src/classification/difficulty_tier.py`
- `src/classification/guidance_generator.py`
- `src/classification/templates/guidance_templates.py`

## 2) Write tests first (TDD)

Create fixtures and tests:

- `tests/fixtures/m8_classification_fixtures.py`
- `tests/unit/test_serp_archetype.py`
- `tests/unit/test_ai_exposure.py`
- `tests/unit/test_difficulty_tier.py`
- `tests/unit/test_guidance_generator.py`
- `tests/unit/test_classification_pipeline.py`

Core test coverage:

- archetype rule precedence and boundary behavior (aggregator, local-pack, barren, mixed)
- AI exposure threshold boundaries for all four labels
- difficulty tier mapping across strategy profiles and competition levels
- guidance text consistency with archetype/tier/exposure
- fail-safe guidance fallback on LLM timeout/error

## 3) Run focused unit tests

```bash
python3 -m pytest tests/unit/test_serp_archetype.py tests/unit/test_ai_exposure.py tests/unit/test_difficulty_tier.py tests/unit/test_guidance_generator.py tests/unit/test_classification_pipeline.py -v
```

## 4) Run quality-gate checks

```bash
python3 -m ruff check src/classification tests/fixtures/m8_classification_fixtures.py tests/unit/test_serp_archetype.py tests/unit/test_ai_exposure.py tests/unit/test_difficulty_tier.py tests/unit/test_guidance_generator.py tests/unit/test_classification_pipeline.py
python3 -m pytest tests/unit/test_serp_archetype.py tests/unit/test_ai_exposure.py tests/unit/test_difficulty_tier.py tests/unit/test_guidance_generator.py tests/unit/test_classification_pipeline.py -v
```

## 5) Validate contract behavior

For representative fixture runs:

- verify exactly one valid enum for `serp_archetype`, `ai_exposure`, and `difficulty_tier`
- verify guidance remains present and coherent in both generated and fallback modes
- verify M8 does not recompute M7 scores or invoke external APIs beyond M3 guidance call path
- verify output bundle shape matches `contracts/classification-guidance-contract.md`
