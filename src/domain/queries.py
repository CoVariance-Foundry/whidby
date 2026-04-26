from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.entities import City, Market
from src.domain.lenses import ScoringLens, BALANCED


@dataclass(frozen=True)
class CityFilter:
    field: str
    operator: str
    value: Any


@dataclass(frozen=True)
class ServiceFilter:
    field: str
    operator: str
    value: Any


@dataclass
class MarketQuery:
    city_filters: list[CityFilter] = field(default_factory=list)
    service_filters: list[ServiceFilter] = field(default_factory=list)
    lens: ScoringLens = field(default_factory=lambda: BALANCED)
    portfolio_context: list[Market] | None = None
    reference_city: City | None = None
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
