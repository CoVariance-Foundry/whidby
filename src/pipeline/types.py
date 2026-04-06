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


@dataclass(frozen=True)
class ReportMeta:
    """Meta block for final report output."""

    total_api_calls: int
    total_cost_usd: float
    processing_time_seconds: float
    feedback_log_id: str | None = None


@dataclass(frozen=True)
class ReportOutcome:
    """Nullable delayed outcome fields for feedback records."""

    user_acted: bool | None = None
    site_built: bool | None = None
    ranking_achieved_days: int | None = None
    local_pack_entered_days: int | None = None
    first_lead_days: int | None = None
    monthly_lead_volume: float | None = None
    monthly_revenue: float | None = None
    user_satisfaction_rating: int | None = None
    outcome_reported_at: str | None = None


REQUIRED_REPORT_INPUT_PATHS: tuple[str, ...] = (
    "run_id",
    "input",
    "keyword_expansion",
    "metros",
    "meta.total_api_calls",
    "meta.total_cost_usd",
    "meta.processing_time_seconds",
)

REQUIRED_METRO_ENTRY_PATHS: tuple[str, ...] = (
    "cbsa_code",
    "cbsa_name",
    "population",
    "scores.demand",
    "scores.organic_competition",
    "scores.local_competition",
    "scores.monetization",
    "scores.ai_resilience",
    "scores.opportunity",
    "confidence",
    "serp_archetype",
    "ai_exposure",
    "difficulty_tier",
    "signals",
    "guidance",
)

REQUIRED_REPORT_DOCUMENT_PATHS: tuple[str, ...] = (
    "report_id",
    "generated_at",
    "spec_version",
    "input",
    "keyword_expansion",
    "metros",
    "meta.total_api_calls",
    "meta.total_cost_usd",
    "meta.processing_time_seconds",
    "meta.feedback_log_id",
)


def require_paths(payload: dict[str, Any], paths: tuple[str, ...]) -> None:
    """Validate that all dotted paths exist and are non-null.

    Args:
        payload: Dictionary to validate.
        paths: Dotted field paths to require.

    Raises:
        ValueError: If a required path is missing or null.
    """
    for path in paths:
        current: Any = payload
        for segment in path.split("."):
            if not isinstance(current, dict) or segment not in current:
                raise ValueError(f"missing required field: {path}")
            current = current[segment]
        if current is None:
            raise ValueError(f"required field is null: {path}")


def coerce_numeric(value: Any, path: str, target_type: type) -> int | float:
    """Coerce a value to int or float with a path-specific error message.

    Args:
        value: Value to coerce.
        path: Dotted field path for error messages.
        target_type: Target numeric type (int or float).

    Returns:
        Coerced numeric value.

    Raises:
        ValueError: If the value cannot be coerced.
    """
    try:
        return target_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid numeric value at {path}: {exc}") from exc

