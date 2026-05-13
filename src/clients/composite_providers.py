"""Composite data providers — compose sub-providers into full Protocol interfaces.

Census ACS (demographics) + CBP (business density) → CompositeCityDataProvider
BLS (ACV) + Trends (seasonality) + CBP (growth) → CompositeServiceDataProvider
"""
from __future__ import annotations

from typing import Any

from src.domain.entities import City, SeasonalityCurve
from src.clients.census.adapter import CensusCityDataProvider
from src.clients.census.cbp_adapter import CBPCityDataProvider
from src.clients.bls.adapter import BLSServiceDataProvider
from src.clients.trends.adapter import TrendsServiceDataProvider


class CompositeCityDataProvider:
    """Combines Census ACS (demographics) + CBP (business density)."""

    def __init__(
        self,
        acs: CensusCityDataProvider,
        cbp: CBPCityDataProvider | None = None,
    ):
        self._acs = acs
        self._cbp = cbp

    def get_demographics(self, city_id: str) -> dict[str, Any] | None:
        return self._acs.get_demographics(city_id)

    def get_business_density(
        self, city_id: str, naics: str | None = None
    ) -> dict[str, Any] | None:
        if self._cbp is None:
            return None
        return self._cbp.get_business_density(city_id, naics)

    def find_similar_cities(
        self, reference: City, limit: int = 10
    ) -> list[tuple[City, float]]:
        return self._acs.find_similar_cities(reference, limit)


class CompositeServiceDataProvider:
    """Combines BLS (ACV) + Trends (seasonality)."""

    def __init__(
        self,
        bls: BLSServiceDataProvider | None = None,
        trends: TrendsServiceDataProvider | None = None,
    ):
        self._bls = bls
        self._trends = trends

    def get_acv_estimate(self, naics: str, city_id: str) -> float | None:
        if self._bls is None:
            return None
        return self._bls.get_acv_estimate(naics, city_id)

    def get_seasonality(self, service_name: str) -> SeasonalityCurve | None:
        if self._trends is None:
            return None
        return self._trends.get_seasonality(service_name)

    def get_establishment_growth(
        self, naics: str, city_id: str
    ) -> float | None:
        return None
