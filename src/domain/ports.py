from __future__ import annotations

from typing import Any, Protocol

from src.domain.entities import City, Market, SeasonalityCurve
from src.domain.queries import MarketQuery


class SERPDataProvider(Protocol):
    async def fetch_keyword_volume(
        self, keywords: list[str], location_code: int
    ) -> list[dict[str, Any]]: ...

    async def fetch_serp_organic(
        self, keyword: str, location_code: int
    ) -> dict[str, Any]: ...


class KeywordExpander(Protocol):
    async def expand(self, niche: str) -> dict[str, Any]: ...


class CityDataProvider(Protocol):
    def get_demographics(self, city_id: str) -> dict[str, Any] | None: ...
    def get_business_density(
        self, city_id: str, naics: str | None = None
    ) -> dict[str, Any] | None: ...
    def find_similar_cities(
        self, reference: City, limit: int = 10
    ) -> list[tuple[City, float]]: ...


class ServiceDataProvider(Protocol):
    def get_acv_estimate(self, naics: str, city_id: str) -> float | None: ...
    def get_seasonality(self, service_name: str) -> SeasonalityCurve | None: ...
    def get_establishment_growth(
        self, naics: str, city_id: str
    ) -> float | None: ...


class MarketStore(Protocol):
    def persist_report(self, report: dict[str, Any]) -> str: ...
    def read_report(self, report_id: str) -> dict[str, Any] | None: ...
    def query_markets(self, query: MarketQuery) -> list[Market]: ...


class KnowledgeStore(Protocol):
    def upsert_entity(self, key: Any) -> str: ...
    def create_snapshot(self, entity_id: str, **kwargs: Any) -> str: ...
    def store_evidence(
        self, snapshot_id: str, artifact_type: str, payload: Any
    ) -> None: ...
    def link_report(
        self, *, report_id: str, entity_id: str, snapshot_id: str
    ) -> None: ...
    def insert_feedback(self, row: dict[str, Any]) -> str: ...


class GeoLookup(Protocol):
    def find_by_city(
        self, city: str, state: str | None = None
    ) -> City | None: ...
    def all_metros(self) -> list[City]: ...


class CostLogger(Protocol):
    def log(self, provider: str, operation: str, cost: float) -> None: ...
