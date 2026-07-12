"""Unit tests for the authoritative first-report benchmark verdict."""

from __future__ import annotations

from typing import Any

import pytest

from scripts.perf.first_report_benchmark import aggregate_process_rss_bytes, validate_run


def _passing_run(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "elapsed_seconds": 60.0,
        "memory_peak_bytes": 500_000_000,
        "memory_current_bytes": 400_000_000,
        "process_rss_bytes": 350_000_000,
        "post_status": 200,
        "read_status": 200,
        "post_report_id": "report-1",
        "read_report_id": "report-1",
        "required_read_paths_ok": True,
        "persist_warning": None,
        "container_oom": False,
    }
    values.update(overrides)
    return values


def test_validate_run_accepts_values_at_hard_limits() -> None:
    assert validate_run(**_passing_run())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("elapsed_seconds", 60.000_001),
        ("memory_peak_bytes", 500_000_001),
        ("memory_current_bytes", 500_000_001),
        ("process_rss_bytes", 500_000_001),
    ],
)
def test_validate_run_rejects_values_above_hard_limits(field: str, value: object) -> None:
    assert not validate_run(**_passing_run(**{field: value}))


def test_validate_run_rejects_an_exhausted_shared_deadline() -> None:
    assert not validate_run(**_passing_run(deadline_exhausted=True))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("post_status", 199),
        ("post_status", 300),
        ("read_status", 199),
        ("read_status", 300),
    ],
)
def test_validate_run_rejects_non_2xx_responses(field: str, value: object) -> None:
    assert not validate_run(**_passing_run(**{field: value}))


@pytest.mark.parametrize(
    "overrides",
    [
        {"post_report_id": None},
        {"post_report_id": ""},
        {"read_report_id": None},
        {"read_report_id": ""},
        {"read_report_id": "report-2"},
    ],
)
def test_validate_run_rejects_null_or_mismatched_report_ids(
    overrides: dict[str, object],
) -> None:
    assert not validate_run(**_passing_run(**overrides))


def test_validate_run_rejects_a_malformed_read_body() -> None:
    assert not validate_run(**_passing_run(required_read_paths_ok=False))


@pytest.mark.parametrize("persist_warning", ["write failed", ""])
def test_validate_run_rejects_persist_warning(persist_warning: str) -> None:
    assert not validate_run(**_passing_run(persist_warning=persist_warning))


def test_validate_run_rejects_container_oom() -> None:
    assert not validate_run(**_passing_run(container_oom=True))


@pytest.mark.parametrize(
    "overrides",
    [
        {"memory_current_growth_bytes": 50_000_001},
        {"process_rss_growth_bytes": 50_000_001},
    ],
)
def test_validate_run_rejects_retained_growth_overflow(
    overrides: dict[str, int],
) -> None:
    assert not validate_run(**_passing_run(**overrides))


def test_validate_run_accepts_retained_growth_at_limit() -> None:
    assert validate_run(
        **_passing_run(
            memory_current_growth_bytes=50_000_000,
            process_rss_growth_bytes=50_000_000,
        )
    )


def test_aggregate_process_rss_sums_every_numeric_proc_pid() -> None:
    statuses = {
        "1": "Name:\tsh\nVmRSS:\t1280 kB\n",
        "7": "Name:\tuvicorn\nVmRSS:\t128000 kB\n",
        "21": "Name:\tworker\nVmRSS:\t4096 kB\n",
        "self": "Name:\tcollector\nVmRSS:\t999999 kB\n",
        "22": "Name:\tzombie\nState:\tZ (zombie)\n",
    }

    assert aggregate_process_rss_bytes(statuses) == (1_280 + 128_000 + 4_096) * 1024
