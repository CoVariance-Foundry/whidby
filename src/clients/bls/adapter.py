"""Adapter implementing ServiceDataProvider (ACV) from BLS wage data."""
from __future__ import annotations

import logging

from src.domain.entities import SeasonalityCurve
from src.clients.bls.client import BLSClient
from src.clients.bls.naics_soc_map import (
    compute_acv,
    get_soc_for_naics,
)

logger = logging.getLogger(__name__)


class BLSServiceDataProvider:
    """Partial ServiceDataProvider for ACV estimates from BLS wages."""

    def __init__(self, client: BLSClient):
        self._client = client
        self._cache: dict[str, float] = {}

    def get_acv_estimate(self, naics: str, city_id: str) -> float | None:
        key = f"{naics}:{city_id}"
        local = self._cache.get(key)
        if local is not None:
            return local
        return self._cache.get(f"{naics}:national")

    def get_seasonality(self, service_name: str) -> SeasonalityCurve | None:
        return None

    def get_establishment_growth(
        self, naics: str, city_id: str
    ) -> float | None:
        return None

    async def load_acv_for_naics(
        self, naics: str, area_code: str = "0000000"
    ) -> float | None:
        """Fetch wages and compute ACV for a NAICS code."""
        mapping = get_soc_for_naics(naics)
        if mapping is None:
            logger.warning("No SOC mapping for NAICS %s", naics)
            return None

        wages = await self._client.fetch_occupation_wages(
            mapping.soc, area_code
        )
        if wages is None:
            return None

        acv = compute_acv(
            wages["mean_hourly_wage"],
            mapping.avg_job_hours,
            mapping.overhead_multiplier,
        )

        city_key = "national" if area_code == "0000000" else area_code
        self._cache[f"{naics}:{city_key}"] = acv

        logger.info(
            "BLS ACV loaded naics=%s area=%s wage=%.2f acv=%.2f",
            naics, area_code, wages["mean_hourly_wage"], acv,
        )
        return acv

    async def load_all_national(self) -> None:
        """Load national-level ACV for all mapped NAICS codes."""
        from src.clients.bls.naics_soc_map import NAICS_SOC_MAP

        for naics in NAICS_SOC_MAP:
            await self.load_acv_for_naics(naics)
        logger.info(
            "BLSServiceDataProvider loaded %d national ACVs",
            len(self._cache),
        )
