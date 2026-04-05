# M07 Quickstart

## Validate module quality gates

```bash
ruff check src tests
pytest tests/unit/test_m07_* -v
```

## Core validation scenarios

- Score range clamp: all score fields are between 0 and 100.
- Determinism: same fixture input yields identical output over repeated runs.
- Competition inversion: stronger competition lowers opportunity contribution.
- Strategy profile switching: only `resolved_weights` and composite behavior shift.
- Cohort impact: percentile-dependent paths change with cohort composition only.
- Confidence penalties: missing data yields expected flags and score reductions.

## Latest execution results

- `pytest tests/unit/test_m07_* -v`: PASS (30 passed)
- `ruff check src/scoring tests/unit/test_m07_* tests/fixtures/m07_scoring_fixtures.py`: PASS

### Remediation run (2026-04-05)

Fixes applied: auto profile resolution with `local_pack_position`, ads key canonical to `ads_top_present`, confidence null-safe coercion. All 30 M07 tests pass.
