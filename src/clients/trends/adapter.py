"""Adapter implementing ServiceDataProvider (seasonality) from DataForSEO Trends."""
from __future__ import annotations

import logging
from typing import Any, Protocol

from src.domain.entities import SeasonalityCurve

logger = logging.getLogger(__name__)


class TrendsDataSource(Protocol):
    """Protocol for the trends data source (DataForSEO or fake).

    DataForSEOClient.google_trends() returns APIResponse (dataclass with
    .data containing the raw JSON dict). Fakes should return objects with
    a .data attribute matching this structure.
    """
    async def google_trends(
        self, keywords: list[str], **kwargs: Any
    ) -> Any: ...


class TrendsServiceDataProvider:
    """Partial ServiceDataProvider for seasonality from Google Trends via DataForSEO."""

    def __init__(self, client: TrendsDataSource):
        self._client = client
        self._cache: dict[str, SeasonalityCurve] = {}

    def get_acv_estimate(self, naics: str, city_id: str) -> float | None:
        return None

    def get_seasonality(self, service_name: str) -> SeasonalityCurve | None:
        return self._cache.get(service_name.lower())

    def get_establishment_growth(
        self, naics: str, city_id: str
    ) -> float | None:
        return None

    async def load_seasonality(
        self, service_name: str, location_code: int = 2840
    ) -> SeasonalityCurve | None:
        """Fetch interest-over-time from DataForSEO and build a SeasonalityCurve."""
        logger.info(
            "TrendsServiceDataProvider.load_seasonality START keyword=%s",
            service_name,
        )

        response = await self._client.google_trends(
            keywords=[service_name],
            location_code=location_code,
        )

        # DataForSEOClient returns APIResponse(data=...) — extract raw dict
        raw = response.data if hasattr(response, "data") else response
        monthly = self._extract_monthly_averages(raw)
        if not monthly:
            logger.warning("No trends data for '%s'", service_name)
            return None

        peak_month = max(monthly, key=monthly.get)
        trough_month = min(monthly, key=monthly.get)
        max_val = max(monthly.values())
        amplitude = (
            (monthly[peak_month] - monthly[trough_month]) / max_val
            if max_val > 0
            else 0
        )

        normalized = {
            m: v / max_val if max_val > 0 else 0.0
            for m, v in monthly.items()
        }

        curve = SeasonalityCurve(
            monthly_index=normalized,
            peak_month=peak_month,
            trough_month=trough_month,
            amplitude=amplitude,
        )
        self._cache[service_name.lower()] = curve

        logger.info(
            "TrendsServiceDataProvider.load_seasonality DONE peak=%d trough=%d amp=%.2f",
            peak_month, trough_month, amplitude,
        )
        return curve

    @staticmethod
    def _extract_monthly_averages(
        response: Any,
    ) -> dict[int, float] | None:
        """Extract monthly averages from DataForSEO Trends response.

        Response: tasks[0].result[0].items[] where each item of type
        "google_trends_graph" has data[] with {date_from, values[]}.
        Values are 0-100 interest index per keyword.
        We average each month across years to get a seasonal profile.
        """
        try:
            tasks = response.get("tasks", [])
            if not tasks:
                return None
            result = tasks[0].get("result", [])
            if not result:
                return None
            items = result[0].get("items", [])
            if not items:
                return None
        except (AttributeError, IndexError, TypeError):
            return None

        month_sums: dict[int, float] = {}
        month_counts: dict[int, int] = {}

        for item in items:
            if item.get("type") != "google_trends_graph":
                continue
            data_points = item.get("data", [])
            if not data_points:
                continue

            for point in data_points:
                date_str = point.get("date_from", "")
                values = point.get("values", [])
                if not date_str or not values:
                    continue

                try:
                    month = int(date_str.split("-")[1])
                except (IndexError, ValueError):
                    continue

                value = values[0] if isinstance(values, list) else 0
                if value is None:
                    continue

                month_sums[month] = month_sums.get(month, 0) + float(value)
                month_counts[month] = month_counts.get(month, 0) + 1

        if not month_sums:
            return None

        return {
            m: month_sums[m] / month_counts[m]
            for m in sorted(month_sums)
        }
