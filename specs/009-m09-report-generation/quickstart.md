# Quickstart: M9 Report Generation + Feedback Logging

## Prerequisites

- Python 3.11+
- Dependencies installed for `src/` and tests
- Upstream fixture data representing M4-M8 outputs
- Supabase credentials available only for optional integration validation

## 1) Create module skeleton

Implement or update:

- `src/pipeline/report_generator.py`
- `src/pipeline/feedback_logger.py`

## 2) Write tests first (TDD)

Create tests and fixtures:

- `tests/fixtures/m9_report_fixtures.py`
- `tests/unit/test_report_generator.py`
- `tests/unit/test_feedback_logger.py`
- `tests/unit/test_report_contract.py`

Coverage goals:

- report schema-required fields and data mapping
- deterministic ordering by `opportunity` with tie-break behavior
- exact meta/cost passthrough in report output
- one feedback record per ranked metro with nullable outcomes
- persistence failure path leaves generated report unchanged

## 3) Run focused unit tests

```bash
python3 -m pytest tests/unit/test_report_generator.py tests/unit/test_feedback_logger.py tests/unit/test_report_contract.py -v
```

## 4) Run lint + quality gates

```bash
python3 -m ruff check src/pipeline tests/fixtures/m9_report_fixtures.py tests/unit/test_report_generator.py tests/unit/test_feedback_logger.py tests/unit/test_report_contract.py
python3 -m pytest tests/unit/test_report_generator.py tests/unit/test_feedback_logger.py tests/unit/test_report_contract.py -v
```

## 5) Optional integration validation

When credentials are available, run a Supabase integration check to ensure feedback rows persist with nullable outcomes and expected foreign-key linkage for one sample report run.

## 6) Manual contract sanity check

- Inspect one generated fixture report and verify `spec_version`, ranked metro order, and `meta` values.
- Inspect one persisted feedback row and verify context/signals/scores/classification fields plus nullable `outcome`.

