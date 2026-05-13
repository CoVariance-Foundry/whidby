"""Boundary tests for CBPCityDataProvider."""
import pytest

from src.domain.entities import City
from src.clients.census.cbp_adapter import CBPCityDataProvider


class FakeCBPClient:
    async def fetch_establishments_by_msa(self, naics_codes=None, year=2021):
        return [
            {
                "cbsa_code": "14260",
                "naics": "238220",
                "establishments": 145,
                "employees": 890,
                "payroll_thousands": 42_000,
                "year": year,
            },
            {
                "cbsa_code": "14260",
                "naics": "561730",
                "establishments": 210,
                "employees": 1_200,
                "payroll_thousands": 28_000,
                "year": year,
            },
            {
                "cbsa_code": "38060",
                "naics": "238220",
                "establishments": 820,
                "employees": 5_100,
                "payroll_thousands": 245_000,
                "year": year,
            },
        ]


@pytest.fixture
async def provider():
    p = CBPCityDataProvider(FakeCBPClient())
    await p.load_msa_data()
    return p


async def test_business_density_by_naics(provider):
    data = provider.get_business_density("14260", "238220")
    assert data is not None
    assert data["establishments"] == 145
    assert data["employees"] == 890


async def test_business_density_all_naics(provider):
    data = provider.get_business_density("14260")
    assert data is not None
    assert data["establishments"] == 145 + 210
    assert data["employees"] == 890 + 1_200
    assert data["payroll_thousands"] == 42_000 + 28_000


async def test_business_density_missing_city(provider):
    assert provider.get_business_density("00000", "238220") is None


async def test_demographics_returns_none(provider):
    assert provider.get_demographics("14260") is None


async def test_find_similar_returns_empty(provider):
    city = City(city_id="14260", name="Boise")
    assert provider.find_similar_cities(city) == []
