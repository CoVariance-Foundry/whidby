"""Adapter implementing CityDataProvider (business density) from Census CBP."""
from __future__ import annotations

import logging
from typing import Any

from src.domain.entities import City
from src.clients.census.cbp_client import CBPClient

logger = logging.getLogger(__name__)


class CBPCityDataProvider:
    """Partial CityDataProvider for business density and establishment growth."""

    def __init__(self, client: CBPClient):
        self._client = client
        self._cache: dict[str, dict[str, Any]] = {}

    def get_demographics(self, city_id: str) -> dict[str, Any] | None:
        return None

    def get_business_density(
        self, city_id: str, naics: str | None = None
    ) -> dict[str, Any] | None:
        key = f"{city_id}:{naics or 'all'}"
        return self._cache.get(key)

    def find_similar_cities(
        self, reference: City, limit: int = 10
    ) -> list[tuple[City, float]]:
        return []

    async def load_msa_data(
        self, naics_codes: list[str] | None = None, year: int = 2021
    ) -> None:
        """Bulk load establishment data into cache."""
        results = await self._client.fetch_establishments_by_msa(naics_codes, year)
        for r in results:
            cbsa = r["cbsa_code"]
            naics = r["naics"]
            key = f"{cbsa}:{naics}"
            self._cache[key] = {
                "establishments": r["establishments"],
                "employees": r["employees"],
                "payroll_thousands": r["payroll_thousands"],
                "density": r["establishments"],
                "year": r["year"],
            }
            all_key = f"{cbsa}:all"
            if all_key not in self._cache:
                self._cache[all_key] = {
                    "establishments": 0, "employees": 0,
                    "payroll_thousands": 0, "density": 0, "year": year,
                }
            self._cache[all_key]["establishments"] += r["establishments"]
            self._cache[all_key]["employees"] += r["employees"]
            self._cache[all_key]["payroll_thousands"] += r["payroll_thousands"]
            self._cache[all_key]["density"] += r["establishments"]

        logger.info(
            "CBPCityDataProvider loaded %d entries", len(self._cache)
        )
