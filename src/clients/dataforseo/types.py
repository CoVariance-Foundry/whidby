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
    """Single row written to the api_usage_log table."""

    endpoint: str
    task_id: str
    cost: float
    cached: bool
    latency_ms: int
    parameters: dict[str, Any] = field(default_factory=dict)
