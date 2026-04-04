"""Response types for the LLM client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResult:
    """Wrapper for all LLM responses."""

    success: bool
    data: Any | None = None
    error: str | None = None
    tokens_used: int = 0
    cost_usd: float = 0.0
