"""Per-call cost logging for DataForSEO API usage."""

from __future__ import annotations

from typing import Any

from .types import CostRecord


class CostTracker:
    """Accumulates cost records in-memory for backward-compatible access.

    When an ``ObservationStore`` is configured on the ``DataForSEOClient``,
    cost is also persisted to the ``observations.cost_usd`` column.  The
    ``api_usage_log`` table is deprecated — cost writes now go to
    ``observations`` instead.  This in-memory tracker is retained so that
    ``client.cost_log`` and ``client.total_cost`` continue to work.
    """

    def __init__(self) -> None:
        self._records: list[CostRecord] = []

    def record(
        self,
        endpoint: str,
        task_id: str,
        cost: float,
        cached: bool,
        latency_ms: int,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        self._records.append(
            CostRecord(
                endpoint=endpoint,
                task_id=task_id,
                cost=cost,
                cached=cached,
                latency_ms=latency_ms,
                parameters=parameters or {},
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
