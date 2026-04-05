"""Failure normalization helpers for M5 execution."""

from __future__ import annotations

from src.clients.dataforseo.types import APIResponse

from .types import CollectionTask, FailureRecord


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

