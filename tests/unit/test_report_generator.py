"""Unit tests for M9 report generation."""

from __future__ import annotations

import pytest

from src.pipeline.errors import ReportValidationError
from src.pipeline.report_generator import generate_report
from tests.fixtures.m9_report_fixtures import (
    deep_copy_payload,
    make_invalid_run_input_missing_path,
    make_run_input,
    make_run_input_with_invalid_meta_type,
    make_run_input_with_invalid_metro_scores,
    make_run_input_with_metro_missing_field,
    make_run_input_with_non_dict_metro,
    make_tie_break_run_input,
)


def test_generate_report_has_required_top_level_fields() -> None:
    report = generate_report(make_run_input())

    assert report["report_id"]
    assert report["generated_at"]
    assert report["spec_version"] == "1.1"
    assert "input" in report
    assert "keyword_expansion" in report
    assert "metros" in report
    assert "meta" in report


def test_generate_report_orders_by_opportunity_desc_with_tie_break() -> None:
    report = generate_report(make_tie_break_run_input())
    metros = report["metros"]

    assert metros[0]["scores"]["opportunity"] >= metros[1]["scores"]["opportunity"]
    assert metros[0]["cbsa_code"] == "38060"
    assert metros[1]["cbsa_code"] == "49740"


def test_generate_report_passthroughs_meta_cost_fields_exactly() -> None:
    run_input = make_run_input()
    report = generate_report(run_input)

    assert report["meta"]["total_api_calls"] == run_input["meta"]["total_api_calls"]
    assert report["meta"]["total_cost_usd"] == run_input["meta"]["total_cost_usd"]
    assert report["meta"]["processing_time_seconds"] == run_input["meta"]["processing_time_seconds"]


def test_generate_report_raises_on_missing_required_fields() -> None:
    with pytest.raises(ReportValidationError, match="total_cost_usd"):
        generate_report(make_invalid_run_input_missing_path())


def test_generate_report_does_not_mutate_input_payload() -> None:
    run_input = make_run_input()
    before = deep_copy_payload(run_input)

    generate_report(run_input)

    assert run_input == before


def test_generate_report_meta_includes_feedback_log_id() -> None:
    report = generate_report(make_run_input())

    assert "feedback_log_id" in report["meta"]
    assert isinstance(report["meta"]["feedback_log_id"], str)
    assert len(report["meta"]["feedback_log_id"]) > 0


def test_generate_report_raises_on_metro_missing_required_field() -> None:
    with pytest.raises(ReportValidationError, match=r"metros\[0\].*scores\.demand"):
        generate_report(make_run_input_with_metro_missing_field())


def test_generate_report_raises_on_non_dict_metro() -> None:
    with pytest.raises(ReportValidationError, match=r"metros\[1\].*must be a dictionary"):
        generate_report(make_run_input_with_non_dict_metro())


def test_generate_report_raises_on_non_numeric_opportunity() -> None:
    with pytest.raises(ReportValidationError, match=r"metros\[0\]\.scores\.opportunity"):
        generate_report(make_run_input_with_invalid_metro_scores())


def test_generate_report_raises_on_invalid_meta_numeric_type() -> None:
    with pytest.raises(ReportValidationError, match="meta.total_api_calls"):
        generate_report(make_run_input_with_invalid_meta_type())


def test_generate_report_raises_on_non_dict_input() -> None:
    with pytest.raises(ReportValidationError, match="run_input must be a dictionary"):
        generate_report("not-a-dict")  # type: ignore[arg-type]
