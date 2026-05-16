from __future__ import annotations

from typing import Any


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
        query = self._client.table("metro_score_v2").select("*")
        if niche_normalized:
            query = query.eq("niche_normalized", niche_normalized)
        if cbsa_code:
            query = query.eq("cbsa_code", cbsa_code)
        response = query.limit(limit).execute()
        return list(response.data or [])

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
        return list(response.data or [])

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
        rows = list(response.data or [])
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
