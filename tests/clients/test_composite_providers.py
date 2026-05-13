"""Tests for composite data providers."""
import pytest

from src.domain.entities import City
from src.clients.composite_providers import (
    CompositeCityDataProvider,
    CompositeServiceDataProvider,
)


class FakeACS:
    def __init__(self):
        self._data = {"14260": {"total_population": 780_000}}

    def get_demographics(self, city_id):
        return self._data.get(city_id)

    def get_business_density(self, city_id, naics=None):
        return None

    def find_similar_cities(self, reference, limit=10):
        return [(City(city_id="38060", name="Phoenix"), 0.95)]


class FakeCBP:
    def get_demographics(self, city_id):
        return None

    def get_business_density(self, city_id, naics=None):
        if city_id == "14260" and naics == "238220":
            return {"establishments": 145}
        return None

    def find_similar_cities(self, reference, limit=10):
        return []


class FakeBLS:
    def get_acv_estimate(self, naics, city_id):
        if naics == "238220":
            return 360.0
        return None

    def get_seasonality(self, service_name):
        return None

    def get_establishment_growth(self, naics, city_id):
        return None


class FakeTrends:
    def get_acv_estimate(self, naics, city_id):
        return None

    def get_seasonality(self, service_name):
        from src.domain.entities import SeasonalityCurve
        if service_name == "ac repair":
            return SeasonalityCurve(
                monthly_index={m: 0.5 for m in range(1, 13)},
                peak_month=7, trough_month=12, amplitude=0.78,
            )
        return None

    def get_establishment_growth(self, naics, city_id):
        return None


def test_composite_city_demographics():
    provider = CompositeCityDataProvider(FakeACS(), FakeCBP())
    data = provider.get_demographics("14260")
    assert data is not None
    assert data["total_population"] == 780_000


def test_composite_city_business_density():
    provider = CompositeCityDataProvider(FakeACS(), FakeCBP())
    data = provider.get_business_density("14260", "238220")
    assert data is not None
    assert data["establishments"] == 145


def test_composite_city_business_density_without_cbp():
    provider = CompositeCityDataProvider(FakeACS())
    assert provider.get_business_density("14260", "238220") is None


def test_composite_city_similar():
    provider = CompositeCityDataProvider(FakeACS())
    similar = provider.find_similar_cities(City(city_id="14260", name="Boise"))
    assert len(similar) == 1
    assert similar[0][0].city_id == "38060"


def test_composite_service_acv():
    provider = CompositeServiceDataProvider(bls=FakeBLS(), trends=FakeTrends())
    assert provider.get_acv_estimate("238220", "14260") == 360.0


def test_composite_service_seasonality():
    provider = CompositeServiceDataProvider(bls=FakeBLS(), trends=FakeTrends())
    curve = provider.get_seasonality("ac repair")
    assert curve is not None
    assert curve.peak_month == 7


def test_composite_service_without_providers():
    provider = CompositeServiceDataProvider()
    assert provider.get_acv_estimate("238220", "14260") is None
    assert provider.get_seasonality("anything") is None
    assert provider.get_establishment_growth("238220", "14260") is None
