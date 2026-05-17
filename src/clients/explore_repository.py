"""Supabase repository for Explore city read models."""

from __future__ import annotations

from typing import Any

from src.pipeline.canonical_key import normalize_niche


SORT_COLUMNS = {
    "score": "presentation_score",
    "best_score": "presentation_score",
    "presentation_score": "presentation_score",
    "population": "population",
    "income": "median_household_income_usd",
    "density": "business_density_per_1k",
    "business_density": "business_density_per_1k",
    "growth": "establishment_growth_yoy",
    "cached_services": "cached_services_count",
    "last_scored_at": "latest_scored_at",
    "latest_scored_at": "latest_scored_at",
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
        else:
            query = query.eq("representative_service_rank", 1)
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

        order_column = SORT_COLUMNS.get(sort, "presentation_score")
        descending = direction.lower() != "asc"
        query = query.order(order_column, desc=descending).order("cbsa_code", desc=False)
        offset = _cursor_offset(cursor)
        if hasattr(query, "range"):
            query = query.range(offset, offset + limit)
        else:
            query = query.limit(limit + 1)

        try:
            response = query.execute()
        except Exception as exc:
            raise RuntimeError(f"Supabase request failed: {exc}") from exc
        return _result_rows(response)

    def load_city_detail(self, cbsa_code: str) -> dict[str, Any] | None:
        query = (
            self._client.table("explore_market_cells")
            .select("*")
            .eq("cbsa_code", cbsa_code)
            .order("presentation_score", desc=True)
        )
        try:
            response = query.execute()
        except Exception as exc:
            raise RuntimeError(f"Supabase request failed: {exc}") from exc
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
            "cached_scores": [
                _cached_score(row) for row in rows if _has_cached_service(row)
            ],
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


def _cursor_offset(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        offset = int(cursor)
    except (TypeError, ValueError):
        return 0
    return max(0, offset)


def _has_cached_service(row: dict[str, Any]) -> bool:
    return bool(row.get("niche_normalized"))


def _cached_score(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "niche_normalized": row.get("niche_normalized"),
        "niche_keyword": row.get("niche_keyword"),
        "report_id": row.get("report_id"),
        "presentation_score": row.get("presentation_score"),
        "score_system": row.get("score_system"),
        "latest_scored_at": row.get("latest_scored_at"),
        "last_refreshed_at": row.get("last_refreshed_at") or row.get("latest_scored_at"),
        "refresh_target_id": row.get("refresh_target_id"),
        "next_refresh_at": row.get("next_refresh_at"),
        "stale": row.get("stale"),
        "business_density_per_1k": row.get("business_density_per_1k"),
        "establishment_growth_yoy": row.get("establishment_growth_yoy"),
        "growth_available": row.get("growth_available"),
    }
