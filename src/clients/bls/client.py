"""BLS Occupational Employment & Wage Statistics (OEWS) API client.

Fetches mean hourly wages by occupation and area.
API v2 docs: https://www.bls.gov/developers/api_signature_v2.htm
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


class BLSClient:
    """Fetches occupation wage data from BLS OEWS."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    async def fetch_occupation_wages(
        self,
        soc_code: str,
        area_code: str = "0000000",
        start_year: int = 2023,
        end_year: int = 2023,
    ) -> dict[str, Any] | None:
        """Fetch mean hourly wage for an occupation in an area.

        Series ID format: OEUM{area}{industry}{occupation}{datatype}
        Data type 04 = Mean hourly wage.
        """
        series_id = f"OEUM{area_code}000000{soc_code}04"
        payload: dict[str, Any] = {
            "seriesid": [series_id],
            "startyear": str(start_year),
            "endyear": str(end_year),
        }
        if self._api_key:
            payload["registrationkey"] = self._api_key

        logger.info(
            "BLSClient.fetch_occupation_wages START soc=%s area=%s",
            soc_code, area_code,
        )

        async with httpx.AsyncClient() as client:
            resp = await client.post(BLS_API_URL, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "REQUEST_SUCCEEDED":
            logger.warning("BLS request failed: %s", data.get("message"))
            return None

        series = data.get("Results", {}).get("series", [])
        if not series or not series[0].get("data"):
            return None

        latest = series[0]["data"][0]
        result = {
            "soc_code": soc_code,
            "area_code": area_code,
            "mean_hourly_wage": float(latest["value"]),
            "year": int(latest["year"]),
        }
        logger.info(
            "BLSClient.fetch_occupation_wages DONE wage=%.2f",
            result["mean_hourly_wage"],
        )
        return result
