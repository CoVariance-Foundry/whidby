"""Unit tests for M9 feedback logger."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from src.pipeline.errors import FeedbackLoggingError, ReportValidationError
from src.pipeline.feedback_logger import log_feedback
from src.pipeline.report_generator import generate_report
from tests.fixtures.m9_report_fixtures import (
    make_minimal_invalid_report_for_feedback,
    make_run_input,
)


class StubPersistenceClient:
    """Simple in-memory persistence stub."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def insert_feedback(self, row: dict[str, Any]) -> str:
        self.rows.append(deepcopy(row))
        return row["log_id"]


class FailingPersistenceClient(StubPersistenceClient):
    """Persistence stub that fails on configurable index."""

    def __init__(self, fail_on: int) -> None:
        super().__init__()
        self._fail_on = fail_on

    def insert_feedback(self, row: dict[str, Any]) -> str:
        if len(self.rows) == self._fail_on:
            raise RuntimeError("simulated persistence failure")
        return super().insert_feedback(row)


def test_log_feedback_writes_one_row_per_ranked_metro() -> None:
    report = generate_report(make_run_input())
    client = StubPersistenceClient()

    result = log_feedback(report, client)

    assert result["success"] is True
    assert result["inserted_count"] == len(report["metros"])
    assert len(client.rows) == len(report["metros"])
    assert client.rows[0]["recommendation_rank"] == 1


def test_log_feedback_preserves_nullable_outcomes_as_none() -> None:
    report = generate_report(make_run_input())
    client = StubPersistenceClient()

    log_feedback(report, client)

    outcome = client.rows[0]["outcome"]
    assert all(value is None for value in outcome.values())


def test_log_feedback_surfaces_failure_without_mutating_report() -> None:
    report = generate_report(make_run_input())
    before = deepcopy(report)
    client = FailingPersistenceClient(fail_on=1)

    result = log_feedback(report, client)

    assert result["success"] is False
    assert result["inserted_count"] == 1
    assert "simulated persistence failure" in result["cause"]
    assert report == before


def test_log_feedback_requires_insert_feedback_method() -> None:
    report = generate_report(make_run_input())

    with pytest.raises(FeedbackLoggingError, match="insert_feedback"):
        log_feedback(report, object())


def test_log_feedback_rejects_minimal_dict_missing_full_contract() -> None:
    """Arbitrary dicts that don't match the full report contract are rejected."""
    minimal = make_minimal_invalid_report_for_feedback()
    client = StubPersistenceClient()

    with pytest.raises(ReportValidationError, match="missing required field"):
        log_feedback(minimal, client)


def test_log_feedback_rejects_report_with_invalid_metro_missing_scores() -> None:
    """Metros missing required fields in report_document are rejected."""
    report = generate_report(make_run_input())
    del report["metros"][0]["scores"]
    client = StubPersistenceClient()

    with pytest.raises(ReportValidationError, match=r"metros\[0\].*scores\.demand"):
        log_feedback(report, client)


def test_log_feedback_rejects_report_with_non_dict_metro() -> None:
    """Non-dict metro entries in report_document are rejected."""
    report = generate_report(make_run_input())
    report["metros"][0] = "not-a-dict"
    client = StubPersistenceClient()

    with pytest.raises(ReportValidationError, match=r"metros\[0\].*must be a dictionary"):
        log_feedback(report, client)


def test_log_feedback_rejects_non_dict_report() -> None:
    with pytest.raises(ReportValidationError, match="report_document must be a dictionary"):
        log_feedback("not-a-dict", StubPersistenceClient())  # type: ignore[arg-type]


def test_log_feedback_includes_feedback_log_id_in_context() -> None:
    """Each feedback row context includes the report's feedback_log_id."""
    report = generate_report(make_run_input())
    client = StubPersistenceClient()

    log_feedback(report, client)

    for row in client.rows:
        assert row["context"]["feedback_log_id"] == report["meta"]["feedback_log_id"]
