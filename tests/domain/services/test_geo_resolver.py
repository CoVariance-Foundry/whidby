from __future__ import annotations

import pytest

from src.domain.entities import City
from src.domain.services.geo_resolver import GeoResolutionError, GeoResolver, ResolvedTarget


# ---------------------------------------------------------------------------
# Fake implementation of the GeoLookup protocol
# ---------------------------------------------------------------------------

class FakeGeoLookup:
    def __init__(self, cities: list[City]) -> None:
        self._cities = cities

    def find_by_city(self, city: str, state: str | None = None) -> City | None:
        city_norm = city.strip().lower()
        state_norm = state.strip().upper() if state else None
        for c in self._cities:
            name_match = (
                c.name.strip().lower() == city_norm
                or any(pc.strip().lower() == city_norm for pc in c.principal_cities)
            )
            if name_match and (state_norm is None or c.state == state_norm):
                return c
        return None

    def all_metros(self) -> list[City]:
        return list(self._cities)


# ---------------------------------------------------------------------------
# Seed cities used across tests
# ---------------------------------------------------------------------------

PHOENIX = City(
    city_id="38060",
    name="Phoenix",
    state="AZ",
    population=1_600_000,
    cbsa_code="38060",
    dataforseo_location_codes=[1023191],
    principal_cities=["Phoenix", "Mesa", "Scottsdale"],
)

TUCSON = City(
    city_id="46060",
    name="Tucson",
    state="AZ",
    population=500_000,
    cbsa_code="46060",
    dataforseo_location_codes=[1023200],
    principal_cities=["Tucson"],
)

DENVER = City(
    city_id="19740",
    name="Denver",
    state="CO",
    population=2_900_000,
    cbsa_code="19740",
    dataforseo_location_codes=[1023571],
    principal_cities=["Denver", "Aurora", "Lakewood"],
)

PHOENIX_NO_DFS = City(
    city_id="38060-nodfs",
    name="Phoenix",
    state="AZ",
    population=1_600_000,
    cbsa_code="38060",
    dataforseo_location_codes=[],  # empty — used for test_resolve_seed_match_without_dfs_codes_raises
    principal_cities=["Phoenix"],
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_resolve_known_city() -> None:
    """Path 2: city found in seed → real CBSA fields, is_synthetic=False."""
    resolver = GeoResolver(FakeGeoLookup([PHOENIX]))
    result = resolver.resolve("Phoenix", "AZ")

    assert isinstance(result, ResolvedTarget)
    assert result.cbsa_code == "38060"
    assert result.location_code == 1023191
    assert result.is_synthetic is False
    assert result.state_code == "AZ"


def test_resolve_normalizes_whitespace_and_case() -> None:
    """Whitespace-padded and mixed-case inputs should resolve identically."""
    resolver = GeoResolver(FakeGeoLookup([PHOENIX]))
    result = resolver.resolve("  phoenix  ", "  az ")

    assert result.cbsa_code == "38060"
    assert result.location_code == 1023191
    assert result.is_synthetic is False
    assert result.state_code == "AZ"


def test_resolve_explicit_dfs_code_with_place_id() -> None:
    """Path 1: explicit DFS code + place_id → synthetic target with mapbox: cbsa."""
    resolver = GeoResolver(FakeGeoLookup([]))
    result = resolver.resolve(
        "Smallville",
        "KS",
        place_id="abc123",
        dataforseo_location_code=21184,
    )

    assert result.cbsa_code == "mapbox:abc123"
    assert result.is_synthetic is True
    assert result.location_code == 21184


def test_resolve_explicit_dfs_code_without_place_id() -> None:
    """Path 1: explicit DFS code without place_id → manual: cbsa."""
    resolver = GeoResolver(FakeGeoLookup([]))
    result = resolver.resolve("Smallville", "KS", dataforseo_location_code=21184)

    assert result.cbsa_code == "manual:smallville"
    assert result.is_synthetic is True
    assert result.location_code == 21184


def test_resolve_state_fallback_borrows_donor_dfs_code() -> None:
    """Path 3: city not in seed but state has metros → borrows donor DFS code."""
    resolver = GeoResolver(FakeGeoLookup([PHOENIX]))
    result = resolver.resolve("Sedona", "AZ")

    assert result.cbsa_code == "fallback:sedona"
    assert result.is_synthetic is True
    assert result.location_code == PHOENIX.dataforseo_location_codes[0]
    assert result.state_code == "AZ"


def test_resolve_state_fallback_picks_highest_population() -> None:
    """Path 3: multiple state metros → picks the one with the highest population."""
    # Tucson (500k) and Phoenix (1.6M) both in AZ — Phoenix should be donor
    resolver = GeoResolver(FakeGeoLookup([TUCSON, PHOENIX]))
    result = resolver.resolve("Sedona", "AZ")

    # Phoenix has higher population so its DFS code should be used
    assert result.location_code == PHOENIX.dataforseo_location_codes[0]
    assert result.is_synthetic is True


def test_resolve_unknown_city_raises() -> None:
    """Completely unknown city/state with no state fallback → GeoResolutionError."""
    resolver = GeoResolver(FakeGeoLookup([PHOENIX]))
    with pytest.raises(GeoResolutionError, match="no CBSA match") as exc_info:
        resolver.resolve("Atlantis", "XX")

    assert isinstance(exc_info.value, ValueError)


def test_resolve_seed_match_without_dfs_codes_raises() -> None:
    """City found in seed but has no DataForSEO location codes → GeoResolutionError."""
    resolver = GeoResolver(FakeGeoLookup([PHOENIX_NO_DFS]))
    with pytest.raises(GeoResolutionError, match="no DataForSEO location codes"):
        resolver.resolve("Phoenix", "AZ")


def test_resolve_without_state_resolves_from_city() -> None:
    """No state given: resolver finds city in seed and fills state_code from City."""
    resolver = GeoResolver(FakeGeoLookup([DENVER]))
    result = resolver.resolve("Denver")

    assert result.state_code == "CO"
    assert result.cbsa_code == "19740"
    assert result.is_synthetic is False


def test_resolve_geo_key_format() -> None:
    """geo_key is lowercased city + ', ' + uppercased state."""
    resolver = GeoResolver(FakeGeoLookup([PHOENIX]))
    result = resolver.resolve("Phoenix", "AZ")

    assert result.geo_key == "phoenix, AZ"


def test_resolve_batch_skips_failures() -> None:
    """resolve_batch ignores GeoResolutionError entries and returns only successes."""
    resolver = GeoResolver(FakeGeoLookup([PHOENIX, DENVER]))
    targets = [
        {"city": "Phoenix", "state": "AZ"},
        {"city": "Atlantis", "state": "XX"},
        {"city": "Denver", "state": "CO"},
    ]
    results = resolver.resolve_batch(targets)

    assert len(results) == 2
    cbsa_codes = {r.cbsa_code for r in results}
    assert "38060" in cbsa_codes
    assert "19740" in cbsa_codes


def test_resolve_batch_empty() -> None:
    """resolve_batch with empty input returns empty list."""
    resolver = GeoResolver(FakeGeoLookup([PHOENIX]))
    assert resolver.resolve_batch([]) == []
