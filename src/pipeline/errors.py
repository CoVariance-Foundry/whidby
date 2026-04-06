"""Failure normalization helpers for M5 execution."""

from __future__ import annotations

from src.clients.dataforseo.types import APIResponse

from .types import CollectionTask, FailureRecord


class ReportValidationError(ValueError):
    """Raised when report generation input fails contract validation."""


class FeedbackLoggingError(RuntimeError):
    """Raised when feedback persistence fails."""

    def __init__(
        self,
        message: str,
        *,
        rows_attempted: int | None = None,
        inserted_count: int | None = None,
    ) -> None:
        super().__init__(message)
        self.rows_attempted = rows_attempted
        self.inserted_count = inserted_count

    def __str__(self) -> str:
        details: list[str] = [super().__str__()]
        if self.rows_attempted is not None:
            details.append(f"rows_attempted={self.rows_attempted}")
        if self.inserted_count is not None:
            details.append(f"inserted_count={self.inserted_count}")
        return " | ".join(details)


def failure_from_response(task: CollectionTask, response: APIResponse) -> FailureRecord:
    """Build a failure record from an API response."""
    return FailureRecord(
        task_id=task.task_id,
        task_type=task.task_type,
        metro_id=task.metro_id,
        message=response.error or "unknown API error",
        is_retryable=True,
    )


def failure_from_exception(task: CollectionTask, exc: Exception) -> FailureRecord:
    """Build a failure record from an exception."""
    return FailureRecord(
        task_id=task.task_id,
        task_type=task.task_type,
        metro_id=task.metro_id,
        message=str(exc),
        is_retryable=True,
    )

