import pytest

from src.clients.census.client import (
    DEMOGRAPHIC_VARIABLES,
    _parse_demographic_value,
)


def test_demographic_variables_include_median_age() -> None:
    assert DEMOGRAPHIC_VARIABLES["B01002_001E"] == "median_age_years"


def test_parse_demographic_value_preserves_decimal_median_age() -> None:
    assert _parse_demographic_value("median_age_years", "37.4") == 37.4


def test_parse_demographic_value_keeps_other_fields_as_ints() -> None:
    assert _parse_demographic_value("total_population", "5015678") == 5_015_678

    with pytest.raises(ValueError):
        _parse_demographic_value("total_population", "37.4")
