"""Boundary tests for BLSServiceDataProvider."""
import pytest

from src.clients.bls.adapter import BLSServiceDataProvider
from src.clients.bls.naics_soc_map import compute_acv, get_soc_for_naics


class FakeBLSClient:
    def __init__(self):
        self.wages = {
            "472152": {"soc_code": "472152", "area_code": "0000000",
                       "mean_hourly_wage": 60.0, "year": 2023},
            "472111": {"soc_code": "472111", "area_code": "0000000",
                       "mean_hourly_wage": 55.0, "year": 2023},
        }

    async def fetch_occupation_wages(self, soc_code, area_code="0000000",
                                     start_year=2023, end_year=2023):
        return self.wages.get(soc_code)


@pytest.fixture
async def provider():
    p = BLSServiceDataProvider(FakeBLSClient())
    await p.load_all_national()
    return p


async def test_acv_loaded_for_plumbing(provider):
    acv = provider.get_acv_estimate("238220", "any_city")
    assert acv is not None
    # 60 * 3.0 * 2.0 = 360
    assert acv == pytest.approx(360.0)


async def test_acv_loaded_for_electrical(provider):
    acv = provider.get_acv_estimate("238210", "any_city")
    assert acv is not None
    # 55 * 2.5 * 2.0 = 275
    assert acv == pytest.approx(275.0)


async def test_acv_missing_naics(provider):
    assert provider.get_acv_estimate("999999", "any_city") is None


async def test_seasonality_returns_none(provider):
    assert provider.get_seasonality("plumbing") is None


async def test_establishment_growth_returns_none(provider):
    assert provider.get_establishment_growth("238220", "14260") is None


def test_compute_acv_formula():
    assert compute_acv(50.0, 4.0, 2.0) == 400.0
    assert compute_acv(30.0, 2.0, 1.5) == 90.0


def test_get_soc_known():
    mapping = get_soc_for_naics("238220")
    assert mapping is not None
    assert mapping.soc == "472152"
    assert mapping.avg_job_hours == 3.0


def test_get_soc_unknown():
    assert get_soc_for_naics("000000") is None
