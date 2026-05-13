"""Boundary tests for TrendsServiceDataProvider."""
import pytest
from dataclasses import dataclass
from typing import Any

from src.domain.entities import SeasonalityCurve
from src.clients.trends.adapter import TrendsServiceDataProvider


@dataclass
class FakeAPIResponse:
    """Mimics DataForSEO APIResponse(data=...)."""
    data: Any = None


class FakeTrendsClient:
    """Returns synthetic Google Trends data mimicking DataForSEO response."""

    def __init__(self, monthly_values: dict[int, float] | None = None):
        if monthly_values is None:
            # AC repair: peaks in summer (June-Aug), troughs in winter
            self._monthly = {
                1: 25, 2: 28, 3: 35, 4: 45, 5: 62,
                6: 85, 7: 100, 8: 92, 9: 70, 10: 48,
                11: 30, 12: 22,
            }
        else:
            self._monthly = monthly_values

    async def google_trends(self, keywords, **kwargs):
        data_points = []
        for month, value in self._monthly.items():
            data_points.append({
                "date_from": f"2023-{month:02d}-01",
                "date_to": f"2023-{month:02d}-28",
                "values": [value],
            })
        return FakeAPIResponse(data={
            "tasks": [{
                "result": [{
                    "items": [{
                        "type": "google_trends_graph",
                        "data": data_points,
                    }],
                }],
            }],
        })


class FakeEmptyTrendsClient:
    async def google_trends(self, keywords, **kwargs):
        return FakeAPIResponse(data={"tasks": [{"result": [{"items": []}]}]})


class FakeErrorTrendsClient:
    async def google_trends(self, keywords, **kwargs):
        return FakeAPIResponse(data={"tasks": []})


@pytest.fixture
async def provider():
    p = TrendsServiceDataProvider(FakeTrendsClient())
    await p.load_seasonality("ac repair")
    return p


async def test_seasonality_loaded(provider):
    curve = provider.get_seasonality("ac repair")
    assert curve is not None
    assert isinstance(curve, SeasonalityCurve)


async def test_peak_is_july(provider):
    curve = provider.get_seasonality("ac repair")
    assert curve.peak_month == 7


async def test_trough_is_december(provider):
    curve = provider.get_seasonality("ac repair")
    assert curve.trough_month == 12


async def test_amplitude_positive(provider):
    curve = provider.get_seasonality("ac repair")
    assert curve.amplitude > 0.5


async def test_monthly_index_normalized(provider):
    curve = provider.get_seasonality("ac repair")
    assert curve.monthly_index[7] == pytest.approx(1.0)
    assert all(0 <= v <= 1 for v in curve.monthly_index.values())


async def test_case_insensitive_lookup(provider):
    assert provider.get_seasonality("AC Repair") is not None
    assert provider.get_seasonality("AC REPAIR") is not None


async def test_missing_service(provider):
    assert provider.get_seasonality("plumbing") is None


async def test_acv_returns_none(provider):
    assert provider.get_acv_estimate("238220", "14260") is None


async def test_establishment_growth_returns_none(provider):
    assert provider.get_establishment_growth("238220", "14260") is None


async def test_empty_response_returns_none():
    p = TrendsServiceDataProvider(FakeEmptyTrendsClient())
    result = await p.load_seasonality("anything")
    assert result is None


async def test_error_response_returns_none():
    p = TrendsServiceDataProvider(FakeErrorTrendsClient())
    result = await p.load_seasonality("anything")
    assert result is None
