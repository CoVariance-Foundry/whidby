# V2 Scoring Benchmark Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make V2 scoring consume `seo_benchmarks` through an injectable repository boundary instead of direct Supabase queries inside scoring code.

**Architecture:** Keep scoring pure: `src/scoring/` owns benchmark cell types, repository protocol, and V2 formulas, while `src/clients/` owns the Supabase implementation. The orchestrator can attach V2 score vectors only when a repository is provided, preserving the current V1.1 report path and dry-run behavior. Tests use fixture repositories and fake Supabase clients, so no benchmark test needs network access.

**Tech Stack:** Python 3.11, dataclasses, Protocol interfaces, pytest, ruff, Supabase PostgREST client shape.

---

## Scope

This plan implements the repository boundary and a first V2 scoring integration point. It does not cut over the product UI to V2, does not alter the benchmark schema, and does not require live Supabase credentials for tests.

The implementation targets the Phase 7 branch state where these files exist:

- `supabase/migrations/010_v2_benchmarks.sql`
- `docs/algo_spec_v2.md`
- `src/domain/ports.py`
- `src/pipeline/orchestrator.py`
- `src/scoring/engine.py`
- `src/clients/supabase_adapter.py`

## File Structure

- Create: `src/scoring/benchmark_repository.py`
  - Pure benchmark contract: `SeoBenchmarkCell`, `BenchmarkConfidence`, and `SeoBenchmarkRepository`.
  - No Supabase imports, no environment reads, no network code.
- Create: `tests/scoring/test_benchmark_repository_contract.py`
  - Verifies row coercion, confidence validation, and undersampled semantics.
- Create: `src/clients/seo_benchmark_repository.py`
  - Supabase-backed implementation of the benchmark repository protocol.
  - Owns `seo_benchmarks` table name, selected columns, and env-backed client creation.
- Create: `tests/clients/test_seo_benchmark_repository.py`
  - Verifies Supabase query shape and no-row behavior with a fake client.
- Create: `src/scoring/v2.py`
  - Pure V2 score-vector formulas and a repository-backed entrypoint.
  - Reads benchmark cells through the protocol only.
- Create: `tests/scoring/test_v2_scoring.py`
  - Verifies repository lookup, missing-benchmark flags, no-local-pack behavior, and explicit score directions.
- Modify: `src/pipeline/orchestrator.py`
  - Add optional `benchmark_repository` parameter.
  - Attach `v2_scores` to the metro report entry when a repository is supplied.
- Modify: `tests/unit/test_pipeline_orchestrator.py`
  - Add one composition test proving the orchestrator passes benchmark-backed V2 scores without direct Supabase access.
- Modify: `docs-canonical/ARCHITECTURE.md`
  - Add the concrete repository files to the component map because this is an architecture boundary.
- Modify: `docs-canonical/DATA-MODEL.md`
  - Add a short note that `SeoBenchmark` rows are consumed through `SeoBenchmarkRepository`.
- Modify: `docs/algo_spec_v2.md`
  - Replace the future-tense boundary note with the implemented file paths.

## Task 0: Align Worktree And Baseline

**Files:**
- Read: `AGENTS.md`
- Read: `docs-canonical/ARCHITECTURE.md`
- Read: `docs-canonical/DATA-MODEL.md`
- Read: `docs/algo_spec_v2.md`
- Read: `supabase/migrations/010_v2_benchmarks.sql`

- [ ] **Step 1: Confirm branch and dirty files**

Run:

```bash
git status -sb
git branch --show-current
```

Expected:

```text
## phase-7-data-providers
```

If the worktree is detached, switch to the existing branch while preserving local changes:

```bash
git switch phase-7-data-providers
```

Expected:

```text
Switched to branch 'phase-7-data-providers'
```

- [ ] **Step 2: Read the canonical and V2 benchmark docs**

Run:

```bash
sed -n '1,220p' docs-canonical/ARCHITECTURE.md
sed -n '1,260p' docs-canonical/DATA-MODEL.md
sed -n '1,380p' docs/algo_spec_v2.md
sed -n '167,260p' supabase/migrations/010_v2_benchmarks.sql
```

Expected:

```text
ARCHITECTURE includes the V2 benchmark boundary note.
DATA-MODEL lists SeoBenchmark.
algo_spec_v2 says V2 reads seo_benchmarks by niche_normalized + population_class.
010_v2_benchmarks.sql defines public.seo_benchmarks and public.metro_score_v2.
```

- [ ] **Step 3: Run focused baseline tests**

Run:

```bash
.venv/bin/python -m pytest tests/scoring tests/clients/test_supabase_adapter.py tests/unit/test_pipeline_orchestrator.py -v
```

Expected:

```text
All selected tests pass before the repository-boundary change.
```

If `.venv/bin/python` is missing, run:

```bash
python -m pytest tests/scoring tests/clients/test_supabase_adapter.py tests/unit/test_pipeline_orchestrator.py -v
```

Expected:

```text
All selected tests pass before the repository-boundary change.
```

## Task 1: Define The Pure Benchmark Repository Contract

**Files:**
- Create: `tests/scoring/test_benchmark_repository_contract.py`
- Create: `src/scoring/benchmark_repository.py`

- [ ] **Step 1: Write failing contract tests**

Create `tests/scoring/test_benchmark_repository_contract.py`:

```python
"""Tests for the pure seo_benchmarks repository contract."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.scoring.benchmark_repository import SeoBenchmarkCell


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "niche_normalized": "plumber",
        "naics_code": "238220",
        "population_class": "metro_1m_5m",
        "p25_total_volume_per_capita": Decimal("0.001000"),
        "median_total_volume_per_capita": Decimal("0.002500"),
        "p75_total_volume_per_capita": Decimal("0.004000"),
        "p25_avg_cpc": Decimal("8.25"),
        "median_avg_cpc": Decimal("12.50"),
        "p75_avg_cpc": Decimal("18.75"),
        "median_top3_review_count_min": 42,
        "median_top3_review_velocity": Decimal("3.75"),
        "pct_with_local_pack": Decimal("0.7500"),
        "median_aggregator_count": Decimal("2.50"),
        "median_local_biz_count": Decimal("5.00"),
        "median_establishments_per_100k": Decimal("64.50"),
        "median_lsa_present_rate": Decimal("0.2500"),
        "median_ads_present_rate": Decimal("0.5000"),
        "median_aio_trigger_rate": Decimal("0.1250"),
        "sample_size_metros": 12,
        "sample_size_observations": 144,
        "confidence_label": "medium",
        "fact_window_start": "2026-01-01",
        "fact_window_end": "2026-05-01",
    }
    row.update(overrides)
    return row


def test_from_mapping_coerces_supabase_numeric_values() -> None:
    cell = SeoBenchmarkCell.from_mapping(_row())

    assert cell.niche_normalized == "plumber"
    assert cell.naics_code == "238220"
    assert cell.population_class == "metro_1m_5m"
    assert cell.median_total_volume_per_capita == 0.0025
    assert cell.median_avg_cpc == 12.5
    assert cell.median_top3_review_count_min == 42
    assert cell.median_top3_review_velocity == 3.75
    assert cell.sample_size_metros == 12
    assert cell.sample_size_observations == 144
    assert cell.confidence_label == "medium"
    assert cell.is_undersampled is False


def test_from_mapping_preserves_nullable_benchmark_columns() -> None:
    cell = SeoBenchmarkCell.from_mapping(
        _row(
            naics_code=None,
            median_top3_review_count_min=None,
            median_top3_review_velocity=None,
            median_establishments_per_100k=None,
        )
    )

    assert cell.naics_code is None
    assert cell.median_top3_review_count_min is None
    assert cell.median_top3_review_velocity is None
    assert cell.median_establishments_per_100k is None


def test_low_and_insufficient_cells_are_undersampled() -> None:
    low = SeoBenchmarkCell.from_mapping(_row(sample_size_metros=3, confidence_label="low"))
    insufficient = SeoBenchmarkCell.from_mapping(
        _row(sample_size_metros=1, confidence_label="insufficient")
    )

    assert low.is_undersampled is True
    assert insufficient.is_undersampled is True


def test_invalid_confidence_label_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unsupported benchmark confidence"):
        SeoBenchmarkCell.from_mapping(_row(confidence_label="experimental"))
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/scoring/test_benchmark_repository_contract.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'src.scoring.benchmark_repository'
```

- [ ] **Step 3: Implement the pure contract**

Create `src/scoring/benchmark_repository.py`:

```python
"""Pure repository contract for V2 seo_benchmarks cells."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, Mapping, Protocol

BenchmarkConfidence = Literal["high", "medium", "low", "insufficient"]
_CONFIDENCE_VALUES: set[str] = {"high", "medium", "low", "insufficient"}


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _required_text(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if value is None:
        raise ValueError(f"Missing required benchmark column: {key}")
    text = str(value).strip()
    if not text:
        raise ValueError(f"Empty required benchmark column: {key}")
    return text


def _confidence(value: Any) -> BenchmarkConfidence:
    label = str(value or "").strip()
    if label not in _CONFIDENCE_VALUES:
        raise ValueError(f"Unsupported benchmark confidence: {label!r}")
    return label  # type: ignore[return-value]


@dataclass(frozen=True)
class SeoBenchmarkCell:
    """One `seo_benchmarks` cell keyed by niche and population class."""

    niche_normalized: str
    population_class: str
    naics_code: str | None
    p25_total_volume_per_capita: float | None
    median_total_volume_per_capita: float | None
    p75_total_volume_per_capita: float | None
    p25_avg_cpc: float | None
    median_avg_cpc: float | None
    p75_avg_cpc: float | None
    median_top3_review_count_min: int | None
    median_top3_review_velocity: float | None
    pct_with_local_pack: float | None
    median_aggregator_count: float | None
    median_local_biz_count: float | None
    median_establishments_per_100k: float | None
    median_lsa_present_rate: float | None
    median_ads_present_rate: float | None
    median_aio_trigger_rate: float | None
    sample_size_metros: int
    sample_size_observations: int
    confidence_label: BenchmarkConfidence
    fact_window_start: str | None = None
    fact_window_end: str | None = None

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "SeoBenchmarkCell":
        """Build a benchmark cell from a PostgREST/Supabase row."""
        return cls(
            niche_normalized=_required_text(row, "niche_normalized"),
            population_class=_required_text(row, "population_class"),
            naics_code=(
                str(row["naics_code"]).strip()
                if row.get("naics_code") is not None and str(row["naics_code"]).strip()
                else None
            ),
            p25_total_volume_per_capita=_float_or_none(row.get("p25_total_volume_per_capita")),
            median_total_volume_per_capita=_float_or_none(
                row.get("median_total_volume_per_capita")
            ),
            p75_total_volume_per_capita=_float_or_none(row.get("p75_total_volume_per_capita")),
            p25_avg_cpc=_float_or_none(row.get("p25_avg_cpc")),
            median_avg_cpc=_float_or_none(row.get("median_avg_cpc")),
            p75_avg_cpc=_float_or_none(row.get("p75_avg_cpc")),
            median_top3_review_count_min=_int_or_none(row.get("median_top3_review_count_min")),
            median_top3_review_velocity=_float_or_none(row.get("median_top3_review_velocity")),
            pct_with_local_pack=_float_or_none(row.get("pct_with_local_pack")),
            median_aggregator_count=_float_or_none(row.get("median_aggregator_count")),
            median_local_biz_count=_float_or_none(row.get("median_local_biz_count")),
            median_establishments_per_100k=_float_or_none(
                row.get("median_establishments_per_100k")
            ),
            median_lsa_present_rate=_float_or_none(row.get("median_lsa_present_rate")),
            median_ads_present_rate=_float_or_none(row.get("median_ads_present_rate")),
            median_aio_trigger_rate=_float_or_none(row.get("median_aio_trigger_rate")),
            sample_size_metros=int(row.get("sample_size_metros") or 0),
            sample_size_observations=int(row.get("sample_size_observations") or 0),
            confidence_label=_confidence(row.get("confidence_label")),
            fact_window_start=(
                str(row["fact_window_start"]) if row.get("fact_window_start") is not None else None
            ),
            fact_window_end=(
                str(row["fact_window_end"]) if row.get("fact_window_end") is not None else None
            ),
        )

    @property
    def is_undersampled(self) -> bool:
        """True when V2 should show preliminary/limited benchmark messaging."""
        return self.confidence_label in {"low", "insufficient"} or self.sample_size_metros < 8


class SeoBenchmarkRepository(Protocol):
    """Read boundary for V2 scoring benchmark cells."""

    def get(
        self,
        *,
        niche_normalized: str,
        population_class: str,
    ) -> SeoBenchmarkCell | None:
        """Return the benchmark cell for one `(niche, population_class)` key."""
        ...
```

- [ ] **Step 4: Run the contract tests and verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/scoring/test_benchmark_repository_contract.py -v
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add src/scoring/benchmark_repository.py tests/scoring/test_benchmark_repository_contract.py
git commit -m "feat(scoring): add seo benchmark repository contract"
```

Expected:

```text
[phase-7-data-providers ...] feat(scoring): add seo benchmark repository contract
```

## Task 2: Add The Supabase Benchmark Repository Adapter

**Files:**
- Create: `tests/clients/test_seo_benchmark_repository.py`
- Create: `src/clients/seo_benchmark_repository.py`

- [ ] **Step 1: Write failing adapter tests**

Create `tests/clients/test_seo_benchmark_repository.py`:

```python
"""Tests for the Supabase-backed seo_benchmarks repository."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.clients.seo_benchmark_repository import SupabaseSeoBenchmarkRepository


def _benchmark_row() -> dict[str, object]:
    return {
        "niche_normalized": "plumber",
        "naics_code": "238220",
        "population_class": "metro_1m_5m",
        "p25_total_volume_per_capita": 0.001,
        "median_total_volume_per_capita": 0.0025,
        "p75_total_volume_per_capita": 0.004,
        "p25_avg_cpc": 8.25,
        "median_avg_cpc": 12.5,
        "p75_avg_cpc": 18.75,
        "median_top3_review_count_min": 42,
        "median_top3_review_velocity": 3.75,
        "pct_with_local_pack": 0.75,
        "median_aggregator_count": 2.5,
        "median_local_biz_count": 5.0,
        "median_establishments_per_100k": 64.5,
        "median_lsa_present_rate": 0.25,
        "median_ads_present_rate": 0.5,
        "median_aio_trigger_rate": 0.125,
        "sample_size_metros": 12,
        "sample_size_observations": 144,
        "confidence_label": "medium",
        "fact_window_start": "2026-01-01",
        "fact_window_end": "2026-05-01",
    }


def _fake_client(data: list[dict[str, object]]) -> MagicMock:
    client = MagicMock()
    response = MagicMock(data=data)
    query = client.table.return_value.select.return_value
    query.eq.return_value.eq.return_value.limit.return_value.execute.return_value = response
    return client


def test_get_queries_seo_benchmarks_by_niche_and_population_class() -> None:
    client = _fake_client([_benchmark_row()])
    repo = SupabaseSeoBenchmarkRepository(client=client)

    cell = repo.get(niche_normalized="plumber", population_class="metro_1m_5m")

    assert cell is not None
    assert cell.niche_normalized == "plumber"
    assert cell.population_class == "metro_1m_5m"
    assert cell.median_avg_cpc == 12.5
    client.table.assert_called_once_with("seo_benchmarks")
    select_arg = client.table.return_value.select.call_args.args[0]
    assert "median_total_volume_per_capita" in select_arg
    assert "confidence_label" in select_arg
    first_eq = client.table.return_value.select.return_value.eq
    first_eq.assert_called_once_with("niche_normalized", "plumber")
    second_eq = first_eq.return_value.eq
    second_eq.assert_called_once_with("population_class", "metro_1m_5m")


def test_get_returns_none_when_no_benchmark_cell_exists() -> None:
    client = _fake_client([])
    repo = SupabaseSeoBenchmarkRepository(client=client)

    assert repo.get(niche_normalized="roofing", population_class="large_300k_1m") is None
```

- [ ] **Step 2: Run the adapter tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/clients/test_seo_benchmark_repository.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'src.clients.seo_benchmark_repository'
```

- [ ] **Step 3: Implement the Supabase adapter**

Create `src/clients/seo_benchmark_repository.py`:

```python
"""Supabase-backed repository for V2 seo_benchmarks cells."""
from __future__ import annotations

import os
from typing import Any, Protocol

from src.scoring.benchmark_repository import SeoBenchmarkCell


class _SupabaseLike(Protocol):
    def table(self, name: str) -> Any:
        """Return a PostgREST query builder."""
        ...


_BENCHMARK_COLUMNS = (
    "niche_normalized,naics_code,population_class,"
    "p25_total_volume_per_capita,median_total_volume_per_capita,p75_total_volume_per_capita,"
    "p25_avg_cpc,median_avg_cpc,p75_avg_cpc,"
    "median_top3_review_count_min,median_top3_review_velocity,pct_with_local_pack,"
    "median_aggregator_count,median_local_biz_count,"
    "median_establishments_per_100k,median_lsa_present_rate,median_ads_present_rate,"
    "median_aio_trigger_rate,sample_size_metros,sample_size_observations,"
    "confidence_label,fact_window_start,fact_window_end"
)


class SupabaseSeoBenchmarkRepository:
    """Reads `seo_benchmarks` through a narrow repository boundary."""

    def __init__(self, *, client: _SupabaseLike | None = None) -> None:
        if client is None:
            from supabase import create_client

            url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            if not url or not key:
                missing = [
                    name
                    for name in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
                    if not os.environ.get(name)
                ]
                raise RuntimeError(
                    "Cannot read seo_benchmarks; missing env var(s): "
                    + ", ".join(missing)
                )
            client = create_client(url, key)
        self._client = client

    def get(
        self,
        *,
        niche_normalized: str,
        population_class: str,
    ) -> SeoBenchmarkCell | None:
        response = (
            self._client.table("seo_benchmarks")
            .select(_BENCHMARK_COLUMNS)
            .eq("niche_normalized", niche_normalized)
            .eq("population_class", population_class)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if not rows:
            return None
        return SeoBenchmarkCell.from_mapping(rows[0])
```

- [ ] **Step 4: Run adapter tests and contract tests**

Run:

```bash
.venv/bin/python -m pytest tests/clients/test_seo_benchmark_repository.py tests/scoring/test_benchmark_repository_contract.py -v
```

Expected:

```text
6 passed
```

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add src/clients/seo_benchmark_repository.py tests/clients/test_seo_benchmark_repository.py
git commit -m "feat(clients): add Supabase seo benchmark repository"
```

Expected:

```text
[phase-7-data-providers ...] feat(clients): add Supabase seo benchmark repository
```

## Task 3: Add Pure V2 Scoring That Reads Through The Repository Protocol

**Files:**
- Create: `tests/scoring/test_v2_scoring.py`
- Create: `src/scoring/v2.py`

- [ ] **Step 1: Write failing V2 scoring tests**

Create `tests/scoring/test_v2_scoring.py`:

```python
"""Tests for V2 benchmark-relative scoring."""
from __future__ import annotations

from src.scoring.benchmark_repository import SeoBenchmarkCell
from src.scoring.v2 import compute_v2_scores, compute_v2_scores_with_repository


class FakeBenchmarkRepository:
    def __init__(self, cell: SeoBenchmarkCell | None) -> None:
        self.cell = cell
        self.calls: list[tuple[str, str]] = []

    def get(self, *, niche_normalized: str, population_class: str) -> SeoBenchmarkCell | None:
        self.calls.append((niche_normalized, population_class))
        return self.cell


def benchmark_cell(**overrides: object) -> SeoBenchmarkCell:
    row: dict[str, object] = {
        "niche_normalized": "plumber",
        "naics_code": "238220",
        "population_class": "metro_1m_5m",
        "p25_total_volume_per_capita": 0.001,
        "median_total_volume_per_capita": 0.002,
        "p75_total_volume_per_capita": 0.004,
        "p25_avg_cpc": 7.5,
        "median_avg_cpc": 10.0,
        "p75_avg_cpc": 15.0,
        "median_top3_review_count_min": 40,
        "median_top3_review_velocity": 3.0,
        "pct_with_local_pack": 0.8,
        "median_aggregator_count": 2.0,
        "median_local_biz_count": 5.0,
        "median_establishments_per_100k": 50.0,
        "median_lsa_present_rate": 0.25,
        "median_ads_present_rate": 0.5,
        "median_aio_trigger_rate": 0.1,
        "sample_size_metros": 12,
        "sample_size_observations": 120,
        "confidence_label": "medium",
    }
    row.update(overrides)
    return SeoBenchmarkCell.from_mapping(row)


def signal_fixture(**overrides: object) -> dict[str, object]:
    signals: dict[str, object] = {
        "population": 500_000,
        "population_class": "metro_1m_5m",
        "total_search_volume": 2_000,
        "avg_cpc": 12.0,
        "aggregator_count": 2.0,
        "local_biz_count": 5.0,
        "avg_top5_da": 30.0,
        "local_pack_present": True,
        "top3_review_count_min": 60,
        "review_velocity_avg": 4.5,
        "cbp_establishments": 350,
        "lsa_present": True,
        "ads_present": True,
        "aio_trigger_rate": 0.08,
        "transactional_keyword_ratio": 0.7,
        "local_fulfillment_required": 1.0,
        "paa_density": 2.0,
    }
    signals.update(overrides)
    return signals


def test_compute_v2_scores_with_repository_uses_niche_and_population_key() -> None:
    repo = FakeBenchmarkRepository(benchmark_cell())

    result = compute_v2_scores_with_repository(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(),
        benchmark_repository=repo,
    )

    assert repo.calls == [("plumber", "metro_1m_5m")]
    assert result["benchmark"] == {
        "population_class": "metro_1m_5m",
        "sample_size": 12,
        "confidence_label": "medium",
    }
    assert result["flags"]["benchmark_undersampled"] is False
    assert result["scores"]["demand_strength"]["higher_is_better"] is True
    assert result["scores"]["organic_difficulty"]["higher_is_better"] is False


def test_missing_benchmark_sets_undersampled_flag_and_still_scores() -> None:
    result = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(),
        benchmark=None,
    )

    assert result["benchmark"] == {
        "population_class": "metro_1m_5m",
        "sample_size": 0,
        "confidence_label": "insufficient",
    }
    assert result["flags"]["benchmark_undersampled"] is True
    assert isinstance(result["scores"]["demand_strength"]["value"], int)
    assert isinstance(result["scores"]["monetization_signal"]["value"], int)


def test_local_difficulty_is_null_when_no_local_pack_is_detected() -> None:
    result = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(local_pack_present=False),
        benchmark=benchmark_cell(),
    )

    assert result["scores"]["local_difficulty"]["value"] is None
    assert result["flags"]["no_local_pack_detected"] is True


def test_low_confidence_benchmark_sets_undersampled_flag() -> None:
    result = compute_v2_scores(
        niche_normalized="plumber",
        cbsa_code="31080",
        metro_signals=signal_fixture(),
        benchmark=benchmark_cell(sample_size_metros=3, confidence_label="low"),
    )

    assert result["benchmark"]["confidence_label"] == "low"
    assert result["flags"]["benchmark_undersampled"] is True
```

- [ ] **Step 2: Run V2 tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/scoring/test_v2_scoring.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'src.scoring.v2'
```

- [ ] **Step 3: Implement V2 scoring**

Create `src/scoring/v2.py`:

```python
"""V2 benchmark-relative score vector implementation."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.config.constants import MEDIAN_LOCAL_SERVICE_CPC

from .ai_resilience_score import compute_ai_resilience_score
from .benchmark_repository import SeoBenchmarkCell, SeoBenchmarkRepository
from .normalization import clamp

DEFAULT_VOLUME_PER_CAPITA = 0.0025
DEFAULT_ESTABLISHMENTS_PER_100K = 50.0
DEFAULT_REVIEW_FLOOR = 30.0
DEFAULT_REVIEW_VELOCITY = 3.0


def compute_v2_scores_with_repository(
    *,
    niche_normalized: str,
    cbsa_code: str,
    metro_signals: Mapping[str, Any],
    benchmark_repository: SeoBenchmarkRepository,
) -> dict[str, Any]:
    """Compute V2 scores after reading the benchmark through the repository."""
    signals = _flatten_signals(metro_signals)
    population_class = str(signals.get("population_class") or "").strip()
    benchmark = None
    if population_class:
        benchmark = benchmark_repository.get(
            niche_normalized=niche_normalized,
            population_class=population_class,
        )
    return compute_v2_scores(
        niche_normalized=niche_normalized,
        cbsa_code=cbsa_code,
        metro_signals=signals,
        benchmark=benchmark,
    )


def compute_v2_scores(
    *,
    niche_normalized: str,
    cbsa_code: str,
    metro_signals: Mapping[str, Any],
    benchmark: SeoBenchmarkCell | None,
) -> dict[str, Any]:
    """Compute the V2 score vector for one metro."""
    signals = _flatten_signals(metro_signals)
    population_class = str(
        signals.get("population_class")
        or (benchmark.population_class if benchmark is not None else "")
        or ""
    )
    no_local_pack = not _bool(signals.get("local_pack_present"))
    cbp_missing = signals.get("cbp_establishments") is None and signals.get("establishments") is None
    benchmark_confidence = benchmark.confidence_label if benchmark else "insufficient"
    benchmark_sample_size = benchmark.sample_size_metros if benchmark else 0

    return {
        "niche_normalized": niche_normalized,
        "cbsa_code": cbsa_code,
        "scores": {
            "demand_strength": {
                "value": _demand_strength(signals, benchmark),
                "higher_is_better": True,
                "range": "0-200",
            },
            "organic_difficulty": {
                "value": _organic_difficulty(signals),
                "higher_is_better": False,
                "range": "0-100",
            },
            "local_difficulty": {
                "value": None if no_local_pack else _local_difficulty(signals, benchmark),
                "higher_is_better": False,
                "range": "0-100",
            },
            "monetization_signal": {
                "value": _monetization_signal(signals, benchmark),
                "higher_is_better": True,
                "range": "0-200",
            },
            "ai_resilience": {
                "value": int(round(compute_ai_resilience_score(signals))),
                "higher_is_better": True,
                "range": "0-100",
            },
        },
        "benchmark": {
            "population_class": population_class or None,
            "sample_size": benchmark_sample_size,
            "confidence_label": benchmark_confidence,
        },
        "flags": {
            "no_local_pack_detected": no_local_pack,
            "benchmark_undersampled": benchmark is None or benchmark.is_undersampled,
            "cbp_data_missing": cbp_missing,
        },
        "spec_version": "2.0",
    }


def _flatten_signals(signals: Mapping[str, Any]) -> dict[str, Any]:
    flattened = dict(signals)
    for key in (
        "demand",
        "organic_competition",
        "local_competition",
        "monetization",
        "ai_resilience",
    ):
        value = signals.get(key)
        if isinstance(value, Mapping):
            flattened.update(value)
    return flattened


def _number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any) -> bool:
    return bool(value)


def _positive(value: float | None, default: float) -> float:
    if value is None or value <= 0:
        return default
    return value


def _demand_strength(signals: Mapping[str, Any], benchmark: SeoBenchmarkCell | None) -> int:
    observed_volume = _number(
        signals.get("commercial_search_volume", signals.get("total_search_volume")),
        _number(signals.get("effective_search_volume")),
    )
    population = max(_number(signals.get("population"), 1.0), 1.0)
    observed_cpc = _number(signals.get("avg_cpc"))

    observed_per_capita = observed_volume / population
    benchmark_per_capita = _positive(
        benchmark.median_total_volume_per_capita if benchmark else None,
        DEFAULT_VOLUME_PER_CAPITA,
    )
    benchmark_cpc = _positive(
        benchmark.median_avg_cpc if benchmark else None,
        MEDIAN_LOCAL_SERVICE_CPC,
    )

    volume_score = min(observed_per_capita / benchmark_per_capita, 2.0) * 100.0
    cpc_ratio = observed_cpc / max(benchmark_cpc, 0.01)
    cpc_adjustment = clamp(cpc_ratio, 0.5, 1.5)
    return int(round(clamp(volume_score * cpc_adjustment, 0.0, 200.0)))


def _organic_difficulty(signals: Mapping[str, Any]) -> int:
    aggregator_count = _number(signals.get("aggregator_count"))
    local_biz_count = _number(signals.get("local_biz_count"))
    avg_top5_da = signals.get("avg_top5_da")

    aggregator_pressure = clamp(aggregator_count / 10.0, 0.0, 1.0)
    local_density = clamp(local_biz_count / 10.0, 0.0, 1.0)
    raw = (aggregator_pressure * 0.55 + local_density * 0.30) * 100.0

    if avg_top5_da is not None:
        da_score = clamp(_number(avg_top5_da) / 60.0, 0.0, 1.0) * 100.0
        raw = raw * 0.85 + da_score * 0.15
    return int(round(clamp(raw)))


def _local_difficulty(signals: Mapping[str, Any], benchmark: SeoBenchmarkCell | None) -> int:
    review_floor = _number(
        signals.get("top3_review_count_min"),
        _number(signals.get("local_pack_review_count_avg")),
    )
    velocity = _number(signals.get("top3_review_velocity_avg"), _number(signals.get("review_velocity_avg")))
    benchmark_floor = _positive(
        float(benchmark.median_top3_review_count_min)
        if benchmark and benchmark.median_top3_review_count_min is not None
        else None,
        DEFAULT_REVIEW_FLOOR,
    )
    benchmark_velocity = _positive(
        benchmark.median_top3_review_velocity if benchmark else None,
        DEFAULT_REVIEW_VELOCITY,
    )

    review_pressure = min(review_floor / max(benchmark_floor, 1.0), 3.0)
    velocity_pressure = min(velocity / max(benchmark_velocity, 0.1), 3.0)
    raw = (review_pressure / 3.0) * 60.0 + (velocity_pressure / 3.0) * 40.0
    return int(round(clamp(raw)))


def _monetization_signal(signals: Mapping[str, Any], benchmark: SeoBenchmarkCell | None) -> int:
    population = max(_number(signals.get("population"), 1.0), 1.0)
    establishments = signals.get("cbp_establishments", signals.get("establishments"))

    if establishments is None:
        cbp_score = 50.0
    else:
        establishments_per_100k = (_number(establishments) / population) * 100_000.0
        benchmark_density = _positive(
            benchmark.median_establishments_per_100k if benchmark else None,
            DEFAULT_ESTABLISHMENTS_PER_100K,
        )
        cbp_score = min(establishments_per_100k / benchmark_density, 2.0) * 100.0

    spend_signal = 0.0
    if _bool(signals.get("lsa_present")):
        spend_signal += 30.0
    if _bool(signals.get("ads_present") or signals.get("ads_top_present")):
        spend_signal += 20.0

    raw = cbp_score * 0.70 + spend_signal * 1.5 * 0.30
    return int(round(clamp(raw, 0.0, 200.0)))
```

- [ ] **Step 4: Run V2 tests and verify they pass**

Run:

```bash
.venv/bin/python -m pytest tests/scoring/test_v2_scoring.py -v
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add src/scoring/v2.py tests/scoring/test_v2_scoring.py
git commit -m "feat(scoring): add repository-backed V2 score vector"
```

Expected:

```text
[phase-7-data-providers ...] feat(scoring): add repository-backed V2 score vector
```

## Task 4: Attach Optional V2 Scores In The Orchestrator

**Files:**
- Modify: `tests/unit/test_pipeline_orchestrator.py`
- Modify: `src/pipeline/orchestrator.py`

- [ ] **Step 1: Add a failing orchestrator composition test**

In `tests/unit/test_pipeline_orchestrator.py`, add imports near the existing imports:

```python
from src.scoring.benchmark_repository import SeoBenchmarkCell
```

Add this helper after `_make_fake_dfs_client()`:

```python
class _FakeBenchmarkRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get(self, *, niche_normalized: str, population_class: str) -> SeoBenchmarkCell | None:
        self.calls.append((niche_normalized, population_class))
        return SeoBenchmarkCell.from_mapping(
            {
                "niche_normalized": niche_normalized,
                "naics_code": "238160",
                "population_class": population_class,
                "median_total_volume_per_capita": 0.002,
                "median_avg_cpc": 10.0,
                "median_top3_review_count_min": 40,
                "median_top3_review_velocity": 3.0,
                "median_aggregator_count": 2.0,
                "median_local_biz_count": 5.0,
                "median_establishments_per_100k": 50.0,
                "median_lsa_present_rate": 0.2,
                "median_ads_present_rate": 0.5,
                "median_aio_trigger_rate": 0.1,
                "sample_size_metros": 12,
                "sample_size_observations": 100,
                "confidence_label": "medium",
            }
        )
```

Add this test after `test_score_niche_for_metro_composes_pipeline_and_returns_result`:

```python
def test_score_niche_for_metro_attaches_v2_scores_when_repository_is_provided() -> None:
    fake_dfs = _make_fake_dfs_client()
    repo = _FakeBenchmarkRepository()
    signals = {
        **_FAKE_SIGNALS,
        "population": 500_000,
        "population_class": "metro_1m_5m",
        "total_search_volume": 2_000,
        "avg_cpc": 12.0,
        "aggregator_count": 2.0,
        "local_biz_count": 5.0,
        "avg_top5_da": 30.0,
        "local_pack_present": True,
        "top3_review_count_min": 60,
        "review_velocity_avg": 4.5,
        "cbp_establishments": 350,
        "lsa_present": True,
        "ads_present": True,
        "aio_trigger_rate": 0.08,
        "transactional_keyword_ratio": 0.7,
        "local_fulfillment_required": 1.0,
        "paa_density": 2.0,
    }

    with patch("src.pipeline.orchestrator.expand_keywords",
               new=AsyncMock(return_value=_FAKE_KEYWORD_EXPANSION)), \
         patch("src.pipeline.orchestrator.collect_data",
               new=AsyncMock(return_value=_FAKE_RAW_COLLECTION)), \
         patch("src.pipeline.orchestrator.extract_signals",
               return_value=signals), \
         patch("src.pipeline.orchestrator.compute_scores",
               return_value=_FAKE_SCORES), \
         patch("src.pipeline.orchestrator.classify_ai_exposure", return_value="low"), \
         patch("src.pipeline.orchestrator.classify_serp_archetype",
               return_value=_FAKE_SERP_ARCHETYPE_RESULT), \
         patch("src.pipeline.orchestrator.compute_difficulty_tier",
               return_value=_FAKE_DIFFICULTY_RESULT), \
         patch("src.pipeline.orchestrator.classify_and_generate_guidance",
               new=AsyncMock(return_value=_FAKE_GUIDANCE_BUNDLE)):
        result = asyncio.run(
            score_niche_for_metro(
                niche="roofing",
                city="Phoenix",
                state="AZ",
                strategy_profile="balanced",
                llm_client=object(),
                dataforseo_client=fake_dfs,
                benchmark_repository=repo,
            )
        )

    assert repo.calls == [("roofing", "metro_1m_5m")]
    metro = result.report["metros"][0]
    assert metro["v2_scores"]["spec_version"] == "2.0"
    assert metro["v2_scores"]["benchmark"]["confidence_label"] == "medium"
    assert "opportunity" in metro["scores"]
```

- [ ] **Step 2: Run the orchestrator test and verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_pipeline_orchestrator.py::test_score_niche_for_metro_attaches_v2_scores_when_repository_is_provided -v
```

Expected:

```text
TypeError: score_niche_for_metro() got an unexpected keyword argument 'benchmark_repository'
```

- [ ] **Step 3: Modify the orchestrator signature and imports**

In `src/pipeline/orchestrator.py`, add these imports:

```python
from src.scoring.benchmark_repository import SeoBenchmarkRepository
from src.scoring.v2 import compute_v2_scores_with_repository
```

Update the `score_niche_for_metro` signature:

```python
async def score_niche_for_metro(
    *,
    niche: str,
    city: str,
    state: str | None = None,
    place_id: str | None = None,
    dataforseo_location_code: int | None = None,
    strategy_profile: str = "balanced",
    llm_client: Any,
    dataforseo_client: Any,
    metro_db: MetroDB | None = None,
    benchmark_repository: SeoBenchmarkRepository | None = None,
    dry_run: bool = False,
    request_id: str | None = None,
) -> ScoreNicheResult:
```

- [ ] **Step 4: Attach `population` and `population_class` to signals before V2 scoring**

After `signals = extract_signals(...)` in `src/pipeline/orchestrator.py`, add:

```python
    signals = {
        **signals,
        "population": resolved.population,
        "population_class": getattr(resolved, "population_class", None),
    }
```

If `ResolvedTarget` does not have `population_class`, replace the assignment with this explicit safe lookup:

```python
    resolved_population_class = getattr(resolved, "population_class", None)
    signals = {
        **signals,
        "population": resolved.population,
        "population_class": resolved_population_class,
    }
```

- [ ] **Step 5: Compute optional V2 scores before report assembly**

After M8 guidance generation and before `run_input = { ... }`, add:

```python
    v2_scores = None
    if benchmark_repository is not None:
        v2_scores = compute_v2_scores_with_repository(
            niche_normalized=niche.strip().lower(),
            cbsa_code=resolved.cbsa_code,
            metro_signals=signals,
            benchmark_repository=benchmark_repository,
        )
```

In the single metro entry inside `run_input["metros"]`, add:

```python
                **({"v2_scores": v2_scores} if v2_scores is not None else {}),
```

The metro entry should still include the existing V1.1 fields:

```python
            {
                "cbsa_code": resolved.cbsa_code,
                "cbsa_name": resolved.metro_name,
                "population": resolved.population,
                "scores": scores,
                "confidence": scores["confidence"],
                "serp_archetype": serp_archetype,
                "ai_exposure": ai_exposure,
                "difficulty_tier": difficulty,
                "signals": signals,
                "guidance": guidance_bundle,
                **({"v2_scores": v2_scores} if v2_scores is not None else {}),
            }
```

- [ ] **Step 6: Run the new orchestrator test**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_pipeline_orchestrator.py::test_score_niche_for_metro_attaches_v2_scores_when_repository_is_provided -v
```

Expected:

```text
1 passed
```

- [ ] **Step 7: Run the full orchestrator test file**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_pipeline_orchestrator.py -v
```

Expected:

```text
All tests in tests/unit/test_pipeline_orchestrator.py pass.
```

- [ ] **Step 8: Commit Task 4**

Run:

```bash
git add src/pipeline/orchestrator.py tests/unit/test_pipeline_orchestrator.py
git commit -m "feat(pipeline): attach optional benchmark-backed V2 scores"
```

Expected:

```text
[phase-7-data-providers ...] feat(pipeline): attach optional benchmark-backed V2 scores
```

## Task 5: Document The Concrete Boundary

**Files:**
- Modify: `docs-canonical/ARCHITECTURE.md`
- Modify: `docs-canonical/DATA-MODEL.md`
- Modify: `docs/algo_spec_v2.md`

- [ ] **Step 1: Update canonical architecture component map**

In `docs-canonical/ARCHITECTURE.md`, add this row below the V2 benchmark note or near the scoring/persistence rows:

```markdown
| V2 benchmark repository | Pure `seo_benchmarks` read contract plus Supabase adapter for benchmark-backed score vectors | `src/scoring/benchmark_repository.py`, `src/clients/seo_benchmark_repository.py`, `src/scoring/v2.py` | `tests/scoring/test_benchmark_repository_contract.py`, `tests/clients/test_seo_benchmark_repository.py`, `tests/scoring/test_v2_scoring.py` |
```

- [ ] **Step 2: Update canonical data model**

In `docs-canonical/DATA-MODEL.md`, add this paragraph after the `SeoBenchmark` entity row or in the `Schema Definitions` section:

```markdown
`SeoBenchmark` rows are consumed by V2 scoring through `src.scoring.benchmark_repository.SeoBenchmarkRepository`. The Supabase implementation lives in `src.clients.seo_benchmark_repository.SupabaseSeoBenchmarkRepository`; scoring formulas must not query Supabase directly.
```

- [ ] **Step 3: Update the V2 spec boundary note**

In `docs/algo_spec_v2.md`, replace this sentence:

```markdown
Current boundary: Phase 7 completes when `seo_benchmarks` can be recomputed and audited in staging. V2 scoring integration is the next implementation slice and should add a repository around `seo_benchmarks` rather than querying Supabase ad hoc from scoring formulas.
```

With:

```markdown
Implemented boundary: V2 scoring reads benchmark cells through `src.scoring.benchmark_repository.SeoBenchmarkRepository`. The Supabase adapter is `src.clients.seo_benchmark_repository.SupabaseSeoBenchmarkRepository`; formula code in `src.scoring.v2` receives repository-backed `SeoBenchmarkCell` values and does not issue Supabase queries directly.
```

- [ ] **Step 4: Run DocGuard**

Run:

```bash
npx docguard-cli guard
```

Expected:

```text
DocGuard reports no blocking canonical-document violations.
```

- [ ] **Step 5: Commit Task 5**

Run:

```bash
git add docs-canonical/ARCHITECTURE.md docs-canonical/DATA-MODEL.md docs/algo_spec_v2.md
git commit -m "docs: record V2 benchmark repository boundary"
```

Expected:

```text
[phase-7-data-providers ...] docs: record V2 benchmark repository boundary
```

## Task 6: Final Verification

**Files:**
- Verify: `src/scoring/benchmark_repository.py`
- Verify: `src/clients/seo_benchmark_repository.py`
- Verify: `src/scoring/v2.py`
- Verify: `src/pipeline/orchestrator.py`
- Verify: documentation changed in Task 5

- [ ] **Step 1: Run focused Python tests**

Run:

```bash
.venv/bin/python -m pytest \
  tests/scoring/test_benchmark_repository_contract.py \
  tests/clients/test_seo_benchmark_repository.py \
  tests/scoring/test_v2_scoring.py \
  tests/unit/test_pipeline_orchestrator.py \
  -v
```

Expected:

```text
All selected tests pass.
```

- [ ] **Step 2: Run architecture tests**

Run:

```bash
.venv/bin/python -m pytest tests/architecture -v
```

Expected:

```text
Domain architecture tests pass.
```

- [ ] **Step 3: Run ruff on touched Python files**

Run:

```bash
.venv/bin/python -m ruff check \
  src/scoring/benchmark_repository.py \
  src/clients/seo_benchmark_repository.py \
  src/scoring/v2.py \
  src/pipeline/orchestrator.py \
  tests/scoring/test_benchmark_repository_contract.py \
  tests/clients/test_seo_benchmark_repository.py \
  tests/scoring/test_v2_scoring.py \
  tests/unit/test_pipeline_orchestrator.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 4: Run DocGuard after docs changes**

Run:

```bash
npx docguard-cli guard
```

Expected:

```text
DocGuard reports no blocking canonical-document violations.
```

- [ ] **Step 5: Confirm no scoring code imports Supabase**

Run:

```bash
rg -n "supabase|create_client|\\.table\\(" src/scoring
```

Expected:

```text
No matches.
```

- [ ] **Step 6: Inspect git diff**

Run:

```bash
git diff --stat
git diff --check
```

Expected:

```text
git diff --check produces no whitespace errors.
```

- [ ] **Step 7: Commit any final cleanup**

If Task 6 produced small cleanup changes, commit them:

```bash
git add <changed-files>
git commit -m "chore: verify V2 benchmark repository boundary"
```

Expected:

```text
Commit is created only if verification cleanup changed files.
```

## Self-Review

**Spec coverage:** This plan covers the V2 spec requirement that benchmark lookup is keyed by `(niche_normalized, population_class)`, that benchmark confidence and sample size flow into the score output, that insufficient/low cells set `benchmark_undersampled`, and that formula code does not issue Supabase queries.

**Placeholder scan:** No task uses deferred placeholders. Each code-writing step includes exact code and each verification step includes exact commands and expected outcomes.

**Type consistency:** The repository protocol returns `SeoBenchmarkCell | None`; the Supabase adapter returns that same type; V2 scoring accepts the protocol in `compute_v2_scores_with_repository`; the orchestrator accepts `SeoBenchmarkRepository | None` and preserves the existing `ScoreNicheResult` shape.
