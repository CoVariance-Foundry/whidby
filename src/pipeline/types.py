"""Core data types and validation helpers for M5 collection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


TaskType = Literal[
    "keyword_volume",
    "serp_organic",
    "serp_maps",
    "business_listings",
    "google_reviews",
    "gbp_info",
    "backlinks",
    "lighthouse",
]


@dataclass(frozen=True)
class KeywordDescriptor:
    """Single keyword with metadata used to plan collection."""

    keyword: str
    tier: int
    intent: str

    @property
    def is_serp_eligible(self) -> bool:
        """Return whether this keyword should receive SERP collection."""
        return self.tier in {1, 2} and self.intent.lower() in {"transactional", "commercial"}


@dataclass(frozen=True)
class MetroInput:
    """Metro and location context for API targeting."""

    metro_id: str
    location_code: int
    principal_city: str | None = None


@dataclass(frozen=True)
class CollectionRequest:
    """Validated request for one M5 collection run."""

    keywords: list[KeywordDescriptor]
    metros: list[MetroInput]
    strategy_profile: str


@dataclass(frozen=True)
class CollectionTask:
    """Planned execution unit."""

    task_id: str
    metro_id: str
    task_type: TaskType
    payload: dict[str, Any]
    depends_on: tuple[str, ...] = ()
    dedup_key: str | None = None


@dataclass(frozen=True)
class FailureRecord:
    """Structured failure emitted by execution."""

    task_id: str
    task_type: str
    metro_id: str
    message: str
    is_retryable: bool = True


@dataclass(frozen=True)
class RunMetadata:
    """Top-level run metadata."""

    total_api_calls: int
    total_cost_usd: float
    collection_time_seconds: float
    errors: list[FailureRecord] = field(default_factory=list)


@dataclass(frozen=True)
class MetroCollectionResult:
    """Required raw categories for a metro."""

    metro_id: str
    serp_organic: list[dict[str, Any]] = field(default_factory=list)
    serp_maps: list[dict[str, Any]] = field(default_factory=list)
    keyword_volume: list[dict[str, Any]] = field(default_factory=list)
    business_listings: list[dict[str, Any]] = field(default_factory=list)
    google_reviews: list[dict[str, Any]] = field(default_factory=list)
    gbp_info: list[dict[str, Any]] = field(default_factory=list)
    backlinks: list[dict[str, Any]] = field(default_factory=list)
    lighthouse: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class RawCollectionResult:
    """M5 output contract consumed by downstream modules."""

    metros: dict[str, MetroCollectionResult]
    meta: RunMetadata


def build_collection_request(
    keywords: list[dict[str, Any]],
    metros: list[dict[str, Any]],
    strategy_profile: str,
) -> CollectionRequest:
    """Create validated collection request.

    Args:
        keywords: Keyword descriptors with keyword/tier/intent.
        metros: Metro descriptors with metro_id/location_code.
        strategy_profile: Strategy profile name.

    Returns:
        A validated `CollectionRequest`.

    Raises:
        ValueError: If required fields are missing or malformed.
    """
    if not keywords:
        raise ValueError("keywords must be non-empty")
    if not metros:
        raise ValueError("metros must be non-empty")

    keyword_models: list[KeywordDescriptor] = []
    for item in keywords:
        keyword = str(item.get("keyword", "")).strip()
        intent = str(item.get("intent", "")).strip().lower()
        tier = int(item.get("tier", 0))
        if not keyword:
            raise ValueError("keyword must be non-empty")
        if not intent:
            raise ValueError("intent is required for each keyword")
        if tier <= 0:
            raise ValueError("tier must be > 0")
        keyword_models.append(KeywordDescriptor(keyword=keyword, tier=tier, intent=intent))

    metro_models: list[MetroInput] = []
    seen_metros: set[str] = set()
    for item in metros:
        metro_id = str(item.get("metro_id", "")).strip()
        if not metro_id:
            raise ValueError("metro_id is required for each metro")
        if metro_id in seen_metros:
            raise ValueError(f"duplicate metro_id found: {metro_id}")
        seen_metros.add(metro_id)
        location_code = int(item.get("location_code", 0))
        if location_code <= 0:
            raise ValueError(f"location_code must be > 0 for metro {metro_id}")
        metro_models.append(
            MetroInput(
                metro_id=metro_id,
                location_code=location_code,
                principal_city=item.get("principal_city"),
            )
        )

    return CollectionRequest(
        keywords=keyword_models,
        metros=metro_models,
        strategy_profile=strategy_profile,
    )

