# Phase 5: DiscoveryService + `/api/discover`

**Objective:** Build `src/domain/services/discovery_service.py` and the new `/api/discover` endpoint. This composes MarketService with city/service filtering and lens-based ranking. No existing code is modified — this is pure additive.

**Risk:** Low. New feature, no existing code changed.
**Depends on:** Phase 3 (MarketService), Phase 4 (lens-based scoring).
**Blocks:** Phase 7 (data providers enrich discovery results).

---

## Agent Instructions

### Step 0: Understand what DiscoveryService composes

DiscoveryService answers: "Given filters on cities, filters on services, and a scoring lens — which markets should I look at, and how do they rank?"

It does NOT run the full M4→M9 pipeline for every city×service pair. Instead:
1. It queries already-scored markets from MarketStore (cached results)
2. For markets not yet scored, it can trigger MarketService.score() on-demand
3. It applies city/service filters before scoring (to reduce the search space)
4. It ranks results through the requested lens

### Step 1: Create DiscoveryService

**`src/domain/services/discovery_service.py`:**

```python
"""
DiscoveryService — multi-market query execution.

Given a MarketQuery (filters + lens), discovers and ranks markets.
Powers: strategy pages, city browsing, service browsing, portfolio
recommendations, expansion search — all through MarketQuery.
"""
from __future__ import annotations

import logging
from typing import Any

from src.domain.entities import City, Service, Market, ScoredMarket
from src.domain.lenses import ScoringLens, BALANCED
from src.domain.queries import MarketQuery, CityFilter, ServiceFilter
from src.domain.scoring import score_markets_batch
from src.domain.ports import (
    CityDataProvider,
    ServiceDataProvider,
    MarketStore,
)
from src.domain.services.market_service import MarketService

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Execute multi-market discovery queries."""

    def __init__(
        self,
        market_service: MarketService,
        city_provider: CityDataProvider | None = None,
        service_provider: ServiceDataProvider | None = None,
        market_store: MarketStore | None = None,
    ):
        self._market_service = market_service
        self._city_provider = city_provider
        self._service_provider = service_provider
        self._market_store = market_store

    async def discover(self, query: MarketQuery) -> list[ScoredMarket]:
        """
        Execute a market discovery query.

        Flow:
        1. Resolve candidate cities (from filters, similarity, or all)
        2. Resolve candidate services (from filters or all)
        3. For each city×service, check for cached scores or score fresh
        4. Apply portfolio context if present
        5. Score and rank through the lens
        """
        # 1. Resolve cities
        cities = self._resolve_cities(query)
        logger.info(f"Discovery: {len(cities)} candidate cities")

        # 2. Resolve services
        services = self._resolve_services(query)
        logger.info(f"Discovery: {len(services)} candidate services")

        # 3. Get or score markets
        markets = await self._get_markets(cities, services, query)
        logger.info(f"Discovery: {len(markets)} markets to score")

        # 4. Score through lens
        scored = score_markets_batch(markets, query.lens)

        # 5. Apply portfolio ranking if applicable
        if query.is_portfolio_query():
            scored = self._apply_portfolio_ranking(scored, query.portfolio_context)

        # 6. Apply limit/offset
        scored = scored[query.offset : query.offset + query.limit]

        return scored

    def _resolve_cities(self, query: MarketQuery) -> list[City]:
        """
        Resolve which cities to include in the discovery.

        Priority:
        1. If expansion query → find similar cities to reference
        2. If city filters → filter from all known cities
        3. Otherwise → all cities (capped for performance)
        """
        if query.is_expansion_query() and self._city_provider:
            similar = self._city_provider.find_similar_cities(
                query.reference_city, limit=query.limit
            )
            return [city for city, _score in similar]

        # Get all cities from market store or city provider
        all_cities = self._get_all_cities()

        if not query.has_city_filters():
            return all_cities

        return [
            city for city in all_cities
            if self._passes_city_filters(city, query.city_filters)
        ]

    def _resolve_services(self, query: MarketQuery) -> list[Service]:
        """Resolve which services to include in the discovery."""
        all_services = self._get_all_services()

        if not query.has_service_filters():
            return all_services

        return [
            svc for svc in all_services
            if self._passes_service_filters(svc, query.service_filters)
        ]

    async def _get_markets(
        self,
        cities: list[City],
        services: list[Service],
        query: MarketQuery,
    ) -> list[Market]:
        """
        Get Market objects for each city×service pair.

        First checks MarketStore for cached scores. Falls back to
        creating sparse Market objects that can be scored by the lens.

        NOTE: In early implementation, this returns sparse markets from
        cached report data. It does NOT trigger full pipeline scoring
        for every combination — that would be prohibitively expensive.
        """
        markets = []

        if self._market_store:
            # Try to get cached markets matching the query
            cached = self._market_store.query_markets(query)
            if cached:
                return cached

        # Fallback: create sparse markets from available data
        for city in cities:
            for service in services:
                market = Market(city=city, service=service)
                markets.append(market)

        return markets

    def _apply_portfolio_ranking(
        self,
        scored: list[ScoredMarket],
        context: list[Market],
    ) -> list[ScoredMarket]:
        """
        Re-rank markets considering portfolio context.

        Markets in the same city as existing portfolio entries get a
        complementarity bonus. Markets for services already in the
        portfolio get penalized (diminishing returns).

        Full implementation requires NAICS similarity data (Phase 7).
        For now, apply a simple same-city bonus.
        """
        if not context:
            return scored

        # Cities already in portfolio
        portfolio_cities = {m.city.city_id for m in context}
        portfolio_services = {m.service.service_id for m in context}

        reranked = []
        for sm in scored:
            bonus = 0.0
            # Same city as existing portfolio entry → complementarity bonus
            if sm.market.city.city_id in portfolio_cities:
                bonus += 5.0
            # Same service → penalty (already doing this)
            if sm.market.service.service_id in portfolio_services:
                bonus -= 10.0

            reranked.append(ScoredMarket(
                market=sm.market,
                opportunity_score=sm.opportunity_score + bonus,
                lens_id=sm.lens_id,
                rank=sm.rank,
                score_breakdown=sm.score_breakdown,
            ))

        reranked.sort(key=lambda s: s.opportunity_score, reverse=True)
        for i, sm in enumerate(reranked):
            reranked[i] = ScoredMarket(
                market=sm.market,
                opportunity_score=sm.opportunity_score,
                lens_id=sm.lens_id,
                rank=i + 1,
                score_breakdown=sm.score_breakdown,
            )
        return reranked

    def _get_all_cities(self) -> list[City]:
        """Get all known cities. Uses GeoLookup or MarketStore."""
        # Phase 7 will populate this from Census data
        # For now, return cities from the geo resolver's metro DB
        return []

    def _get_all_services(self) -> list[Service]:
        """Get all known services. Uses ServiceDataProvider or hard-coded list."""
        # Phase 7 will populate this from BLS/Census data
        # For now, return empty — discovery works only with cached markets
        return []

    @staticmethod
    def _passes_city_filters(city: City, filters: list[CityFilter]) -> bool:
        """Check if a city passes all filters."""
        for f in filters:
            value = getattr(city, f.field, None)
            if value is None:
                return False  # Can't evaluate filter on missing data
            if not _evaluate_predicate(value, f.operator, f.value):
                return False
        return True

    @staticmethod
    def _passes_service_filters(service: Service, filters: list[ServiceFilter]) -> bool:
        """Check if a service passes all filters."""
        for f in filters:
            value = getattr(service, f.field, None)
            if value is None:
                return False
            if not _evaluate_predicate(value, f.operator, f.value):
                return False
        return True


def _evaluate_predicate(value: Any, operator: str, target: Any) -> bool:
    """Evaluate a filter predicate."""
    ops = {
        ">": lambda v, t: v > t,
        "<": lambda v, t: v < t,
        ">=": lambda v, t: v >= t,
        "<=": lambda v, t: v <= t,
        "=": lambda v, t: v == t,
        "!=": lambda v, t: v != t,
        "in": lambda v, t: v in t,
        "like": lambda v, t: t.lower() in str(v).lower(),
    }
    op_fn = ops.get(operator)
    if op_fn is None:
        raise ValueError(f"Unknown filter operator: {operator}")
    return op_fn(value, target)
```

### Step 2: Create the API endpoint

**Add to `src/research_agent/api.py`:**

```python
from pydantic import BaseModel, Field
from typing import Any


class DiscoverRequest(BaseModel):
    """Request body for /api/discover."""
    lens_id: str = "balanced"
    city_filters: list[dict[str, Any]] = Field(default_factory=list)
    service_filters: list[dict[str, Any]] = Field(default_factory=list)
    portfolio_market_ids: list[str] | None = None
    reference_city_id: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


@app.post("/api/discover")
async def discover(req: DiscoverRequest) -> dict[str, Any]:
    """
    Multi-market discovery — strategies, filters, similarity.

    This is the general-purpose query surface. Every access pattern
    (strategy ranking, city browse, service browse, portfolio, expansion)
    goes through this endpoint with different filter/lens combos.
    """
    from src.domain.lenses import get_lens
    from src.domain.queries import MarketQuery, CityFilter, ServiceFilter

    lens = get_lens(req.lens_id)

    query = MarketQuery(
        city_filters=[
            CityFilter(f["field"], f["operator"], f["value"])
            for f in req.city_filters
        ],
        service_filters=[
            ServiceFilter(f["field"], f["operator"], f["value"])
            for f in req.service_filters
        ],
        lens=lens,
        limit=req.limit,
        offset=req.offset,
    )

    # Handle portfolio context
    if req.portfolio_market_ids:
        # Load existing markets from store
        # query.portfolio_context = [market_store.read_report(mid) for mid in req.portfolio_market_ids]
        pass

    # Handle expansion query
    if req.reference_city_id:
        # Load reference city
        # query.reference_city = geo_resolver.resolve_by_id(req.reference_city_id)
        pass

    results = await discovery_service.discover(query)

    return {
        "markets": [
            {
                "rank": r.rank,
                "opportunity_score": round(r.opportunity_score, 1),
                "lens_id": r.lens_id,
                "city": {
                    "city_id": r.market.city.city_id,
                    "name": r.market.city.name,
                    "state": r.market.city.state,
                    "population": r.market.city.population,
                },
                "service": {
                    "service_id": r.market.service.service_id,
                    "name": r.market.service.name,
                },
                "score_breakdown": r.score_breakdown,
            }
            for r in results
        ],
        "total": len(results),
        "lens": {
            "lens_id": lens.lens_id,
            "name": lens.name,
            "description": lens.description,
        },
        "query": {
            "city_filters": req.city_filters,
            "service_filters": req.service_filters,
            "limit": req.limit,
            "offset": req.offset,
        },
    }


@app.get("/api/lenses")
async def list_lenses() -> dict[str, Any]:
    """List all available scoring lenses."""
    from src.domain.lenses import available_lenses

    return {
        "lenses": [
            {
                "lens_id": lens.lens_id,
                "name": lens.name,
                "description": lens.description,
                "weights": lens.weights,
                "filters": [
                    {"signal": f.signal, "operator": f.operator, "value": f.value}
                    for f in lens.filters
                ],
            }
            for lens in available_lenses()
        ]
    }
```

### Step 3: Wire up DiscoveryService at startup

```python
# In app startup/lifespan (alongside MarketService wiring from Phase 3):
from src.domain.services.discovery_service import DiscoveryService

discovery_service = DiscoveryService(
    market_service=market_service,
    market_store=market_store,
    # city_provider and service_provider are None until Phase 7
)
```

### Step 4: Write tests

**`tests/domain/services/test_discovery_service.py`:**

```python
"""Tests for DiscoveryService — multi-market discovery."""
import asyncio
import pytest
from src.domain.entities import City, Service, Market, ScoredMarket
from src.domain.lenses import BALANCED, EASY_WIN
from src.domain.queries import MarketQuery, CityFilter, ServiceFilter
from src.domain.services.discovery_service import DiscoveryService, _evaluate_predicate


# --- Fakes ---

class FakeMarketService:
    """Fake that returns pre-configured results."""
    pass


class FakeMarketStore:
    def __init__(self, markets: list[Market] | None = None):
        self._markets = markets or []

    def persist_report(self, report):
        return "fake-id"

    def read_report(self, report_id):
        return None

    def query_markets(self, query):
        return self._markets


# --- Test data ---

BOISE = City(city_id="boise-id", name="Boise", state="ID", population=235_000)
PHOENIX = City(city_id="phoenix-az", name="Phoenix", state="AZ", population=1_600_000)
SMALL_TOWN = City(city_id="small-id", name="Smallville", state="KS", population=45_000)

PLUMBING = Service(service_id="plumbing", name="Plumbing", fulfillment_type="physical")
WEB_DESIGN = Service(service_id="web-design", name="Web Design", fulfillment_type="remote")

FULL_SIGNALS = {
    "demand": {"score": 75.0},
    "organic_competition": {"score": 68.0},
    "local_competition": {"score": 55.0},
    "monetization": {"score": 60.0},
    "ai_resilience": {"score": 80.0},
    "gbp": {"score": 45.0},
}


def _make_markets() -> list[Market]:
    return [
        Market(city=BOISE, service=PLUMBING, signals=FULL_SIGNALS),
        Market(city=PHOENIX, service=PLUMBING, signals=FULL_SIGNALS),
        Market(city=BOISE, service=WEB_DESIGN, signals=FULL_SIGNALS),
        Market(city=SMALL_TOWN, service=PLUMBING, signals=FULL_SIGNALS),
    ]


@pytest.fixture
def discovery():
    store = FakeMarketStore(markets=_make_markets())
    return DiscoveryService(
        market_service=FakeMarketService(),
        market_store=store,
    )


def test_discover_returns_scored_markets(discovery):
    """Basic discovery returns scored markets."""
    query = MarketQuery(lens=BALANCED)
    results = asyncio.run(discovery.discover(query))
    assert len(results) > 0
    assert all(isinstance(r, ScoredMarket) for r in results)


def test_discover_with_city_filter(discovery):
    """City filter narrows results."""
    query = MarketQuery(
        city_filters=[CityFilter("population", ">", 200_000)],
        lens=BALANCED,
    )
    results = asyncio.run(discovery.discover(query))
    for r in results:
        assert r.market.city.population > 200_000


def test_discover_with_service_filter(discovery):
    """Service filter narrows results."""
    query = MarketQuery(
        service_filters=[ServiceFilter("fulfillment_type", "=", "physical")],
        lens=BALANCED,
    )
    results = asyncio.run(discovery.discover(query))
    for r in results:
        assert r.market.service.fulfillment_type == "physical"


def test_discover_respects_limit(discovery):
    """Limit caps results."""
    query = MarketQuery(lens=BALANCED, limit=2)
    results = asyncio.run(discovery.discover(query))
    assert len(results) <= 2


def test_discover_results_are_ranked(discovery):
    """Results have sequential ranks."""
    query = MarketQuery(lens=BALANCED)
    results = asyncio.run(discovery.discover(query))
    ranks = [r.rank for r in results]
    assert ranks == list(range(1, len(ranks) + 1))


def test_portfolio_context_boosts_same_city():
    """Portfolio context gives same-city bonus."""
    existing = Market(city=BOISE, service=PLUMBING)
    store = FakeMarketStore(markets=_make_markets())
    discovery = DiscoveryService(
        market_service=FakeMarketService(),
        market_store=store,
    )
    query = MarketQuery(
        lens=BALANCED,
        portfolio_context=[existing],
    )
    results = asyncio.run(discovery.discover(query))
    # Boise markets should rank higher due to same-city bonus
    boise_ranks = [r.rank for r in results if r.market.city.city_id == "boise-id"]
    other_ranks = [r.rank for r in results if r.market.city.city_id != "boise-id"]
    # At least one Boise market should be in top half
    assert min(boise_ranks) <= len(results) // 2


def test_evaluate_predicate_operators():
    """All predicate operators work."""
    assert _evaluate_predicate(100, ">", 50)
    assert _evaluate_predicate(100, "<", 200)
    assert _evaluate_predicate("physical", "=", "physical")
    assert _evaluate_predicate("Growth Sunbelt", "like", "sunbelt")
    assert _evaluate_predicate("physical", "in", ["physical", "hybrid"])
```

**`tests/api/test_discover_endpoint.py`:**

```python
"""Tests for /api/discover and /api/lenses endpoints."""
import pytest
from httpx import AsyncClient  # or however the app is tested


@pytest.mark.asyncio
async def test_discover_endpoint_basic():
    """
    /api/discover returns markets with expected shape.
    The agent should adapt this to the actual test setup
    (TestClient, httpx, etc.) used in the project.
    """
    # async with AsyncClient(app=app, base_url="http://test") as client:
    #     resp = await client.post("/api/discover", json={
    #         "lens_id": "balanced",
    #         "limit": 10,
    #     })
    #     assert resp.status_code == 200
    #     data = resp.json()
    #     assert "markets" in data
    #     assert "lens" in data
    #     assert data["lens"]["lens_id"] == "balanced"
    pass


@pytest.mark.asyncio
async def test_lenses_endpoint():
    """
    /api/lenses returns all available lenses.
    """
    # async with AsyncClient(app=app, base_url="http://test") as client:
    #     resp = await client.get("/api/lenses")
    #     assert resp.status_code == 200
    #     data = resp.json()
    #     assert "lenses" in data
    #     assert len(data["lenses"]) == 9
    #     ids = [l["lens_id"] for l in data["lenses"]]
    #     assert "balanced" in ids
    #     assert "easy_win" in ids
    pass
```

### Step 5: Validate

```bash
# Run discovery tests
python -m pytest tests/domain/services/test_discovery_service.py -v
python -m pytest tests/api/test_discover_endpoint.py -v

# Run full suite — no regressions
python -m pytest tests/ -v

# Test the endpoint manually
curl -X POST http://localhost:8000/api/discover \
  -H "Content-Type: application/json" \
  -d '{"lens_id":"easy_win","city_filters":[{"field":"population","operator":">","value":200000}],"limit":10}' \
  | python -m json.tool

curl http://localhost:8000/api/lenses | python -m json.tool

# Verify domain import rules
grep -r "from src.clients" src/domain/ && echo "FAIL" || echo "PASS"
```

**Done criteria:**
- `/api/discover` endpoint works with lens, city filters, service filters
- `/api/lenses` endpoint returns all 9 lens definitions
- DiscoveryService uses MarketStore for cached results (no full pipeline per query)
- Portfolio context applies same-city bonus and same-service penalty
- Results are ranked with sequential ranks
- Limit/offset pagination works
- No existing endpoints are modified
- All tests pass
- Discovery with no cached data returns empty list (not an error)
