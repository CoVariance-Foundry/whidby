"""Assemble raw per-metro collection outputs and metadata."""

from __future__ import annotations

from typing import Any

from .batch_executor import ExecutionState
from .types import (
    CollectionRequest,
    MetroCollectionResult,
    RawCollectionResult,
    RunMetadata,
)


def empty_metro_result(metro_id: str) -> MetroCollectionResult:
    """Create a metro result with explicit empty categories."""
    return MetroCollectionResult(metro_id=metro_id)


def assemble_raw_collection_result(
    request: CollectionRequest,
    state: ExecutionState,
    duration_seconds: float,
) -> RawCollectionResult:
    """Build final output contract from execution state.

    Args:
        request: Validated request.
        state: Execution state with task results and failures.
        duration_seconds: Wall clock run duration.

    Returns:
        Normalized `RawCollectionResult`.
    """
    metro_results = {metro.metro_id: empty_metro_result(metro.metro_id) for metro in request.metros}

    for task_id, results in state.task_results.items():
        metro_id = state.task_metros.get(task_id)
        category = state.task_categories.get(task_id)
        if not metro_id or not category:
            continue
        bucket = metro_results[metro_id]
        _append_category(bucket, category, results)

    metadata = RunMetadata(
        total_api_calls=state.total_api_calls,
        total_cost_usd=round(sum(state.task_costs.values()), 6),
        collection_time_seconds=duration_seconds,
        errors=state.failures,
    )
    return RawCollectionResult(metros=metro_results, meta=metadata)


def _append_category(
    metro_result: MetroCollectionResult,
    category: str,
    results: list[dict[str, Any]],
) -> None:
    """Append normalized records to category collection."""
    if category == "keyword_volume":
        metro_result.keyword_volume.extend(results)
    elif category == "serp_organic":
        metro_result.serp_organic.extend(results)
    elif category == "serp_maps":
        metro_result.serp_maps.extend(results)
    elif category == "business_listings":
        metro_result.business_listings.extend(results)
    elif category == "google_reviews":
        metro_result.google_reviews.extend(results)
    elif category == "gbp_info":
        metro_result.gbp_info.extend(results)
    elif category == "backlinks":
        metro_result.backlinks.extend(results)
    elif category == "lighthouse":
        metro_result.lighthouse.extend(results)

