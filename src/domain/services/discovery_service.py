"""DiscoveryService — multi-market query execution.

Given a MarketQuery (filters + lens), discovers and ranks markets.
Powers: strategy pages, city browsing, service browsing, portfolio
recommendations, expansion search — all through MarketQuery.
"""
from __future__ import annotations

import logging
from typing import Any

from src.domain.entities import City, Market, ScoredMarket, Service
from src.domain.queries import CityFilter, MarketQuery, ServiceFilter
from src.domain.ports import CityDataProvider, MarketStore, ServiceDataProvider
from src.domain.scoring import score_markets_batch

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
