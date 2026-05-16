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
from src.domain.strategy_projection import (
    project_ai_resilience_warning,
    project_expand_conquer,
    project_easy_win,
    project_gbp_blitz,
    project_keyword_hijack,
)

logger = logging.getLogger(__name__)

_STRATEGY_PROJECTIONS = {
    "easy_win": project_easy_win,
    "gbp_blitz": project_gbp_blitz,
    "keyword_hijack": project_keyword_hijack,
    "expand_conquer": project_expand_conquer,
}


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
            markets = [m for m in markets if _passes_city_filters(m.city, query.city_filters)]

        if query.has_service_filters():
            markets = [
                m for m in markets if _passes_service_filters(m.service, query.service_filters)
            ]

        logger.info("Discovery: %d markets after filtering", len(markets))

        if not markets:
            return []

        if query.lens.lens_id in _STRATEGY_PROJECTIONS:
            scored = _score_strategy_markets(
                markets,
                query.lens.lens_id,
                ai_resilience_filter=query.ai_resilience_filter,
            )
        else:
            scored = score_markets_batch(markets, query.lens)

        if query.is_portfolio_query() and query.portfolio_context:
            scored = self._apply_portfolio_ranking(scored, query.portfolio_context)

        return scored[query.offset : query.offset + query.limit]

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
            adjusted.append(
                ScoredMarket(
                    market=sm.market,
                    opportunity_score=sm.opportunity_score + bonus,
                    lens_id=sm.lens_id,
                    score_breakdown=sm.score_breakdown,
                    strategy_evidence=sm.strategy_evidence,
                    warnings=sm.warnings,
                )
            )

        adjusted.sort(key=lambda s: s.opportunity_score, reverse=True)
        return [
            ScoredMarket(
                market=s.market,
                opportunity_score=s.opportunity_score,
                lens_id=s.lens_id,
                rank=i + 1,
                score_breakdown=s.score_breakdown,
                strategy_evidence=s.strategy_evidence,
                warnings=s.warnings,
            )
            for i, s in enumerate(adjusted)
        ]


def _score_strategy_markets(
    markets: list[Market],
    lens_id: str,
    *,
    ai_resilience_filter: bool = False,
) -> list[ScoredMarket]:
    """Project, sort, and rank markets for launch strategy lenses."""
    scored = [
        projected
        for market in markets
        if (
            projected := _project_strategy_market(
                market,
                lens_id,
                ai_resilience_filter=ai_resilience_filter,
            )
        )
        is not None
    ]
    skipped = len(markets) - len(scored)
    if skipped:
        logger.warning(
            "Discovery: skipped %d markets without usable %s strategy rows",
            skipped,
            lens_id,
        )
    scored.sort(key=lambda s: s.opportunity_score, reverse=True)
    return [
        ScoredMarket(
            market=s.market,
            opportunity_score=s.opportunity_score,
            lens_id=s.lens_id,
            rank=i + 1,
            score_breakdown=s.score_breakdown,
            strategy_evidence=s.strategy_evidence,
            warnings=s.warnings,
        )
        for i, s in enumerate(scored)
    ]


def _project_strategy_market(
    market: Market,
    lens_id: str,
    *,
    ai_resilience_filter: bool = False,
) -> ScoredMarket | None:
    """Build a ScoredMarket from a cached strategy projection row."""
    projection_fn = _STRATEGY_PROJECTIONS.get(lens_id)
    if projection_fn is None:
        return None

    strategy_row = market.signals.get("strategy_row")
    if not isinstance(strategy_row, dict):
        return None

    try:
        projection = projection_fn(strategy_row)
    except (TypeError, ValueError) as exc:
        logger.warning(
            "Discovery: skipped malformed strategy row lens=%s city_id=%s service_id=%s error=%s",
            lens_id,
            market.city.city_id,
            market.service.service_id,
            exc,
        )
        return None
    warnings = list(projection.warnings)
    if ai_resilience_filter:
        ai_warning = project_ai_resilience_warning(strategy_row)
        if ai_warning:
            warnings.append(ai_warning["code"])
    return ScoredMarket(
        market=market,
        opportunity_score=projection.score,
        lens_id=projection.strategy_id,
        score_breakdown={"projection_score": projection.score},
        strategy_evidence=projection.evidence,
        warnings=warnings,
    )


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
