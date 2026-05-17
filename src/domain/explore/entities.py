"""Typed read models for Explore Cities."""

from typing import Any, NotRequired, TypedDict


class ExploreCitySummary(TypedDict):
    cbsa_code: str
    cbsa_name: str
    state: str | None
    population: int | None
    population_class: str | None
    median_household_income_usd: int | None
    owner_occupancy_rate: NotRequired[float | None]
    median_age_years: NotRequired[float | None]
    business_density_per_1k: float | None
    establishment_growth_yoy: float | None
    growth_available: bool
    cached_services_count: int
    best_score: int | None
    score_system: str
    last_scored_at: NotRequired[Any | None]
    stale: bool | None
    cached_scores: list[dict[str, Any]]


class ExplorePageResult(TypedDict):
    cities: list[ExploreCitySummary]
    next_cursor: str | None
    growth_available: bool
    service_filter: str | None
