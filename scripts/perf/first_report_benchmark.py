#!/usr/bin/env python3
"""Run the authoritative first-report latency and memory acceptance gate."""

from __future__ import annotations

import argparse
import json
import math
import os
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

FIRST_REPORT_MAX_SECONDS = 60.0
FIRST_REPORT_MAX_MEMORY_BYTES = 500_000_000
FIRST_REPORT_MAX_RETAINED_GROWTH_BYTES = 50_000_000
HEALTH_MAX_SECONDS = 30.0
REQUIRED_READ_PATHS = (
    "generated_at",
    "spec_version",
    "input",
    "keyword_expansion",
    "metros",
    "meta",
)
CANONICAL_PAYLOAD = {
    "niche": "plumbing",
    "city": "Tampa",
    "state": "FL",
    "dataforseo_location_code": 1015270,
    "cbsa_code": "45300",
    "cbsa_name": "Tampa-St. Petersburg-Clearwater, FL",
    "population": 3175275,
    "metadata_source": "explicit_cbsa",
    "collection_profile": "interactive",
}
REPO_ROOT = Path(__file__).resolve().parents[2]


class BenchmarkError(RuntimeError):
    """A safe-to-report benchmark execution error."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _is_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def validation_failures(
    elapsed_seconds: float,
    memory_peak_bytes: int | None,
    memory_current_bytes: int | None,
    process_rss_bytes: int | None,
    post_status: int | None,
    read_status: int | None,
    post_report_id: str | None,
    read_report_id: str | None,
    required_read_paths_ok: bool,
    persist_warning: object | None,
    container_oom: bool | None,
    deadline_exhausted: bool = False,
    memory_current_growth_bytes: int | None = None,
    process_rss_growth_bytes: int | None = None,
    timeout_seconds: float = FIRST_REPORT_MAX_SECONDS,
    memory_limit_bytes: int = FIRST_REPORT_MAX_MEMORY_BYTES,
    max_retained_growth_bytes: int = FIRST_REPORT_MAX_RETAINED_GROWTH_BYTES,
) -> tuple[str, ...]:
    """Return stable failure codes for one benchmark run."""
    failures: list[str] = []
    if not _is_number(elapsed_seconds) or elapsed_seconds < 0:
        failures.append("elapsed_seconds_invalid")
    elif elapsed_seconds > timeout_seconds:
        failures.append("shared_deadline_exceeded")
    if deadline_exhausted:
        failures.append("shared_deadline_exhausted")

    for name, value in (
        ("memory_peak", memory_peak_bytes),
        ("memory_current", memory_current_bytes),
        ("aggregate_process_rss", process_rss_bytes),
    ):
        if not _is_number(value) or value < 0:
            failures.append(f"{name}_unavailable")
        elif value > memory_limit_bytes:
            failures.append(f"{name}_limit_exceeded")

    for name, value in (
        ("post", post_status),
        ("read", read_status),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or not 200 <= value < 300:
            failures.append(f"{name}_status_not_2xx")

    if not isinstance(post_report_id, str) or not post_report_id.strip():
        failures.append("post_report_id_missing")
    if not isinstance(read_report_id, str) or not read_report_id.strip():
        failures.append("read_report_id_missing")
    if post_report_id and read_report_id and post_report_id != read_report_id:
        failures.append("report_id_mismatch")
    if required_read_paths_ok is not True:
        failures.append("read_body_invalid")
    if persist_warning is not None:
        failures.append("persist_warning_present")
    if container_oom is not False:
        failures.append("container_oom_or_unknown")

    for name, value in (
        ("memory_current", memory_current_growth_bytes),
        ("aggregate_process_rss", process_rss_growth_bytes),
    ):
        if value is None:
            continue
        if not _is_number(value):
            failures.append(f"{name}_growth_unavailable")
        elif value > max_retained_growth_bytes:
            failures.append(f"{name}_retained_growth_exceeded")
    return tuple(dict.fromkeys(failures))


def validate_run(
    elapsed_seconds: float,
    memory_peak_bytes: int | None,
    memory_current_bytes: int | None,
    process_rss_bytes: int | None,
    post_status: int | None,
    read_status: int | None,
    post_report_id: str | None,
    read_report_id: str | None,
    required_read_paths_ok: bool,
    persist_warning: object | None,
    container_oom: bool | None,
    deadline_exhausted: bool = False,
    memory_current_growth_bytes: int | None = None,
    process_rss_growth_bytes: int | None = None,
    timeout_seconds: float = FIRST_REPORT_MAX_SECONDS,
    memory_limit_bytes: int = FIRST_REPORT_MAX_MEMORY_BYTES,
    max_retained_growth_bytes: int = FIRST_REPORT_MAX_RETAINED_GROWTH_BYTES,
) -> bool:
    """Return whether a run satisfies every latency, durability, and memory limit."""
    return not validation_failures(
        elapsed_seconds=elapsed_seconds,
        memory_peak_bytes=memory_peak_bytes,
        memory_current_bytes=memory_current_bytes,
        process_rss_bytes=process_rss_bytes,
        post_status=post_status,
        read_status=read_status,
        post_report_id=post_report_id,
        read_report_id=read_report_id,
        required_read_paths_ok=required_read_paths_ok,
        persist_warning=persist_warning,
        container_oom=container_oom,
        deadline_exhausted=deadline_exhausted,
        memory_current_growth_bytes=memory_current_growth_bytes,
        process_rss_growth_bytes=process_rss_growth_bytes,
        timeout_seconds=timeout_seconds,
        memory_limit_bytes=memory_limit_bytes,
        max_retained_growth_bytes=max_retained_growth_bytes,
    )


def _docker(
    *args: str,
    timeout: float = 30.0,
    check: bool = True,
    quiet: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["docker", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1:] or ["docker command failed"]
        raise BenchmarkError("docker_command_failed", detail[0][:500])
    if not quiet and result.stdout:
        print(result.stdout, end="")
    return result


def _build_image(dockerfile: Path, image: str) -> None:
    print(f"Building production image {image} from {dockerfile}...")
    _docker(
        "build",
        "--file",
        str(dockerfile),
        "--tag",
        image,
        str(REPO_ROOT),
        timeout=900.0,
        quiet=True,
    )


def _container_env() -> dict[str, str]:
    source_map = {
        "NEXT_PUBLIC_SUPABASE_URL": "STAGING_SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY": "STAGING_SUPABASE_SERVICE_ROLE_KEY",
        "DATAFORSEO_LOGIN": "DATAFORSEO_LOGIN",
        "DATAFORSEO_PASSWORD": "DATAFORSEO_PASSWORD",
        "ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY",
    }
    missing = [source for source in source_map.values() if not os.environ.get(source)]
    if missing:
        raise BenchmarkError(
            "missing_environment",
            f"missing required environment variables: {', '.join(sorted(missing))}",
        )
    values = {runtime: os.environ[source] for runtime, source in source_map.items()}
    values["ENVIRONMENT"] = "staging"
    if os.environ.get("DATAFORSEO_BASE_URL"):
        values["DATAFORSEO_BASE_URL"] = os.environ["DATAFORSEO_BASE_URL"]
    return values


def _write_env_file(values: dict[str, str]) -> Path:
    for name, value in values.items():
        if "\n" in value or "\r" in value:
            raise BenchmarkError("invalid_environment", f"{name} contains a newline")
    descriptor, raw_path = tempfile.mkstemp(prefix="whidby-first-report-", suffix=".env")
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            for name, value in values.items():
                handle.write(f"{name}={value}\n")
        path = Path(raw_path)
        if path.stat().st_mode & 0o777 != 0o600:
            raise BenchmarkError("env_file_permissions", "temporary env file is not mode 0600")
        return path
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        Path(raw_path).unlink(missing_ok=True)
        raise


def _request_json(request: Request, timeout: float) -> tuple[int | None, Any, str | None, bool]:
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            raw_body = response.read()
            status = response.status
    except HTTPError as error:
        raw_body = error.read()
        status = error.code
    except (TimeoutError, socket.timeout):
        return None, None, "timeout", True
    except URLError:
        return None, None, "connection_error", False
    except (ConnectionError, OSError):
        return None, None, "connection_error", False

    try:
        body = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return status, None, "invalid_json", False
    return status, body, None, False


def _read_body_valid(body: object) -> bool:
    if not isinstance(body, dict) or not all(path in body for path in REQUIRED_READ_PATHS):
        return False
    return (
        isinstance(body["generated_at"], str)
        and bool(body["generated_at"])
        and isinstance(body["spec_version"], str)
        and bool(body["spec_version"])
        and isinstance(body["input"], dict)
        and isinstance(body["keyword_expansion"], dict)
        and isinstance(body["metros"], list)
        and isinstance(body["meta"], dict)
    )


def _container_oom(container_id: str) -> bool | None:
    result = _docker(
        "inspect",
        "--format",
        "{{json .State.OOMKilled}}",
        container_id,
        check=False,
        quiet=True,
    )
    if result.returncode != 0:
        return None
    try:
        return bool(json.loads(result.stdout))
    except json.JSONDecodeError:
        return None


def _container_value(container_id: str, path: str) -> int | None:
    result = _docker("exec", container_id, "cat", path, check=False, quiet=True)
    if result.returncode != 0:
        return None
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def aggregate_process_rss_bytes(status_by_pid: Mapping[str, str]) -> int:
    """Sum VmRSS for every numeric proc PID represented in a status mapping."""
    total_bytes = 0
    for pid, status in status_by_pid.items():
        if not pid.isdecimal():
            continue
        for line in status.splitlines():
            if not line.startswith("VmRSS:"):
                continue
            fields = line.split()
            if len(fields) >= 3 and fields[2] == "kB":
                try:
                    total_bytes += int(fields[1]) * 1024
                except ValueError:
                    pass
            break
    return total_bytes


def _aggregate_process_rss(container_id: str) -> int | None:
    list_result = _docker(
        "exec",
        container_id,
        "sh",
        "-c",
        "for path in /proc/[0-9]*/status; do "
        "pid=${path#/proc/}; printf '%s\\n' \"${pid%/status}\"; done",
        check=False,
        quiet=True,
    )
    if list_result.returncode != 0:
        return None
    statuses: dict[str, str] = {}
    pids = {value for value in list_result.stdout.splitlines() if value.isdecimal()}
    for pid in sorted(pids, key=int):
        status_result = _docker(
            "exec",
            container_id,
            "cat",
            f"/proc/{pid}/status",
            check=False,
            quiet=True,
        )
        if status_result.returncode == 0:
            statuses[pid] = status_result.stdout
    if not statuses:
        return None
    return aggregate_process_rss_bytes(statuses)


def _memory_sample(container_id: str, phase: str) -> dict[str, Any]:
    return {
        "phase": phase,
        "memory_peak_bytes": _container_value(container_id, "/sys/fs/cgroup/memory.peak"),
        "memory_current_bytes": _container_value(container_id, "/sys/fs/cgroup/memory.current"),
        "aggregate_process_rss_bytes": _aggregate_process_rss(container_id),
    }


def _wait_for_health(base_url: str, timeout_seconds: float) -> tuple[bool, float]:
    started_at = time.monotonic()
    deadline = started_at + timeout_seconds
    request = Request(f"{base_url}/health", method="GET")
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False, time.monotonic() - started_at
        status, _, _, _ = _request_json(request, timeout=min(1.0, remaining))
        if status is not None and 200 <= status < 300:
            return True, time.monotonic() - started_at
        time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))


def _run_report(
    container_id: str,
    base_url: str,
    args: argparse.Namespace,
    run_index: int,
    quiesce: bool,
) -> dict[str, Any]:
    payload = json.dumps(CANONICAL_PAYLOAD, separators=(",", ":")).encode("utf-8")
    post_request = Request(
        f"{base_url}/api/niches/score",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started_at = time.monotonic()
    deadline = started_at + args.timeout_seconds
    post_started_at = time.monotonic()
    post_status, post_body, post_error, post_timeout = _request_json(
        post_request, timeout=max(0.001, deadline - time.monotonic())
    )
    post_seconds = time.monotonic() - post_started_at
    post_report_id = post_body.get("report_id") if isinstance(post_body, dict) else None
    persist_warning = post_body.get("persist_warning") if isinstance(post_body, dict) else None

    read_status: int | None = None
    read_body: Any = None
    read_error: str | None = None
    read_timeout = False
    read_seconds: float | None = None
    deadline_exhausted = post_timeout or time.monotonic() > deadline
    if (
        isinstance(post_status, int)
        and 200 <= post_status < 300
        and isinstance(post_report_id, str)
        and post_report_id
        and not deadline_exhausted
    ):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            deadline_exhausted = True
        else:
            read_started_at = time.monotonic()
            read_request = Request(
                f"{base_url}/api/niches/{quote(post_report_id, safe='')}", method="GET"
            )
            read_status, read_body, read_error, read_timeout = _request_json(
                read_request, timeout=remaining
            )
            read_seconds = time.monotonic() - read_started_at
            deadline_exhausted = read_timeout or time.monotonic() > deadline

    read_report_id = read_body.get("report_id") if isinstance(read_body, dict) else None
    required_read_paths_ok = _read_body_valid(read_body)
    elapsed_seconds = time.monotonic() - started_at
    read_validated = (
        isinstance(read_status, int)
        and 200 <= read_status < 300
        and post_report_id == read_report_id
        and required_read_paths_ok
    )
    if quiesce and read_validated:
        time.sleep(args.quiescence_seconds)
        sample_phase = "post_quiescence"
    else:
        sample_phase = "immediate"
    memory = _memory_sample(container_id, sample_phase)
    container_oom = _container_oom(container_id)

    failures = list(
        validation_failures(
            elapsed_seconds=elapsed_seconds,
            memory_peak_bytes=memory["memory_peak_bytes"],
            memory_current_bytes=memory["memory_current_bytes"],
            process_rss_bytes=memory["aggregate_process_rss_bytes"],
            post_status=post_status,
            read_status=read_status,
            post_report_id=post_report_id,
            read_report_id=read_report_id,
            required_read_paths_ok=required_read_paths_ok,
            persist_warning=persist_warning,
            container_oom=container_oom,
            deadline_exhausted=deadline_exhausted,
            timeout_seconds=args.timeout_seconds,
            memory_limit_bytes=args.memory_bytes,
            max_retained_growth_bytes=args.max_retained_growth_bytes,
        )
    )
    for error in (post_error, read_error):
        if error and error not in failures:
            failures.append(error)
    return {
        "run_index": run_index,
        "timings": {
            "post_seconds": round(post_seconds, 6),
            "read_seconds": round(read_seconds, 6) if read_seconds is not None else None,
            "elapsed_seconds": round(elapsed_seconds, 6),
        },
        "status": {
            "post_status": post_status,
            "read_status": read_status,
            "deadline_exhausted": deadline_exhausted,
            "container_oom": container_oom,
        },
        "report_id": post_report_id,
        "read_contract": {
            "report_ids_match": bool(post_report_id and post_report_id == read_report_id),
            "required_paths_ok": required_read_paths_ok,
            "persist_warning_present": persist_warning is not None,
        },
        "memory": memory,
        "verdict": {"status": "FAIL" if failures else "PASS", "failures": failures},
    }


def _port_for_container(container_id: str) -> int:
    result = _docker("port", container_id, "8000/tcp", quiet=True)
    value = result.stdout.strip().splitlines()[0]
    try:
        return int(value.rsplit(":", 1)[1])
    except (IndexError, ValueError) as error:
        raise BenchmarkError("docker_port_unavailable", "could not parse random port") from error


def _run_container(
    mode: str,
    container_index: int,
    run_count: int,
    env_file: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    name = f"whidby-first-report-{uuid.uuid4().hex[:12]}"
    record: dict[str, Any] = {
        "mode": mode,
        "container_index": container_index,
        "health": None,
        "startup_memory": None,
        "runs": [],
        "verdict": {"status": "FAIL", "failures": []},
    }
    container_id: str | None = None
    try:
        result = _docker(
            "run",
            "--detach",
            "--name",
            name,
            f"--memory={args.memory_bytes}",
            f"--memory-swap={args.memory_bytes}",
            "--env-file",
            str(env_file),
            "--publish",
            "127.0.0.1::8000",
            args.image,
            quiet=True,
        )
        container_id = result.stdout.strip()
        base_url = f"http://127.0.0.1:{_port_for_container(container_id)}"
        healthy, health_seconds = _wait_for_health(base_url, args.health_timeout_seconds)
        record["health"] = {
            "status": "PASS" if healthy else "FAIL",
            "elapsed_seconds": round(health_seconds, 6),
        }
        if not healthy:
            raise BenchmarkError("health_timeout", "container health did not pass in time")
        record["startup_memory"] = _memory_sample(container_id, "post_health")
        for run_index in range(1, run_count + 1):
            record["runs"].append(
                _run_report(
                    container_id,
                    base_url,
                    args,
                    run_index,
                    quiesce=mode == "sequential",
                )
            )

        if mode == "sequential" and len(record["runs"]) >= 3:
            first_memory = record["runs"][0]["memory"]
            third_memory = record["runs"][2]["memory"]
            current_growth = _growth(
                first_memory["memory_current_bytes"],
                third_memory["memory_current_bytes"],
            )
            rss_growth = _growth(
                first_memory["aggregate_process_rss_bytes"],
                third_memory["aggregate_process_rss_bytes"],
            )
            growth_failures = []
            if current_growth is None:
                growth_failures.append("memory_current_growth_unavailable")
            elif current_growth > args.max_retained_growth_bytes:
                growth_failures.append("memory_current_retained_growth_exceeded")
            if rss_growth is None:
                growth_failures.append("aggregate_process_rss_growth_unavailable")
            elif rss_growth > args.max_retained_growth_bytes:
                growth_failures.append("aggregate_process_rss_retained_growth_exceeded")
            record["retained_growth"] = {
                "run_one_to_run_three": {
                    "memory_current_bytes": current_growth,
                    "aggregate_process_rss_bytes": rss_growth,
                },
                "max_bytes": args.max_retained_growth_bytes,
                "verdict": {
                    "status": "FAIL" if growth_failures else "PASS",
                    "failures": growth_failures,
                },
            }
            if growth_failures:
                record["runs"][2]["verdict"]["status"] = "FAIL"
                record["runs"][2]["verdict"]["failures"].extend(growth_failures)

        failures = [
            f"run_{run['run_index']}"
            for run in record["runs"]
            if run["verdict"]["status"] != "PASS"
        ]
        record["verdict"] = {
            "status": "FAIL" if failures else "PASS",
            "failures": failures,
        }
    except BenchmarkError as error:
        record["verdict"] = {
            "status": "FAIL",
            "failures": [error.code],
            "diagnostic": error.detail,
        }
    finally:
        if container_id:
            _docker("rm", "--force", container_id, check=False, quiet=True)
    return record


def _growth(first: int | None, third: int | None) -> int | None:
    if first is None or third is None:
        return None
    return third - first


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dockerfile", type=Path)
    parser.add_argument("--image", default="whidby-first-report-perf:local")
    parser.add_argument("--fresh-containers", type=int, default=2)
    parser.add_argument("--sequential-runs", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=FIRST_REPORT_MAX_SECONDS)
    parser.add_argument("--memory-bytes", type=int, default=FIRST_REPORT_MAX_MEMORY_BYTES)
    parser.add_argument("--health-timeout-seconds", type=float, default=HEALTH_MAX_SECONDS)
    parser.add_argument("--quiescence-seconds", type=float, default=5.0)
    parser.add_argument(
        "--max-retained-growth-bytes",
        type=int,
        default=FIRST_REPORT_MAX_RETAINED_GROWTH_BYTES,
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("artifacts/performance/first-report.json"),
    )
    parser.add_argument("--allow-paid-provider-calls", action="store_true")
    args = parser.parse_args(argv)
    if not args.allow_paid_provider_calls:
        parser.error("refusing paid provider calls without --allow-paid-provider-calls")
    if args.fresh_containers < 0 or args.sequential_runs < 0:
        parser.error("run counts must be non-negative")
    if args.fresh_containers + args.sequential_runs == 0:
        parser.error("at least one benchmark run is required")
    if not 0 < args.timeout_seconds <= FIRST_REPORT_MAX_SECONDS:
        parser.error("--timeout-seconds must be in (0, 60]")
    if not 0 < args.memory_bytes <= FIRST_REPORT_MAX_MEMORY_BYTES:
        parser.error("--memory-bytes must be in (0, 500000000]")
    if not 0 < args.health_timeout_seconds <= HEALTH_MAX_SECONDS:
        parser.error("--health-timeout-seconds must be in (0, 30]")
    if args.quiescence_seconds < 5:
        parser.error("--quiescence-seconds must be at least 5")
    if not 0 <= args.max_retained_growth_bytes <= FIRST_REPORT_MAX_RETAINED_GROWTH_BYTES:
        parser.error("--max-retained-growth-bytes must be in [0, 50000000]")
    return args


def _write_results(path: Path, result: dict[str, Any]) -> None:
    resolved = path if path.is_absolute() else REPO_ROOT / path
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    result: dict[str, Any] = {
        "schema_version": 1,
        "benchmark": "first_report",
        "configuration": {
            "fresh_containers": args.fresh_containers,
            "sequential_runs": args.sequential_runs,
            "timeout_seconds": args.timeout_seconds,
            "memory_bytes": args.memory_bytes,
            "health_timeout_seconds": args.health_timeout_seconds,
            "quiescence_seconds": args.quiescence_seconds,
            "max_retained_growth_bytes": args.max_retained_growth_bytes,
        },
        "containers": [],
        "verdict": {"status": "FAIL", "failures": []},
    }
    env_file: Path | None = None
    try:
        _docker("version", "--format", "{{.Server.Version}}", timeout=15, quiet=True)
        if args.dockerfile is not None:
            dockerfile = args.dockerfile
            if not dockerfile.is_absolute():
                dockerfile = REPO_ROOT / dockerfile
            _build_image(dockerfile, args.image)
        env_file = _write_env_file(_container_env())
        for container_index in range(1, args.fresh_containers + 1):
            result["containers"].append(_run_container("fresh", container_index, 1, env_file, args))
        if args.sequential_runs:
            result["containers"].append(
                _run_container("sequential", 1, args.sequential_runs, env_file, args)
            )
        failures = [
            f"{container['mode']}_{container['container_index']}"
            for container in result["containers"]
            if container["verdict"]["status"] != "PASS"
        ]
        result["verdict"] = {
            "status": "FAIL" if failures else "PASS",
            "failures": failures,
        }
    except (BenchmarkError, FileNotFoundError, subprocess.TimeoutExpired) as error:
        if isinstance(error, BenchmarkError):
            code, detail = error.code, error.detail
        elif isinstance(error, FileNotFoundError):
            code, detail = "docker_unavailable", "docker executable was not found"
        else:
            code, detail = "execution_timeout", "a bounded Docker command timed out"
        result["verdict"] = {
            "status": "FAIL",
            "failures": [code],
            "diagnostic": detail,
        }
    finally:
        if env_file is not None:
            env_file.unlink(missing_ok=True)
        _write_results(args.results, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
