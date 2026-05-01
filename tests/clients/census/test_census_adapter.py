"""Boundary tests for CensusCityDataProvider."""
import pytest

from src.domain.entities import City
from src.clients.census.adapter import CensusCityDataProvider, _cosine_similarity


class FakeCensusClient:
    async def fetch_msa_demographics(self, cbsa_codes=None):
        return [
            {
                "cbsa_code": "14260",
                "name": "Boise City, ID",
                "total_population": 780_000,
                "median_household_income": 62_000,
                "total_housing_units": 290_000,
                "owner_occupied_units": 195_000,
                "median_year_built": 1995,
                "broadband_subscriptions": 250_000,
                "total_internet_universe": 280_000,
            },
            {
                "cbsa_code": "38060",
                "name": "Phoenix-Mesa-Chandler, AZ",
                "total_population": 4_900_000,
                "median_household_income": 72_000,
                "total_housing_units": 1_900_000,
                "owner_occupied_units": 1_200_000,
                "median_year_built": 1998,
                "broadband_subscriptions": 1_500_000,
                "total_internet_universe": 1_700_000,
            },
            {
                "cbsa_code": "99999",
                "name": "Sparse City, XX",
                "total_population": 50_000,
                "median_household_income": 45_000,
                "total_housing_units": 20_000,
                "owner_occupied_units": 12_000,
                "median_year_built": 1970,
                "broadband_subscriptions": 8_000,
                "total_internet_universe": 15_000,
            },
        ]


@pytest.fixture
async def provider():
    p = CensusCityDataProvider(FakeCensusClient())
    await p.load_all()
    return p


async def test_demographics_loaded(provider):
    data = provider.get_demographics("14260")
    assert data is not None
    assert data["total_population"] == 780_000
    assert data["median_household_income"] == 62_000


async def test_demographics_missing_city(provider):
    assert provider.get_demographics("00000") is None


async def test_business_density_returns_none(provider):
    assert provider.get_business_density("14260") is None


async def test_find_similar_cities(provider):
    boise = City(
        city_id="14260",
        name="Boise",
        population=780_000,
        median_income=62_000,
        homeownership_rate=0.67,
        growth_rate=0.02,
        broadband_penetration=0.89,
    )
    similar = provider.find_similar_cities(boise, limit=5)
    assert len(similar) == 2
    assert all(sim > 0 for _, sim in similar)
    # Phoenix is more similar to Boise than Sparse City
    assert similar[0][0].city_id == "38060"


async def test_find_similar_skips_self(provider):
    boise = City(
        city_id="14260",
        name="Boise",
        population=780_000,
        median_income=62_000,
        homeownership_rate=0.67,
    )
    similar = provider.find_similar_cities(boise, limit=10)
    city_ids = [c.city_id for c, _ in similar]
    assert "14260" not in city_ids


async def test_find_similar_returns_empty_for_incomplete_city(provider):
    incomplete = City(city_id="no_data", name="No Data")
    assert provider.find_similar_cities(incomplete) == []


def test_cosine_similarity_identical():
    assert _cosine_similarity([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    assert _cosine_similarity([0, 0, 0], [1, 2, 3]) == 0.0
