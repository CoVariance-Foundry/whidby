"""Generate the final M9 report document from M4-M8 outputs."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .errors import ReportValidationError
from .types import (
    REQUIRED_METRO_ENTRY_PATHS,
    REQUIRED_REPORT_INPUT_PATHS,
    coerce_numeric,
    require_paths,
)


def generate_report(run_input: dict[str, Any], *, spec_version: str = "1.1") -> dict[str, Any]:
    """Build the final report document for a single run.

    Args:
        run_input: Consolidated run payload from previous pipeline stages.
        spec_version: Report schema version.

    Returns:
        A report dictionary conforming to the M9 contract.

    Raises:
        ReportValidationError: If required fields are missing or malformed.
    """
    if not isinstance(run_input, dict):
        raise ReportValidationError("run_input must be a dictionary")

    try:
        require_paths(run_input, REQUIRED_REPORT_INPUT_PATHS)
    except ValueError as exc:
        raise ReportValidationError(str(exc)) from exc

    metros = run_input["metros"]
    if not isinstance(metros, list):
        raise ReportValidationError("metros must be a list")

    normalized_metros = [_validate_and_copy_metro(metro, idx) for idx, metro in enumerate(metros)]
    sorted_metros = sorted(
        normalized_metros,
        key=lambda item: (
            -float(item["scores"]["opportunity"]),
            str(item["cbsa_code"]),
            str(item["cbsa_name"]),
        ),
    )

    feedback_log_id = str(uuid4())

    try:
        meta = deepcopy(run_input["meta"])
        meta["total_api_calls"] = coerce_numeric(meta["total_api_calls"], "meta.total_api_calls", int)
        meta["total_cost_usd"] = coerce_numeric(meta["total_cost_usd"], "meta.total_cost_usd", float)
        meta["processing_time_seconds"] = coerce_numeric(
            meta["processing_time_seconds"], "meta.processing_time_seconds", float
        )
        meta["feedback_log_id"] = feedback_log_id
    except ValueError as exc:
        raise ReportValidationError(str(exc)) from exc

    return {
        "report_id": str(uuid4()),
        "generated_at": datetime.now(UTC).isoformat(),
        "spec_version": spec_version,
        "input": deepcopy(run_input["input"]),
        "keyword_expansion": deepcopy(run_input["keyword_expansion"]),
        "metros": sorted_metros,
        "meta": meta,
    }


def _validate_and_copy_metro(metro: dict[str, Any], index: int) -> dict[str, Any]:
    if not isinstance(metro, dict):
        raise ReportValidationError(f"metros[{index}] must be a dictionary")

    try:
        require_paths(metro, REQUIRED_METRO_ENTRY_PATHS)
    except ValueError as exc:
        raise ReportValidationError(f"metros[{index}] {exc}") from exc

    copied = deepcopy(metro)
    try:
        copied["scores"]["opportunity"] = coerce_numeric(
            copied["scores"]["opportunity"], f"metros[{index}].scores.opportunity", float
        )
    except ValueError as exc:
        raise ReportValidationError(str(exc)) from exc

    return copied
