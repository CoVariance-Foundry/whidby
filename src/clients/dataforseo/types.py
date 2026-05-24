"""Response types for DataForSEO client. (Algo Spec V1.1, §14)"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class APIResponse:
    """Standardised wrapper returned by every DataForSEOClient method."""

    status: str  # "ok" | "error"
    data: Any | None = None
    cost: float = 0.0
    cached: bool = False
    latency_ms: int = 0
    error: str | None = None
    task_id: str | None = None


@dataclass
class CostRecord:
    """Single DataForSEO call record with cost and private response lineage."""

    endpoint: str
    task_id: str
    cost: float
    cached: bool
    latency_ms: int
    parameters: dict[str, Any] = field(default_factory=dict)
    collected_at: str | None = None
    response_hash: str | None = None
    response_storage_uri: str | None = None
    response_payload: dict[str, Any] | None = None
