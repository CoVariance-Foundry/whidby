"""Request-to-task planner for M5 data collection."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice

from .task_graph import validate_task_graph
from .types import CollectionRequest, CollectionTask, KeywordDescriptor

MAX_VOLUME_BATCH_SIZE = 700


@dataclass(frozen=True)
class CollectionPlan:
    """Planned tasks for base and dependent phases."""

    base_tasks: list[CollectionTask]
    dependent_templates: list[CollectionTask]


def build_collection_plan(request: CollectionRequest) -> CollectionPlan:
    """Build phase-aware task plan from a validated request.

    Args:
        request: Collection request.

    Returns:
        A phase-aware collection plan.
    """
    base_tasks: list[CollectionTask] = []
    dependent_templates: list[CollectionTask] = []
    next_id = 1

    for metro in request.metros:
        metro_keywords = [item.keyword for item in request.keywords]
        eligible = [item for item in request.keywords if item.is_serp_eligible]
        keyword_batches = _chunked(metro_keywords, MAX_VOLUME_BATCH_SIZE)

        for batch_index, batch in enumerate(keyword_batches, start=1):
            task_id = f"task-{next_id:05d}"
            next_id += 1
            base_tasks.append(
                CollectionTask(
                    task_id=task_id,
                    metro_id=metro.metro_id,
                    task_type="keyword_volume",
                    payload={
                        "keywords": batch,
                        "location_code": metro.location_code,
                        "batch_index": batch_index,
                    },
                )
            )

        serp_task_ids: list[str] = []
        for keyword in eligible:
            task_id = f"task-{next_id:05d}"
            next_id += 1
            serp_task_ids.append(task_id)
            base_tasks.append(
                CollectionTask(
                    task_id=task_id,
                    metro_id=metro.metro_id,
                    task_type="serp_organic",
                    payload={
                        "keyword": keyword.keyword,
                        "location_code": metro.location_code,
                        "principal_city": metro.principal_city,
                    },
                )
            )

        if eligible:
            maps_keyword = _select_maps_keyword(eligible)
            task_id = f"task-{next_id:05d}"
            next_id += 1
            base_tasks.append(
                CollectionTask(
                    task_id=task_id,
                    metro_id=metro.metro_id,
                    task_type="serp_maps",
                    payload={"keyword": maps_keyword.keyword, "location_code": metro.location_code},
                )
            )

            first_serp_task = serp_task_ids[0] if serp_task_ids else task_id
            dependent_templates.extend(
                [
                    CollectionTask(
                        task_id=f"tmpl-{metro.metro_id}-backlinks",
                        metro_id=metro.metro_id,
                        task_type="backlinks",
                        payload={"source": "serp_organic"},
                        depends_on=(first_serp_task,),
                        dedup_key=f"{metro.metro_id}:backlinks",
                    ),
                    CollectionTask(
                        task_id=f"tmpl-{metro.metro_id}-lighthouse",
                        metro_id=metro.metro_id,
                        task_type="lighthouse",
                        payload={"source": "serp_organic"},
                        depends_on=(first_serp_task,),
                        dedup_key=f"{metro.metro_id}:lighthouse",
                    ),
                    CollectionTask(
                        task_id=f"tmpl-{metro.metro_id}-gbp",
                        metro_id=metro.metro_id,
                        task_type="gbp_info",
                        payload={"source": "serp_maps"},
                        depends_on=(task_id,),
                        dedup_key=f"{metro.metro_id}:gbp_info",
                    ),
                    CollectionTask(
                        task_id=f"tmpl-{metro.metro_id}-reviews",
                        metro_id=metro.metro_id,
                        task_type="google_reviews",
                        payload={"source": "serp_maps"},
                        depends_on=(task_id,),
                        dedup_key=f"{metro.metro_id}:google_reviews",
                    ),
                    CollectionTask(
                        task_id=f"tmpl-{metro.metro_id}-listings",
                        metro_id=metro.metro_id,
                        task_type="business_listings",
                        payload={"source": "serp_maps"},
                        depends_on=(task_id,),
                        dedup_key=f"{metro.metro_id}:business_listings",
                    ),
                ]
            )

    validate_task_graph(base_tasks)
    return CollectionPlan(base_tasks=base_tasks, dependent_templates=dependent_templates)


def _chunked(items: list[str], size: int) -> list[list[str]]:
    """Chunk items into fixed-size lists."""
    iterator = iter(items)
    chunks: list[list[str]] = []
    while True:
        chunk = list(islice(iterator, size))
        if not chunk:
            return chunks
        chunks.append(chunk)


def _select_maps_keyword(keywords: list[KeywordDescriptor]) -> KeywordDescriptor:
    """Select head keyword for maps pull."""
    tier_one = next((item for item in keywords if item.tier == 1), None)
    return tier_one or keywords[0]

