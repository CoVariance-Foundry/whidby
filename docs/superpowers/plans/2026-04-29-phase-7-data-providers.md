# Phase 7: Data Providers — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Census ACS (city demographics), Census CBP (business density), BLS (occupation wages → ACV), and DataForSEO Trends (search seasonality) as data provider adapters implementing the `CityDataProvider` and `ServiceDataProvider` protocols from `src/domain/ports.py`. Each lights up additional lenses: Expand & Conquer, Blue Ocean, Cash Cow, and Seasonal Arbitrage.

**Architecture:** Four independent client packages under `src/clients/` (census, bls, trends), each with a raw API client and a domain adapter. 7A–7C hit free government APIs (Census, BLS). 7D extends the existing DataForSEO client with a Trends endpoint. A `CompositeProviders` module composes sub-providers into the full `CityDataProvider` / `ServiceDataProvider` interfaces that `DiscoveryService` already accepts. No domain layer changes — everything is additive in the infrastructure layer.

**Tech Stack:** Python 3.11+, httpx (already a dep), numpy (to add), Census ACS/CBP free APIs, BLS OES API v2, DataForSEO Keywords Data / Google Trends API

**Testing:** Implement-first, test at boundaries per project convention. Boundary tests for each adapter using fake clients. Targeted unit tests only for complex pure logic (cosine similarity, growth-rate math, ACV formula). No per-function unit tests for HTTP normalization glue.

**Design decisions:**
- **Census/BLS clients use raw httpx — no rate limiting, cost tracking, or caching.** These are free government APIs with annual data updates. The overhead of `_RateLimiter` / `CostTracker` / `PersistentResponseCache` (used by DataForSEO) is not justified. 7D reuses the existing DataForSEO client which already has all three.
- **`growth_rate` is deferred.** `CensusClient.compute_growth_rate()` is implemented but not wired into `load_all()` — it requires two API calls per MSA (~400 MSAs × 2 = ~800 requests) which is expensive on first load. The cosine similarity vector carries 0 in the growth_rate slot until we add a background job or Supabase-backed cache. This is acceptable for v1.

**Pre-existing failures:** 3 failures in `tests/unit/test_api_reports.py` (HTTP 400 vs 422 status mismatch) predate Phase 7 — ignore in validation. Assert no NEW failures.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| **7A: Census ACS** | | |
| Create | `src/clients/census/__init__.py` | Package init |
| Create | `src/clients/census/client.py` | Census ACS API client (demographics at MSA level) |
| Create | `src/clients/census/adapter.py` | `CensusCityDataProvider` — implements `CityDataProvider.get_demographics` + `find_similar_cities` |
| Create | `tests/clients/census/__init__.py` | Test package init |
| Create | `tests/clients/census/test_census_adapter.py` | Boundary tests for Census adapter |
| **7B: Census CBP** | | |
| Create | `src/clients/census/cbp_client.py` | Census CBP API client (establishments by NAICS) |
| Create | `src/clients/census/cbp_adapter.py` | `CBPCityDataProvider` — implements `CityDataProvider.get_business_density` |
| Create | `tests/clients/census/test_cbp_adapter.py` | Boundary tests for CBP adapter |
| **7C: BLS Wages** | | |
| Create | `src/clients/bls/__init__.py` | Package init |
| Create | `src/clients/bls/client.py` | BLS OEWS API client (occupation wages) |
| Create | `src/clients/bls/naics_soc_map.py` | NAICS → SOC mapping + average job hours data |
| Create | `src/clients/bls/adapter.py` | `BLSServiceDataProvider` — implements `ServiceDataProvider.get_acv_estimate` |
| Create | `tests/clients/bls/__init__.py` | Test package init |
| Create | `tests/clients/bls/test_bls_adapter.py` | Boundary tests for BLS adapter |
| **7D: DataForSEO Trends** | | |
| Modify | `src/clients/dataforseo/endpoints.py` | Add `GOOGLE_TRENDS` endpoint |
| Modify | `src/clients/dataforseo/client.py` | Add `google_trends()` method |
| Create | `src/clients/trends/__init__.py` | Package init |
| Create | `src/clients/trends/adapter.py` | `TrendsServiceDataProvider` — implements `ServiceDataProvider.get_seasonality` |
| Create | `tests/clients/trends/__init__.py` | Test package init |
| Create | `tests/clients/trends/test_trends_adapter.py` | Boundary tests for Trends adapter |
| **Composition** | | |
| Create | `src/clients/composite_providers.py` | `CompositeCityDataProvider` + `CompositeServiceDataProvider` |
| Create | `tests/clients/test_composite_providers.py` | Composition tests |
| Create | `supabase/migrations/011_data_provider_tables.sql` | Reference tables for cities, business_patterns, service_acv_estimates |

---

## Task 0: Create Feature Branch

- [ ] **Step 1: Create branch from dev**

```bash
git checkout dev && git pull origin dev
git checkout -b phase-7-data-providers
```

---

## Task 1: Verify Green Baseline + Add numpy

Confirm all tests pass, then add the numpy dependency needed for cosine similarity in 7A.

- [ ] **Step 1: Run full test suite**

```bash
python3.11 -m pytest tests/ -v --ignore=tests/integration/ 2>&1 | tail -20
```

Expected: 627+ passed (3 pre-existing failures in test_api_reports.py are known — OK).

- [ ] **Step 2: Add numpy to pyproject.toml**

In `pyproject.toml`, add `"numpy"` to the `dependencies` list:

```toml
dependencies = [
    "anthropic",
    "httpx",
    "supabase",
    "pydantic>=2",
    "networkx",
    "numpy",
]
```

- [ ] **Step 3: Install and verify**

```bash
python3.11 -m pip install -e ".[dev]"
python3.11 -c "import numpy; print(numpy.__version__)"
```

- [ ] **Step 4: Verify architecture lint passes**

```bash
python3.11 scripts/check_domain_imports.py
```

Expected: `12 files checked, 0 violations.`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add numpy dependency for Phase 7 cosine similarity"
```

---

## Task Group 7A: Census ACS (City Demographics)

**Unlocks:** `Expand & Conquer` lens (`find_similar_cities`), city filtering by demographics.

### Task 2: Census ACS Client

**Files:**
- Create: `src/clients/census/__init__.py`
- Create: `src/clients/census/client.py`

- [ ] **Step 1: Create package init**

```python
# src/clients/census/__init__.py
```

(Empty file.)

- [ ] **Step 2: Implement CensusClient**

Create `src/clients/census/client.py`:

```python
"""Census Bureau ACS 5-Year Estimates API client.

Fetches demographic data at the MSA level. Free API — optional key for higher rate limits.
Docs: https://api.census.gov/data/2022/acs/acs5
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ACS_BASE_URL = "https://api.census.gov/data/{year}/acs/acs5"

DEMOGRAPHIC_VARIABLES = {
    "B01003_001E": "total_population",
    "B19013_001E": "median_household_income",
    "B25003_001E": "total_housing_units",
    "B25003_002E": "owner_occupied_units",
    "B25035_001E": "median_year_built",
    "B28002_004E": "broadband_subscriptions",
    "B28002_001E": "total_internet_universe",
}

SENTINEL_NULL = -666666666


class CensusClient:
    """Fetches demographic data from the Census ACS API."""

    def __init__(self, api_key: str | None = None, year: int = 2022):
        self._api_key = api_key
        self._year = year
        self._base_url = ACS_BASE_URL.format(year=year)

    async def fetch_msa_demographics(
        self, cbsa_codes: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch demographic data for MSAs.

        If cbsa_codes is None, fetches all MSAs.
        Returns list of dicts with normalized field names.
        """
        variables = ",".join(DEMOGRAPHIC_VARIABLES.keys())
        params: dict[str, str] = {
            "get": f"NAME,{variables}",
            "for": "metropolitan statistical area/micropolitan statistical area:*",
        }
        if self._api_key:
            params["key"] = self._api_key

        logger.info(
            "CensusClient.fetch_msa_demographics START year=%d vars=%d",
            self._year, len(DEMOGRAPHIC_VARIABLES),
        )

        async with httpx.AsyncClient() as client:
            resp = await client.get(self._base_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        headers = data[0]
        results: list[dict[str, Any]] = []
        for row in data[1:]:
            record = dict(zip(headers, row))
            cbsa = record.get(
                "metropolitan statistical area/micropolitan statistical area"
            )
            if cbsa_codes and cbsa not in cbsa_codes:
                continue

            normalized: dict[str, Any] = {
                "cbsa_code": cbsa,
                "name": record.get("NAME", ""),
            }
            for var_code, field_name in DEMOGRAPHIC_VARIABLES.items():
                raw = record.get(var_code)
                if raw is None or int(raw) == SENTINEL_NULL:
                    normalized[field_name] = None
                else:
                    normalized[field_name] = int(raw)

            results.append(normalized)

        logger.info(
            "CensusClient.fetch_msa_demographics DONE count=%d", len(results)
        )
        return results

    async def fetch_population_for_year(
        self, cbsa_code: str, year: int
    ) -> int | None:
        """Fetch total population for a single MSA in a given ACS year."""
        url = ACS_BASE_URL.format(year=year)
        params: dict[str, str] = {
            "get": "B01003_001E",
            "for": f"metropolitan statistical area/micropolitan statistical area:{cbsa_code}",
        }
        if self._api_key:
            params["key"] = self._api_key

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        if len(data) < 2:
            return None
        raw = data[1][0]
        if raw is None or int(raw) == SENTINEL_NULL:
            return None
        return int(raw)

    async def compute_growth_rate(
        self,
        cbsa_code: str,
        year_old: int = 2017,
        year_new: int = 2022,
    ) -> float | None:
        """Annualized population growth rate between two ACS years."""
        pop_old = await self.fetch_population_for_year(cbsa_code, year_old)
        pop_new = await self.fetch_population_for_year(cbsa_code, year_new)

        if not pop_old or not pop_new or pop_old == 0:
            return None

        span = year_new - year_old
        return (pop_new / pop_old) ** (1 / span) - 1
```

- [ ] **Step 3: Verify import**

```bash
python3.11 -c "from src.clients.census.client import CensusClient; print('OK')"
```

---

### Task 3: Census ACS Adapter

**Files:**
- Create: `src/clients/census/adapter.py`

- [ ] **Step 1: Implement CensusCityDataProvider**

Create `src/clients/census/adapter.py`:

```python
"""Adapter implementing CityDataProvider using Census ACS data."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from src.domain.entities import City
from src.clients.census.client import CensusClient

logger = logging.getLogger(__name__)


class CensusCityDataProvider:
    """Implements CityDataProvider (demographics + similarity) using Census ACS."""

    def __init__(self, client: CensusClient):
        self._client = client
        self._cache: dict[str, dict[str, Any]] = {}

    def get_demographics(self, city_id: str) -> dict[str, Any] | None:
        return self._cache.get(city_id)

    def get_business_density(
        self, city_id: str, naics: str | None = None
    ) -> dict[str, Any] | None:
        return None

    def find_similar_cities(
        self, reference: City, limit: int = 10
    ) -> list[tuple[City, float]]:
        """Cosine similarity on demographic vectors.

        Vector: [log(population), median_income, homeownership_rate,
                 growth_rate, broadband_penetration]
        """
        ref_vector = self._city_to_vector(reference)
        if ref_vector is None:
            return []

        similarities: list[tuple[City, float]] = []
        for city_id, data in self._cache.items():
            if city_id == reference.city_id:
                continue
            city = self._data_to_city(city_id, data)
            vec = self._city_to_vector(city)
            if vec is None:
                continue
            sim = _cosine_similarity(ref_vector, vec)
            similarities.append((city, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]

    async def load_all(self) -> None:
        """Bulk load all MSA demographics into cache."""
        results = await self._client.fetch_msa_demographics()
        for r in results:
            self._cache[r["cbsa_code"]] = r
        logger.info("CensusCityDataProvider loaded %d MSAs", len(self._cache))

    @staticmethod
    def _city_to_vector(city: City) -> list[float] | None:
        if city.population is None or city.median_income is None:
            return None
        return [
            np.log(city.population) if city.population > 0 else 0.0,
            float(city.median_income or 0),
            float(city.homeownership_rate or 0),
            float(city.growth_rate or 0),
            float(city.broadband_penetration or 0),
        ]

    @staticmethod
    def _data_to_city(city_id: str, data: dict[str, Any]) -> City:
        pop = data.get("total_population")
        owner = data.get("owner_occupied_units")
        total_housing = data.get("total_housing_units")
        broadband = data.get("broadband_subscriptions")
        internet_total = data.get("total_internet_universe")

        return City(
            city_id=city_id,
            name=data.get("name", ""),
            population=pop,
            median_income=data.get("median_household_income"),
            homeownership_rate=(
                owner / total_housing if owner and total_housing else None
            ),
            housing_age_median=(
                2024 - data["median_year_built"]
                if data.get("median_year_built")
                else None
            ),
            broadband_penetration=(
                broadband / internet_total
                if broadband and internet_total
                else None
            ),
            cbsa_code=city_id,
        )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if norm == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / norm)
```

- [ ] **Step 2: Verify imports and architecture lint**

```bash
python3.11 -c "from src.clients.census.adapter import CensusCityDataProvider; print('OK')"
python3.11 scripts/check_domain_imports.py
```

---

### Task 4: Census ACS Boundary Tests

**Files:**
- Create: `tests/clients/census/__init__.py`
- Create: `tests/clients/census/test_census_adapter.py`

- [ ] **Step 1: Create test package**

```python
# tests/clients/census/__init__.py
```

(Empty file.)

- [ ] **Step 2: Write boundary tests**

Create `tests/clients/census/test_census_adapter.py`:

```python
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
        city_id="14260", name="Boise", population=780_000, median_income=62_000,
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
```

- [ ] **Step 3: Run tests**

```bash
python3.11 -m pytest tests/clients/census/test_census_adapter.py -v
```

Expected: 8 passed.

- [ ] **Step 4: Commit 7A**

```bash
git add src/clients/census/ tests/clients/census/
git commit -m "feat(clients): add Census ACS client and CensusCityDataProvider adapter

Implements CityDataProvider.get_demographics and find_similar_cities
using Census ACS 5-Year Estimates at MSA level. Cosine similarity
on demographic vectors for Expand & Conquer lens."
```

---

## Task Group 7B: Census CBP (Business Density)

**Unlocks:** `Blue Ocean` lens (`establishment_growth` filter), `business_density` on City entities.

### Task 5: CBP Client

**Files:**
- Create: `src/clients/census/cbp_client.py`

- [ ] **Step 1: Implement CBPClient**

Create `src/clients/census/cbp_client.py`:

```python
"""Census County Business Patterns API client.

Fetches establishment counts by NAICS code at the MSA level.
Docs: https://api.census.gov/data/2021/cbp
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CBP_BASE_URL = "https://api.census.gov/data/{year}/cbp"


class CBPClient:
    """Fetches establishment data from Census CBP API."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    async def fetch_establishments_by_msa(
        self,
        naics_codes: list[str] | None = None,
        year: int = 2021,
    ) -> list[dict[str, Any]]:
        """Fetch establishment counts by MSA and NAICS code."""
        url = CBP_BASE_URL.format(year=year)
        params: dict[str, str] = {
            "get": "ESTAB,EMP,PAYANN,NAICS2017",
            "for": "metropolitan statistical area/micropolitan statistical area:*",
        }
        if naics_codes:
            params["NAICS2017"] = ",".join(naics_codes)
        if self._api_key:
            params["key"] = self._api_key

        logger.info(
            "CBPClient.fetch_establishments START year=%d naics=%s",
            year, naics_codes,
        )

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        headers = data[0]
        results: list[dict[str, Any]] = []
        for row in data[1:]:
            record = dict(zip(headers, row))
            results.append({
                "cbsa_code": record.get(
                    "metropolitan statistical area/micropolitan statistical area"
                ),
                "naics": record.get("NAICS2017"),
                "establishments": int(record.get("ESTAB", 0)),
                "employees": int(record.get("EMP", 0)),
                "payroll_thousands": int(record.get("PAYANN", 0)),
                "year": year,
            })

        logger.info("CBPClient.fetch_establishments DONE count=%d", len(results))
        return results

    async def compute_establishment_growth(
        self,
        cbsa_code: str,
        naics: str,
        year_old: int = 2017,
        year_new: int = 2021,
    ) -> float | None:
        """Annualized establishment growth rate between two CBP years."""
        old_data = await self.fetch_establishments_by_msa([naics], year_old)
        new_data = await self.fetch_establishments_by_msa([naics], year_new)

        old_count = next(
            (d["establishments"] for d in old_data if d["cbsa_code"] == cbsa_code),
            None,
        )
        new_count = next(
            (d["establishments"] for d in new_data if d["cbsa_code"] == cbsa_code),
            None,
        )

        if not old_count or not new_count or old_count == 0:
            return None

        span = year_new - year_old
        return (new_count / old_count) ** (1 / span) - 1
```

- [ ] **Step 2: Verify import**

```bash
python3.11 -c "from src.clients.census.cbp_client import CBPClient; print('OK')"
```

---

### Task 6: CBP Adapter

**Files:**
- Create: `src/clients/census/cbp_adapter.py`

- [ ] **Step 1: Implement CBPCityDataProvider**

Create `src/clients/census/cbp_adapter.py`:

```python
"""Adapter implementing CityDataProvider (business density) from Census CBP."""
from __future__ import annotations

import logging
from typing import Any

from src.domain.entities import City
from src.clients.census.cbp_client import CBPClient

logger = logging.getLogger(__name__)


class CBPCityDataProvider:
    """Partial CityDataProvider for business density and establishment growth."""

    def __init__(self, client: CBPClient):
        self._client = client
        self._cache: dict[str, dict[str, Any]] = {}

    def get_demographics(self, city_id: str) -> dict[str, Any] | None:
        return None

    def get_business_density(
        self, city_id: str, naics: str | None = None
    ) -> dict[str, Any] | None:
        key = f"{city_id}:{naics or 'all'}"
        return self._cache.get(key)

    def find_similar_cities(
        self, reference: City, limit: int = 10
    ) -> list[tuple[City, float]]:
        return []

    async def load_msa_data(
        self, naics_codes: list[str] | None = None, year: int = 2021
    ) -> None:
        """Bulk load establishment data into cache."""
        results = await self._client.fetch_establishments_by_msa(naics_codes, year)
        for r in results:
            cbsa = r["cbsa_code"]
            naics = r["naics"]
            key = f"{cbsa}:{naics}"
            self._cache[key] = {
                "establishments": r["establishments"],
                "employees": r["employees"],
                "payroll_thousands": r["payroll_thousands"],
                "density": r["establishments"],
                "year": r["year"],
            }
            all_key = f"{cbsa}:all"
            if all_key not in self._cache:
                self._cache[all_key] = {
                    "establishments": 0, "employees": 0,
                    "payroll_thousands": 0, "density": 0, "year": year,
                }
            self._cache[all_key]["establishments"] += r["establishments"]
            self._cache[all_key]["employees"] += r["employees"]
            self._cache[all_key]["payroll_thousands"] += r["payroll_thousands"]
            self._cache[all_key]["density"] += r["establishments"]

        logger.info(
            "CBPCityDataProvider loaded %d entries", len(self._cache)
        )
```

- [ ] **Step 2: Verify import and architecture lint**

```bash
python3.11 -c "from src.clients.census.cbp_adapter import CBPCityDataProvider; print('OK')"
python3.11 scripts/check_domain_imports.py
```

---

### Task 7: CBP Boundary Tests

**Files:**
- Create: `tests/clients/census/test_cbp_adapter.py`

- [ ] **Step 1: Write boundary tests**

Create `tests/clients/census/test_cbp_adapter.py`:

```python
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


async def test_business_density_missing_city(provider):
    assert provider.get_business_density("00000", "238220") is None


async def test_demographics_returns_none(provider):
    assert provider.get_demographics("14260") is None


async def test_find_similar_returns_empty(provider):
    city = City(city_id="14260", name="Boise")
    assert provider.find_similar_cities(city) == []
```

- [ ] **Step 2: Run tests**

```bash
python3.11 -m pytest tests/clients/census/ -v
```

Expected: 13 passed (8 from 7A + 5 from 7B).

- [ ] **Step 3: Commit 7B**

```bash
git add src/clients/census/cbp_client.py src/clients/census/cbp_adapter.py tests/clients/census/test_cbp_adapter.py
git commit -m "feat(clients): add Census CBP client and CBPCityDataProvider adapter

Implements CityDataProvider.get_business_density using Census
County Business Patterns data. Establishment counts by NAICS
per MSA — enables Blue Ocean lens."
```

---

## Task Group 7C: BLS Wages (ACV Estimates)

**Unlocks:** Full `Cash Cow` lens (`acv_estimate` filter), ACV on Service entities.

### Task 8: BLS Client

**Files:**
- Create: `src/clients/bls/__init__.py`
- Create: `src/clients/bls/client.py`

- [ ] **Step 1: Create package init**

```python
# src/clients/bls/__init__.py
```

(Empty file.)

- [ ] **Step 2: Implement BLSClient**

Create `src/clients/bls/client.py`:

```python
"""BLS Occupational Employment & Wage Statistics (OEWS) API client.

Fetches mean hourly wages by occupation and area.
API v2 docs: https://www.bls.gov/developers/api_signature_v2.htm
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


class BLSClient:
    """Fetches occupation wage data from BLS OEWS."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    async def fetch_occupation_wages(
        self,
        soc_code: str,
        area_code: str = "0000000",
        start_year: int = 2023,
        end_year: int = 2023,
    ) -> dict[str, Any] | None:
        """Fetch mean hourly wage for an occupation in an area.

        Series ID format: OEUM{area}{industry}{occupation}{datatype}
        Data type 04 = Mean hourly wage.
        """
        series_id = f"OEUM{area_code}000000{soc_code}04"
        payload: dict[str, Any] = {
            "seriesid": [series_id],
            "startyear": str(start_year),
            "endyear": str(end_year),
        }
        if self._api_key:
            payload["registrationkey"] = self._api_key

        logger.info(
            "BLSClient.fetch_occupation_wages START soc=%s area=%s",
            soc_code, area_code,
        )

        async with httpx.AsyncClient() as client:
            resp = await client.post(BLS_API_URL, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "REQUEST_SUCCEEDED":
            logger.warning("BLS request failed: %s", data.get("message"))
            return None

        series = data.get("Results", {}).get("series", [])
        if not series or not series[0].get("data"):
            return None

        latest = series[0]["data"][0]
        result = {
            "soc_code": soc_code,
            "area_code": area_code,
            "mean_hourly_wage": float(latest["value"]),
            "year": int(latest["year"]),
        }
        logger.info(
            "BLSClient.fetch_occupation_wages DONE wage=%.2f",
            result["mean_hourly_wage"],
        )
        return result
```

- [ ] **Step 3: Verify import**

```bash
python3.11 -c "from src.clients.bls.client import BLSClient; print('OK')"
```

---

### Task 9: NAICS-SOC Mapping

**Files:**
- Create: `src/clients/bls/naics_soc_map.py`

- [ ] **Step 1: Create mapping module**

Create `src/clients/bls/naics_soc_map.py`:

```python
"""NAICS → SOC code mapping and average job-hours data.

Maps service NAICS codes to primary BLS occupation codes (SOC)
and stores average job duration estimates for ACV calculation.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceOccupation:
    naics: str
    soc: str
    label: str
    avg_job_hours: float
    overhead_multiplier: float = 2.0


NAICS_SOC_MAP: dict[str, ServiceOccupation] = {
    "238220": ServiceOccupation(
        naics="238220", soc="472152",
        label="Plumbing contractors → Plumbers",
        avg_job_hours=3.0,
    ),
    "238210": ServiceOccupation(
        naics="238210", soc="472111",
        label="Electrical contractors → Electricians",
        avg_job_hours=2.5,
    ),
    "238160": ServiceOccupation(
        naics="238160", soc="472181",
        label="Roofing contractors → Roofers",
        avg_job_hours=8.0,
    ),
    "561730": ServiceOccupation(
        naics="561730", soc="372012",
        label="Landscaping → Landscaping workers",
        avg_job_hours=2.0,
    ),
    "561720": ServiceOccupation(
        naics="561720", soc="372012",
        label="Janitorial → Janitors",
        avg_job_hours=2.0,
        overhead_multiplier=1.5,
    ),
    "238140": ServiceOccupation(
        naics="238140", soc="472031",
        label="Masonry contractors → Masons",
        avg_job_hours=6.0,
    ),
    "238330": ServiceOccupation(
        naics="238330", soc="472044",
        label="Flooring contractors → Tile setters",
        avg_job_hours=5.0,
    ),
    "238910": ServiceOccupation(
        naics="238910", soc="499071",
        label="Site preparation → Maintenance workers",
        avg_job_hours=4.0,
    ),
}


def get_soc_for_naics(naics: str) -> ServiceOccupation | None:
    return NAICS_SOC_MAP.get(naics)


def compute_acv(
    mean_hourly_wage: float,
    avg_job_hours: float,
    overhead_multiplier: float = 2.0,
) -> float:
    """ACV = mean_hourly_wage × avg_job_hours × overhead_multiplier."""
    return mean_hourly_wage * avg_job_hours * overhead_multiplier
```

- [ ] **Step 2: Verify import**

```bash
python3.11 -c "from src.clients.bls.naics_soc_map import compute_acv; print(compute_acv(60, 3, 2.0))"
```

Expected: `360.0`

---

### Task 10: BLS Adapter

**Files:**
- Create: `src/clients/bls/adapter.py`

- [ ] **Step 1: Implement BLSServiceDataProvider**

Create `src/clients/bls/adapter.py`:

```python
"""Adapter implementing ServiceDataProvider (ACV) from BLS wage data."""
from __future__ import annotations

import logging
from typing import Any

from src.domain.entities import SeasonalityCurve
from src.clients.bls.client import BLSClient
from src.clients.bls.naics_soc_map import (
    compute_acv,
    get_soc_for_naics,
)

logger = logging.getLogger(__name__)


class BLSServiceDataProvider:
    """Partial ServiceDataProvider for ACV estimates from BLS wages."""

    def __init__(self, client: BLSClient):
        self._client = client
        self._cache: dict[str, float] = {}

    def get_acv_estimate(self, naics: str, city_id: str) -> float | None:
        key = f"{naics}:{city_id}"
        local = self._cache.get(key)
        if local is not None:
            return local
        return self._cache.get(f"{naics}:national")

    def get_seasonality(self, service_name: str) -> SeasonalityCurve | None:
        return None

    def get_establishment_growth(
        self, naics: str, city_id: str
    ) -> float | None:
        return None

    async def load_acv_for_naics(
        self, naics: str, area_code: str = "0000000"
    ) -> float | None:
        """Fetch wages and compute ACV for a NAICS code."""
        mapping = get_soc_for_naics(naics)
        if mapping is None:
            logger.warning("No SOC mapping for NAICS %s", naics)
            return None

        wages = await self._client.fetch_occupation_wages(
            mapping.soc, area_code
        )
        if wages is None:
            return None

        acv = compute_acv(
            wages["mean_hourly_wage"],
            mapping.avg_job_hours,
            mapping.overhead_multiplier,
        )

        city_key = "national" if area_code == "0000000" else area_code
        self._cache[f"{naics}:{city_key}"] = acv

        logger.info(
            "BLS ACV loaded naics=%s area=%s wage=%.2f acv=%.2f",
            naics, area_code, wages["mean_hourly_wage"], acv,
        )
        return acv

    async def load_all_national(self) -> None:
        """Load national-level ACV for all mapped NAICS codes."""
        from src.clients.bls.naics_soc_map import NAICS_SOC_MAP

        for naics in NAICS_SOC_MAP:
            await self.load_acv_for_naics(naics)
        logger.info(
            "BLSServiceDataProvider loaded %d national ACVs",
            len(self._cache),
        )
```

- [ ] **Step 2: Verify import and architecture lint**

```bash
python3.11 -c "from src.clients.bls.adapter import BLSServiceDataProvider; print('OK')"
python3.11 scripts/check_domain_imports.py
```

---

### Task 11: BLS Boundary Tests

**Files:**
- Create: `tests/clients/bls/__init__.py`
- Create: `tests/clients/bls/test_bls_adapter.py`

- [ ] **Step 1: Create test package**

```python
# tests/clients/bls/__init__.py
```

(Empty file.)

- [ ] **Step 2: Write boundary tests**

Create `tests/clients/bls/test_bls_adapter.py`:

```python
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
```

- [ ] **Step 3: Run tests**

```bash
python3.11 -m pytest tests/clients/bls/ -v
```

Expected: 8 passed.

- [ ] **Step 4: Commit 7C**

```bash
git add src/clients/bls/ tests/clients/bls/
git commit -m "feat(clients): add BLS OEWS client and BLSServiceDataProvider adapter

Implements ServiceDataProvider.get_acv_estimate using BLS occupation
wage data. ACV = hourly_wage × job_hours × overhead_multiplier.
NAICS→SOC mapping covers 8 service categories. Enables Cash Cow lens."
```

---

## Task Group 7D: DataForSEO Trends (Search Seasonality)

**Unlocks:** `Seasonal Arbitrage` lens (`months_to_peak` filter, `seasonal_timing` signal).

### Task 12: Add Trends Endpoint to DataForSEO Client

**Files:**
- Modify: `src/clients/dataforseo/endpoints.py`
- Modify: `src/clients/dataforseo/client.py`

- [ ] **Step 1: Add GOOGLE_TRENDS endpoint**

In `src/clients/dataforseo/endpoints.py`, add after the `LOCATIONS` endpoint:

```python
GOOGLE_TRENDS = Endpoint(
    post_path="keywords_data/google_trends/explore/live",
    get_path=None,
    mode=QueueMode.LIVE,
    cost_per_call=0.05,
)
```

- [ ] **Step 2: Add google_trends method to DataForSEOClient**

In `src/clients/dataforseo/client.py`, add a new method after the existing API methods (after `keyword_suggestions`):

```python
async def google_trends(
    self,
    keywords: list[str],
    location_code: int = 2840,  # US
    time_range: str = "past_5_years",
) -> APIResponse:
    """Fetch Google Trends interest-over-time data.

    Returns monthly interest index (0-100) for keywords.
    Endpoint: keywords_data/google_trends/explore/live
    Max 5 keywords per request, $0.05/task.
    """
    payload = [
        {
            "keywords": keywords[:5],
            "location_code": location_code,
            "time_range": time_range,
        }
    ]
    return await self._live_request(ep.GOOGLE_TRENDS, payload)
```

- [ ] **Step 3: Verify import**

```bash
python3.11 -c "from src.clients.dataforseo.endpoints import GOOGLE_TRENDS; print(GOOGLE_TRENDS.post_path)"
```

Expected: `keywords_data/google_trends/explore/live`

---

### Task 13: Trends Adapter

**Files:**
- Create: `src/clients/trends/__init__.py`
- Create: `src/clients/trends/adapter.py`

- [ ] **Step 1: Create package init**

```python
# src/clients/trends/__init__.py
```

(Empty file.)

- [ ] **Step 2: Implement TrendsServiceDataProvider**

Create `src/clients/trends/adapter.py`:

```python
"""Adapter implementing ServiceDataProvider (seasonality) from DataForSEO Trends."""
from __future__ import annotations

import logging
from typing import Any, Protocol

from src.domain.entities import SeasonalityCurve

logger = logging.getLogger(__name__)


class TrendsDataSource(Protocol):
    """Protocol for the trends data source (DataForSEO or fake).

    DataForSEOClient.google_trends() returns APIResponse (dataclass with
    .data containing the raw JSON dict). Fakes should return objects with
    a .data attribute matching this structure.
    """
    async def google_trends(
        self, keywords: list[str], **kwargs: Any
    ) -> Any: ...


class TrendsServiceDataProvider:
    """Partial ServiceDataProvider for seasonality from Google Trends via DataForSEO."""

    def __init__(self, client: TrendsDataSource):
        self._client = client
        self._cache: dict[str, SeasonalityCurve] = {}

    def get_acv_estimate(self, naics: str, city_id: str) -> float | None:
        return None

    def get_seasonality(self, service_name: str) -> SeasonalityCurve | None:
        return self._cache.get(service_name.lower())

    def get_establishment_growth(
        self, naics: str, city_id: str
    ) -> float | None:
        return None

    async def load_seasonality(
        self, service_name: str, location_code: int = 2840
    ) -> SeasonalityCurve | None:
        """Fetch interest-over-time from DataForSEO and build a SeasonalityCurve."""
        logger.info(
            "TrendsServiceDataProvider.load_seasonality START keyword=%s",
            service_name,
        )

        response = await self._client.google_trends(
            keywords=[service_name],
            location_code=location_code,
        )

        # DataForSEOClient returns APIResponse(data=...) — extract raw dict
        raw = response.data if hasattr(response, "data") else response
        monthly = self._extract_monthly_averages(raw)
        if not monthly:
            logger.warning("No trends data for '%s'", service_name)
            return None

        peak_month = max(monthly, key=monthly.get)
        trough_month = min(monthly, key=monthly.get)
        max_val = max(monthly.values())
        amplitude = (
            (monthly[peak_month] - monthly[trough_month]) / max_val
            if max_val > 0
            else 0
        )

        normalized = {
            m: v / max_val if max_val > 0 else 0.0
            for m, v in monthly.items()
        }

        curve = SeasonalityCurve(
            monthly_index=normalized,
            peak_month=peak_month,
            trough_month=trough_month,
            amplitude=amplitude,
        )
        self._cache[service_name.lower()] = curve

        logger.info(
            "TrendsServiceDataProvider.load_seasonality DONE peak=%d trough=%d amp=%.2f",
            peak_month, trough_month, amplitude,
        )
        return curve

    @staticmethod
    def _extract_monthly_averages(
        response: Any,
    ) -> dict[int, float] | None:
        """Extract monthly averages from DataForSEO Trends response.

        Response: tasks[0].result[0].items[] where each item of type
        "google_trends_graph" has data[] with {date_from, values[]}.
        Values are 0-100 interest index per keyword.
        We average each month across years to get a seasonal profile.
        """
        try:
            tasks = response.get("tasks", [])
            if not tasks:
                return None
            result = tasks[0].get("result", [])
            if not result:
                return None
            items = result[0].get("items", [])
            if not items:
                return None
        except (AttributeError, IndexError, TypeError):
            return None

        month_sums: dict[int, float] = {}
        month_counts: dict[int, int] = {}

        for item in items:
            if item.get("type") != "google_trends_graph":
                continue
            data_points = item.get("data", [])
            if not data_points:
                continue

            for point in data_points:
                date_str = point.get("date_from", "")
                values = point.get("values", [])
                if not date_str or not values:
                    continue

                try:
                    month = int(date_str.split("-")[1])
                except (IndexError, ValueError):
                    continue

                value = values[0] if isinstance(values, list) else 0
                if value is None:
                    continue

                month_sums[month] = month_sums.get(month, 0) + float(value)
                month_counts[month] = month_counts.get(month, 0) + 1

        if not month_sums:
            return None

        return {
            m: month_sums[m] / month_counts[m]
            for m in sorted(month_sums)
        }
```

- [ ] **Step 3: Verify import and architecture lint**

```bash
python3.11 -c "from src.clients.trends.adapter import TrendsServiceDataProvider; print('OK')"
python3.11 scripts/check_domain_imports.py
```

---

### Task 14: Trends Boundary Tests

**Files:**
- Create: `tests/clients/trends/__init__.py`
- Create: `tests/clients/trends/test_trends_adapter.py`

- [ ] **Step 1: Create test package**

```python
# tests/clients/trends/__init__.py
```

(Empty file.)

- [ ] **Step 2: Write boundary tests**

Create `tests/clients/trends/test_trends_adapter.py`:

```python
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
```

- [ ] **Step 3: Run tests**

```bash
python3.11 -m pytest tests/clients/trends/ -v
```

Expected: 11 passed.

- [ ] **Step 4: Commit 7D**

```bash
git add src/clients/dataforseo/endpoints.py src/clients/dataforseo/client.py \
    src/clients/trends/ tests/clients/trends/
git commit -m "feat(clients): add DataForSEO Trends endpoint and TrendsServiceDataProvider

Extends DataForSEO client with google_trends() method hitting
keywords_data/google_trends/explore/live. TrendsServiceDataProvider
builds SeasonalityCurve from monthly averages. Enables Seasonal
Arbitrage lens."
```

---

## Task Group: Composition + Migration

### Task 15: Composite Providers

**Files:**
- Create: `src/clients/composite_providers.py`

- [ ] **Step 1: Implement CompositeProviders**

Create `src/clients/composite_providers.py`:

```python
"""Composite data providers — compose sub-providers into full Protocol interfaces.

Census ACS (demographics) + CBP (business density) → CompositeCityDataProvider
BLS (ACV) + Trends (seasonality) + CBP (growth) → CompositeServiceDataProvider
"""
from __future__ import annotations

from typing import Any

from src.domain.entities import City, SeasonalityCurve
from src.clients.census.adapter import CensusCityDataProvider
from src.clients.census.cbp_adapter import CBPCityDataProvider
from src.clients.bls.adapter import BLSServiceDataProvider
from src.clients.trends.adapter import TrendsServiceDataProvider


class CompositeCityDataProvider:
    """Combines Census ACS (demographics) + CBP (business density)."""

    def __init__(
        self,
        acs: CensusCityDataProvider,
        cbp: CBPCityDataProvider | None = None,
    ):
        self._acs = acs
        self._cbp = cbp

    def get_demographics(self, city_id: str) -> dict[str, Any] | None:
        return self._acs.get_demographics(city_id)

    def get_business_density(
        self, city_id: str, naics: str | None = None
    ) -> dict[str, Any] | None:
        if self._cbp is None:
            return None
        return self._cbp.get_business_density(city_id, naics)

    def find_similar_cities(
        self, reference: City, limit: int = 10
    ) -> list[tuple[City, float]]:
        return self._acs.find_similar_cities(reference, limit)


class CompositeServiceDataProvider:
    """Combines BLS (ACV) + Trends (seasonality)."""

    def __init__(
        self,
        bls: BLSServiceDataProvider | None = None,
        trends: TrendsServiceDataProvider | None = None,
    ):
        self._bls = bls
        self._trends = trends

    def get_acv_estimate(self, naics: str, city_id: str) -> float | None:
        if self._bls is None:
            return None
        return self._bls.get_acv_estimate(naics, city_id)

    def get_seasonality(self, service_name: str) -> SeasonalityCurve | None:
        if self._trends is None:
            return None
        return self._trends.get_seasonality(service_name)

    def get_establishment_growth(
        self, naics: str, city_id: str
    ) -> float | None:
        return None
```

- [ ] **Step 2: Verify import and architecture lint**

```bash
python3.11 -c "from src.clients.composite_providers import CompositeCityDataProvider, CompositeServiceDataProvider; print('OK')"
python3.11 scripts/check_domain_imports.py
```

---

### Task 16: Composite Provider Tests

**Files:**
- Create: `tests/clients/test_composite_providers.py`

- [ ] **Step 1: Write tests**

Create `tests/clients/test_composite_providers.py`:

```python
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
```

- [ ] **Step 2: Run all provider tests**

```bash
python3.11 -m pytest tests/clients/census/ tests/clients/bls/ tests/clients/trends/ tests/clients/test_composite_providers.py -v
```

Expected: 39 passed total (8 Census + 5 CBP + 8 BLS + 11 Trends + 7 Composite).

- [ ] **Step 3: Commit composition**

```bash
git add src/clients/composite_providers.py tests/clients/test_composite_providers.py
git commit -m "feat(clients): add CompositeCityDataProvider and CompositeServiceDataProvider

Composes ACS+CBP into CityDataProvider and BLS+Trends into
ServiceDataProvider. Ready for DiscoveryService wiring."
```

---

### Task 17: SQL Migration

**Files:**
- Create: `supabase/migrations/011_data_provider_tables.sql`

- [ ] **Step 1: Create migration**

Create `supabase/migrations/011_data_provider_tables.sql`:

```sql
-- Phase 7: Reference tables for data providers
-- Census ACS demographics, CBP business patterns, BLS ACV estimates

-- Cities reference table (Census ACS)
CREATE TABLE IF NOT EXISTS cities (
    city_id TEXT PRIMARY KEY,
    cbsa_code TEXT UNIQUE,
    name TEXT NOT NULL,
    state TEXT,
    population INTEGER,
    median_income NUMERIC,
    homeownership_rate NUMERIC,
    housing_age_median NUMERIC,
    broadband_penetration NUMERIC,
    growth_rate NUMERIC,
    archetype TEXT,
    demographics JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cities_population ON cities(population);
CREATE INDEX IF NOT EXISTS idx_cities_state ON cities(state);
CREATE INDEX IF NOT EXISTS idx_cities_archetype ON cities(archetype);

-- Business patterns (Census CBP)
CREATE TABLE IF NOT EXISTS business_patterns (
    cbsa_code TEXT NOT NULL,
    naics_code TEXT NOT NULL,
    year INTEGER NOT NULL,
    establishments INTEGER,
    employees INTEGER,
    payroll_thousands INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (cbsa_code, naics_code, year)
);

CREATE INDEX IF NOT EXISTS idx_bp_cbsa ON business_patterns(cbsa_code);
CREATE INDEX IF NOT EXISTS idx_bp_naics ON business_patterns(naics_code);

-- Service ACV estimates (BLS wages)
CREATE TABLE IF NOT EXISTS service_acv_estimates (
    naics_code TEXT NOT NULL,
    cbsa_code TEXT DEFAULT 'national',
    mean_hourly_wage NUMERIC,
    avg_job_hours NUMERIC,
    overhead_multiplier NUMERIC DEFAULT 2.0,
    acv_estimate NUMERIC,
    year INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (naics_code, cbsa_code)
);
```

- [ ] **Step 2: Commit migration**

```bash
git add supabase/migrations/011_data_provider_tables.sql
git commit -m "feat(db): add reference tables for Census, CBP, and BLS data providers"
```

---

### Task 18: Final Validation

- [ ] **Step 1: Run full test suite**

```bash
python3.11 -m pytest tests/ -v --ignore=tests/integration/ 2>&1 | tail -30
```

Expected: 660+ passed (627 baseline + ~39 new provider tests). 3 pre-existing failures in test_api_reports.py are known — assert no NEW failures.

- [ ] **Step 2: Architecture lint (script + pytest)**

```bash
python3.11 scripts/check_domain_imports.py
python3.11 -m pytest tests/architecture/ -v
```

Expected: `0 violations` from lint script. 2 passed from architecture tests. New files are all in `src/clients/`, not `src/domain/`.

- [ ] **Step 3: Verify lens requirements are addressable**

```bash
python3.11 -c "
from src.domain.lenses import BLUE_OCEAN, SEASONAL_ARBITRAGE, EXPAND_CONQUER, CASH_COW
print('Blue Ocean requires:', BLUE_OCEAN.required_signals)
print('Seasonal Arbitrage requires:', SEASONAL_ARBITRAGE.required_signals)
print('Expand & Conquer requires:', EXPAND_CONQUER.required_signals)
print('Cash Cow filters:', [(f.signal, f.operator, f.value) for f in CASH_COW.filters])
"
```

- [ ] **Step 4: Verify ruff lint**

```bash
ruff check src/clients/census/ src/clients/bls/ src/clients/trends/ src/clients/composite_providers.py
```

Expected: No errors.

- [ ] **Step 5: Final commit — no code changes, just verify clean state**

```bash
git status
git log --oneline phase-7-data-providers...dev
```

Expected: 7 commits on the branch (numpy dep + 4 sub-phases + composite + migration).

---

## Summary of What Each Sub-Phase Enables

| Sub-Phase | Provider | Protocol Methods | Lenses Unlocked |
|-----------|----------|-----------------|-----------------|
| 7A | `CensusCityDataProvider` | `get_demographics`, `find_similar_cities` | Expand & Conquer |
| 7B | `CBPCityDataProvider` | `get_business_density` | Blue Ocean |
| 7C | `BLSServiceDataProvider` | `get_acv_estimate` | Cash Cow (full) |
| 7D | `TrendsServiceDataProvider` | `get_seasonality` | Seasonal Arbitrage |
| Composite | `CompositeCityDataProvider` + `CompositeServiceDataProvider` | All of the above | All 9 lenses functional |

## New Files Created (20 total)

```
src/clients/census/__init__.py
src/clients/census/client.py
src/clients/census/adapter.py
src/clients/census/cbp_client.py
src/clients/census/cbp_adapter.py
src/clients/bls/__init__.py
src/clients/bls/client.py
src/clients/bls/naics_soc_map.py
src/clients/bls/adapter.py
src/clients/trends/__init__.py
src/clients/trends/adapter.py
src/clients/composite_providers.py
tests/clients/census/__init__.py
tests/clients/census/test_census_adapter.py
tests/clients/census/test_cbp_adapter.py
tests/clients/bls/__init__.py
tests/clients/bls/test_bls_adapter.py
tests/clients/trends/__init__.py
tests/clients/trends/test_trends_adapter.py
tests/clients/test_composite_providers.py
supabase/migrations/011_data_provider_tables.sql
```

## Existing Files Modified (2 total)

```
src/clients/dataforseo/endpoints.py  (add GOOGLE_TRENDS)
src/clients/dataforseo/client.py     (add google_trends method)
pyproject.toml                       (add numpy dep)
```
