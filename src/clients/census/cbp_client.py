"""Census County Business Patterns API client.

Fetches establishment counts by NAICS code at the MSA level.
Docs: https://api.census.gov/data/2021/cbp
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CBP_BASE_URL = "https://api.census.gov/data/{year}/cbp"


class CBPClient:
    """Fetches establishment data from Census CBP API."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    async def fetch_establishments_by_msa(
        self,
        naics_codes: list[str] | None = None,
        year: int = 2021,
    ) -> list[dict[str, Any]]:
        """Fetch establishment counts by MSA and NAICS code."""
        url = CBP_BASE_URL.format(year=year)
        params: dict[str, str] = {
            "get": "ESTAB,EMP,PAYANN,NAICS2017",
            "for": "metropolitan statistical area/micropolitan statistical area:*",
        }
        if naics_codes:
            params["NAICS2017"] = ",".join(naics_codes)
        if self._api_key:
            params["key"] = self._api_key

        logger.info(
            "CBPClient.fetch_establishments START year=%d naics=%s",
            year, naics_codes,
        )

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        headers = data[0]
        results: list[dict[str, Any]] = []
        for row in data[1:]:
            record = dict(zip(headers, row))
            results.append({
                "cbsa_code": record.get(
                    "metropolitan statistical area/micropolitan statistical area"
                ),
                "naics": record.get("NAICS2017"),
                "establishments": int(record.get("ESTAB", 0)),
                "employees": int(record.get("EMP", 0)),
                "payroll_thousands": int(record.get("PAYANN", 0)),
                "year": year,
            })

        logger.info("CBPClient.fetch_establishments DONE count=%d", len(results))
        return results

    async def compute_establishment_growth(
        self,
        cbsa_code: str,
        naics: str,
        year_old: int = 2017,
        year_new: int = 2021,
    ) -> float | None:
        """Annualized establishment growth rate between two CBP years."""
        old_data = await self.fetch_establishments_by_msa([naics], year_old)
        new_data = await self.fetch_establishments_by_msa([naics], year_new)

        old_count = next(
            (d["establishments"] for d in old_data if d["cbsa_code"] == cbsa_code),
            None,
        )
        new_count = next(
            (d["establishments"] for d in new_data if d["cbsa_code"] == cbsa_code),
            None,
        )

        if not old_count or not new_count or old_count == 0:
            return None

        span = year_new - year_old
        return (new_count / old_count) ** (1 / span) - 1
