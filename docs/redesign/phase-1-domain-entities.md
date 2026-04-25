# Phase 1: Domain Entities and Ports

**Objective:** Create the `src/domain/` package with all core type definitions — entities, signals, lenses, queries, and port interfaces. No behavior, no side effects, no existing code changes. Pure types that the rest of the redesign builds on.

**Risk:** Zero. No existing code is modified.
**Depends on:** Nothing.
**Blocks:** Phase 2, 3, 4, 5.

---

## Agent Instructions

### Step 1: Create the domain package structure

Create the following empty files to establish the package:

```
src/domain/__init__.py
src/domain/entities.py
src/domain/signals.py
src/domain/scoring.py
src/domain/lenses.py
src/domain/queries.py
src/domain/ports.py
src/domain/services/__init__.py
```

The `src/domain/__init__.py` should re-export key types:

```python
from src.domain.entities import City, Service, Market
from src.domain.signals import SignalBundle, SignalType
from src.domain.lenses import ScoringLens
from src.domain.queries import MarketQuery, CityFilter, ServiceFilter

__all__ = [
    "City",
    "Service",
    "Market",
    "SignalBundle",
    "SignalType",
    "ScoringLens",
    "MarketQuery",
    "CityFilter",
    "ServiceFilter",
]
```

### Step 2: Define entities (`src/domain/entities.py`)

Create frozen dataclasses for the three core entities. These start sparse and fill in over time.

```python
"""
Core domain entities: City, Service, Market.

These are value objects — immutable, no behavior beyond data access.
They start sparse (just a name/id) and enrich as data providers come online.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class City:
    """A geographic market with demographic, economic, and competitive profile."""
    city_id: str                                # canonical key or place_id
    name: str
    state: str | None = None
    population: int | None = None
    median_income: float | None = None
    homeownership_rate: float | None = None
    housing_age_median: float | None = None
    business_density: dict[str, Any] = field(default_factory=dict)
    broadband_penetration: float | None = None
    growth_rate: float | None = None
    archetype: str | None = None                # cluster label ("Growth Sunbelt", etc.)
    demographics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Service:
    """A local service category with economic and competitive profile."""
    service_id: str                             # normalized niche keyword
    name: str
    naics_code: str | None = None
    acv_estimate: float | None = None           # average customer value from BLS
    seasonality: SeasonalityCurve | None = None
    fulfillment_type: str = "physical"          # "physical" | "remote" | "hybrid"
    ai_resilience_baseline: float | None = None
    keyword_universe: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SeasonalityCurve:
    """Monthly search/demand curve for a service."""
    monthly_index: dict[int, float]             # month (1-12) → relative demand (0-1)
    peak_month: int
    trough_month: int
    amplitude: float                            # peak - trough


@dataclass(frozen=True)
class Market:
    """The intersection of a City and a Service — where signals and scores live."""
    city: City
    service: Service
    signals: dict[str, dict[str, Any]] = field(default_factory=dict)  # M6 signal bundles
    scores: dict[str, float] | None = None      # M7 scores (lens-dependent)
    scored_at: str | None = None
    snapshot_id: str | None = None
    report_id: str | None = None


@dataclass(frozen=True)
class ScoredMarket:
    """A Market with its computed score and ranking metadata."""
    market: Market
    opportunity_score: float
    lens_id: str
    rank: int | None = None
    score_breakdown: dict[str, float] = field(default_factory=dict)
```

### Step 3: Define signal types (`src/domain/signals.py`)

Map the M6 signal extraction output into typed structures.

```python
"""
Signal bundle types matching the M4→M9 pipeline output.

Each signal type corresponds to a module in the pipeline:
- DemandSignals ← M5 (keyword volume, trend, intent)
- CompetitionSignals ← M6 (organic SERP, local pack)
- MonetizationSignals ← M6 (GMB presence, ad landscape)
- AIResilienceSignals ← M6 (AIO trigger rate, transactional ratio)
- GBPSignals ← M6 (review counts, ratings, completeness)
"""
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
    volume_trend: float | None = None           # YoY change
    keyword_count: int | None = None
    commercial_intent_ratio: float | None = None
    informational_ratio: float | None = None


@dataclass(frozen=True)
class CompetitionSignals:
    avg_domain_authority: float | None = None
    avg_page_authority: float | None = None
    weak_competitor_ratio: float | None = None   # DA < 30
    exact_match_domain_present: bool | None = None
    serp_archetype: str | None = None            # "fragmented", "dominated", etc.


@dataclass(frozen=True)
class LocalCompetitionSignals:
    gmb_count: int | None = None
    avg_review_count: float | None = None
    avg_rating: float | None = None
    low_review_ratio: float | None = None        # businesses with < 10 reviews
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
```

### Step 4: Define scoring lenses (`src/domain/lenses.py`)

```python
"""
ScoringLens definitions — strategies as weight configurations.

A lens is a data object that configures how scoring.py computes scores
from a Market's signals. Adding a new strategy = adding a new lens instance.

The BALANCED lens reproduces the current default behavior for backward compat.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SignalFilter:
    """Pre-condition on a signal value for a lens to apply."""
    signal: str
    operator: str       # ">", "<", ">=", "<=", "=", "!="
    value: Any


@dataclass(frozen=True)
class ScoringLens:
    """Configuration for how to score and rank markets."""
    lens_id: str
    name: str
    description: str
    weights: dict[str, float]
    filters: list[SignalFilter] = field(default_factory=list)
    required_signals: frozenset[str] = field(default_factory=frozenset)
    sort_key: str = "opportunity"
    sort_descending: bool = True


# --- Lens Registry ---

# Backward-compatible default: reproduces current FIXED_WEIGHTS + balanced profile
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

# --- Lenses requiring new data providers (Phase 7) ---

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


# --- Lens Registry ---

LENS_REGISTRY: dict[str, ScoringLens] = {
    lens.lens_id: lens
    for lens in [
        BALANCED, EASY_WIN, CASH_COW, GBP_BLITZ, AI_PROOF,
        BLUE_OCEAN, PORTFOLIO_BUILDER, EXPAND_CONQUER, SEASONAL_ARBITRAGE,
    ]
}


def get_lens(lens_id: str) -> ScoringLens:
    """Look up a lens by ID. Falls back to BALANCED if not found."""
    return LENS_REGISTRY.get(lens_id, BALANCED)


def available_lenses() -> list[ScoringLens]:
    """Return all registered lenses."""
    return list(LENS_REGISTRY.values())
```

### Step 5: Define query types (`src/domain/queries.py`)

```python
"""
Composable query types for market discovery.

A MarketQuery says "which markets should I look at?"
A ScoringLens says "how should I score them?"
They compose — queries filter the space, lenses rank it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.entities import City, Market
from src.domain.lenses import ScoringLens, BALANCED


@dataclass(frozen=True)
class CityFilter:
    """Filter predicate on a City attribute."""
    field: str          # "population", "archetype", "growth_rate", etc.
    operator: str       # ">", "<", ">=", "<=", "=", "!=", "in", "like"
    value: Any


@dataclass(frozen=True)
class ServiceFilter:
    """Filter predicate on a Service attribute."""
    field: str          # "acv_estimate", "fulfillment_type", "seasonality_peak", etc.
    operator: str       # ">", "<", ">=", "<=", "=", "!=", "in", "like"
    value: Any


@dataclass
class MarketQuery:
    """Composable query over the market space."""
    city_filters: list[CityFilter] = field(default_factory=list)
    service_filters: list[ServiceFilter] = field(default_factory=list)
    lens: ScoringLens = field(default_factory=lambda: BALANCED)
    portfolio_context: list[Market] | None = None   # for Portfolio Builder
    reference_city: City | None = None               # for Expand & Conquer
    limit: int = 50
    offset: int = 0

    def has_city_filters(self) -> bool:
        return len(self.city_filters) > 0

    def has_service_filters(self) -> bool:
        return len(self.service_filters) > 0

    def is_portfolio_query(self) -> bool:
        return self.portfolio_context is not None

    def is_expansion_query(self) -> bool:
        return self.reference_city is not None
```

### Step 6: Define port interfaces (`src/domain/ports.py`)

```python
"""
Port interfaces (Protocols) for all infrastructure dependencies.

The domain layer defines WHAT it needs; infrastructure adapters provide HOW.
These are structural types — any class matching the method signatures works.

Ports with no current implementation are still defined here. They return None
until the corresponding adapter is built (Phase 7 for Census/BLS/Trends).
"""
from __future__ import annotations

from typing import Any, Protocol

from src.domain.entities import City, Market, Service, SeasonalityCurve
from src.domain.queries import MarketQuery


class SERPDataProvider(Protocol):
    """Fetches SERP and keyword data. Implemented by DataForSEO adapter."""
    async def fetch_keyword_volume(
        self, keywords: list[str], location_code: int
    ) -> list[dict[str, Any]]: ...

    async def fetch_serp_organic(
        self, keyword: str, location_code: int
    ) -> dict[str, Any]: ...


class KeywordExpander(Protocol):
    """Expands a niche keyword into a keyword universe. LLM-backed."""
    async def expand(self, niche: str) -> dict[str, Any]: ...


class CityDataProvider(Protocol):
    """City demographics and economics. Implemented by Census adapter (Phase 7)."""
    def get_demographics(self, city_id: str) -> dict[str, Any] | None: ...
    def get_business_density(
        self, city_id: str, naics: str | None = None
    ) -> dict[str, Any] | None: ...
    def find_similar_cities(
        self, reference: City, limit: int = 10
    ) -> list[tuple[City, float]]: ...


class ServiceDataProvider(Protocol):
    """Service-level data. Implemented by BLS/Trends adapters (Phase 7)."""
    def get_acv_estimate(self, naics: str, city_id: str) -> float | None: ...
    def get_seasonality(self, service_name: str) -> SeasonalityCurve | None: ...
    def get_establishment_growth(
        self, naics: str, city_id: str
    ) -> float | None: ...


class MarketStore(Protocol):
    """Persists and queries scored markets. Implemented by Supabase adapter."""
    def persist_report(self, report: dict[str, Any]) -> str: ...
    def read_report(self, report_id: str) -> dict[str, Any] | None: ...
    def query_markets(self, query: MarketQuery) -> list[Market]: ...


class KnowledgeStore(Protocol):
    """KB entity and snapshot operations. Implemented by KB persistence adapter."""
    def upsert_entity(self, key: Any) -> str: ...
    def create_snapshot(self, entity_id: str, **kwargs: Any) -> str: ...
    def store_evidence(
        self, snapshot_id: str, artifact_type: str, payload: Any
    ) -> None: ...


class GeoLookup(Protocol):
    """Metro/place resolution. Implemented by MetroDB."""
    def find_by_city(
        self, city: str, state: str | None = None
    ) -> City | None: ...
    def all_metros(self) -> list[City]: ...


class CostLogger(Protocol):
    """Logs API costs for budget tracking."""
    def log(self, provider: str, operation: str, cost: float) -> None: ...
```

### Step 7: Create `src/domain/scoring.py` (pure scoring stub)

```python
"""
Score computation: apply a ScoringLens to a Market's signals.

This module contains the pure scoring logic. It takes signals in and returns
scores out. No side effects. The actual scoring math lives in src/scoring/engine.py —
this module bridges the domain model to the scoring engine.
"""
from __future__ import annotations

from src.domain.entities import Market, ScoredMarket
from src.domain.lenses import ScoringLens


def score_market(market: Market, lens: ScoringLens) -> ScoredMarket:
    """
    Apply a ScoringLens to a Market's signal bundles, returning a ScoredMarket.

    This is a stub that will be fully implemented in Phase 4 when the scoring
    engine is refactored to accept weight dicts from lenses.
    """
    raise NotImplementedError(
        "score_market will be implemented in Phase 4 (lens-based scoring)"
    )
```

### Step 8: Write tests (`tests/domain/test_entities.py`, `tests/domain/test_lenses.py`, `tests/domain/test_queries.py`)

Create `tests/domain/__init__.py` (empty).

**`tests/domain/test_entities.py`:**

```python
"""Tests for domain entity value objects."""
from src.domain.entities import City, Service, Market, SeasonalityCurve, ScoredMarket


def test_city_minimal_creation():
    """City can be created with just id and name."""
    city = City(city_id="boise-id", name="Boise")
    assert city.city_id == "boise-id"
    assert city.name == "Boise"
    assert city.population is None
    assert city.demographics == {}


def test_city_is_frozen():
    """City is immutable."""
    city = City(city_id="boise-id", name="Boise")
    try:
        city.name = "Not Boise"
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass


def test_city_with_full_data():
    """City can hold all enrichment data."""
    city = City(
        city_id="boise-id",
        name="Boise",
        state="ID",
        population=235_000,
        median_income=58_000,
        growth_rate=0.032,
        archetype="Growth Sunbelt",
        demographics={"pct_owner_occupied": 0.65},
    )
    assert city.population == 235_000
    assert city.archetype == "Growth Sunbelt"


def test_service_minimal_creation():
    """Service can be created with just id and name."""
    svc = Service(service_id="plumbing", name="Plumbing")
    assert svc.fulfillment_type == "physical"
    assert svc.keyword_universe == []


def test_market_links_city_and_service():
    """Market is the intersection of City and Service."""
    city = City(city_id="boise-id", name="Boise")
    svc = Service(service_id="plumbing", name="Plumbing")
    market = Market(city=city, service=svc)
    assert market.city.city_id == "boise-id"
    assert market.service.service_id == "plumbing"
    assert market.signals == {}
    assert market.scores is None


def test_seasonality_curve():
    """SeasonalityCurve captures monthly demand shape."""
    curve = SeasonalityCurve(
        monthly_index={1: 0.3, 2: 0.4, 6: 1.0, 12: 0.2},
        peak_month=6,
        trough_month=12,
        amplitude=0.8,
    )
    assert curve.peak_month == 6
    assert curve.amplitude == 0.8


def test_scored_market():
    """ScoredMarket wraps a Market with scoring metadata."""
    city = City(city_id="boise-id", name="Boise")
    svc = Service(service_id="plumbing", name="Plumbing")
    market = Market(city=city, service=svc)
    scored = ScoredMarket(
        market=market,
        opportunity_score=78.5,
        lens_id="easy_win",
        rank=1,
        score_breakdown={"demand": 20.0, "competition": 25.0},
    )
    assert scored.opportunity_score == 78.5
    assert scored.lens_id == "easy_win"
```

**`tests/domain/test_lenses.py`:**

```python
"""Tests for ScoringLens definitions and registry."""
from src.domain.lenses import (
    BALANCED, EASY_WIN, CASH_COW, GBP_BLITZ, AI_PROOF,
    BLUE_OCEAN, PORTFOLIO_BUILDER, EXPAND_CONQUER, SEASONAL_ARBITRAGE,
    LENS_REGISTRY, get_lens, available_lenses,
)


ALL_LENSES = [
    BALANCED, EASY_WIN, CASH_COW, GBP_BLITZ, AI_PROOF,
    BLUE_OCEAN, PORTFOLIO_BUILDER, EXPAND_CONQUER, SEASONAL_ARBITRAGE,
]


def test_all_lens_weights_sum_to_one():
    """Every lens's weights must sum to 1.0 (within floating point tolerance)."""
    for lens in ALL_LENSES:
        total = sum(lens.weights.values())
        assert abs(total - 1.0) < 0.01, (
            f"Lens '{lens.lens_id}' weights sum to {total}, expected 1.0"
        )


def test_all_lenses_have_unique_ids():
    """No two lenses share an ID."""
    ids = [lens.lens_id for lens in ALL_LENSES]
    assert len(ids) == len(set(ids))


def test_all_lenses_have_descriptions():
    """Every lens has a non-empty description."""
    for lens in ALL_LENSES:
        assert lens.description, f"Lens '{lens.lens_id}' has no description"


def test_balanced_lens_matches_current_weights():
    """BALANCED lens reproduces the existing FIXED_WEIGHTS + balanced profile."""
    assert BALANCED.weights["demand"] == 0.25
    assert BALANCED.weights["monetization"] == 0.20
    assert BALANCED.weights["ai_resilience"] == 0.15


def test_registry_contains_all_lenses():
    """All defined lenses are in the registry."""
    assert len(LENS_REGISTRY) == 9
    for lens in ALL_LENSES:
        assert lens.lens_id in LENS_REGISTRY


def test_get_lens_returns_correct_lens():
    """get_lens retrieves by ID."""
    assert get_lens("easy_win").lens_id == "easy_win"


def test_get_lens_falls_back_to_balanced():
    """Unknown lens ID returns BALANCED."""
    lens = get_lens("nonexistent")
    assert lens.lens_id == "balanced"


def test_available_lenses_returns_all():
    """available_lenses returns the full list."""
    assert len(available_lenses()) == 9


def test_required_signals_are_frozenset():
    """required_signals should be frozenset for hashability."""
    for lens in ALL_LENSES:
        assert isinstance(lens.required_signals, frozenset)
```

**`tests/domain/test_queries.py`:**

```python
"""Tests for MarketQuery composition."""
from src.domain.entities import City, Service, Market
from src.domain.lenses import EASY_WIN, BALANCED
from src.domain.queries import MarketQuery, CityFilter, ServiceFilter


def test_empty_query_defaults():
    """Empty query has balanced lens and no filters."""
    q = MarketQuery()
    assert q.lens.lens_id == "balanced"
    assert q.city_filters == []
    assert q.service_filters == []
    assert q.limit == 50


def test_city_filter_composition():
    """Query composes city filters."""
    q = MarketQuery(
        city_filters=[
            CityFilter("population", ">", 200_000),
            CityFilter("archetype", "=", "Growth Sunbelt"),
        ],
        lens=EASY_WIN,
    )
    assert q.has_city_filters()
    assert not q.has_service_filters()
    assert len(q.city_filters) == 2
    assert q.lens.lens_id == "easy_win"


def test_service_filter_composition():
    """Query composes service filters."""
    q = MarketQuery(
        service_filters=[
            ServiceFilter("fulfillment_type", "=", "physical"),
            ServiceFilter("acv_estimate", ">", 5000),
        ],
    )
    assert q.has_service_filters()
    assert not q.has_city_filters()


def test_portfolio_query():
    """Portfolio query carries context markets."""
    existing = Market(
        city=City(city_id="boise-id", name="Boise"),
        service=Service(service_id="plumbing", name="Plumbing"),
    )
    q = MarketQuery(portfolio_context=[existing])
    assert q.is_portfolio_query()
    assert not q.is_expansion_query()


def test_expansion_query():
    """Expansion query carries a reference city."""
    boise = City(city_id="boise-id", name="Boise", state="ID")
    q = MarketQuery(reference_city=boise)
    assert q.is_expansion_query()
    assert not q.is_portfolio_query()


def test_combined_filters_and_lens():
    """Full query with city + service filters + lens."""
    q = MarketQuery(
        city_filters=[CityFilter("population", ">", 200_000)],
        service_filters=[ServiceFilter("fulfillment_type", "=", "physical")],
        lens=EASY_WIN,
        limit=25,
    )
    assert q.has_city_filters()
    assert q.has_service_filters()
    assert q.lens.lens_id == "easy_win"
    assert q.limit == 25
```

### Step 9: Validate

Run all tests and confirm:

```bash
# From project root
python -m pytest tests/domain/ -v

# Verify no infrastructure imports in domain
grep -r "from src.clients" src/domain/ && echo "FAIL: domain imports infrastructure" || echo "PASS: no infrastructure imports"
grep -r "from src.research_agent" src/domain/ && echo "FAIL: domain imports API layer" || echo "PASS: no API layer imports"
grep -r "import supabase" src/domain/ && echo "FAIL: domain imports supabase" || echo "PASS"
grep -r "import httpx" src/domain/ && echo "FAIL: domain imports httpx" || echo "PASS"

# Verify type checking passes
python -m mypy src/domain/ --ignore-missing-imports
```

**Done criteria:**
- All tests pass
- `src/domain/` has zero imports from `src/clients/`, `src/research_agent/`, `src/data/`
- All entity dataclasses are frozen
- All lens weights sum to 1.0
- `scoring.py` has a `NotImplementedError` stub (Phase 4 implements it)
- `services/` directory exists but is empty except for `__init__.py`
