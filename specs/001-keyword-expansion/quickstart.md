# Quickstart: M04 Keyword Expansion

## Goal

Implement and validate M4 so a single niche keyword reliably returns a deterministic `KeywordExpansion` payload for downstream modules.

## 1) Implement module files

Create/update:

- `src/pipeline/keyword_expansion.py`
- `src/pipeline/intent_classifier.py`
- `src/pipeline/keyword_deduplication.py`
- `src/config/constants.py` (only if new constants are needed)

Key implementation checkpoints:

1. Build orchestrator flow: LLM expansion -> DataForSEO suggestions -> merge/dedupe -> classify/label -> metrics.
2. Ensure deterministic ordering and deterministic fallback behavior.
3. Ensure summary counters reconcile with keyword-level records.

## 2) Add tests first (TDD)

Create/update:

- `tests/unit/test_keyword_expansion.py`
- `tests/unit/test_intent_classifier.py`
- `tests/unit/test_keyword_deduplication.py`
- `tests/integration/test_keyword_expansion_integration.py` (optional, marked integration)

Minimum unit test coverage:

- Valid input returns non-empty expansion.
- Duplicate variants are collapsed after normalization.
- Every keyword has allowed `intent`, `tier`, `aio_risk`.
- Informational keywords are counted/excluded correctly.
- Confidence mapping follows threshold rules.
- Same input returns identical ordered result.
- Upstream partial failure still returns structured low-confidence result.

## 3) Run validation commands

From repo root:

```bash
ruff check src tests
python -m pytest tests/unit/test_keyword_expansion.py tests/unit/test_intent_classifier.py tests/unit/test_keyword_deduplication.py -v
python -m pytest tests/unit/ -v
```

Optional live validation:

```bash
python -m pytest tests/integration/test_keyword_expansion_integration.py -v -m integration
```

## 4) Verify contract compliance

Validate produced output against `specs/001-keyword-expansion/contracts/keyword-expansion.schema.json` in unit tests.

Required assertions:

- Contract-required fields are present and typed correctly.
- Allowed enum values are enforced.
- Counter reconciliation checks pass.

## 5) Done criteria

M4 is ready for `/speckit.tasks` when:

- Unit tests for new public functions pass without network access.
- Contract validation tests pass.
- Determinism and edge-case tests pass.
- No constitution gate violations are introduced.

## 6) Current implementation status

Implemented in this branch:

- `src/pipeline/keyword_expansion.py`
- `src/pipeline/intent_classifier.py`
- `src/pipeline/keyword_deduplication.py`
- `tests/unit/test_keyword_expansion.py`
- `tests/unit/test_intent_classifier.py`
- `tests/unit/test_keyword_deduplication.py`
