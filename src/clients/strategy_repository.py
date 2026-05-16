from __future__ import annotations

from typing import Any

from src.domain.entities import City, Market, Service
from src.domain.queries import MarketQuery


def _raise_on_error(result: Any) -> None:
    error = getattr(result, "error", None)
    if error:
        message = getattr(error, "message", None) or str(error)
        raise RuntimeError(f"Supabase request failed: {message}")


def _result_rows(result: Any) -> list[dict[str, Any]]:
    _raise_on_error(result)
    return list(getattr(result, "data", None) or [])


class StrategyRepository:
    """Supabase adapter for strategy discovery read models and run lineage."""

    def __init__(self, supabase_client: Any):
        self._client = supabase_client

    def fetch_cached_markets(
        self,
        *,
        niche_normalized: str | None = None,
        cbsa_code: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = self._client.table("metro_score_v2").select("*, metros(*)")
        if niche_normalized:
            query = query.eq("niche_normalized", niche_normalized)
        if cbsa_code:
            query = query.eq("cbsa_code", cbsa_code)
        response = query.limit(limit).execute()
        return _result_rows(response)

    def persist_report(self, report: dict[str, Any]) -> str:
        return ""

    def read_report(self, report_id: str) -> dict[str, Any] | None:
        return None

    def query_markets(self, query: MarketQuery) -> list[Market]:
        niche = _first_filter_value(query.service_filters, "name")
        cbsa_code = _first_filter_value(query.city_filters, "cbsa_code")
        limit = max(query.limit + query.offset, 50)
        rows = self.fetch_cached_markets(
            niche_normalized=_normalize_niche(niche),
            cbsa_code=str(cbsa_code) if cbsa_code else None,
            limit=limit,
        )
        return [_market_from_cached_row(row, query) for row in rows]

    def fetch_local_pack_facts(
        self,
        *,
        cbsa_code: str,
        niche_normalized: str,
        keyword: str,
    ) -> list[dict[str, Any]]:
        response = (
            self._client.table("local_pack_listing_facts")
            .select("*")
            .eq("cbsa_code", cbsa_code)
            .eq("niche_normalized", niche_normalized)
            .eq("keyword", keyword)
            .order("snapshot_date", desc=True)
            .order("listing_rank")
            .limit(10)
            .execute()
        )
        return _result_rows(response)

    def fetch_feature_vector(
        self, *, cbsa_code: str, feature_version: str = "strategy_v1"
    ) -> dict[str, Any] | None:
        response = (
            self._client.table("metro_feature_vectors")
            .select("*")
            .eq("cbsa_code", cbsa_code)
            .eq("feature_version", feature_version)
            .limit(1)
            .execute()
        )
        rows = _result_rows(response)
        return rows[0] if rows else None

    def create_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.table("strategy_runs").insert(payload).execute()
        rows = _result_rows(response)
        if not rows or not rows[0].get("id"):
            raise RuntimeError("Supabase create_run returned no run id")
        return rows[0]

    def insert_run_items(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._client.table("strategy_run_items").insert(rows).execute()
        inserted = _result_rows(response)
        if not inserted:
            raise RuntimeError("Supabase insert_run_items returned no rows")
        return inserted


def _first_filter_value(filters: list[Any], field: str) -> Any | None:
    for item in filters:
        if item.field == field and item.operator in {"=", "like"}:
            return item.value
    return None


def _normalize_niche(value: Any | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower().replace(" ", "_")
    return normalized or None


def _number(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _score_signal(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = _number(row, key)
    return {"score": value} if value is not None else {}


def _strategy_row_from_cached_row(row: dict[str, Any], query: MarketQuery) -> dict[str, Any]:
    local_pack_present = not bool(row.get("no_local_pack_detected", False))
    primary_keyword = (
        query.primary_keyword or row.get("primary_keyword") or row.get("niche_keyword")
    )
    return {
        **row,
        "primary_keyword": primary_keyword,
        "local_pack_present": local_pack_present,
        "local_difficulty": row.get("local_difficulty"),
        "benchmark_confidence": row.get("benchmark_confidence"),
        "search_volume_monthly": row.get("search_volume_monthly"),
        "exact_match_name_taken": row.get("exact_match_name_taken"),
        "aio_trigger_rate": row.get("aio_trigger_rate"),
    }


def _market_from_cached_row(row: dict[str, Any], query: MarketQuery) -> Market:
    metro = row.get("metros") or row.get("metro") or {}
    if not isinstance(metro, dict):
        metro = {}
    cbsa_code = str(row.get("cbsa_code") or metro.get("cbsa_code") or "")
    niche = str(row.get("niche_normalized") or "unknown")
    service_name = niche.replace("_", " ").title()
    city = City(
        city_id=cbsa_code or str(row.get("id") or ""),
        name=str(
            metro.get("city")
            or metro.get("principal_city")
            or metro.get("cbsa_name")
            or row.get("city")
            or row.get("cbsa_name")
            or cbsa_code
        ),
        state=metro.get("state") or row.get("state"),
        population=metro.get("population") or row.get("population"),
        cbsa_code=cbsa_code or None,
    )
    service = Service(
        service_id=niche,
        name=str(row.get("service_name") or service_name),
    )
    return Market(
        city=city,
        service=service,
        report_id=row.get("report_id"),
        scored_at=row.get("scored_at"),
        signals={
            "demand": _score_signal(row, "demand_strength"),
            "organic_competition": _score_signal(row, "organic_difficulty"),
            "local_competition": _score_signal(row, "local_difficulty"),
            "monetization": _score_signal(row, "monetization_signal"),
            "ai_resilience": _score_signal(row, "ai_resilience"),
            "strategy_row": _strategy_row_from_cached_row(row, query),
        },
    )
