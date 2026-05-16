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
        "principal_cities": ["Phoenix", "Mesa"],
        "dataforseo_location_codes": [1012873],
    }
    acs = {
        "total_population": 5_015_678,
        "median_household_income": 82_000,
        "total_housing_units": 1_900_000,
        "owner_occupied_units": 1_150_000,
        "median_year_built": 1994,
        "median_age_years": 37,
        "acs_vintage": 2022,
    }

    payload = build_metro_payload(seed, acs)

    assert payload["cbsa_code"] == "38060"
    assert payload["population"] == 5_015_678
    assert payload["median_household_income_usd"] == 82_000
    assert payload["population_class"] == "mega_5m_plus"
    assert payload["owner_occupancy_rate"] == 0.6053
    assert payload["principal_cities"] == ["Phoenix", "Mesa"]
    assert payload["dataforseo_location_codes"] == [1012873]
