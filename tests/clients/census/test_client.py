from src.clients.census.client import DEMOGRAPHIC_VARIABLES


def test_demographic_variables_include_median_age() -> None:
    assert DEMOGRAPHIC_VARIABLES["B01002_001E"] == "median_age_years"
