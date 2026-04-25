# Phase 2: Extract Geo Resolution

**Objective:** Move metro/city resolution logic from `orchestrator.py` (lines ~62-106) into `src/domain/services/geo_resolver.py`. The orchestrator calls the resolver instead of doing geo logic inline. Unit tests cover edge cases.

**Risk:** Low. Orchestrator's public interface doesn't change.
**Depends on:** Phase 1 (City entity, GeoLookup port).
**Blocks:** Phase 3 (MarketService uses GeoResolver).

---

## Agent Instructions

### Step 0: Read existing code

Before writing anything, read these files to understand the current geo resolution logic:

```bash
# Read the orchestrator to find geo resolution logic
cat src/pipeline/orchestrator.py

# Read metro_db to understand the current lookup interface
cat src/data/metro_db.py

# Read canonical_key.py to understand key normalization
cat src/scoring/canonical_key.py  # or wherever it lives
```

Identify:
1. Where in `orchestrator.py` the geo resolution happens (city/state → metro target, place_id, location_code)
2. What edge cases exist (city not in CBSA, state fallback, synthetic metro)
3. What `metro_db.py` exposes (find functions, all_metros, CBSA lookup)

### Step 1: Create `src/domain/services/geo_resolver.py`

```python
"""
Geographic resolution service.

Resolves user-provided city/state strings into structured City entities
with metro area context, location codes, and canonical keys.

Extracted from orchestrator.py to make geo resolution independently
testable and reusable across MarketService and DiscoveryService.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.domain.entities import City
from src.domain.ports import GeoLookup


@dataclass(frozen=True)
class ResolvedTarget:
    """Result of geo resolution — everything downstream needs to run the pipeline."""
    city: City
    metro_name: str
    state_code: str
    location_code: int              # DataForSEO location code
    place_id: str | None            # Google Place ID if available
    canonical_key: str              # normalized "city-state" key
    cbsa_code: str | None           # CBSA code if in a metro area
    is_synthetic: bool = False      # True if city isn't in a known CBSA


class GeoResolver:
    """Resolves city/state inputs into structured targets for the pipeline."""

    def __init__(self, geo_lookup: GeoLookup):
        self._geo = geo_lookup

    def resolve(
        self,
        city: str,
        state: str | None = None,
    ) -> ResolvedTarget:
        """
        Resolve a city/state string into a ResolvedTarget.

        Logic extracted from orchestrator.py:
        1. Normalize input (strip, title case)
        2. Look up in metro DB
        3. If not found and state provided, try state fallback
        4. If still not found, create synthetic metro entry
        5. Build canonical key
        6. Return ResolvedTarget with all fields populated

        Raises:
            GeoResolutionError: If city cannot be resolved at all
        """
        # --- EXTRACT THE ACTUAL LOGIC FROM orchestrator.py HERE ---
        # The agent should read orchestrator.py and transplant the
        # geo resolution block (approximately lines 62-106) into this method.
        #
        # Key operations to preserve:
        # - City/state string normalization
        # - Metro DB lookup (self._geo.find_by_city)
        # - State fallback logic
        # - Synthetic metro creation for non-CBSA cities
        # - Canonical key generation
        # - Location code resolution for DataForSEO
        raise NotImplementedError("Extract from orchestrator.py")

    def resolve_batch(
        self,
        targets: list[dict[str, str]],
    ) -> list[ResolvedTarget]:
        """Resolve multiple city/state pairs. Failures are logged and skipped."""
        results = []
        for target in targets:
            try:
                resolved = self.resolve(
                    city=target["city"],
                    state=target.get("state"),
                )
                results.append(resolved)
            except GeoResolutionError:
                # Log and skip — don't fail the batch for one bad target
                continue
        return results


class GeoResolutionError(Exception):
    """Raised when a city/state cannot be resolved to a valid target."""
    pass
```

### Step 2: Create the MetroDB adapter for GeoLookup port

```python
# src/data/metro_db_adapter.py
"""
Adapter wrapping metro_db.py to implement the GeoLookup protocol.

This is a thin wrapper — metro_db already has the right methods,
this just maps its return types to domain entities.
"""
from __future__ import annotations

from src.domain.entities import City
from src.data.metro_db import MetroDB  # or whatever the current class/module is


class MetroDBGeoLookup:
    """Implements GeoLookup port using the existing MetroDB."""

    def __init__(self, metro_db: MetroDB):
        self._db = metro_db

    def find_by_city(self, city: str, state: str | None = None) -> City | None:
        """
        Look up a city in the metro database and return a City entity.

        The agent should read metro_db.py to understand:
        - What method to call (find_metro, lookup, search, etc.)
        - What the return type is (dict, namedtuple, custom class)
        - How to map it to a City entity
        """
        # Map metro_db result → City entity
        # result = self._db.find(city, state)
        # if result is None:
        #     return None
        # return City(
        #     city_id=result.canonical_key,
        #     name=result.city,
        #     state=result.state,
        #     population=result.population,
        # )
        raise NotImplementedError("Map metro_db result to City entity")

    def all_metros(self) -> list[City]:
        """Return all metros as City entities."""
        raise NotImplementedError("Map metro_db.all_metros to City entities")
```

### Step 3: Update `orchestrator.py` to use GeoResolver

**Do not change the orchestrator's public interface.** The `score_niche_for_metro` function should accept the same parameters and return the same result. Internally, it delegates geo resolution to `GeoResolver`.

```python
# In orchestrator.py, replace the inline geo resolution block with:

from src.domain.services.geo_resolver import GeoResolver, ResolvedTarget

# ... in score_niche_for_metro:
# BEFORE (inline geo logic ~lines 62-106):
#   metro = find_metro(city, state)
#   location_code = metro.location_code
#   canonical = canonical_key(city, state)
#   ...

# AFTER:
#   resolver = GeoResolver(geo_lookup=metro_db_adapter)
#   target = resolver.resolve(city=city, state=state)
#   location_code = target.location_code
#   canonical = target.canonical_key
#   ...
```

The key constraint: **remove geo resolution logic from orchestrator, don't duplicate it.** The orchestrator should have zero knowledge of how cities are resolved.

### Step 4: Write tests

**`tests/domain/services/test_geo_resolver.py`:**

```python
"""Tests for GeoResolver — geo resolution extracted from orchestrator."""
import pytest
from src.domain.entities import City
from src.domain.services.geo_resolver import GeoResolver, GeoResolutionError, ResolvedTarget


class FakeGeoLookup:
    """In-memory fake implementing GeoLookup protocol."""

    def __init__(self, cities: dict[str, City] | None = None):
        self._cities = cities or {}

    def find_by_city(self, city: str, state: str | None = None) -> City | None:
        key = f"{city.lower()}-{state.lower()}" if state else city.lower()
        return self._cities.get(key)

    def all_metros(self) -> list[City]:
        return list(self._cities.values())


BOISE = City(city_id="boise-id", name="Boise", state="ID", population=235_000)
PHOENIX = City(city_id="phoenix-az", name="Phoenix", state="AZ", population=1_600_000)


@pytest.fixture
def resolver():
    lookup = FakeGeoLookup(cities={
        "boise-id": BOISE,
        "phoenix-az": PHOENIX,
    })
    return GeoResolver(geo_lookup=lookup)


def test_resolve_known_city(resolver):
    """Known city resolves to a ResolvedTarget."""
    target = resolver.resolve("Boise", "ID")
    assert isinstance(target, ResolvedTarget)
    assert target.city.city_id == "boise-id"
    assert target.state_code == "ID"


def test_resolve_normalizes_input(resolver):
    """Input is normalized (strip, case)."""
    target = resolver.resolve("  boise  ", "id")
    assert target.city.city_id == "boise-id"


def test_resolve_unknown_city_raises(resolver):
    """Unknown city raises GeoResolutionError."""
    with pytest.raises(GeoResolutionError):
        resolver.resolve("Atlantis", "XX")


def test_resolve_batch_skips_failures(resolver):
    """Batch resolution skips failures and returns successes."""
    targets = [
        {"city": "Boise", "state": "ID"},
        {"city": "Atlantis", "state": "XX"},
        {"city": "Phoenix", "state": "AZ"},
    ]
    results = resolver.resolve_batch(targets)
    assert len(results) == 2
    assert results[0].city.city_id == "boise-id"
    assert results[1].city.city_id == "phoenix-az"


def test_resolve_state_fallback(resolver):
    """
    If city is found without state, resolution still works.
    Adjust this test based on actual fallback logic in orchestrator.py.
    """
    # This test should be refined after reading the actual orchestrator code
    pass


def test_resolve_synthetic_metro(resolver):
    """
    City not in a CBSA gets a synthetic metro entry.
    Adjust based on actual orchestrator logic.
    """
    # This test should be refined after reading the actual orchestrator code
    pass
```

### Step 5: Validate

```bash
# Run new tests
python -m pytest tests/domain/services/test_geo_resolver.py -v

# Run existing orchestrator tests to confirm no regression
python -m pytest tests/ -k "orchestrator" -v

# Verify the orchestrator no longer contains inline geo resolution
# (the agent should confirm that the geo logic block has been replaced
# with a GeoResolver.resolve() call)

# Verify domain import rules still hold
grep -r "from src.clients" src/domain/ && echo "FAIL" || echo "PASS"
```

**Done criteria:**
- `GeoResolver.resolve()` contains the logic previously in orchestrator.py lines ~62-106
- `orchestrator.py` calls `GeoResolver` instead of doing geo logic inline
- All existing orchestrator tests still pass (no behavior change)
- New unit tests pass with in-memory fakes (no MetroDB or Mapbox needed)
- `GeoResolver` has no infrastructure imports — it depends only on `GeoLookup` protocol
- `resolve_batch` handles failures gracefully (skip, don't crash)
