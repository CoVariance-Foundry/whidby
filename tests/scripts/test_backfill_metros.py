import sys

import pytest

import scripts.explore.backfill_metros as backfill_metros
from scripts.explore.backfill_metros import (
    build_metro_payload,
    derive_population_class,
)


def test_derive_population_class_boundaries() -> None:
    assert derive_population_class(None) is None
    assert derive_population_class(49_999) == "micro_under_50k"
    assert derive_population_class(50_000) == "small_50_100k"
    assert derive_population_class(100_000) == "medium_100_300k"
    assert derive_population_class(300_000) == "large_300k_1m"
    assert derive_population_class(1_000_000) == "metro_1m_5m"
    assert derive_population_class(5_000_000) == "mega_5m_plus"


def test_build_metro_payload_prefers_acs_values() -> None:
    seed = {
        "cbsa_code": "38060",
        "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
        "state": "AZ",
        "population": 4_946_145,
        "cbsa_type": "metro",
        "principal_cities": ["Phoenix", "Mesa"],
        "dataforseo_location_codes": [1012873],
    }
    acs = {
        "total_population": 5_015_678,
        "median_household_income": 82_000,
        "total_housing_units": 1_900_000,
        "owner_occupied_units": 1_150_000,
        "renter_occupied_units": 750_000,
        "median_year_built": 1994,
        "median_age_years": 37,
        "acs_vintage": 2022,
    }

    payload = build_metro_payload(seed, acs, acs_loaded_at="2026-05-16T12:00:00Z")

    assert payload["cbsa_code"] == "38060"
    assert payload["cbsa_type"] == "metro"
    assert payload["population"] == 5_015_678
    assert payload["median_household_income_usd"] == 82_000
    assert payload["population_class"] == "mega_5m_plus"
    assert payload["households"] == 1_900_000
    assert payload["owner_occupied_housing_units"] == 1_150_000
    assert payload["renter_occupied_housing_units"] == 750_000
    assert payload["owner_occupancy_rate"] == 0.6053
    assert payload["median_year_structure_built"] == 1994
    assert payload["median_age_years"] == 37
    assert payload["acs_vintage"] == 2022
    assert payload["acs_loaded_at"] == "2026-05-16T12:00:00Z"
    assert payload["principal_cities"] == ["Phoenix", "Mesa"]
    assert payload["dataforseo_location_codes"] == [1012873]


@pytest.mark.asyncio
async def test_main_defaults_to_preview_without_live_write(monkeypatch, capsys) -> None:
    async def fake_load_acs_by_cbsa(year: int):
        assert year == 2022
        return {}

    def fail_upsert(url, service_key, rows):  # noqa: ANN001
        raise AssertionError("default mode must not write to PostgREST")

    monkeypatch.setattr(sys, "argv", ["backfill_metros.py"])
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    monkeypatch.setattr(
        backfill_metros,
        "load_seed",
        lambda: [{"cbsa_code": "1", "cbsa_name": "Test, TX", "state": "TX"}],
    )
    monkeypatch.setattr(backfill_metros, "load_acs_by_cbsa", fake_load_acs_by_cbsa)
    monkeypatch.setattr(backfill_metros, "postgrest_upsert", fail_upsert)

    assert await backfill_metros.main() == 0

    output = capsys.readouterr().out
    assert "dry_run=true" in output
    assert "prepared_rows=1" in output
    assert "service-role" not in output


@pytest.mark.asyncio
async def test_main_sanitizes_acs_fetch_errors(monkeypatch, capsys) -> None:
    async def fail_load_acs_by_cbsa(year: int):  # noqa: ARG001
        raise RuntimeError("request failed for https://api.census.gov/data?key=secret")

    monkeypatch.setattr(sys, "argv", ["backfill_metros.py", "--dry-run"])
    monkeypatch.setattr(
        backfill_metros,
        "load_seed",
        lambda: [{"cbsa_code": "1", "cbsa_name": "Test, TX", "state": "TX"}],
    )
    monkeypatch.setattr(backfill_metros, "load_acs_by_cbsa", fail_load_acs_by_cbsa)

    assert await backfill_metros.main() == 1

    output = capsys.readouterr().out
    assert "ACS fetch failed:" in output
    assert "RuntimeError" in output
    assert "Traceback" not in output
    assert "api.census.gov" not in output
    assert "secret" not in output
