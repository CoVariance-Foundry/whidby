"""Tests for the Supabase-backed city data provider."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

from src.clients.city_data_repository import SupabaseCityDataProvider


def _fake_client(data: list[dict[str, object]]) -> MagicMock:
    client = MagicMock()
    response = MagicMock(data=data)
    query = client.table.return_value.select.return_value
    (
        query.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value
    ) = response
    return client


def test_get_business_density_queries_latest_cbp_row() -> None:
    client = _fake_client(
        [
            {
                "cbsa_code": "14260",
                "naics_code": "238220",
                "naics_label": "Plumbing contractors",
                "year": 2022,
                "est": 123,
                "suppressed": False,
                "loaded_at": "2026-05-01T00:00:00+00:00",
            }
        ]
    )
    provider = SupabaseCityDataProvider(client=client)

    density = provider.get_business_density("14260", "238220")

    assert density == {
        "establishments": 123,
        "cbsa_code": "14260",
        "naics_code": "238220",
        "naics_label": "Plumbing contractors",
        "year": 2022,
        "suppressed": False,
        "loaded_at": "2026-05-01T00:00:00+00:00",
        "source_table": "census_cbp_establishments",
    }
    client.table.assert_called_once_with("census_cbp_establishments")
    select_arg = client.table.return_value.select.call_args.args[0]
    assert "est" in select_arg
    assert "year" in select_arg
    first_eq = client.table.return_value.select.return_value.eq
    first_eq.assert_called_once_with("cbsa_code", "14260")
    second_eq = first_eq.return_value.eq
    second_eq.assert_called_once_with("naics_code", "238220")
    order = second_eq.return_value.order
    order.assert_called_once_with("year", desc=True)
    order.return_value.limit.assert_called_once_with(1)


def test_get_business_density_returns_empty_dict_when_no_row() -> None:
    client = _fake_client([])
    provider = SupabaseCityDataProvider(client=client)

    assert provider.get_business_density("14260", "238220") == {}


def test_get_business_density_returns_empty_dict_without_naics() -> None:
    client = _fake_client([])
    provider = SupabaseCityDataProvider(client=client)

    assert provider.get_business_density("14260") == {}
    client.table.assert_not_called()


def test_get_business_density_returns_empty_dict_when_execute_raises(
    caplog,
) -> None:
    client = _fake_client([])
    execute = (
        client.table.return_value.select.return_value.eq.return_value.eq.return_value
        .order.return_value.limit.return_value.execute
    )
    execute.side_effect = RuntimeError("supabase unavailable")
    provider = SupabaseCityDataProvider(client=client)

    caplog.set_level(logging.WARNING)

    assert provider.get_business_density("14260", "238220") == {}
    assert "CBP business density lookup failed" in caplog.text
