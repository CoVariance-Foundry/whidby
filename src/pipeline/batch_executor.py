"""Dependency-aware executor for planned collection tasks."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlunsplit, urlsplit

from src.clients.dataforseo.types import APIResponse
from src.pipeline.domain_classifier import is_aggregator, normalize_domain

from .collection_plan import CollectionPlan
from .errors import failure_from_exception, failure_from_response
from .task_graph import dependency_levels, validate_task_graph
from .types import CollectionRequest, CollectionTask, FailureRecord

logger = logging.getLogger(__name__)


@dataclass
class ExecutionState:
    """Mutable execution state consumed by the result assembler."""

    task_results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    task_costs: dict[str, float] = field(default_factory=dict)
    task_categories: dict[str, str] = field(default_factory=dict)
    task_metros: dict[str, str] = field(default_factory=dict)
    task_payloads: dict[str, dict[str, Any]] = field(default_factory=dict)
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

    base_start = time.monotonic()
    await _execute_tasks(plan.base_tasks, client, state)
    base_ms = int((time.monotonic() - base_start) * 1000)
    logger.info("M5 base phase DONE tasks=%d duration_ms=%d", len(plan.base_tasks), base_ms)

    dependent_tasks = _materialize_dependent_tasks(plan, request, state)

    dep_start = time.monotonic()
    await _execute_tasks(dependent_tasks, client, state)
    dep_ms = int((time.monotonic() - dep_start) * 1000)
    logger.info("M5 dependent phase DONE tasks=%d duration_ms=%d", len(dependent_tasks), dep_ms)

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
        if template.task_type in {"google_reviews", "gbp_info"}:
            profile = _best_maps_profile_for_metro(template.metro_id, state)
            if profile is not None:
                payload = dict(template.payload)
                query = profile["query"]
                if template.task_type == "gbp_info":
                    query = (
                        profile.get("business_name")
                        or profile.get("source_query")
                        or profile["query"]
                    )
                payload.update(
                    {
                        "keyword": query,
                        "location_code": metro.location_code,
                        "cid": profile.get("cid"),
                        "place_id": profile.get("place_id"),
                        "business_name": profile.get("business_name"),
                        "source_query": profile.get("source_query"),
                        "preferred_identifier_mode": profile["identifier_mode"],
                        "review_retrieval_mode": (
                            profile["identifier_mode"]
                            if template.task_type == "google_reviews"
                            else None
                        ),
                        "gbp_retrieval_mode": (
                            "keyword" if template.task_type == "gbp_info" else None
                        ),
                    }
                )
                concrete_key = template.dedup_key
                if concrete_key and concrete_key in state.seen_dedup_keys:
                    continue
                tasks.append(
                    CollectionTask(
                        task_id=f"dep-{next_id:05d}",
                        metro_id=template.metro_id,
                        task_type=template.task_type,
                        payload=payload,
                        depends_on=(),
                        dedup_key=concrete_key,
                    )
                )
                if concrete_key:
                    state.seen_dedup_keys.add(concrete_key)
                next_id += 1
        elif template.task_type == "business_listings":
            payload = dict(template.payload)
            payload.update(
                {
                    "keyword": _first_maps_keyword_for_metro(template.metro_id, state) or "",
                    "location_code": metro.location_code,
                }
            )
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
            next_id += 1
        elif template.task_type == "backlinks":
            for domain in _top_domains_for_metro(template.metro_id, plan, state, limit=5):
                concrete_key = f"{template.dedup_key}:{domain}" if template.dedup_key else None
                if concrete_key and concrete_key in state.seen_dedup_keys:
                    continue
                payload = dict(template.payload)
                payload.update({"target": domain})
                tasks.append(
                    CollectionTask(
                        task_id=f"dep-{next_id:05d}",
                        metro_id=template.metro_id,
                        task_type=template.task_type,
                        payload=payload,
                        depends_on=(),
                        dedup_key=concrete_key,
                    )
                )
                if concrete_key:
                    state.seen_dedup_keys.add(concrete_key)
                next_id += 1
        elif template.task_type == "lighthouse":
            for url in _top_urls_for_metro(template.metro_id, plan, state, limit=5):
                url_key = _canonical_lighthouse_url_key(url)
                concrete_key = f"{template.dedup_key}:{url_key}" if template.dedup_key else None
                if concrete_key and concrete_key in state.seen_dedup_keys:
                    continue
                payload = dict(template.payload)
                payload.update({"url": url})
                tasks.append(
                    CollectionTask(
                        task_id=f"dep-{next_id:05d}",
                        metro_id=template.metro_id,
                        task_type=template.task_type,
                        payload=payload,
                        depends_on=(),
                        dedup_key=concrete_key,
                    )
                )
                if concrete_key:
                    state.seen_dedup_keys.add(concrete_key)
                next_id += 1

        if template.dedup_key:
            state.seen_dedup_keys.add(template.dedup_key)

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
    for level_idx, level in enumerate(dependency_levels(tasks)):
        level_start = time.monotonic()
        task_types = {}
        for t in level:
            task_types[t.task_type] = task_types.get(t.task_type, 0) + 1
        await asyncio.gather(*[_run_task(task, client, state) for task in level])
        level_ms = int((time.monotonic() - level_start) * 1000)
        logger.info(
            "M5 exec level=%d tasks=%d types=%s duration_ms=%d",
            level_idx, len(level), task_types, level_ms,
        )


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
    state.task_payloads[task.task_id] = dict(task.payload)

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
        mode = payload.get("review_retrieval_mode")
        return await client.google_reviews(
            payload.get("keyword"),
            payload["location_code"],
            cid=payload.get("cid") if mode == "cid" else None,
            place_id=payload.get("place_id") if mode == "place_id" else None,
        )
    if task.task_type == "gbp_info":
        return await client.google_my_business_info(payload["keyword"], payload["location_code"])
    if task.task_type == "backlinks":
        return await client.backlinks_summary(payload["target"])
    if task.task_type == "lighthouse":
        return await client.lighthouse(payload["url"])
    raise ValueError(f"unsupported task type: {task.task_type}")


def _top_domains_for_metro(
    metro_id: str,
    plan: CollectionPlan,
    state: ExecutionState,
    *,
    limit: int,
) -> list[str]:
    """Extract unique organic result domains for metro in planned SERP order."""
    domains: list[str] = []
    seen: set[str] = set()
    for task_id in _organic_task_ids_for_metro(metro_id, plan, state):
        for result in state.task_results.get(task_id, []):
            for item in result.get("items", []):
                domain = str(item.get("domain") or "").strip()
                if not domain:
                    continue
                key = normalize_domain(domain)
                if not key:
                    continue
                if is_aggregator(key):
                    continue
                if key in seen:
                    continue
                domains.append(key)
                seen.add(key)
                if len(domains) >= limit:
                    return domains
    return domains


def _top_urls_for_metro(
    metro_id: str,
    plan: CollectionPlan,
    state: ExecutionState,
    *,
    limit: int,
) -> list[str]:
    """Extract unique organic result URLs for metro in planned SERP order."""
    urls: list[str] = []
    seen: set[str] = set()
    for task_id in _organic_task_ids_for_metro(metro_id, plan, state):
        for result in state.task_results.get(task_id, []):
            for item in result.get("items", []):
                url = str(item.get("url") or "").strip()
                if not url:
                    continue
                competitor_domain = str(item.get("domain") or url).strip()
                if is_aggregator(competitor_domain):
                    continue
                key = _canonical_lighthouse_url_key(url)
                if key in seen:
                    continue
                urls.append(url)
                seen.add(key)
                if len(urls) >= limit:
                    return urls
    return urls


def _canonical_lighthouse_url_key(url: str) -> str:
    """Build a stable dedupe key while preserving original URLs for paid calls."""
    parsed = urlsplit(url)
    host = normalize_domain(url)
    path = parsed.path.rstrip("/")
    return urlunsplit(("", host, path, parsed.query, ""))


def _organic_task_ids_for_metro(
    metro_id: str,
    plan: CollectionPlan,
    state: ExecutionState,
) -> list[str]:
    """Return completed organic task ids in collection-plan order."""
    return [
        task.task_id
        for task in plan.base_tasks
        if task.task_type == "serp_organic"
        and task.metro_id == metro_id
        and state.task_categories.get(task.task_id) == "serp_organic"
    ]


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


def _best_maps_profile_for_metro(
    metro_id: str,
    state: ExecutionState,
) -> dict[str, str | None] | None:
    profiles = _top_maps_profiles_for_metro(metro_id, state, limit=3)
    return profiles[0] if profiles else None


def _top_maps_profiles_for_metro(
    metro_id: str,
    state: ExecutionState,
    *,
    limit: int,
) -> list[dict[str, str | None]]:
    profiles: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for task_id, category in state.task_categories.items():
        if category != "serp_maps" or not _task_matches_metro(task_id, metro_id, state):
            continue
        for result in state.task_results.get(task_id, []):
            source_query = _text(result.get("keyword"))
            items = result.get("items") if isinstance(result.get("items"), list) else []
            if not items and source_query:
                dedup_key = f"keyword:{source_query.lower()}"
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    profiles.append(
                        {
                            "cid": None,
                            "place_id": None,
                            "business_name": None,
                            "source_query": source_query,
                            "identifier_mode": "keyword",
                            "query": source_query,
                            "dedup_key": dedup_key,
                        }
                    )
                    if len(profiles) >= limit:
                        return profiles
            for item in _top_ranked_items(items, limit=limit):
                cid = _text(item.get("cid"))
                place_id = _text(item.get("place_id"))
                business_name = _text(
                    item.get("title") or item.get("name") or item.get("business_name")
                )
                if cid:
                    identifier_mode = "cid"
                    query = cid
                    dedup_key = f"cid:{cid}"
                elif place_id:
                    identifier_mode = "place_id"
                    query = place_id
                    dedup_key = f"place_id:{place_id}"
                elif business_name:
                    identifier_mode = "title"
                    query = business_name
                    dedup_key = f"title:{business_name.lower()}"
                else:
                    identifier_mode = "keyword"
                    query = source_query or ""
                    dedup_key = f"keyword:{query.lower()}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                profiles.append(
                    {
                        "cid": cid,
                        "place_id": place_id,
                        "business_name": business_name,
                        "source_query": source_query,
                        "identifier_mode": identifier_mode,
                        "query": query,
                        "dedup_key": dedup_key,
                    }
                )
                if len(profiles) >= limit:
                    return profiles
    return profiles


def _top_ranked_items(items: list[Any], *, limit: int) -> list[dict[str, Any]]:
    rows = [item for item in items if isinstance(item, dict)]
    if any(_rank_value(row) is not None for row in rows):
        rows = [
            row
            for _, row in sorted(
                enumerate(rows),
                key=lambda pair: (
                    _rank_value(pair[1]) is None,
                    _rank_value(pair[1]) if _rank_value(pair[1]) is not None else 0,
                    pair[0],
                ),
            )
        ]
    return rows[:limit]


def _rank_value(row: dict[str, Any]) -> int | None:
    for rank_field in ("rank_group", "rank", "position", "rank_absolute"):
        value = row.get(rank_field)
        try:
            rank = int(value)
        except (TypeError, ValueError):
            continue
        if rank > 0:
            return rank
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _task_matches_metro(task_id: str, metro_id: str, state: ExecutionState) -> bool:
    """Check if a task result belongs to a metro via stored pseudo marker."""
    return state.task_metros.get(task_id) == metro_id
