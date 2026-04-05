# Quickstart: M6 Signal Extraction

## Prerequisites

- Python 3.11+
- Project dependencies installed
- Existing M4/M5 fixtures or sample payloads available locally
- Unit tests runnable without network/API keys

## 1) Implement module skeleton

Create or update M6 files:

- `src/pipeline/signal_extraction.py`
- `src/pipeline/serp_parser.py`
- `src/pipeline/domain_classifier.py`
- `src/pipeline/effective_volume.py`
- `src/pipeline/review_velocity.py`
- `src/pipeline/gbp_completeness.py`
- `src/pipeline/extractors/demand_signals.py`
- `src/pipeline/extractors/organic_competition.py`
- `src/pipeline/extractors/local_competition.py`
- `src/pipeline/extractors/ai_resilience.py`
- `src/pipeline/extractors/monetization.py`

## 2) Write tests first (TDD)

Create tests and fixtures:

- `tests/fixtures/m6_signal_extraction_fixtures.py`
- `tests/unit/test_signal_extraction.py`
- `tests/unit/test_serp_parser.py`
- `tests/unit/test_domain_classifier.py`
- `tests/unit/test_effective_volume.py`
- `tests/unit/test_review_velocity.py`
- `tests/unit/test_gbp_completeness.py`
- `tests/unit/test_signal_extractors.py`

Core test coverage:

- all required keys by category are always emitted
- effective-volume formula behavior (detected AIO vs intent-based expected rate)
- aggregator detection and cross-metro national classification path
- local-pack presence vs missing-pack default behavior
- review velocity and GBP completeness calculations

## 3) Run focused unit tests

```bash
python3 -m pytest tests/unit/test_signal_extraction.py tests/unit/test_serp_parser.py tests/unit/test_domain_classifier.py tests/unit/test_effective_volume.py tests/unit/test_review_velocity.py tests/unit/test_gbp_completeness.py tests/unit/test_signal_extractors.py -v
```

## 4) Run quality-gate checks

```bash
python3 -m ruff check src/pipeline tests/fixtures/m6_signal_extraction_fixtures.py tests/unit/test_signal_extraction.py tests/unit/test_serp_parser.py tests/unit/test_domain_classifier.py tests/unit/test_effective_volume.py tests/unit/test_review_velocity.py tests/unit/test_gbp_completeness.py tests/unit/test_signal_extractors.py
python3 -m pytest tests/unit/test_signal_extraction.py tests/unit/test_serp_parser.py tests/unit/test_domain_classifier.py tests/unit/test_effective_volume.py tests/unit/test_review_velocity.py tests/unit/test_gbp_completeness.py tests/unit/test_signal_extractors.py -v
```

## 5) Validate contract behavior

For sample fixture runs:

- verify all five categories and required keys exist
- verify shared values (`avg_cpc`, `gbp_completeness_avg`) stay consistent across categories
- verify no-network guarantee (pure transformation)
- verify null-safe defaults for missing local-pack and sparse GBP/review data
