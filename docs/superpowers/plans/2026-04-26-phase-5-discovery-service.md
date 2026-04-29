# Phase 5: DiscoveryService + `/api/discover` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a composable multi-market discovery engine that queries cached markets, applies city/service filters, scores through lenses, and ranks results — exposed via `/api/discover` and `/api/lenses` endpoints.

**Architecture:** DiscoveryService takes a `MarketStore` (protocol from Phase 1) and operates on cached markets only. Flow: fetch cached markets → apply city/service filter predicates → score through lens via `score_markets_batch()` (Phase 4) → optionally apply portfolio ranking → paginate. No existing code is modified — this is pure additive. MarketService (Phase 3, unmerged) is NOT a dependency; when it merges, DiscoveryService can be extended to trigger on-demand scoring.

**Tech Stack:** Python 3.11+, pytest, FastAPI, existing domain layer (`src/domain/`), scoring engine (`src/scoring/`)

**Phase 3 Status:** MarketService (PR #31) is unmerged. This plan does NOT depend on it. DiscoveryService depends only on the `MarketStore` protocol (Phase 1) and `score_markets_batch()` (Phase 4).

**Key Design Decisions:**
1. **Filtering is DiscoveryService's job** — `MarketStore.query_markets()` returns all cached markets; DiscoveryService filters them. This is defensive: works regardless of how smart the store is.
2. **Phase 5 = cached markets only** — `_get_all_cities()` / `_get_all_services()` return `[]`. The city/service enumeration path is Phase 7. Tests only exercise the cached path.
3. **Portfolio/expansion stubs return 400** — `/api/discover` rejects `portfolio_market_ids` and `reference_city_id` with a clear "not yet supported" message instead of silent `pass` blocks.
4. **DI follows existing pattern** — `_get_discovery_service()` lazy singleton in `api.py`, matching `_METRO_DB()` / `_shared_dfs_client()`.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `src/domain/services/discovery_service.py` | DiscoveryService class + `_evaluate_predicate()` filter utility |
| Modify | `src/domain/services/__init__.py` | Export DiscoveryService |
| Modify | `src/research_agent/api.py` | Add `/api/discover`, `/api/lenses` endpoints + DI wiring |
| Create | `tests/domain/services/test_discovery_service.py` | DiscoveryService unit tests (filter predicates, discover flow, portfolio ranking) |
| Create | `tests/unit/test_api_discover.py` | API endpoint tests using `TestClient(app)` + `patch()` |

---

### Task 0: Create Feature Branch

Work on a dedicated branch — never commit Phase 5 directly to `dev`.

- [ ] **Step 1: Create branch**

```bash
git checkout -b phase-5-discovery-service
```

Expected: Clean checkout from current `dev` HEAD.

---

### Task 1: Verify Green Baseline

Confirm all domain and scoring tests pass on the new branch before adding code. If anything is red, stop and fix before proceeding.

- [ ] **Step 1: Run domain + scoring tests**

Run: `python -m pytest tests/domain/ tests/scoring/ -v --tb=short`

Expected: ALL PASS. Record the count (should be ~50+ tests).

If failures exist, investigate and fix before continuing — do not build Phase 5 on a broken baseline.

- [ ] **Step 2: Run lint**

Run: `ruff check src/domain/ src/scoring/`

Expected: Clean (0 errors).

---

### Task 2: TDD — Filter Predicate Utility + DiscoveryService Skeleton

**Files:**
- Create: `src/domain/services/discovery_service.py`
- Create: `tests/domain/services/test_discovery_service.py`

Build the `_evaluate_predicate()` function and the DiscoveryService class skeleton. The predicate evaluator supports `>`, `<`, `>=`, `<=`, `=`, `!=`, `in`, and `like` operators — broader than `scoring.py`'s `_evaluate_filter()` which only handles numeric comparisons.

- [ ] **Step 1: Write failing tests for predicates and filter helpers**

```python
# tests/domain/services/test_discovery_service.py
"""Tests for DiscoveryService — multi-market discovery."""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.domain.entities import City, Market, ScoredMarket, Service
from src.domain.lenses import BALANCED
from src.domain.queries import CityFilter, MarketQuery, ServiceFilter
from src.domain.services.discovery_service import (
    DiscoveryService,
    _evaluate_predicate,
    _passes_city_filters,
    _passes_service_filters,
)


# --- Test data ---

BOISE = City(city_id="boise-id", name="Boise", state="ID", population=235_000)
PHOENIX = City(city_id="phoenix-az", name="Phoenix", state="AZ", population=1_600_000)
SMALL_TOWN = City(city_id="small-ks", name="Smallville", state="KS", population=45_000)

PLUMBING = Service(service_id="plumbing", name="Plumbing", fulfillment_type="physical")
WEB_DESIGN = Service(service_id="web-design", name="Web Design", fulfillment_type="remote")

FULL_SIGNALS: dict[str, dict[str, Any]] = {
    "demand": {"score": 75.0},
    "organic_competition": {"score": 68.0},
    "local_competition": {"score": 55.0},
    "monetization": {"score": 60.0},
    "ai_resilience": {"score": 80.0},
    "gbp": {"score": 45.0},
}


# --- _evaluate_predicate tests ---


def test_predicate_greater_than():
    assert _evaluate_predicate(100, ">", 50) is True
    assert _evaluate_predicate(50, ">", 100) is False


def test_predicate_less_than():
    assert _evaluate_predicate(30, "<", 100) is True
    assert _evaluate_predicate(100, "<", 30) is False


def test_predicate_equality():
    assert _evaluate_predicate("physical", "=", "physical") is True
    assert _evaluate_predicate("remote", "=", "physical") is False


def test_predicate_not_equal():
    assert _evaluate_predicate("remote", "!=", "physical") is True


def test_predicate_gte_lte():
    assert _evaluate_predicate(100, ">=", 100) is True
    assert _evaluate_predicate(99, "<=", 100) is True


def test_predicate_in_operator():
    assert _evaluate_predicate("AZ", "in", ["AZ", "CA", "TX"]) is True
    assert _evaluate_predicate("ID", "in", ["AZ", "CA"]) is False


def test_predicate_like_operator():
    assert _evaluate_predicate("Growth Sunbelt", "like", "sunbelt") is True
    assert _evaluate_predicate("Growth Sunbelt", "like", "arctic") is False


def test_predicate_unknown_operator_raises():
    with pytest.raises(ValueError, match="Unknown filter operator"):
        _evaluate_predicate(1, "~", 1)


# --- Filter helper tests ---


def test_passes_city_filters_population():
    filters = [CityFilter("population", ">", 200_000)]
    assert _passes_city_filters(PHOENIX, filters) is True
    assert _passes_city_filters(SMALL_TOWN, filters) is False


def test_passes_city_filters_state_in():
    filters = [CityFilter("state", "in", ["AZ", "CA"])]
    assert _passes_city_filters(PHOENIX, filters) is True
    assert _passes_city_filters(BOISE, filters) is False


def test_passes_service_filters_fulfillment_type():
    filters = [ServiceFilter("fulfillment_type", "=", "physical")]
    assert _passes_service_filters(PLUMBING, filters) is True
    assert _passes_service_filters(WEB_DESIGN, filters) is False


def test_passes_filters_missing_field_returns_false():
    filters = [CityFilter("nonexistent_field", ">", 0)]
    assert _passes_city_filters(BOISE, filters) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/domain/services/test_discovery_service.py -v --tb=short 2>&1 | head -30`

Expected: ImportError — `discovery_service` module doesn't exist yet.

- [ ] **Step 3: Implement _evaluate_predicate and filter helpers**

```python
# src/domain/services/discovery_service.py
"""DiscoveryService — multi-market query execution.

Given a MarketQuery (filters + lens), discovers and ranks markets.
Powers: strategy pages, city browsing, service browsing, portfolio
recommendations, expansion search — all through MarketQuery.
"""
from __future__ import annotations

import logging
from typing import Any

from src.domain.entities import City, Market, ScoredMarket, Service
from src.domain.lenses import ScoringLens
from src.domain.queries import CityFilter, MarketQuery, ServiceFilter
from src.domain.scoring import score_markets_batch
from src.domain.ports import CityDataProvider, MarketStore, ServiceDataProvider

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Execute multi-market discovery queries against cached market data."""

    def __init__(
        self,
        market_store: MarketStore,
        city_provider: CityDataProvider | None = None,
        service_provider: ServiceDataProvider | None = None,
    ):
        self._market_store = market_store
        self._city_provider = city_provider
        self._service_provider = service_provider

    async def discover(self, query: MarketQuery) -> list[ScoredMarket]:
        raise NotImplementedError("Task 3")

    def _apply_portfolio_ranking(
        self,
        scored: list[ScoredMarket],
        context: list[Market],
    ) -> list[ScoredMarket]:
        raise NotImplementedError("Task 4")


def _evaluate_predicate(value: Any, operator: str, target: Any) -> bool:
    """Evaluate a filter predicate against a value."""
    ops: dict[str, Any] = {
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


def _passes_city_filters(city: City, filters: list[CityFilter]) -> bool:
    """Check if a city passes all filter predicates."""
    for f in filters:
        value = getattr(city, f.field, None)
        if value is None:
            return False
        if not _evaluate_predicate(value, f.operator, f.value):
            return False
    return True


def _passes_service_filters(service: Service, filters: list[ServiceFilter]) -> bool:
    """Check if a service passes all filter predicates."""
    for f in filters:
        value = getattr(service, f.field, None)
        if value is None:
            return False
        if not _evaluate_predicate(value, f.operator, f.value):
            return False
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/domain/services/test_discovery_service.py -v --tb=short`

Expected: ALL PASS (13 tests).

- [ ] **Step 5: Commit**

```bash
git add src/domain/services/discovery_service.py tests/domain/services/test_discovery_service.py
git commit -m "feat(domain): add filter predicate utility and DiscoveryService skeleton"
```

---

### Task 3: TDD — DiscoveryService Core (discover + filtering)

**Files:**
- Modify: `tests/domain/services/test_discovery_service.py`
- Modify: `src/domain/services/discovery_service.py`

Implement the `discover()` method: fetch cached markets → filter by city/service → score → paginate.

- [ ] **Step 1: Write failing tests for discover()**

Append to `tests/domain/services/test_discovery_service.py`:

```python
# --- Fake MarketStore ---


class FakeMarketStore:
    """Returns pre-configured markets regardless of query."""

    def __init__(self, markets: list[Market] | None = None):
        self._markets = markets or []

    def persist_report(self, report: dict[str, Any]) -> str:
        return "fake-id"

    def read_report(self, report_id: str) -> dict[str, Any] | None:
        return None

    def query_markets(self, query: MarketQuery) -> list[Market]:
        return list(self._markets)


def _make_markets() -> list[Market]:
    return [
        Market(city=BOISE, service=PLUMBING, signals=FULL_SIGNALS),
        Market(city=PHOENIX, service=PLUMBING, signals=FULL_SIGNALS),
        Market(city=BOISE, service=WEB_DESIGN, signals=FULL_SIGNALS),
        Market(city=SMALL_TOWN, service=PLUMBING, signals=FULL_SIGNALS),
    ]


@pytest.fixture
def discovery() -> DiscoveryService:
    store = FakeMarketStore(markets=_make_markets())
    return DiscoveryService(market_store=store)


def test_discover_returns_scored_markets(discovery: DiscoveryService):
    query = MarketQuery(lens=BALANCED)
    results = asyncio.run(discovery.discover(query))
    assert len(results) > 0
    assert all(isinstance(r, ScoredMarket) for r in results)


def test_discover_with_city_population_filter(discovery: DiscoveryService):
    query = MarketQuery(
        city_filters=[CityFilter("population", ">", 200_000)],
        lens=BALANCED,
    )
    results = asyncio.run(discovery.discover(query))
    assert len(results) > 0
    for r in results:
        assert r.market.city.population > 200_000


def test_discover_with_service_filter(discovery: DiscoveryService):
    query = MarketQuery(
        service_filters=[ServiceFilter("fulfillment_type", "=", "physical")],
        lens=BALANCED,
    )
    results = asyncio.run(discovery.discover(query))
    assert len(results) > 0
    for r in results:
        assert r.market.service.fulfillment_type == "physical"


def test_discover_combined_filters(discovery: DiscoveryService):
    """City + service filters narrow results to intersection."""
    query = MarketQuery(
        city_filters=[CityFilter("population", ">", 200_000)],
        service_filters=[ServiceFilter("fulfillment_type", "=", "physical")],
        lens=BALANCED,
    )
    results = asyncio.run(discovery.discover(query))
    for r in results:
        assert r.market.city.population > 200_000
        assert r.market.service.fulfillment_type == "physical"


def test_discover_respects_limit(discovery: DiscoveryService):
    query = MarketQuery(lens=BALANCED, limit=2)
    results = asyncio.run(discovery.discover(query))
    assert len(results) <= 2


def test_discover_respects_offset(discovery: DiscoveryService):
    all_results = asyncio.run(discovery.discover(MarketQuery(lens=BALANCED)))
    offset_results = asyncio.run(discovery.discover(MarketQuery(lens=BALANCED, offset=1)))
    assert len(offset_results) == len(all_results) - 1


def test_discover_results_are_ranked(discovery: DiscoveryService):
    query = MarketQuery(lens=BALANCED)
    results = asyncio.run(discovery.discover(query))
    ranks = [r.rank for r in results]
    assert ranks == list(range(1, len(ranks) + 1))


def test_discover_empty_store_returns_empty():
    store = FakeMarketStore(markets=[])
    svc = DiscoveryService(market_store=store)
    results = asyncio.run(svc.discover(MarketQuery(lens=BALANCED)))
    assert results == []


def test_discover_filter_excludes_all_returns_empty(discovery: DiscoveryService):
    query = MarketQuery(
        city_filters=[CityFilter("population", ">", 99_000_000)],
        lens=BALANCED,
    )
    results = asyncio.run(discovery.discover(query))
    assert results == []
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python -m pytest tests/domain/services/test_discovery_service.py::test_discover_returns_scored_markets -v --tb=short`

Expected: FAIL with `NotImplementedError: Task 3`.

- [ ] **Step 3: Implement discover()**

Replace the `discover()` stub in `src/domain/services/discovery_service.py`:

```python
    async def discover(self, query: MarketQuery) -> list[ScoredMarket]:
        """Execute a market discovery query.

        Flow:
        1. Fetch cached markets from MarketStore
        2. Apply city/service filter predicates
        3. Score through lens (score_markets_batch handles errors gracefully)
        4. Apply portfolio ranking if present
        5. Paginate with limit/offset
        """
        markets = self._market_store.query_markets(query)
        logger.info("Discovery: %d cached markets fetched", len(markets))

        if query.has_city_filters():
            markets = [
                m for m in markets
                if _passes_city_filters(m.city, query.city_filters)
            ]

        if query.has_service_filters():
            markets = [
                m for m in markets
                if _passes_service_filters(m.service, query.service_filters)
            ]

        logger.info("Discovery: %d markets after filtering", len(markets))

        if not markets:
            return []

        scored = score_markets_batch(markets, query.lens)

        if query.is_portfolio_query() and query.portfolio_context:
            scored = self._apply_portfolio_ranking(scored, query.portfolio_context)

        return scored[query.offset : query.offset + query.limit]
```

- [ ] **Step 4: Run all discover tests**

Run: `python -m pytest tests/domain/services/test_discovery_service.py -v --tb=short`

Expected: ALL PASS (predicate tests + discover tests; portfolio test still skipped since Task 4).

- [ ] **Step 5: Commit**

```bash
git add src/domain/services/discovery_service.py tests/domain/services/test_discovery_service.py
git commit -m "feat(domain): implement DiscoveryService.discover() with filtering and scoring"
```

---

### Task 4: TDD — Portfolio Ranking

**Files:**
- Modify: `tests/domain/services/test_discovery_service.py`
- Modify: `src/domain/services/discovery_service.py`

Implement `_apply_portfolio_ranking()`: same-city bonus (+5), same-service penalty (-10), re-sort and re-rank.

- [ ] **Step 1: Write failing tests for portfolio ranking**

Append to `tests/domain/services/test_discovery_service.py`:

```python
# --- Portfolio ranking tests ---


def test_portfolio_same_city_bonus():
    """Markets in same city as portfolio entries get a score boost."""
    existing = Market(city=BOISE, service=PLUMBING)
    store = FakeMarketStore(markets=_make_markets())
    svc = DiscoveryService(market_store=store)
    query = MarketQuery(lens=BALANCED, portfolio_context=[existing])
    results = asyncio.run(svc.discover(query))
    boise_markets = [r for r in results if r.market.city.city_id == "boise-id"]
    assert len(boise_markets) > 0
    # Boise markets should rank higher — at least one in top half
    assert min(r.rank for r in boise_markets) <= len(results) // 2


def test_portfolio_same_service_penalty():
    """Markets with same service as portfolio entries get penalized."""
    existing = Market(city=PHOENIX, service=PLUMBING)
    # All 3 plumbing markets get -10 penalty, web-design gets 0
    store = FakeMarketStore(markets=_make_markets())
    svc = DiscoveryService(market_store=store)
    query_with_portfolio = MarketQuery(lens=BALANCED, portfolio_context=[existing])
    query_without = MarketQuery(lens=BALANCED)

    with_portfolio = asyncio.run(svc.discover(query_with_portfolio))
    without = asyncio.run(svc.discover(query_without))

    # Web Design (no penalty) should rank better with portfolio context
    wd_rank_with = next(
        r.rank for r in with_portfolio
        if r.market.service.service_id == "web-design"
    )
    wd_rank_without = next(
        r.rank for r in without
        if r.market.service.service_id == "web-design"
    )
    assert wd_rank_with <= wd_rank_without


def test_portfolio_empty_context_no_change():
    """Empty portfolio context list doesn't alter ranking."""
    store = FakeMarketStore(markets=_make_markets())
    svc = DiscoveryService(market_store=store)
    query = MarketQuery(lens=BALANCED, portfolio_context=[])
    results = asyncio.run(svc.discover(query))
    ranks = [r.rank for r in results]
    assert ranks == list(range(1, len(ranks) + 1))


def test_portfolio_reranked_results_have_sequential_ranks():
    """After portfolio ranking, ranks are sequential starting at 1."""
    existing = Market(city=BOISE, service=PLUMBING)
    store = FakeMarketStore(markets=_make_markets())
    svc = DiscoveryService(market_store=store)
    query = MarketQuery(lens=BALANCED, portfolio_context=[existing])
    results = asyncio.run(svc.discover(query))
    ranks = [r.rank for r in results]
    assert ranks == list(range(1, len(ranks) + 1))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/domain/services/test_discovery_service.py::test_portfolio_same_city_bonus -v --tb=short`

Expected: FAIL with `NotImplementedError: Task 4`.

- [ ] **Step 3: Implement _apply_portfolio_ranking()**

Replace the `_apply_portfolio_ranking()` stub in `src/domain/services/discovery_service.py`:

```python
    def _apply_portfolio_ranking(
        self,
        scored: list[ScoredMarket],
        context: list[Market],
    ) -> list[ScoredMarket]:
        """Re-rank markets considering portfolio context.

        Same-city bonus: +5 (complementarity — can share local knowledge).
        Same-service penalty: -10 (diminishing returns — already doing this).
        Full NAICS similarity scoring is Phase 7.
        """
        if not context:
            return scored

        portfolio_cities = {m.city.city_id for m in context}
        portfolio_services = {m.service.service_id for m in context}

        adjusted: list[ScoredMarket] = []
        for sm in scored:
            bonus = 0.0
            if sm.market.city.city_id in portfolio_cities:
                bonus += 5.0
            if sm.market.service.service_id in portfolio_services:
                bonus -= 10.0
            adjusted.append(ScoredMarket(
                market=sm.market,
                opportunity_score=sm.opportunity_score + bonus,
                lens_id=sm.lens_id,
                score_breakdown=sm.score_breakdown,
            ))

        adjusted.sort(key=lambda s: s.opportunity_score, reverse=True)
        return [
            ScoredMarket(
                market=s.market,
                opportunity_score=s.opportunity_score,
                lens_id=s.lens_id,
                rank=i + 1,
                score_breakdown=s.score_breakdown,
            )
            for i, s in enumerate(adjusted)
        ]
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/domain/services/test_discovery_service.py -v --tb=short`

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add src/domain/services/discovery_service.py tests/domain/services/test_discovery_service.py
git commit -m "feat(domain): add portfolio ranking to DiscoveryService"
```

---

### Task 5: API Endpoints + DI Wiring

**Files:**
- Modify: `src/research_agent/api.py`
- Modify: `src/domain/services/__init__.py`
- Create: `tests/unit/test_api_discover.py`

Add `/api/discover` (POST), `/api/lenses` (GET), and the `_get_discovery_service()` lazy singleton. Tests follow the existing `TestClient(app)` + `patch()` pattern from `test_api_niches.py`.

- [ ] **Step 1: Write failing API tests**

```python
# tests/unit/test_api_discover.py
"""Unit tests for /api/discover and /api/lenses endpoints."""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.domain.entities import City, Market, ScoredMarket, Service
from src.domain.lenses import BALANCED
from src.research_agent.api import app

BOISE = City(city_id="boise-id", name="Boise", state="ID", population=235_000)
PLUMBING = Service(service_id="plumbing", name="Plumbing", fulfillment_type="physical")
SIGNALS: dict[str, dict[str, Any]] = {
    "demand": {"score": 75.0},
    "organic_competition": {"score": 68.0},
    "local_competition": {"score": 55.0},
    "monetization": {"score": 60.0},
    "ai_resilience": {"score": 80.0},
}

SCORED = ScoredMarket(
    market=Market(city=BOISE, service=PLUMBING, signals=SIGNALS),
    opportunity_score=68.5,
    lens_id="balanced",
    rank=1,
    score_breakdown={"demand": 18.75, "organic_competition": 10.2},
)


def test_post_discover_returns_markets():
    """Basic /api/discover returns expected shape."""
    async def _fake_discover(query):
        return [SCORED]

    with patch("src.research_agent.api._get_discovery_service") as mock_svc:
        mock_svc.return_value.discover = _fake_discover
        client = TestClient(app)
        resp = client.post("/api/discover", json={"lens_id": "balanced", "limit": 10})

    assert resp.status_code == 200
    data = resp.json()
    assert "markets" in data
    assert len(data["markets"]) == 1
    assert data["markets"][0]["rank"] == 1
    assert data["markets"][0]["opportunity_score"] == 68.5
    assert data["markets"][0]["city"]["name"] == "Boise"
    assert data["markets"][0]["service"]["name"] == "Plumbing"
    assert data["lens"]["lens_id"] == "balanced"


def test_post_discover_default_lens():
    """Omitting lens_id defaults to balanced."""
    async def _fake_discover(query):
        assert query.lens.lens_id == "balanced"
        return []

    with patch("src.research_agent.api._get_discovery_service") as mock_svc:
        mock_svc.return_value.discover = _fake_discover
        client = TestClient(app)
        resp = client.post("/api/discover", json={})

    assert resp.status_code == 200
    assert resp.json()["markets"] == []


def test_post_discover_with_city_filters():
    """City filters are parsed and forwarded to query."""
    async def _fake_discover(query):
        assert len(query.city_filters) == 1
        assert query.city_filters[0].field == "population"
        assert query.city_filters[0].operator == ">"
        assert query.city_filters[0].value == 200_000
        return []

    with patch("src.research_agent.api._get_discovery_service") as mock_svc:
        mock_svc.return_value.discover = _fake_discover
        client = TestClient(app)
        resp = client.post("/api/discover", json={
            "city_filters": [{"field": "population", "operator": ">", "value": 200_000}],
        })

    assert resp.status_code == 200


def test_post_discover_rejects_portfolio_ids():
    """portfolio_market_ids returns 400 until Phase 7."""
    client = TestClient(app)
    resp = client.post("/api/discover", json={
        "portfolio_market_ids": ["some-id"],
    })
    assert resp.status_code == 400
    assert "not yet supported" in resp.json()["detail"].lower()


def test_post_discover_rejects_reference_city():
    """reference_city_id returns 400 until Phase 7."""
    client = TestClient(app)
    resp = client.post("/api/discover", json={
        "reference_city_id": "some-city",
    })
    assert resp.status_code == 400
    assert "not yet supported" in resp.json()["detail"].lower()


def test_get_lenses_returns_all():
    """/api/lenses returns all 9 lens definitions."""
    client = TestClient(app)
    resp = client.get("/api/lenses")
    assert resp.status_code == 200
    data = resp.json()
    assert "lenses" in data
    assert len(data["lenses"]) == 9
    ids = [lens["lens_id"] for lens in data["lenses"]]
    assert "balanced" in ids
    assert "easy_win" in ids
    assert "gbp_blitz" in ids


def test_get_lenses_shape():
    """/api/lenses entries have expected fields."""
    client = TestClient(app)
    resp = client.get("/api/lenses")
    lens = resp.json()["lenses"][0]
    assert "lens_id" in lens
    assert "name" in lens
    assert "description" in lens
    assert "weights" in lens
    assert isinstance(lens["weights"], dict)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_api_discover.py -v --tb=short 2>&1 | head -20`

Expected: 404 errors — endpoints don't exist yet.

- [ ] **Step 3: Add DI wiring + Pydantic models to api.py**

First, update the Pydantic import at the top of `src/research_agent/api.py` (line 22) to include `Field`:

```python
from pydantic import BaseModel, Field, field_validator
```

Then add the following to `src/research_agent/api.py`, near the other singleton helpers (after the existing `_shared_dfs_client()` area):

```python
# --- Discovery Service singleton ---

from src.domain.services.discovery_service import DiscoveryService
from src.domain.ports import MarketStore as MarketStoreProtocol
from src.domain.queries import MarketQuery, CityFilter, ServiceFilter


class _NullMarketStore:
    """Returns empty results until a real MarketStore adapter is wired."""

    def persist_report(self, report: dict[str, Any]) -> str:
        return ""

    def read_report(self, report_id: str) -> dict[str, Any] | None:
        return None

    def query_markets(self, query: Any) -> list:
        return []


_DISCOVERY_SERVICE: DiscoveryService | None = None


def _get_discovery_service() -> DiscoveryService:
    global _DISCOVERY_SERVICE
    if _DISCOVERY_SERVICE is None:
        _DISCOVERY_SERVICE = DiscoveryService(market_store=_NullMarketStore())
    return _DISCOVERY_SERVICE
```

- [ ] **Step 4: Add /api/discover endpoint to api.py**

```python
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
    """Multi-market discovery — filters, lenses, ranking."""
    if req.portfolio_market_ids:
        raise HTTPException(
            status_code=400,
            detail="portfolio_market_ids not yet supported (Phase 7)",
        )
    if req.reference_city_id:
        raise HTTPException(
            status_code=400,
            detail="reference_city_id not yet supported (Phase 7)",
        )

    from src.domain.lenses import get_lens

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

    svc = _get_discovery_service()
    results = await svc.discover(query)

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
```

- [ ] **Step 5: Add /api/lenses endpoint to api.py**

```python
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

- [ ] **Step 6: Update services/__init__.py**

```python
# src/domain/services/__init__.py
from src.domain.services.geo_resolver import GeoResolutionError, GeoResolver, ResolvedTarget
from src.domain.services.discovery_service import DiscoveryService

__all__ = [
    "DiscoveryService",
    "GeoResolver",
    "GeoResolutionError",
    "ResolvedTarget",
]
```

- [ ] **Step 7: Verify api.py imports cleanly**

Run: `python -c "from src.research_agent.api import app; print('OK')"` 

Expected: Prints `OK` with no errors. If `NameError` or `ImportError`, check the `Field` import and module-level `DiscoveryService` import.

- [ ] **Step 8: Run API tests**

Run: `python -m pytest tests/unit/test_api_discover.py -v --tb=short`

Expected: ALL PASS (8 tests).

- [ ] **Step 9: Commit**

```bash
git add src/research_agent/api.py src/domain/services/__init__.py \
  src/domain/services/discovery_service.py tests/unit/test_api_discover.py
git commit -m "feat(api): add /api/discover and /api/lenses endpoints

DiscoveryService wired via _NullMarketStore (returns empty until
Phase 3 SupabaseMarketStore merges). Portfolio/expansion queries
return 400 until Phase 7 data providers."
```

---

### Task 6: Full Suite Verification

**Files:** None — verification only.

- [ ] **Step 1: Run all domain + scoring tests**

Run: `python -m pytest tests/domain/ tests/scoring/ -v --tb=short`

Expected: ALL PASS. Count should be baseline + ~25 new tests.

- [ ] **Step 2: Run all API tests**

Run: `python -m pytest tests/unit/test_api_discover.py tests/unit/test_api_niches.py tests/unit/test_api_metros_suggest.py tests/unit/test_api_places_suggest.py -v --tb=short`

Expected: ALL PASS. No regressions in existing API tests.

- [ ] **Step 3: Run lint**

Run: `ruff check src/domain/services/discovery_service.py src/research_agent/api.py tests/domain/services/test_discovery_service.py tests/unit/test_api_discover.py`

Expected: Clean (0 errors). Fix any issues and re-run.

- [ ] **Step 4: Run full test suite to check for regressions**

Run: `python -m pytest tests/unit/ tests/domain/ tests/scoring/ -v --tb=short`

Expected: ALL PASS except pre-existing `test_api_reports.py` failures (confirmed not caused by Phase 5 in prior phases).

- [ ] **Step 5: Verify domain import rules**

Run: `grep -r "from src.clients" src/domain/ && echo "FAIL: domain imports clients" || echo "PASS: clean domain boundary"`

Expected: PASS — domain layer must not import from clients layer.

---

## Done Criteria

- [ ] `/api/discover` endpoint works with lens, city filters, service filters
- [ ] `/api/lenses` endpoint returns all 9 lens definitions
- [ ] DiscoveryService filters cached markets post-fetch (doesn't trust store to filter)
- [ ] Portfolio context applies same-city bonus (+5) and same-service penalty (-10)
- [ ] Results are ranked with sequential ranks starting at 1
- [ ] Limit/offset pagination works
- [ ] `portfolio_market_ids` and `reference_city_id` return 400 with clear message
- [ ] Empty store returns empty list (not an error)
- [ ] No existing endpoints modified
- [ ] All tests pass, lint clean
- [ ] Domain layer has no client imports

## Phase 7 Integration Notes

When Phase 3 (MarketService) merges:
- Replace `_NullMarketStore` in `_get_discovery_service()` with `SupabaseMarketStore`
- Optionally inject MarketService for on-demand scoring of uncached markets

When Phase 7 (data providers) ships:
- Implement `CityDataProvider` and `ServiceDataProvider` adapters
- Wire into DiscoveryService constructor
- Enable `portfolio_market_ids` and `reference_city_id` in `/api/discover`
- `_get_all_cities()` / `_get_all_services()` return real data from Census/BLS
