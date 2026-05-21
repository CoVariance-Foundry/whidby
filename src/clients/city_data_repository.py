"""Supabase-backed CityDataProvider adapter for loaded Census CBP rows."""
from __future__ import annotations

import logging
from typing import Any, Protocol

from src.domain.entities import City

logger = logging.getLogger(__name__)


class _SupabaseLike(Protocol):
    def table(self, name: str) -> Any:
        """Return a PostgREST query builder."""
        ...


_CBP_COLUMNS = "cbsa_code,naics_code,naics_label,year,est,suppressed,loaded_at"


class SupabaseCityDataProvider:
    """Reads CBP business-density facts through the CityDataProvider boundary."""

    def __init__(self, *, client: _SupabaseLike) -> None:
        self._client = client

    def get_demographics(self, city_id: str) -> dict[str, Any] | None:
        return None

    def get_business_density(
        self, city_id: str, naics: str | None = None
    ) -> dict[str, Any]:
        if not naics:
            return {}

        try:
            response = (
                self._client.table("census_cbp_establishments")
                .select(_CBP_COLUMNS)
                .eq("cbsa_code", city_id)
                .eq("naics_code", naics)
                .order("year", desc=True)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.warning(
                "CBP business density lookup failed for city_id=%s naics=%s",
                city_id,
                naics,
                exc_info=True,
            )
            return {}
        rows = getattr(response, "data", None) or []
        if not rows:
            return {}

        row = rows[0]
        return {
            "establishments": row.get("est"),
            "cbsa_code": row.get("cbsa_code"),
            "naics_code": row.get("naics_code"),
            "naics_label": row.get("naics_label"),
            "year": row.get("year"),
            "suppressed": row.get("suppressed"),
            "loaded_at": row.get("loaded_at"),
            "source_table": "census_cbp_establishments",
        }

    def find_similar_cities(
        self, reference: City, limit: int = 10
    ) -> list[tuple[City, float]]:
        return []
