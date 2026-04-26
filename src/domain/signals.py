from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SignalType(str, Enum):
    DEMAND = "demand"
    ORGANIC_COMPETITION = "organic_competition"
    LOCAL_COMPETITION = "local_competition"
    MONETIZATION = "monetization"
    AI_RESILIENCE = "ai_resilience"
    GBP = "gbp"
    SITE_QUALITY_GAP = "site_quality_gap"
    ACV_ESTIMATE = "acv_estimate"
    ESTABLISHMENT_GROWTH = "establishment_growth"
    SEASONAL_TIMING = "seasonal_timing"


@dataclass(frozen=True)
class DemandSignals:
    keyword_volume: int | None = None
    volume_trend: float | None = None
    keyword_count: int | None = None
    commercial_intent_ratio: float | None = None
    informational_ratio: float | None = None


@dataclass(frozen=True)
class CompetitionSignals:
    avg_domain_authority: float | None = None
    avg_page_authority: float | None = None
    weak_competitor_ratio: float | None = None
    exact_match_domain_present: bool | None = None
    serp_archetype: str | None = None


@dataclass(frozen=True)
class LocalCompetitionSignals:
    gmb_count: int | None = None
    avg_review_count: float | None = None
    avg_rating: float | None = None
    low_review_ratio: float | None = None
    unclaimed_ratio: float | None = None


@dataclass(frozen=True)
class MonetizationSignals:
    cpc_estimate: float | None = None
    ad_density: float | None = None
    gmb_ad_presence: bool | None = None
    estimated_monthly_value: float | None = None


@dataclass(frozen=True)
class AIResilienceSignals:
    aio_trigger_rate: float | None = None
    transactional_ratio: float | None = None
    local_intent_ratio: float | None = None
    featured_snippet_presence: bool | None = None


@dataclass(frozen=True)
class GBPSignals:
    total_listings: int | None = None
    avg_reviews: float | None = None
    avg_rating: float | None = None
    avg_photos: float | None = None
    completeness_score: float | None = None
