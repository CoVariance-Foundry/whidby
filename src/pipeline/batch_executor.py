"""Dependency-aware executor for planned collection tasks."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from src.clients.dataforseo.types import APIResponse

from .collection_plan import CollectionPlan
from .errors import failure_from_exception, failure_from_response
from .task_graph import dependency_levels, validate_task_graph
from .types import CollectionRequest, CollectionTask, FailureRecord


@dataclass
class ExecutionState:
    """Mutable execution state consumed by the result assembler."""

    task_results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    task_costs: dict[str, float] = field(default_factory=dict)
    task_categories: dict[str, str] = field(default_factory=dict)
    task_metros: dict[str, str] = field(default_factory=dict)
    total_api_calls: int = 0
    failures: list[FailureRecord] = field(default_factory=list)
    seen_dedup_keys: set[str] = field(default_factory=set)


async def execute_collection_plan(
    plan: CollectionPlan,
    request: CollectionRequest,
    client: Any,
) -> ExecutionState:
    """Execute plan in deterministic phases.

    Args:
        plan: Planned task batches.
        request: Validated request context.
        client: DataForSEO client-like object.

    Returns:
        Execution state with task outcomes.
    """
    state = ExecutionState()
    await _execute_tasks(plan.base_tasks, client, state)
    dependent_tasks = _materialize_dependent_tasks(plan, request, state)
    await _execute_tasks(dependent_tasks, client, state)
    return state


def _materialize_dependent_tasks(
    plan: CollectionPlan,
    request: CollectionRequest,
    state: ExecutionState,
) -> list[CollectionTask]:
    """Build concrete dependent tasks from phase-one outputs."""
    tasks: list[CollectionTask] = []
    metros = {metro.metro_id: metro for metro in request.metros}
    next_id = 1

    for template in plan.dependent_templates:
        if template.dedup_key and template.dedup_key in state.seen_dedup_keys:
            continue

        metro = metros[template.metro_id]
        payload = dict(template.payload)
        if template.task_type in {"google_reviews", "gbp_info", "business_listings"}:
            payload.update(
                {
                    "keyword": _first_maps_keyword_for_metro(template.metro_id, state) or "",
                    "location_code": metro.location_code,
                }
            )
        elif template.task_type == "backlinks":
            payload.update({"target": _first_top_domain_for_metro(template.metro_id, state) or ""})
        elif template.task_type == "lighthouse":
            payload.update({"url": _first_top_url_for_metro(template.metro_id, state) or ""})

        tasks.append(
            CollectionTask(
                task_id=f"dep-{next_id:05d}",
                metro_id=template.metro_id,
                task_type=template.task_type,
                payload=payload,
                depends_on=(),
                dedup_key=template.dedup_key,
            )
        )
        if template.dedup_key:
            state.seen_dedup_keys.add(template.dedup_key)
        next_id += 1

    return tasks


async def _execute_tasks(
    tasks: list[CollectionTask],
    client: Any,
    state: ExecutionState,
) -> None:
    """Execute tasks with dependency-safe parallelism."""
    if not tasks:
        return
    validate_task_graph(tasks)
    for level in dependency_levels(tasks):
        await asyncio.gather(*[_run_task(task, client, state) for task in level])


async def _run_task(task: CollectionTask, client: Any, state: ExecutionState) -> None:
    """Run one task and capture result or failure."""
    response: APIResponse
    try:
        response = await _dispatch_task(task, client)
    except Exception as exc:  # pragma: no cover - defensive path
        state.failures.append(failure_from_exception(task, exc))
        return

    state.total_api_calls += 1
    state.task_categories[task.task_id] = task.task_type
    state.task_metros[task.task_id] = task.metro_id

    if response.status != "ok":
        state.failures.append(failure_from_response(task, response))
        return

    result_data = response.data if isinstance(response.data, list) else [response.data]
    normalized = [item for item in result_data if isinstance(item, dict)]
    state.task_results[task.task_id] = normalized
    state.task_costs[task.task_id] = response.cost


async def _dispatch_task(task: CollectionTask, client: Any) -> APIResponse:
    """Dispatch one task through the DataForSEO client boundary."""
    payload = task.payload
    if task.task_type == "keyword_volume":
        return await client.keyword_volume(payload["keywords"], payload["location_code"])
    if task.task_type == "serp_organic":
        return await client.serp_organic(payload["keyword"], payload["location_code"])
    if task.task_type == "serp_maps":
        return await client.serp_maps(payload["keyword"], payload["location_code"])
    if task.task_type == "business_listings":
        category = payload.get("keyword") or "local business"
        return await client.business_listings(category, payload["location_code"])
    if task.task_type == "google_reviews":
        return await client.google_reviews(payload["keyword"], payload["location_code"])
    if task.task_type == "gbp_info":
        return await client.google_my_business_info(payload["keyword"], payload["location_code"])
    if task.task_type == "backlinks":
        return await client.backlinks_summary(payload["target"])
    if task.task_type == "lighthouse":
        return await client.lighthouse(payload["url"])
    raise ValueError(f"unsupported task type: {task.task_type}")


def _first_top_domain_for_metro(metro_id: str, state: ExecutionState) -> str | None:
    """Extract first organic result domain for metro."""
    for task_id, category in state.task_categories.items():
        if category != "serp_organic":
            continue
        if not _task_matches_metro(task_id, metro_id, state):
            continue
        for result in state.task_results.get(task_id, []):
            for item in result.get("items", []):
                domain = item.get("domain")
                if domain:
                    return str(domain)
    return None


def _first_top_url_for_metro(metro_id: str, state: ExecutionState) -> str | None:
    """Extract first organic result URL for metro."""
    for task_id, category in state.task_categories.items():
        if category != "serp_organic":
            continue
        if not _task_matches_metro(task_id, metro_id, state):
            continue
        for result in state.task_results.get(task_id, []):
            for item in result.get("items", []):
                url = item.get("url")
                if url:
                    return str(url)
    return None


def _first_maps_keyword_for_metro(metro_id: str, state: ExecutionState) -> str | None:
    """Extract first maps keyword for metro."""
    for task_id, category in state.task_categories.items():
        if category != "serp_maps":
            continue
        if not _task_matches_metro(task_id, metro_id, state):
            continue
        for result in state.task_results.get(task_id, []):
            keyword = result.get("keyword")
            if keyword:
                return str(keyword)
    return None


def _task_matches_metro(task_id: str, metro_id: str, state: ExecutionState) -> bool:
    """Check if a task result belongs to a metro via stored pseudo marker."""
    return state.task_metros.get(task_id) == metro_id

