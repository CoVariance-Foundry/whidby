"""Adapter implementing CityDataProvider using Census ACS data."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from src.domain.entities import City
from src.clients.census.client import CensusClient

logger = logging.getLogger(__name__)


class CensusCityDataProvider:
    """Implements CityDataProvider (demographics + similarity) using Census ACS."""

    def __init__(self, client: CensusClient):
        self._client = client
        self._cache: dict[str, dict[str, Any]] = {}

    def get_demographics(self, city_id: str) -> dict[str, Any] | None:
        return self._cache.get(city_id)

    def get_business_density(
        self, city_id: str, naics: str | None = None
    ) -> dict[str, Any] | None:
        return None

    def find_similar_cities(
        self, reference: City, limit: int = 10
    ) -> list[tuple[City, float]]:
        """Cosine similarity on demographic vectors.

        Vector: [log(population), median_income, homeownership_rate,
                 growth_rate, broadband_penetration]
        """
        ref_vector = self._city_to_vector(reference)
        if ref_vector is None:
            return []

        similarities: list[tuple[City, float]] = []
        for city_id, data in self._cache.items():
            if city_id == reference.city_id:
                continue
            city = self._data_to_city(city_id, data)
            vec = self._city_to_vector(city)
            if vec is None:
                continue
            sim = _cosine_similarity(ref_vector, vec)
            similarities.append((city, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]

    async def load_all(self) -> None:
        """Bulk load all MSA demographics into cache."""
        results = await self._client.fetch_msa_demographics()
        for r in results:
            self._cache[r["cbsa_code"]] = r
        logger.info("CensusCityDataProvider loaded %d MSAs", len(self._cache))

    @staticmethod
    def _city_to_vector(city: City) -> list[float] | None:
        if city.population is None or city.median_income is None:
            return None
        return [
            np.log(city.population) if city.population > 0 else 0.0,
            float(city.median_income or 0),
            float(city.homeownership_rate or 0),
            float(city.growth_rate or 0),
            float(city.broadband_penetration or 0),
        ]

    @staticmethod
    def _data_to_city(city_id: str, data: dict[str, Any]) -> City:
        pop = data.get("total_population")
        owner = data.get("owner_occupied_units")
        total_housing = data.get("total_housing_units")
        broadband = data.get("broadband_subscriptions")
        internet_total = data.get("total_internet_universe")

        return City(
            city_id=city_id,
            name=data.get("name", ""),
            population=pop,
            median_income=data.get("median_household_income"),
            homeownership_rate=(
                owner / total_housing if owner and total_housing else None
            ),
            housing_age_median=(
                2024 - data["median_year_built"]
                if data.get("median_year_built")
                else None
            ),
            broadband_penetration=(
                broadband / internet_total
                if broadband and internet_total
                else None
            ),
            cbsa_code=city_id,
        )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if norm == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / norm)
