"""Unit tests for the authoritative first-report benchmark verdict."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts.perf import first_report_benchmark as benchmark

aggregate_process_rss_bytes = benchmark.aggregate_process_rss_bytes
validate_run = benchmark.validate_run


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


@pytest.mark.parametrize(
    "statuses",
    [
        {},
        {"self": "VmRSS:\t999 kB\n"},
        {"7": "Name:\tpython\nState:\tS (sleeping)\n"},
        {"7": "VmRSS:\tnot-a-number kB\n"},
        {"7": "VmRSS:\t1024 bytes\n"},
    ],
)
def test_aggregate_process_rss_requires_valid_numeric_pid_evidence(
    statuses: dict[str, str],
) -> None:
    assert aggregate_process_rss_bytes(statuses) is None


class _FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def _runner_args(**overrides: Any) -> SimpleNamespace:
    values = {
        "dockerfile": None,
        "image": "benchmark:test",
        "fresh_containers": 1,
        "sequential_runs": 0,
        "timeout_seconds": 60.0,
        "memory_bytes": 500_000_000,
        "health_timeout_seconds": 30.0,
        "quiescence_seconds": 5.0,
        "max_retained_growth_bytes": 50_000_000,
        "results": Path("artifacts/performance/test.json"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _memory_sample() -> dict[str, Any]:
    return {
        "phase": "immediate",
        "memory_peak_bytes": 200_000_000,
        "memory_current_bytes": 150_000_000,
        "aggregate_process_rss_bytes": 140_000_000,
    }


def _completed(*, stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(
        args=["docker"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _run_record(run_index: int, status: str = "PASS") -> dict[str, Any]:
    failures = [] if status == "PASS" else ["shared_deadline_exhausted"]
    return {
        "run_index": run_index,
        "status": {"deadline_exhausted": status != "PASS"},
        "memory": _memory_sample(),
        "verdict": {"status": status, "failures": failures},
    }


def test_run_report_passes_only_shared_deadline_remainder_to_get() -> None:
    clock = _FakeClock()
    timeouts: list[float] = []
    provider_secret = "provider-body-secret"
    responses = [
        (
            200,
            {"report_id": "report-1", "provider_debug": provider_secret},
            None,
            False,
        ),
        (
            200,
            {
                "report_id": "report-1",
                "generated_at": "2026-07-11T00:00:00Z",
                "spec_version": "1.1",
                "input": {},
                "keyword_expansion": {},
                "metros": [],
                "meta": {"provider_debug": provider_secret},
            },
            None,
            False,
        ),
    ]

    def request_json(_request, timeout: float):
        timeouts.append(timeout)
        clock.advance(12.0 if len(timeouts) == 1 else 5.0)
        return responses.pop(0)

    result = benchmark._run_report(
        "container-1",
        "http://127.0.0.1:49152",
        _runner_args(),
        1,
        quiesce=False,
        request_json=request_json,
        monotonic=clock,
        sleep=lambda _seconds: None,
        memory_sample=lambda _container, _phase: _memory_sample(),
        container_oom=lambda _container: False,
    )

    assert timeouts == pytest.approx([60.0, 48.0])
    assert result["timings"] == {
        "post_seconds": 12.0,
        "read_seconds": 5.0,
        "elapsed_seconds": 17.0,
    }
    assert result["verdict"]["status"] == "PASS"
    assert provider_secret not in json.dumps(result)


def test_run_report_marks_persist_warning_unknown_without_post_body() -> None:
    result = benchmark._run_report(
        "container-1",
        "http://127.0.0.1:49152",
        _runner_args(),
        1,
        quiesce=False,
        request_json=lambda _request, timeout: (None, None, "timeout", True),
        monotonic=lambda: 0.0,
        sleep=lambda _seconds: None,
        memory_sample=lambda _container, _phase: _memory_sample(),
        container_oom=lambda _container: False,
    )

    assert result["read_contract"]["persist_warning_checked"] is False
    assert result["read_contract"]["persist_warning_present"] is None
    assert "persist_warning_unknown" in result["verdict"]["failures"]


@pytest.mark.parametrize(
    "output",
    ["", "not-a-port", "127.0.0.1:", "127.0.0.1:abc", "unexpected:49152"],
)
def test_parse_docker_port_rejects_empty_or_malformed_output(output: str) -> None:
    with pytest.raises(benchmark.BenchmarkError) as error:
        benchmark.parse_docker_port(output)

    assert error.value.code == "docker_port_unavailable"


def test_parse_docker_port_accepts_random_localhost_binding() -> None:
    assert benchmark.parse_docker_port("127.0.0.1:49152\n") == 49152


def test_mode_aggregation_preserves_fresh_and_sequential_failures() -> None:
    containers = [
        {"mode": "fresh", "container_index": 1, "verdict": {"status": "PASS"}},
        {"mode": "fresh", "container_index": 2, "verdict": {"status": "FAIL"}},
        {"mode": "sequential", "container_index": 1, "verdict": {"status": "FAIL"}},
    ]

    assert benchmark.aggregate_mode_verdict(containers) == {
        "status": "FAIL",
        "failures": ["fresh_2", "sequential_1"],
    }


def test_docker_failure_redacts_stderr_and_temp_env_path() -> None:
    secret = "token=do-not-leak /tmp/whidby-first-report-secret.env provider-body"

    def runner(*_args, **_kwargs):
        return _completed(returncode=1, stderr=secret)

    with pytest.raises(benchmark.BenchmarkError) as error:
        benchmark._docker("run", "--env-file", "/tmp/secret.env", runner=runner)

    assert error.value.code == "docker_run_failed"
    assert secret not in error.value.detail
    assert "/tmp/secret.env" not in error.value.detail


def test_docker_timeout_is_sanitized() -> None:
    secret = "secret traceback /tmp/whidby-first-report-secret.env"

    def runner(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["docker", "run"], timeout=30, stderr=secret)

    with pytest.raises(benchmark.BenchmarkError) as error:
        benchmark._docker("run", runner=runner)

    assert error.value.code == "docker_run_timeout"
    assert secret not in error.value.detail


def test_run_timeout_cleans_up_by_generated_container_name() -> None:
    cleanup_targets: list[str] = []

    def docker(*args, **_kwargs):
        assert args[0] == "run"
        raise benchmark.BenchmarkError("docker_run_timeout")

    def cleanup_container(target: str, **_kwargs) -> bool:
        cleanup_targets.append(target)
        return True

    result = benchmark._run_container(
        "fresh",
        1,
        1,
        Path("/tmp/never-emitted.env"),
        _runner_args(),
        docker=docker,
        cleanup_container=cleanup_container,
    )

    assert cleanup_targets[0].startswith("whidby-first-report-")
    assert result["verdict"]["status"] == "FAIL"
    assert "docker_run_timeout" in result["verdict"]["failures"]


def test_cleanup_failure_fails_an_otherwise_passing_container() -> None:
    result = benchmark._run_container(
        "fresh",
        1,
        1,
        Path("/tmp/redacted.env"),
        _runner_args(),
        docker=lambda *args, **kwargs: _completed(stdout="container-1\n"),
        port_for_container=lambda _container, **_kwargs: 49152,
        wait_for_health=lambda _url, _timeout: (True, 0.2),
        memory_sample=lambda _container, _phase: _memory_sample(),
        run_report=lambda *_args, **_kwargs: _run_record(1),
        cleanup_container=lambda _target, **_kwargs: False,
    )

    assert result["verdict"]["status"] == "FAIL"
    assert "container_cleanup_failed" in result["verdict"]["failures"]


def test_sequential_mode_stops_after_failure_and_records_skips() -> None:
    paid_run_indices: list[int] = []

    def run_report(_container, _url, _args, run_index: int, **_kwargs):
        paid_run_indices.append(run_index)
        return _run_record(run_index, status="FAIL")

    result = benchmark._run_container(
        "sequential",
        1,
        3,
        Path("/tmp/redacted.env"),
        _runner_args(sequential_runs=3),
        docker=lambda *args, **kwargs: _completed(stdout="container-1\n"),
        port_for_container=lambda _container, **_kwargs: 49152,
        wait_for_health=lambda _url, _timeout: (True, 0.2),
        memory_sample=lambda _container, _phase: _memory_sample(),
        run_report=run_report,
        cleanup_container=lambda _target, **_kwargs: True,
    )

    assert paid_run_indices == [1]
    assert [run["verdict"]["status"] for run in result["runs"]] == [
        "FAIL",
        "SKIPPED",
        "SKIPPED",
    ]
    assert result["runs"][1]["status"] == {
        "skipped": True,
        "reason": "prior_run_failed",
    }
    assert result["retained_growth"]["verdict"]["status"] == "SKIPPED"


def test_execute_benchmark_removes_temp_env_after_exception(tmp_path: Path) -> None:
    env_file = tmp_path / "secret.env"
    env_file.write_text("SECRET=do-not-leak\n", encoding="utf-8")

    def run_container(*_args, **_kwargs):
        raise RuntimeError("provider-body-secret")

    result = benchmark._execute_benchmark(
        _runner_args(results=tmp_path / "result.json"),
        docker=lambda *args, **kwargs: _completed(),
        build_image=lambda *_args, **_kwargs: None,
        container_env=lambda: {"SECRET": "do-not-leak"},
        write_env_file=lambda _values: env_file,
        run_container=run_container,
    )

    assert not env_file.exists()
    assert result["verdict"]["failures"] == ["unexpected_execution_error"]
    assert "provider-body-secret" not in json.dumps(result)


def test_main_emits_sanitized_result_when_execution_raises(tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    secret = "traceback token /tmp/whidby-first-report-secret.env provider-body"

    def execute_benchmark(_args):
        raise RuntimeError(secret)

    exit_code = benchmark.main(
        [
            "--fresh-containers",
            "1",
            "--sequential-runs",
            "0",
            "--results",
            str(result_path),
            "--allow-paid-provider-calls",
        ],
        execute_benchmark=execute_benchmark,
        emit=lambda _output: None,
    )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert result["verdict"]["failures"] == ["unexpected_execution_error"]
    assert secret not in json.dumps(result)
