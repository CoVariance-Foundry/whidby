"""Dependency utilities for collection tasks."""

from __future__ import annotations

from collections import defaultdict, deque

from .types import CollectionTask


def validate_task_graph(tasks: list[CollectionTask]) -> None:
    """Validate that task dependencies form an acyclic graph.

    Args:
        tasks: Planned tasks.

    Raises:
        ValueError: If a dependency references a missing task or cycle exists.
    """
    by_id = {task.task_id: task for task in tasks}
    for task in tasks:
        for dep in task.depends_on:
            if dep not in by_id:
                raise ValueError(f"task {task.task_id} depends on unknown task {dep}")

    _ = dependency_levels(tasks)  # Raises on cycle.


def dependency_levels(tasks: list[CollectionTask]) -> list[list[CollectionTask]]:
    """Return topological levels for dependency-aware execution."""
    by_id = {task.task_id: task for task in tasks}
    indegree: dict[str, int] = {task.task_id: 0 for task in tasks}
    outgoing: dict[str, list[str]] = defaultdict(list)

    for task in tasks:
        for dep in task.depends_on:
            indegree[task.task_id] += 1
            outgoing[dep].append(task.task_id)

    queue = deque([task_id for task_id, degree in indegree.items() if degree == 0])
    levels: list[list[CollectionTask]] = []

    while queue:
        current_ids = list(queue)
        queue.clear()
        levels.append([by_id[task_id] for task_id in current_ids])

        for task_id in current_ids:
            for child in outgoing[task_id]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)

    visited = sum(len(level) for level in levels)
    if visited != len(tasks):
        raise ValueError("task dependency graph contains a cycle")

    return levels

