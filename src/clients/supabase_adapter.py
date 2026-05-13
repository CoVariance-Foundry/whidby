"""Adapter wrapping SupabasePersistence to implement MarketStore protocol."""
from __future__ import annotations

from typing import Any

from src.clients.supabase_persistence import SupabasePersistence
from src.domain.entities import Market
from src.domain.queries import MarketQuery


class SupabaseMarketStore:
    """Implements MarketStore using existing SupabasePersistence."""

    def __init__(self, persistence: SupabasePersistence) -> None:
        self._persistence = persistence

    def persist_report(self, report: dict[str, Any]) -> str:
        return self._persistence.persist_report(report)

    def read_report(self, report_id: str) -> dict[str, Any] | None:
        res = (
            self._persistence._client
            .table("reports")
            .select("*")
            .eq("id", report_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def query_markets(self, query: MarketQuery) -> list[Market]:
        return []
