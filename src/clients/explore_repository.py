"""Supabase repository for Explore city read models."""

from __future__ import annotations

from typing import Any

from src.pipeline.canonical_key import normalize_niche


SORT_COLUMNS = {
    "score": "presentation_score",
    "best_score": "presentation_score",
    "population": "population",
    "income": "median_household_income_usd",
    "density": "business_density_per_1k",
    "growth": "establishment_growth_yoy",
    "last_scored_at": "latest_scored_at",
    "city": "cbsa_name",
}


class SupabaseExploreRepository:
    """Supabase adapter for the Explore materialized read model."""

    def __init__(self, supabase_client: Any) -> None:
        self._client = supabase_client

    def list_city_rows(
        self,
        *,
        service: str | None,
        states: list[str],
        population_min: int | None,
        population_max: int | None,
        income_min: int | None,
        income_max: int | None,
        growing_only: bool,
        sort: str,
        direction: str,
        limit: int,
        cursor: str | None,
    ) -> list[dict[str, Any]]:
        query = self._client.table("explore_market_cells").select("*")
        normalized_service = _normalize_service(service)
        if normalized_service:
            query = query.eq("niche_normalized", normalized_service)
        if states:
            query = query.in_("state", states)
        if population_min is not None:
            query = query.gte("population", population_min)
        if population_max is not None:
            query = query.lte("population", population_max)
        if income_min is not None:
            query = query.gte("median_household_income_usd", income_min)
        if income_max is not None:
            query = query.lte("median_household_income_usd", income_max)
        if growing_only:
            query = query.gt("establishment_growth_yoy", 0)
        if cursor:
            query = query.gt("cbsa_code", cursor)

        order_column = SORT_COLUMNS.get(sort, "presentation_score")
        ascending = direction.lower() == "asc"
        response = (
            query.order(order_column, ascending=ascending)
            .order("cbsa_code", ascending=True)
            .limit(limit + 1)
            .execute()
        )
        return _result_rows(response)

    def load_city_detail(self, cbsa_code: str) -> dict[str, Any] | None:
        response = (
            self._client.table("explore_market_cells")
            .select("*")
            .eq("cbsa_code", cbsa_code)
            .order("presentation_score", ascending=False)
            .execute()
        )
        rows = _result_rows(response)
        if not rows:
            return None

        city_row = rows[0]
        return {
            "cbsa_code": str(city_row["cbsa_code"]),
            "cbsa_name": city_row.get("cbsa_name"),
            "state": city_row.get("state"),
            "population": city_row.get("population"),
            "population_class": city_row.get("population_class"),
            "median_household_income_usd": city_row.get(
                "median_household_income_usd"
            ),
            "owner_occupancy_rate": city_row.get("owner_occupancy_rate"),
            "median_age_years": city_row.get("median_age_years"),
            "cached_scores": [_cached_score(row) for row in rows],
        }


def _normalize_service(service: str | None) -> str | None:
    if service is None:
        return None
    normalized = normalize_niche(service)
    return normalized or None


def _raise_on_error(result: Any) -> None:
    error = getattr(result, "error", None)
    if error:
        message = getattr(error, "message", None) or str(error)
        raise RuntimeError(f"Supabase request failed: {message}")


def _result_rows(result: Any) -> list[dict[str, Any]]:
    _raise_on_error(result)
    return list(getattr(result, "data", None) or [])


def _cached_score(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "niche_normalized": row.get("niche_normalized"),
        "niche_keyword": row.get("niche_keyword"),
        "report_id": row.get("report_id"),
        "presentation_score": row.get("presentation_score"),
        "score_system": row.get("score_system"),
        "latest_scored_at": row.get("latest_scored_at"),
        "stale": row.get("stale"),
        "business_density_per_1k": row.get("business_density_per_1k"),
        "establishment_growth_yoy": row.get("establishment_growth_yoy"),
        "growth_available": row.get("growth_available"),
    }
