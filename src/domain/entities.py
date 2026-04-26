from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class City:
    city_id: str
    name: str
    state: str | None = None
    population: int | None = None
    median_income: float | None = None
    homeownership_rate: float | None = None
    housing_age_median: float | None = None
    business_density: dict[str, Any] = field(default_factory=dict)
    broadband_penetration: float | None = None
    growth_rate: float | None = None
    cbsa_code: str | None = None
    dataforseo_location_codes: list[int] = field(default_factory=list)
    principal_cities: list[str] = field(default_factory=list)
    archetype: str | None = None
    demographics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Service:
    service_id: str
    name: str
    naics_code: str | None = None
    acv_estimate: float | None = None
    seasonality: SeasonalityCurve | None = None
    fulfillment_type: str = "physical"
    ai_resilience_baseline: float | None = None
    keyword_universe: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SeasonalityCurve:
    monthly_index: dict[int, float]
    peak_month: int
    trough_month: int
    amplitude: float


@dataclass(frozen=True)
class Market:
    city: City
    service: Service
    signals: dict[str, dict[str, Any]] = field(default_factory=dict)
    scores: dict[str, float] | None = None
    scored_at: str | None = None
    snapshot_id: str | None = None
    report_id: str | None = None


@dataclass(frozen=True)
class ScoredMarket:
    market: Market
    opportunity_score: float
    lens_id: str
    rank: int | None = None
    score_breakdown: dict[str, float] = field(default_factory=dict)
