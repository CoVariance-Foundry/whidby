# Quickstart: M5 Data Collection Refresh

## Prerequisites

- Python 3.11+
- Project dependencies installed
- Unit tests runnable without network/API keys
- Optional: DataForSEO credentials for integration checks

## 1) Implement module skeleton

Create M5 files:

- `src/pipeline/collection_plan.py`
- `src/pipeline/batch_executor.py`
- `src/pipeline/result_assembler.py`
- `src/pipeline/data_collection.py`
- `src/pipeline/task_graph.py`
- `src/pipeline/errors.py`
- `src/pipeline/types.py`

## 2) Write tests first (TDD)

Create tests:

- `tests/unit/test_collection_plan.py`
- `tests/unit/test_batch_executor.py`
- `tests/unit/test_result_assembler.py`
- `tests/unit/test_data_collection.py`
- `tests/fixtures/m5_collection_fixtures.py`

Core test coverage:

- keyword eligibility and batching rules
- dependency ordering and dedup behavior
- metro partitioning correctness
- metadata reconciliation and partial-failure behavior

## 3) Run unit tests

```bash
python3 -m pytest tests/unit/test_collection_plan.py tests/unit/test_batch_executor.py tests/unit/test_result_assembler.py tests/unit/test_data_collection.py -v
```

## 4) Run quality gate checks

```bash
python3 -m ruff check src/pipeline tests/fixtures/m5_collection_fixtures.py tests/unit/test_collection_plan.py tests/unit/test_batch_executor.py tests/unit/test_result_assembler.py tests/unit/test_data_collection.py
python3 -m pytest tests/unit/test_collection_plan.py tests/unit/test_batch_executor.py tests/unit/test_result_assembler.py tests/unit/test_data_collection.py -v
```

## 5) Optional integration verification

```bash
python3 -m pytest tests/integration/test_dataforseo_integration.py -v -m integration
```

## 6) Validate contract outputs

For sample runs:

- ensure all required metro categories are present (explicit empties allowed)
- verify `meta.total_cost_usd` and `meta.total_api_calls` reconcile with tracked records
- verify `meta.errors` contains scoped retry information for failures

