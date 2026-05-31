"""Per-call cost logging for DataForSEO API usage."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
import contextvars
import logging
from typing import Any

from .types import CostRecord

logger = logging.getLogger(__name__)
_ACTIVE_COLLECTION_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "dataforseo_collection_context_id",
    default=None,
)


class CostTracker:
    """Accumulates cost records in-memory and can flush to Supabase api_usage_log."""

    def __init__(self) -> None:
        self._records: list[CostRecord] = []

    @contextmanager
    def capture_context(self, context_id: str) -> Iterator[None]:
        token = _ACTIVE_COLLECTION_CONTEXT.set(context_id)
        try:
            yield
        finally:
            _ACTIVE_COLLECTION_CONTEXT.reset(token)

    def record(
        self,
        endpoint: str,
        task_id: str,
        cost: float,
        cached: bool,
        latency_ms: int,
        parameters: dict[str, Any] | None = None,
        *,
        collected_at: str | None = None,
        collection_context_id: str | None = None,
        response_hash: str | None = None,
        response_storage_uri: str | None = None,
        response_payload: dict[str, Any] | None = None,
    ) -> None:
        self._records.append(
            CostRecord(
                endpoint=endpoint,
                task_id=task_id,
                cost=cost,
                cached=cached,
                latency_ms=latency_ms,
                parameters=parameters or {},
                collected_at=collected_at,
                collection_context_id=collection_context_id
                if collection_context_id is not None
                else _ACTIVE_COLLECTION_CONTEXT.get(),
                response_hash=response_hash,
                response_storage_uri=response_storage_uri,
                response_payload=response_payload,
            )
        )

    @property
    def records(self) -> list[CostRecord]:
        return list(self._records)

    @property
    def total_cost(self) -> float:
        return sum(r.cost for r in self._records)

    @property
    def total_calls(self) -> int:
        return len(self._records)

    @property
    def cached_calls(self) -> int:
        return sum(1 for r in self._records if r.cached)

    def cost_by_endpoint(self) -> dict[str, dict[str, Any]]:
        """Aggregate cost and call counts grouped by endpoint path.

        Returns a dict like::

            {"serp/google/organic/task_post": {"calls": 6, "cost": 0.0036, "cached": 2}}
        """
        groups: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"calls": 0, "cost": 0.0, "cached": 0}
        )
        for r in self._records:
            g = groups[r.endpoint]
            g["calls"] += 1
            g["cost"] += r.cost
            if r.cached:
                g["cached"] += 1
        return dict(groups)

    def flush_to_supabase(self, report_id: str, *, client: Any = None) -> int:
        """Batch-insert all accumulated records into the ``api_usage_log`` table.

        Args:
            report_id: UUID of the report these calls belong to.
            client: Supabase client instance. If *None*, one is created from env vars.

        Returns:
            Number of rows inserted.
        """
        if not self._records:
            return 0

        if client is None:
            import os

            from supabase import create_client

            url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            if not url or not key:
                logger.warning("Cannot flush DFS cost log — missing Supabase env vars")
                return 0
            client = create_client(url, key)

        rows = []
        for r in self._records:
            rows.append(
                {
                    "endpoint": r.endpoint,
                    "task_id": r.task_id,
                    "cost": r.cost,
                    "cached": r.cached,
                    "latency_ms": r.latency_ms,
                    "parameters": r.parameters,
                    "report_id": report_id,
                }
            )

        client.table("api_usage_log").insert(rows).execute()
        count = len(rows)
        logger.info("Flushed %d DFS cost records to api_usage_log for report %s", count, report_id)
        return count
