"""Top-level M5 orchestration entrypoint."""

from __future__ import annotations

import logging
import time
from typing import Any

from .batch_executor import execute_collection_plan
from .collection_plan import build_collection_plan
from .result_assembler import assemble_raw_collection_result
from .types import RawCollectionResult, build_collection_request

logger = logging.getLogger(__name__)


async def collect_data(
    keywords: list[dict[str, Any]],
    metros: list[dict[str, Any]],
    strategy_profile: str,
    client: Any,
) -> RawCollectionResult:
    """Collect M5 raw data for all requested metros.

    Args:
        keywords: Expanded keyword descriptors from M4.
        metros: Metro records from M1.
        strategy_profile: Strategy profile string.
        client: DataForSEO client-compatible object.

    Returns:
        Raw collection result with per-metro categories and run metadata.

    Raises:
        ValueError: If request validation fails.
    """
    started = time.monotonic()
    request = build_collection_request(
        keywords=keywords,
        metros=metros,
        strategy_profile=strategy_profile,
    )
    plan = build_collection_plan(request)
    logger.info(
        "M5 collection plan: base_tasks=%d dependent_templates=%d",
        len(plan.base_tasks), len(plan.dependent_templates),
    )
    state = await execute_collection_plan(plan, request, client)
    elapsed = time.monotonic() - started

    failure_types: dict[str, int] = {}
    for f in state.failures:
        key = getattr(f, "task_type", "unknown")
        failure_types[key] = failure_types.get(key, 0) + 1
    logger.info(
        "M5 collect_data DONE api_calls=%d failures=%d failure_types=%s "
        "elapsed_ms=%d",
        state.total_api_calls, len(state.failures), failure_types,
        int(elapsed * 1000),
    )

    return assemble_raw_collection_result(request, state, elapsed)

