"""Persist M9 feedback logs for ranked report metros."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .errors import FeedbackLoggingError, ReportValidationError
from .types import (
    REQUIRED_METRO_ENTRY_PATHS,
    REQUIRED_REPORT_DOCUMENT_PATHS,
    require_paths,
)


def log_feedback(
    report_document: dict[str, Any],
    persistence_client: Any,
) -> dict[str, Any]:
    """Write one feedback record per ranked metro.

    Args:
        report_document: Report payload produced by `generate_report`.
        persistence_client: Adapter exposing an `insert_feedback(row)` method.

    Returns:
        A structured status dictionary including inserted row IDs.

    Raises:
        ReportValidationError: If report_document is not a valid M9 report.
        FeedbackLoggingError: If persistence_client is missing required methods.
    """
    _validate_feedback_input(report_document, persistence_client)

    feedback_ids: list[str] = []
    rows_attempted = 0
    for rank, metro in enumerate(report_document["metros"], start=1):
        row = _build_feedback_row(report_document, metro, rank)
        rows_attempted += 1
        try:
            inserted = persistence_client.insert_feedback(row)
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "rows_attempted": rows_attempted,
                "inserted_count": len(feedback_ids),
                "feedback_ids": feedback_ids,
                "error": str(
                    FeedbackLoggingError(
                        "feedback logging failed",
                        rows_attempted=rows_attempted,
                        inserted_count=len(feedback_ids),
                    )
                ),
                "cause": str(exc),
            }
        feedback_ids.append(str(inserted or row["log_id"]))

    return {
        "success": True,
        "rows_attempted": rows_attempted,
        "inserted_count": len(feedback_ids),
        "feedback_ids": feedback_ids,
    }


def _validate_feedback_input(report_document: dict[str, Any], persistence_client: Any) -> None:
    if not isinstance(report_document, dict):
        raise ReportValidationError("report_document must be a dictionary")

    try:
        require_paths(report_document, REQUIRED_REPORT_DOCUMENT_PATHS)
    except ValueError as exc:
        raise ReportValidationError(str(exc)) from exc

    metros = report_document["metros"]
    if not isinstance(metros, list):
        raise ReportValidationError("report_document.metros must be a list")

    for idx, metro in enumerate(metros):
        if not isinstance(metro, dict):
            raise ReportValidationError(f"report_document.metros[{idx}] must be a dictionary")
        try:
            require_paths(metro, REQUIRED_METRO_ENTRY_PATHS)
        except ValueError as exc:
            raise ReportValidationError(f"report_document.metros[{idx}] {exc}") from exc

    if not hasattr(persistence_client, "insert_feedback"):
        raise FeedbackLoggingError("persistence_client must expose insert_feedback(row)")


def _build_feedback_row(
    report_document: dict[str, Any], metro: dict[str, Any], rank: int
) -> dict[str, Any]:
    return {
        "log_id": str(uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "context": {
            "report_id": report_document["report_id"],
            "feedback_log_id": report_document["meta"]["feedback_log_id"],
            "cbsa_code": metro["cbsa_code"],
            "cbsa_name": metro["cbsa_name"],
            "population": metro["population"],
        },
        "signals": deepcopy(metro["signals"]),
        "scores": deepcopy(metro["scores"]),
        "classification": {
            "serp_archetype": metro["serp_archetype"],
            "ai_exposure": metro["ai_exposure"],
            "difficulty_tier": metro["difficulty_tier"],
            "confidence": deepcopy(metro["confidence"]),
        },
        "recommendation_rank": rank,
        "outcome": _null_outcome(),
    }


def _null_outcome() -> dict[str, None]:
    return {
        "user_acted": None,
        "site_built": None,
        "ranking_achieved_days": None,
        "local_pack_entered_days": None,
        "first_lead_days": None,
        "monthly_lead_volume": None,
        "monthly_revenue": None,
        "user_satisfaction_rating": None,
        "outcome_reported_at": None,
    }
