"""Unit tests for the DataForSEO location bridge matching logic."""

from __future__ import annotations

import logging
from typing import Any

import pytest

from src.clients.dataforseo.types import APIResponse
from src.research_agent.places import (
    DataForSEOLocationBridge,
    PlaceSuggestion,
    resolve_dataforseo_location,
)


# ---------------------------------------------------------------------------
# Fixtures: realistic DFS location rows
# ---------------------------------------------------------------------------

def _dfs_rows() -> list[dict[str, Any]]:
    """Subset of DataForSEO /serp/google/locations rows for testing."""
    return [
        {"location_code": 2840, "location_name": "United States", "country_iso_code": "US", "location_type": "Country"},
        {"location_code": 21133, "location_name": "Alabama,United States", "country_iso_code": "US", "location_type": "State"},
        {"location_code": 21152, "location_name": "Texas,United States", "country_iso_code": "US", "location_type": "State"},
        {"location_code": 1013939, "location_name": "Huntsville,Alabama,United States", "country_iso_code": "US", "location_type": "City"},
        {"location_code": 1026851, "location_name": "Huntsville,Texas,United States", "country_iso_code": "US", "location_type": "City"},
        {"location_code": 1013211, "location_name": "Phoenix,Arizona,United States", "country_iso_code": "US", "location_type": "City"},
        {"location_code": 1014221, "location_name": "Chicago,Illinois,United States", "country_iso_code": "US", "location_type": "City"},
        {"location_code": 9001, "location_name": "Berlin,Berlin,Germany", "country_iso_code": "DE", "location_type": "City"},
    ]


_STATE_NAMES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}


def _suggestion(city: str, region: str, country_iso: str = "US", full_name: str = "") -> PlaceSuggestion:
    """Build a test suggestion mirroring Mapbox output (full state name in full_name)."""
    if not full_name:
        country = "United States" if country_iso == "US" else "Germany"
        state_name = _STATE_NAMES.get(region, region)
        full_name = f"{city}, {state_name}, {country}"
    return PlaceSuggestion(
        place_id=f"test:{city.lower()}",
        city=city,
        region=region,
        country="United States" if country_iso == "US" else "Germany",
        country_iso_code=country_iso,
        full_name=full_name,
        latitude=None,
        longitude=None,
    )


# ---------------------------------------------------------------------------
# resolve_dataforseo_location — exact matching
# ---------------------------------------------------------------------------


class TestResolveDFSLocation:
    def test_huntsville_al_matches_with_high_confidence(self) -> None:
        suggestion = _suggestion("Huntsville", "AL")
        code, confidence = resolve_dataforseo_location(suggestion, _dfs_rows())
        assert code == 1013939
        assert confidence == "high"

    def test_huntsville_tx_matches_different_code(self) -> None:
        suggestion = _suggestion("Huntsville", "TX")
        code, confidence = resolve_dataforseo_location(suggestion, _dfs_rows())
        assert code == 1026851
        assert confidence == "high"

    def test_phoenix_matches(self) -> None:
        suggestion = _suggestion("Phoenix", "AZ")
        code, confidence = resolve_dataforseo_location(suggestion, _dfs_rows())
        assert code == 1013211
        assert confidence == "high"

    def test_chicago_matches(self) -> None:
        suggestion = _suggestion("Chicago", "IL")
        code, confidence = resolve_dataforseo_location(suggestion, _dfs_rows())
        assert code == 1014221
        assert confidence == "high"

    def test_country_filter_excludes_wrong_country(self) -> None:
        suggestion = _suggestion("Berlin", "Berlin", country_iso="DE", full_name="Berlin, Germany")
        code, confidence = resolve_dataforseo_location(suggestion, _dfs_rows())
        assert code == 9001
        assert confidence == "high"

    def test_us_suggestion_does_not_match_german_city(self) -> None:
        suggestion = _suggestion("Berlin", "CT", country_iso="US", full_name="Berlin, CT, United States")
        code, confidence = resolve_dataforseo_location(suggestion, _dfs_rows())
        # "Berlin" appears only under DE rows, so no US match at score >= 95.
        assert code is None or confidence != "high"

    def test_unknown_city_returns_none(self) -> None:
        suggestion = _suggestion("Nowhereville", "ZZ")
        code, confidence = resolve_dataforseo_location(suggestion, _dfs_rows())
        # Code is always None for unknown cities — confidence may be "low"
        # if a broad substring match (like "United States") is found.
        assert code is None

    def test_empty_rows_returns_none(self) -> None:
        suggestion = _suggestion("Huntsville", "AL")
        code, confidence = resolve_dataforseo_location(suggestion, [])
        assert code is None

    def test_empty_city_returns_none(self) -> None:
        suggestion = _suggestion("", "AL")
        code, confidence = resolve_dataforseo_location(suggestion, _dfs_rows())
        assert code is None


# ---------------------------------------------------------------------------
# resolve_dataforseo_location — state disambiguation
# ---------------------------------------------------------------------------


class TestStateDiambiguation:
    """When multiple DFS rows share the same city name, the best match
    should correspond to the correct state based on the row's location_name."""

    def test_huntsville_al_not_tx(self) -> None:
        al = _suggestion("Huntsville", "AL")
        tx = _suggestion("Huntsville", "TX")

        al_code, _ = resolve_dataforseo_location(al, _dfs_rows())
        tx_code, _ = resolve_dataforseo_location(tx, _dfs_rows())

        assert al_code != tx_code
        assert al_code == 1013939
        assert tx_code == 1026851


# ---------------------------------------------------------------------------
# DataForSEOLocationBridge — logging on empty rows
# ---------------------------------------------------------------------------


class _FakeDFSClientOk:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    async def locations(self) -> APIResponse:
        return APIResponse(status="ok", data=self._rows)


class _FakeDFSClientEmpty:
    async def locations(self) -> APIResponse:
        return APIResponse(status="ok", data=[])


class _FakeDFSClientError:
    async def locations(self) -> APIResponse:
        return APIResponse(status="error", error="service unavailable")


@pytest.mark.asyncio
async def test_bridge_enrich_returns_codes_for_huntsville() -> None:
    bridge = DataForSEOLocationBridge(_FakeDFSClientOk(_dfs_rows()))  # type: ignore[arg-type]
    suggestions = [_suggestion("Huntsville", "AL"), _suggestion("Phoenix", "AZ")]
    enriched = await bridge.enrich(suggestions)

    assert enriched[0].dataforseo_location_code == 1013939
    assert enriched[0].dataforseo_match_confidence == "high"
    assert enriched[1].dataforseo_location_code == 1013211


@pytest.mark.asyncio
async def test_bridge_logs_warning_on_empty_rows(caplog: pytest.LogCaptureFixture) -> None:
    bridge = DataForSEOLocationBridge(_FakeDFSClientEmpty())  # type: ignore[arg-type]
    suggestions = [_suggestion("Huntsville", "AL")]

    with caplog.at_level(logging.WARNING, logger="src.research_agent.places"):
        await bridge.enrich(suggestions)

    assert any("0 rows" in r.message for r in caplog.records)
    assert suggestions[0].dataforseo_location_code is None


@pytest.mark.asyncio
async def test_bridge_logs_warning_on_zero_matches(caplog: pytest.LogCaptureFixture) -> None:
    rows = [{"location_code": 9001, "location_name": "Berlin,Berlin,Germany", "country_iso_code": "DE", "location_type": "City"}]
    bridge = DataForSEOLocationBridge(_FakeDFSClientOk(rows))  # type: ignore[arg-type]
    suggestions = [_suggestion("Huntsville", "AL")]

    with caplog.at_level(logging.WARNING, logger="src.research_agent.places"):
        await bridge.enrich(suggestions)

    assert any("matched 0" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_bridge_logs_info_on_successful_load(caplog: pytest.LogCaptureFixture) -> None:
    bridge = DataForSEOLocationBridge(_FakeDFSClientOk(_dfs_rows()))  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO, logger="src.research_agent.places"):
        await bridge.enrich([_suggestion("Phoenix", "AZ")])

    assert any("loaded" in r.message and "city rows" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_bridge_error_response_does_not_crash() -> None:
    bridge = DataForSEOLocationBridge(_FakeDFSClientError())  # type: ignore[arg-type]
    suggestions = [_suggestion("Huntsville", "AL")]
    enriched = await bridge.enrich(suggestions)
    assert enriched[0].dataforseo_location_code is None
