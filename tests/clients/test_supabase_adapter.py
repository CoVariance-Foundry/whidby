"""Tests for SupabaseMarketStore adapter."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.clients.supabase_adapter import SupabaseMarketStore


@pytest.fixture
def fake_persistence() -> MagicMock:
    p = MagicMock()
    p.persist_report.return_value = "report-123"
    p._client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "report-123", "niche_keyword": "plumbing"}]
    )
    return p


@pytest.fixture
def store(fake_persistence: MagicMock) -> SupabaseMarketStore:
    return SupabaseMarketStore(fake_persistence)


def test_persist_report_delegates_to_persistence(
    store: SupabaseMarketStore, fake_persistence: MagicMock
) -> None:
    report = {"report_id": "r1", "input": {}, "metros": [], "meta": {}}
    result = store.persist_report(report)
    assert result == "report-123"
    fake_persistence.persist_report.assert_called_once_with(report)


def test_read_report_queries_supabase(
    store: SupabaseMarketStore, fake_persistence: MagicMock
) -> None:
    result = store.read_report("report-123")
    assert result is not None
    assert result["id"] == "report-123"


def test_read_report_returns_none_when_not_found(
    fake_persistence: MagicMock,
) -> None:
    fake_persistence._client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    store = SupabaseMarketStore(fake_persistence)
    assert store.read_report("nonexistent") is None


def test_query_markets_returns_empty_list(
    store: SupabaseMarketStore,
) -> None:
    from src.domain.queries import MarketQuery
    assert store.query_markets(MarketQuery()) == []
