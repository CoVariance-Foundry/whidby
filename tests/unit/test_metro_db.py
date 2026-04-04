"""Unit tests for Metro Database (M1).

Pure Python — no network, no API keys. Tests cover:
  State expansion, region expansion, custom expansion,
  DFS location mapping, population ordering, deep vs standard depth.
"""

from __future__ import annotations

import pytest

from src.data.metro_db import Metro, MetroDB


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db() -> MetroDB:
    """Return a MetroDB loaded from the bundled seed data."""
    return MetroDB.from_seed()


# ---------------------------------------------------------------------------
# State Expansion
# ---------------------------------------------------------------------------

class TestStateExpansion:
    def test_az_returns_metros(self, db: MetroDB):
        metros = db.expand_scope(scope="state", target="AZ", depth="standard")
        assert len(metros) > 0
        assert all(isinstance(m, Metro) for m in metros)

    def test_az_includes_phoenix(self, db: MetroDB):
        metros = db.expand_scope(scope="state", target="AZ", depth="standard")
        names = [m.cbsa_name for m in metros]
        assert any("Phoenix" in n for n in names)

    def test_standard_depth_caps_at_20(self, db: MetroDB):
        metros = db.expand_scope(scope="state", target="CA", depth="standard")
        assert len(metros) <= 20

    def test_results_sorted_by_population_desc(self, db: MetroDB):
        metros = db.expand_scope(scope="state", target="AZ", depth="standard")
        pops = [m.population for m in metros]
        assert pops == sorted(pops, reverse=True)


# ---------------------------------------------------------------------------
# Region Expansion
# ---------------------------------------------------------------------------

class TestRegionExpansion:
    def test_southwest_returns_metros_across_states(self, db: MetroDB):
        metros = db.expand_scope(scope="region", target="Southwest", depth="standard")
        states = {m.state for m in metros}
        assert len(states) > 1

    def test_unknown_region_raises(self, db: MetroDB):
        with pytest.raises(ValueError, match="Unknown region"):
            db.expand_scope(scope="region", target="Narnia", depth="standard")


# ---------------------------------------------------------------------------
# Custom Expansion
# ---------------------------------------------------------------------------

class TestCustomExpansion:
    def test_by_cbsa_codes(self, db: MetroDB):
        metros = db.expand_scope(scope="custom", target=["38060", "46060"])
        assert len(metros) == 2
        codes = {m.cbsa_code for m in metros}
        assert "38060" in codes
        assert "46060" in codes

    def test_unknown_cbsa_ignored(self, db: MetroDB):
        metros = db.expand_scope(scope="custom", target=["38060", "99999"])
        assert len(metros) == 1


# ---------------------------------------------------------------------------
# DFS Location Mapping
# ---------------------------------------------------------------------------

class TestLocationMapping:
    def test_phoenix_has_location_codes(self, db: MetroDB):
        metros = db.expand_scope(scope="custom", target=["38060"])
        assert len(metros) == 1
        assert len(metros[0].dataforseo_location_codes) > 0

    def test_location_codes_are_ints(self, db: MetroDB):
        metros = db.expand_scope(scope="state", target="AZ", depth="standard")
        for m in metros:
            assert all(isinstance(c, int) for c in m.dataforseo_location_codes)


# ---------------------------------------------------------------------------
# Deep vs Standard Depth
# ---------------------------------------------------------------------------

class TestDepth:
    def test_deep_returns_more_than_standard_for_large_state(self, db: MetroDB):
        standard = db.expand_scope(scope="state", target="CA", depth="standard")
        deep = db.expand_scope(scope="state", target="CA", depth="deep")
        assert len(deep) >= len(standard)

    def test_deep_filters_by_population_50k(self, db: MetroDB):
        deep = db.expand_scope(scope="state", target="CA", depth="deep")
        assert all(m.population >= 50000 for m in deep)


# ---------------------------------------------------------------------------
# Metro Object
# ---------------------------------------------------------------------------

class TestMetroObject:
    def test_metro_has_required_fields(self, db: MetroDB):
        metros = db.expand_scope(scope="state", target="AZ", depth="standard")
        m = metros[0]
        assert m.cbsa_code
        assert m.cbsa_name
        assert m.state
        assert m.population > 0
        assert isinstance(m.principal_cities, list)
        assert len(m.principal_cities) > 0
