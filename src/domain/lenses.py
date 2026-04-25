from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SignalFilter:
    signal: str
    operator: str
    value: Any


@dataclass(frozen=True)
class ScoringLens:
    lens_id: str
    name: str
    description: str
    weights: dict[str, float]
    filters: list[SignalFilter] = field(default_factory=list)
    required_signals: frozenset[str] = field(default_factory=frozenset)
    sort_key: str = "opportunity"
    sort_descending: bool = True


BALANCED = ScoringLens(
    lens_id="balanced",
    name="Balanced",
    description="Default balanced scoring across all signal dimensions.",
    weights={
        "demand": 0.25,
        "organic_competition": 0.175,
        "local_competition": 0.175,
        "monetization": 0.20,
        "ai_resilience": 0.15,
        "gbp": 0.05,
    },
    required_signals=frozenset({"demand", "organic_competition"}),
)

EASY_WIN = ScoringLens(
    lens_id="easy_win",
    name="Easy Win",
    description="Low-competition niches with weak incumbent sites. Optimized for fast ranking.",
    weights={
        "demand": 0.20,
        "organic_competition": 0.25,
        "local_competition": 0.20,
        "monetization": 0.10,
        "ai_resilience": 0.10,
        "site_quality_gap": 0.15,
    },
    required_signals=frozenset({"demand", "organic_competition"}),
    sort_key="opportunity",
)

CASH_COW = ScoringLens(
    lens_id="cash_cow",
    name="Cash Cow",
    description="High-ACV niches with strong monetization. Prioritizes revenue potential over ease.",
    weights={
        "demand": 0.10,
        "organic_competition": 0.10,
        "local_competition": 0.10,
        "monetization": 0.35,
        "ai_resilience": 0.10,
        "acv_estimate": 0.25,
    },
    filters=[SignalFilter("acv_estimate", ">", 3000)],
    required_signals=frozenset({"monetization"}),
    sort_key="revenue_potential",
)

GBP_BLITZ = ScoringLens(
    lens_id="gbp_blitz",
    name="GBP Blitz",
    description="Weak local pack — few reviews, low ratings, incomplete profiles. Fast local wins.",
    weights={
        "demand": 0.15,
        "organic_competition": 0.10,
        "local_competition": 0.30,
        "monetization": 0.10,
        "ai_resilience": 0.05,
        "gbp": 0.30,
    },
    filters=[SignalFilter("avg_reviews", "<", 30)],
    required_signals=frozenset({"local_competition", "gbp"}),
    sort_key="opportunity",
)

AI_PROOF = ScoringLens(
    lens_id="ai_proof",
    name="AI-Proof",
    description="Niches resilient to AI Overview displacement. High transactional, low AIO trigger.",
    weights={
        "demand": 0.15,
        "organic_competition": 0.15,
        "local_competition": 0.10,
        "monetization": 0.15,
        "ai_resilience": 0.35,
        "gbp": 0.10,
    },
    filters=[SignalFilter("aio_trigger_rate", "<", 0.10)],
    required_signals=frozenset({"ai_resilience"}),
    sort_key="opportunity",
)

BLUE_OCEAN = ScoringLens(
    lens_id="blue_ocean",
    name="Blue Ocean",
    description="Emerging markets with high establishment growth and sparse SERP coverage.",
    weights={
        "demand": 0.15,
        "organic_competition": 0.20,
        "local_competition": 0.10,
        "monetization": 0.10,
        "ai_resilience": 0.05,
        "establishment_growth": 0.25,
        "site_quality_gap": 0.15,
    },
    filters=[SignalFilter("establishment_growth", ">", 0.20)],
    required_signals=frozenset({"organic_competition", "establishment_growth"}),
    sort_key="opportunity",
)

PORTFOLIO_BUILDER = ScoringLens(
    lens_id="portfolio_builder",
    name="Portfolio Builder",
    description="Complementary niches in a city where you already rank. Maximizes cross-sell.",
    weights={
        "demand": 0.20,
        "organic_competition": 0.20,
        "local_competition": 0.15,
        "monetization": 0.20,
        "ai_resilience": 0.10,
        "gbp": 0.15,
    },
    required_signals=frozenset({"demand", "organic_competition"}),
    sort_key="complementarity",
)

EXPAND_CONQUER = ScoringLens(
    lens_id="expand_conquer",
    name="Expand & Conquer",
    description="Find cities similar to one where you're already winning. Geographic expansion.",
    weights={
        "demand": 0.20,
        "organic_competition": 0.20,
        "local_competition": 0.15,
        "monetization": 0.20,
        "ai_resilience": 0.10,
        "gbp": 0.15,
    },
    required_signals=frozenset({"demand", "organic_competition"}),
    sort_key="similarity",
)

SEASONAL_ARBITRAGE = ScoringLens(
    lens_id="seasonal_arbitrage",
    name="Seasonal Arbitrage",
    description="Build sites in off-season when competition is low. Rank before demand peaks.",
    weights={
        "demand": 0.10,
        "organic_competition": 0.25,
        "local_competition": 0.15,
        "monetization": 0.15,
        "ai_resilience": 0.05,
        "seasonal_timing": 0.30,
    },
    filters=[SignalFilter("months_to_peak", ">", 3)],
    required_signals=frozenset({"organic_competition", "seasonal_timing"}),
    sort_key="timing_advantage",
)


LENS_REGISTRY: dict[str, ScoringLens] = {
    lens.lens_id: lens
    for lens in [
        BALANCED, EASY_WIN, CASH_COW, GBP_BLITZ, AI_PROOF,
        BLUE_OCEAN, PORTFOLIO_BUILDER, EXPAND_CONQUER, SEASONAL_ARBITRAGE,
    ]
}


def get_lens(lens_id: str) -> ScoringLens:
    return LENS_REGISTRY.get(lens_id, BALANCED)


def available_lenses() -> list[ScoringLens]:
    return list(LENS_REGISTRY.values())
