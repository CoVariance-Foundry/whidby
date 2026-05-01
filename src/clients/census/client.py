"""Census Bureau ACS 5-Year Estimates API client.

Fetches demographic data at the MSA level. Free API — optional key for higher rate limits.
Docs: https://api.census.gov/data/2022/acs/acs5
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ACS_BASE_URL = "https://api.census.gov/data/{year}/acs/acs5"

DEMOGRAPHIC_VARIABLES = {
    "B01003_001E": "total_population",
    "B19013_001E": "median_household_income",
    "B25003_001E": "total_housing_units",
    "B25003_002E": "owner_occupied_units",
    "B25035_001E": "median_year_built",
    "B28002_004E": "broadband_subscriptions",
    "B28002_001E": "total_internet_universe",
}

SENTINEL_NULL = -666666666


class CensusClient:
    """Fetches demographic data from the Census ACS API."""

    def __init__(self, api_key: str | None = None, year: int = 2022):
        self._api_key = api_key
        self._year = year
        self._base_url = ACS_BASE_URL.format(year=year)

    async def fetch_msa_demographics(
        self, cbsa_codes: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch demographic data for MSAs.

        If cbsa_codes is None, fetches all MSAs.
        Returns list of dicts with normalized field names.
        """
        variables = ",".join(DEMOGRAPHIC_VARIABLES.keys())
        params: dict[str, str] = {
            "get": f"NAME,{variables}",
            "for": "metropolitan statistical area/micropolitan statistical area:*",
        }
        if self._api_key:
            params["key"] = self._api_key

        logger.info(
            "CensusClient.fetch_msa_demographics START year=%d vars=%d",
            self._year,
            len(DEMOGRAPHIC_VARIABLES),
        )

        async with httpx.AsyncClient() as client:
            resp = await client.get(self._base_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        headers = data[0]
        results: list[dict[str, Any]] = []
        for row in data[1:]:
            record = dict(zip(headers, row))
            cbsa = record.get(
                "metropolitan statistical area/micropolitan statistical area"
            )
            if cbsa_codes and cbsa not in cbsa_codes:
                continue

            normalized: dict[str, Any] = {
                "cbsa_code": cbsa,
                "name": record.get("NAME", ""),
            }
            for var_code, field_name in DEMOGRAPHIC_VARIABLES.items():
                raw = record.get(var_code)
                if raw is None or int(raw) == SENTINEL_NULL:
                    normalized[field_name] = None
                else:
                    normalized[field_name] = int(raw)

            results.append(normalized)

        logger.info(
            "CensusClient.fetch_msa_demographics DONE count=%d", len(results)
        )
        return results

    async def fetch_population_for_year(
        self, cbsa_code: str, year: int
    ) -> int | None:
        """Fetch total population for a single MSA in a given ACS year."""
        url = ACS_BASE_URL.format(year=year)
        params: dict[str, str] = {
            "get": "B01003_001E",
            "for": f"metropolitan statistical area/micropolitan statistical area:{cbsa_code}",
        }
        if self._api_key:
            params["key"] = self._api_key

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        if len(data) < 2:
            return None
        raw = data[1][0]
        if raw is None or int(raw) == SENTINEL_NULL:
            return None
        return int(raw)

    async def compute_growth_rate(
        self,
        cbsa_code: str,
        year_old: int = 2017,
        year_new: int = 2022,
    ) -> float | None:
        """Annualized population growth rate between two ACS years."""
        pop_old = await self.fetch_population_for_year(cbsa_code, year_old)
        pop_new = await self.fetch_population_for_year(cbsa_code, year_new)

        if not pop_old or not pop_new or pop_old == 0:
            return None

        span = year_new - year_old
        return (pop_new / pop_old) ** (1 / span) - 1
