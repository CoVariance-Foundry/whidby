"""Contract-oriented tests for M9 report output."""

from __future__ import annotations

import pytest

from src.pipeline.errors import ReportValidationError
from src.pipeline.report_generator import generate_report
from tests.fixtures.m9_report_fixtures import make_run_input

REQUIRED_TOP_LEVEL_PATHS: tuple[str, ...] = (
    "report_id",
    "generated_at",
    "spec_version",
    "input",
    "keyword_expansion",
    "metros",
    "meta.total_api_calls",
    "meta.total_cost_usd",
    "meta.processing_time_seconds",
    "meta.feedback_log_id",
)


def _assert_required_paths(payload: dict, required_paths: tuple[str, ...]) -> None:
    for path in required_paths:
        current = payload
        for segment in path.split("."):
            assert isinstance(current, dict), f"expected dict at '{segment}' in path '{path}'"
            assert segment in current, f"missing required path: {path}"
            current = current[segment]
        assert current is not None, f"required path is null: {path}"


def _delete_path(payload: dict, path: str) -> None:
    current = payload
    segments = path.split(".")
    for segment in segments[:-1]:
        current = current[segment]
    del current[segments[-1]]


def test_golden_report_passes_required_contract_fields() -> None:
    report = generate_report(make_run_input())

    _assert_required_paths(report, REQUIRED_TOP_LEVEL_PATHS)
    assert report["spec_version"] == "1.1"
    assert isinstance(report["metros"], list)


def test_golden_report_has_feedback_log_id_in_meta() -> None:
    report = generate_report(make_run_input())

    assert "feedback_log_id" in report["meta"]
    assert isinstance(report["meta"]["feedback_log_id"], str)
    assert len(report["meta"]["feedback_log_id"]) > 0


def test_missing_required_field_fails_with_path_pointer() -> None:
    run_input = make_run_input()
    _delete_path(run_input, "meta.total_cost_usd")

    with pytest.raises(ReportValidationError, match="meta.total_cost_usd"):
        generate_report(run_input)


def test_missing_metro_field_fails_with_indexed_path_pointer() -> None:
    run_input = make_run_input()
    _delete_path(run_input["metros"][0], "scores.demand")

    with pytest.raises(ReportValidationError, match=r"metros\[0\].*scores\.demand"):
        generate_report(run_input)


def test_non_numeric_meta_field_fails_with_path_pointer() -> None:
    run_input = make_run_input()
    run_input["meta"]["total_cost_usd"] = "not-a-number"

    with pytest.raises(ReportValidationError, match="meta.total_cost_usd"):
        generate_report(run_input)
