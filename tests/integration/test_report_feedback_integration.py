"""Optional integration check for M9 feedback persistence wiring."""

from __future__ import annotations

import os

import pytest

from src.pipeline.feedback_logger import log_feedback
from src.pipeline.report_generator import generate_report
from tests.fixtures.m9_report_fixtures import make_run_input


@pytest.mark.integration
def test_feedback_logging_integration_stubbed_when_supabase_env_missing() -> None:
    """Keep integration contract shape while allowing CI/local skip."""
    if not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        pytest.skip("SUPABASE_SERVICE_ROLE_KEY not configured")

    class IntegrationLikeClient:
        def insert_feedback(self, row: dict) -> str:
            return str(row["log_id"])

    report = generate_report(make_run_input())
    result = log_feedback(report, IntegrationLikeClient())

    assert result["success"] is True
    assert result["inserted_count"] == len(report["metros"])


@pytest.mark.integration
def test_feedback_log_id_round_trip() -> None:
    """Verify feedback_log_id is set in report and referenced in feedback rows."""

    class TrackingClient:
        def __init__(self) -> None:
            self.rows: list[dict] = []

        def insert_feedback(self, row: dict) -> str:
            self.rows.append(row)
            return str(row["log_id"])

    report = generate_report(make_run_input())
    assert report["meta"]["feedback_log_id"]

    client = TrackingClient()
    result = log_feedback(report, client)

    assert result["success"] is True
    for row in client.rows:
        assert row["context"]["feedback_log_id"] == report["meta"]["feedback_log_id"]
