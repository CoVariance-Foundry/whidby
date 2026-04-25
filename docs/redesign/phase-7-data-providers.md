# Phase 7: New Data Providers

**Objective:** Integrate Census ACS (city demographics), Census CBP (business density, establishment growth), BLS (occupation wages → ACV estimates), and Google Trends (search seasonality). Each is an independent adapter implementing `CityDataProvider` or `ServiceDataProvider`. As each comes online, the remaining lenses light up.

**Risk:** Low per-provider. Each is independent. The domain already defines the interfaces.
**Depends on:** Phase 1 (ports defined), Phase 5 (DiscoveryService ready to consume data).
**Blocks:** Full functionality of Blue Ocean, Portfolio Builder, Expand & Conquer, Seasonal Arbitrage, and full Cash Cow lenses.

**Structure:** This phase is 4 independent sub-phases that can run in parallel.

---

## Sub-Phase 7A: Census ACS (City Demographics)

**Purpose:** Populate City entities with demographic data — population, median income, homeownership rate, housing age, broadband penetration, growth rate. Enables city filtering and the Expand & Conquer similarity search.

**Unlocks:** Expand & Conquer lens, city filtering by demographics.

### Agent Instructions

#### Step 1: Research the Census ACS API

```bash
# The Census Bureau provides a free API. Key endpoints:
# - ACS 5-Year Estimates: https://api.census.gov/data/2022/acs/acs5
# - Variables list: https://api.census.gov/data/2022/acs/acs5/variables.html
# - Geography: MSA/Metro Statistical Area level

# Key variables to fetch:
# B01003_001E  = Total population
# B19013_001E  = Median household income
# B25003_001E  = Total housing units (tenure)
# B25003_002E  = Owner-occupied units
# B25035_001E  = Median year structure built
# B28002_004E  = Broadband internet subscription
# B01003_001E  = Population (for growth rate, compare 2017→2022)
```

#### Step 2: Create the Census client

**`src/clients/census/client.py`:**

```python
"""
Census Bureau API client.

Fetches ACS 5-Year estimates at the MSA (Metropolitan Statistical Area) level.
Free API, optional API key for higher rate limits.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ACS_BASE_URL = "https://api.census.gov/data/{year}/acs/acs5"

# Variables we need for City enrichment
DEMOGRAPHIC_VARIABLES = {
    "B01003_001E": "total_population",
    "B19013_001E": "median_household_income",
    "B25003_001E": "total_housing_units",
    "B25003_002E": "owner_occupied_units",
    "B25035_001E": "median_year_built",
    "B28002_004E": "broadband_subscriptions",
    "B28002_001E": "total_internet_universe",
}


class CensusClient:
    """Fetches demographic data from the Census ACS API."""

    def __init__(self, api_key: str | None = None, year: int = 2022):
        self._api_key = api_key
        self._year = year
        self._base_url = ACS_BASE_URL.format(year=year)

    async def fetch_msa_demographics(
        self, cbsa_codes: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch demographic data for MSAs.

        If cbsa_codes is None, fetches all MSAs.
        Returns list of dicts with normalized field names.
        """
        variables = ",".join(DEMOGRAPHIC_VARIABLES.keys())
        params = {
            "get": f"NAME,{variables}",
            "for": "metropolitan statistical area/micropolitan statistical area:*",
        }
        if self._api_key:
            params["key"] = self._api_key

        async with httpx.AsyncClient() as client:
            resp = await client.get(self._base_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        # First row is headers, rest is data
        headers = data[0]
        results = []
        for row in data[1:]:
            record = dict(zip(headers, row))
            cbsa = record.get("metropolitan statistical area/micropolitan statistical area")

            if cbsa_codes and cbsa not in cbsa_codes:
                continue

            normalized = {
                "cbsa_code": cbsa,
                "name": record.get("NAME", ""),
            }
            for var_code, field_name in DEMOGRAPHIC_VARIABLES.items():
                raw = record.get(var_code)
                normalized[field_name] = int(raw) if raw and raw != "-666666666" else None

            results.append(normalized)

        return results

    async def fetch_growth_rate(
        self, cbsa_code: str, years: tuple[int, int] = (2017, 2022)
    ) -> float | None:
        """
        Compute population growth rate between two ACS years.
        Returns annualized growth rate.
        """
        # Fetch population for both years
        # growth_rate = (pop_new / pop_old) ** (1 / (year_new - year_old)) - 1
        pass  # Implement using two API calls with different years
```

#### Step 3: Create the Census adapter

**`src/clients/census/adapter.py`:**

```python
"""Adapter implementing CityDataProvider using Census ACS data."""
from __future__ import annotations

from typing import Any

import numpy as np  # for cosine similarity

from src.domain.entities import City
from src.clients.census.client import CensusClient


class CensusCityDataProvider:
    """Implements CityDataProvider using Census ACS data."""

    def __init__(self, client: CensusClient):
        self._client = client
        self._cache: dict[str, dict[str, Any]] = {}

    def get_demographics(self, city_id: str) -> dict[str, Any] | None:
        """Return cached demographics for a city."""
        return self._cache.get(city_id)

    def get_business_density(
        self, city_id: str, naics: str | None = None
    ) -> dict[str, Any] | None:
        """Business density comes from CBP (Sub-Phase 7B), not ACS."""
        return None

    def find_similar_cities(
        self, reference: City, limit: int = 10
    ) -> list[tuple[City, float]]:
        """
        Find cities similar to reference using cosine similarity
        on demographic vectors.

        Vector components: population (log), median_income, 
        homeownership_rate, growth_rate, broadband_penetration.
        """
        ref_vector = self._city_to_vector(reference)
        if ref_vector is None:
            return []

        similarities = []
        for city_id, data in self._cache.items():
            if city_id == reference.city_id:
                continue
            city = self._data_to_city(city_id, data)
            vec = self._city_to_vector(city)
            if vec is None:
                continue
            sim = self._cosine_similarity(ref_vector, vec)
            similarities.append((city, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]

    async def load_all(self) -> None:
        """Bulk load all MSA demographics into cache."""
        results = await self._client.fetch_msa_demographics()
        for r in results:
            self._cache[r["cbsa_code"]] = r

    def _city_to_vector(self, city: City) -> list[float] | None:
        """Convert city demographics to a feature vector for similarity."""
        if city.population is None or city.median_income is None:
            return None
        return [
            np.log(city.population) if city.population > 0 else 0,
            city.median_income or 0,
            city.homeownership_rate or 0,
            city.growth_rate or 0,
            city.broadband_penetration or 0,
        ]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        a_arr = np.array(a)
        b_arr = np.array(b)
        norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if norm == 0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / norm)

    @staticmethod
    def _data_to_city(city_id: str, data: dict) -> City:
        """Convert cached data to City entity."""
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
            homeownership_rate=(owner / total_housing) if owner and total_housing else None,
            housing_age_median=2024 - data.get("median_year_built", 2024) if data.get("median_year_built") else None,
            broadband_penetration=(broadband / internet_total) if broadband and internet_total else None,
        )
```

#### Step 4: Create reference table

```sql
-- Migration: create cities reference table
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

CREATE INDEX idx_cities_population ON cities(population);
CREATE INDEX idx_cities_state ON cities(state);
CREATE INDEX idx_cities_archetype ON cities(archetype);
```

#### Step 5: Write tests

```python
"""Tests for Census ACS data provider."""
import pytest
from src.domain.entities import City
from src.clients.census.adapter import CensusCityDataProvider


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
        ]


@pytest.fixture
async def provider():
    p = CensusCityDataProvider(FakeCensusClient())
    await p.load_all()
    return p


@pytest.mark.asyncio
async def test_demographics_loaded(provider):
    data = provider.get_demographics("14260")
    assert data is not None
    assert data["total_population"] == 780_000


@pytest.mark.asyncio
async def test_find_similar_cities(provider):
    boise = City(
        city_id="14260", name="Boise", population=780_000,
        median_income=62_000, homeownership_rate=0.67,
    )
    similar = provider.find_similar_cities(boise, limit=5)
    assert len(similar) > 0
    assert similar[0][1] > 0  # similarity score
```

#### Validate

```bash
python -m pytest tests/clients/census/ -v
python scripts/check_domain_imports.py  # Census adapter doesn't touch domain internals
```

---

## Sub-Phase 7B: Census CBP (Business Density & Establishment Growth)

**Purpose:** County Business Patterns data provides establishment counts by NAICS code per metro — the "supply side" of a market. Establishment growth rate over time signals emerging vs. saturated markets.

**Unlocks:** Blue Ocean lens (establishment_growth filter), business_density on City entities.

### Agent Instructions

#### Step 1: Research Census CBP API

```bash
# CBP endpoint: https://api.census.gov/data/2021/cbp
# Key variables:
# ESTAB = Number of establishments
# EMP = Number of employees
# PAYANN = Annual payroll ($1,000s)
# NAICS2017 = NAICS code
# Geography: MSA level
#
# For growth rate: compare CBP 2017 vs 2021
```

#### Step 2: Create CBP client and adapter

**`src/clients/census/cbp_client.py`:**

```python
"""Census County Business Patterns client."""
from __future__ import annotations

import httpx
from typing import Any

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
        """
        Fetch establishment counts by MSA and NAICS code.
        Returns list of {cbsa_code, naics, establishments, employees, payroll}.
        """
        url = CBP_BASE_URL.format(year=year)
        params = {
            "get": "ESTAB,EMP,PAYANN,NAICS2017",
            "for": "metropolitan statistical area/micropolitan statistical area:*",
        }
        if naics_codes:
            params["NAICS2017"] = ",".join(naics_codes)
        if self._api_key:
            params["key"] = self._api_key

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        headers = data[0]
        results = []
        for row in data[1:]:
            record = dict(zip(headers, row))
            results.append({
                "cbsa_code": record.get("metropolitan statistical area/micropolitan statistical area"),
                "naics": record.get("NAICS2017"),
                "establishments": int(record.get("ESTAB", 0)),
                "employees": int(record.get("EMP", 0)),
                "payroll_thousands": int(record.get("PAYANN", 0)),
                "year": year,
            })
        return results

    async def compute_establishment_growth(
        self, cbsa_code: str, naics: str,
        year_old: int = 2017, year_new: int = 2021,
    ) -> float | None:
        """
        Compute establishment growth rate between two years.
        Returns annualized growth rate.
        """
        old_data = await self.fetch_establishments_by_msa([naics], year_old)
        new_data = await self.fetch_establishments_by_msa([naics], year_new)

        old_count = next(
            (d["establishments"] for d in old_data if d["cbsa_code"] == cbsa_code),
            None
        )
        new_count = next(
            (d["establishments"] for d in new_data if d["cbsa_code"] == cbsa_code),
            None
        )

        if not old_count or not new_count or old_count == 0:
            return None

        years = year_new - year_old
        return (new_count / old_count) ** (1 / years) - 1
```

#### Step 3: Add business density to CityDataProvider adapter

Extend `CensusCityDataProvider` or create a composite:

```python
# The CBP adapter adds get_business_density to the CityDataProvider
class CBPCityDataProvider:
    """Partial CityDataProvider for business density (from CBP)."""

    def __init__(self, cbp_client: CBPClient):
        self._client = cbp_client
        self._cache: dict[str, dict] = {}

    def get_business_density(self, city_id: str, naics: str | None = None) -> dict | None:
        key = f"{city_id}:{naics or 'all'}"
        return self._cache.get(key)

    # ... load methods
```

#### Step 4: Create reference table

```sql
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

CREATE INDEX idx_bp_cbsa ON business_patterns(cbsa_code);
CREATE INDEX idx_bp_naics ON business_patterns(naics_code);
```

---

## Sub-Phase 7C: BLS Wages → ACV Estimates

**Purpose:** Bureau of Labor Statistics occupation wage data provides the basis for estimating Average Customer Value (ACV) by service category. A plumber earning $60/hr with an average job of 3 hours = ~$180 ACV. This enriches the Cash Cow lens.

**Unlocks:** Full Cash Cow lens (acv_estimate filter), ACV on Service entities.

### Agent Instructions

#### Step 1: Research BLS API

```bash
# BLS API v2: https://api.bls.gov/publicAPI/v2/timeseries/data/
# Occupational Employment and Wage Statistics (OEWS):
# Series ID format: OEUM{area}{industry}{occupation}{datatype}
#
# Key data types:
# 04 = Mean hourly wage
# 01 = Employment count
#
# Map NAICS → SOC (occupation) codes:
# 472152 = Plumbers (→ "plumbing" service)
# 238220 = Plumbing contractors (NAICS)
#
# Alternative: Use the flat files (faster for bulk):
# https://www.bls.gov/oes/tables.htm
```

#### Step 2: Create BLS client and adapter

**`src/clients/bls/client.py`:**

```python
"""BLS Occupational Employment & Wage Statistics client."""
from __future__ import annotations

import httpx
from typing import Any

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


class BLSClient:
    """Fetches wage data from BLS OEWS."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    async def fetch_occupation_wages(
        self, soc_code: str, area_code: str = "0000000"
    ) -> dict[str, Any] | None:
        """Fetch mean hourly wage for an occupation in an area."""
        # Build series ID
        series_id = f"OEUM{area_code}000000{soc_code}04"
        payload = {
            "seriesid": [series_id],
            "startyear": "2023",
            "endyear": "2023",
        }
        if self._api_key:
            payload["registrationkey"] = self._api_key

        async with httpx.AsyncClient() as client:
            resp = await client.post(BLS_API_URL, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "REQUEST_SUCCEEDED":
            return None

        series = data.get("Results", {}).get("series", [])
        if not series or not series[0].get("data"):
            return None

        latest = series[0]["data"][0]
        return {
            "soc_code": soc_code,
            "area_code": area_code,
            "mean_hourly_wage": float(latest["value"]),
            "year": int(latest["year"]),
        }
```

**`src/clients/bls/adapter.py`:**

```python
"""Adapter implementing ServiceDataProvider (ACV) from BLS wage data."""
from __future__ import annotations

from typing import Any

from src.domain.entities import SeasonalityCurve
from src.clients.bls.client import BLSClient

# NAICS → SOC mapping (service category → primary occupation)
# This needs to be built out as services are added
NAICS_TO_SOC = {
    "238220": "472152",  # Plumbing contractors → Plumbers
    "238210": "472111",  # Electrical contractors → Electricians
    "238160": "472181",  # Roofing contractors → Roofers
    "561730": "372012",  # Landscaping → Landscaping workers
    "561720": "372012",  # Janitorial → Janitors
}

# Average job hours by service (rough estimates for ACV calc)
AVG_JOB_HOURS = {
    "238220": 3.0,   # Plumbing: ~3 hours average
    "238210": 2.5,   # Electrical: ~2.5 hours
    "238160": 8.0,   # Roofing: ~8 hours (full day)
    "561730": 2.0,   # Landscaping: ~2 hours
}


class BLSServiceDataProvider:
    """Partial ServiceDataProvider for ACV estimates from BLS wages."""

    def __init__(self, client: BLSClient):
        self._client = client
        self._cache: dict[str, float] = {}

    def get_acv_estimate(self, naics: str, city_id: str) -> float | None:
        """
        Estimate ACV from BLS wage data.

        ACV ≈ mean_hourly_wage × avg_job_hours × overhead_multiplier

        The overhead multiplier (1.5-2.5x) accounts for:
        - Materials cost
        - Business overhead
        - Profit margin
        """
        key = f"{naics}:{city_id}"
        return self._cache.get(key)

    def get_seasonality(self, service_name: str) -> SeasonalityCurve | None:
        """Seasonality comes from Google Trends (Sub-Phase 7D), not BLS."""
        return None

    def get_establishment_growth(self, naics: str, city_id: str) -> float | None:
        """Establishment growth comes from CBP (Sub-Phase 7B), not BLS."""
        return None
```

#### Step 3: Create reference table

```sql
CREATE TABLE IF NOT EXISTS service_acv_estimates (
    naics_code TEXT NOT NULL,
    cbsa_code TEXT,  -- NULL = national average
    mean_hourly_wage NUMERIC,
    avg_job_hours NUMERIC,
    overhead_multiplier NUMERIC DEFAULT 2.0,
    acv_estimate NUMERIC GENERATED ALWAYS AS (
        mean_hourly_wage * avg_job_hours * overhead_multiplier
    ) STORED,
    year INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (naics_code, COALESCE(cbsa_code, 'national'))
);
```

---

## Sub-Phase 7D: Google Trends (Search Seasonality)

**Purpose:** Google Trends interest-over-time data reveals when demand peaks and troughs for each service. Building a rank-and-rent site 3-6 months before peak season means ranking by the time demand arrives.

**Unlocks:** Seasonal Arbitrage lens (months_to_peak filter, seasonal_timing signal).

### Agent Instructions

#### Step 1: Research Google Trends access

```bash
# Options:
# 1. pytrends library (unofficial, rate-limited, fragile)
# 2. SerpAPI Google Trends endpoint (paid, reliable)
# 3. DataForSEO Trends endpoint (if available in current plan)
#
# Recommended: Check if DataForSEO already has a Trends endpoint.
# If so, add it to the existing DataForSEO client.
# If not, use pytrends with aggressive caching.
```

#### Step 2: Create Trends client and adapter

**`src/clients/trends/client.py`:**

```python
"""Google Trends client for search seasonality data."""
from __future__ import annotations

from typing import Any

# Use pytrends or DataForSEO Trends endpoint
# from pytrends.request import TrendReq


class TrendsClient:
    """Fetches interest-over-time data for seasonality analysis."""

    def __init__(self):
        pass  # self._client = TrendReq()

    async def fetch_interest_over_time(
        self, keyword: str, geo: str = "US", timeframe: str = "today 5-y"
    ) -> dict[int, float] | None:
        """
        Fetch monthly interest index (0-100) for a keyword.
        Returns {month: avg_interest} averaged across years.
        """
        # result = self._client.build_payload([keyword], timeframe=timeframe, geo=geo)
        # df = self._client.interest_over_time()
        # ... aggregate by month, average across years
        # return {1: 45.2, 2: 48.1, ..., 12: 62.3}
        raise NotImplementedError("Implement with pytrends or DataForSEO")
```

**`src/clients/trends/adapter.py`:**

```python
"""Adapter implementing ServiceDataProvider (seasonality) from Google Trends."""
from __future__ import annotations

from src.domain.entities import SeasonalityCurve
from src.clients.trends.client import TrendsClient


class TrendsServiceDataProvider:
    """Partial ServiceDataProvider for seasonality from Google Trends."""

    def __init__(self, client: TrendsClient):
        self._client = client
        self._cache: dict[str, SeasonalityCurve] = {}

    def get_acv_estimate(self, naics: str, city_id: str) -> float | None:
        return None  # ACV comes from BLS

    def get_seasonality(self, service_name: str) -> SeasonalityCurve | None:
        return self._cache.get(service_name)

    def get_establishment_growth(self, naics: str, city_id: str) -> float | None:
        return None  # Growth comes from CBP

    async def load_seasonality(self, service_name: str) -> SeasonalityCurve | None:
        """Fetch and cache seasonality for a service."""
        monthly = await self._client.fetch_interest_over_time(service_name)
        if not monthly:
            return None

        peak_month = max(monthly, key=monthly.get)
        trough_month = min(monthly, key=monthly.get)
        amplitude = monthly[peak_month] - monthly[trough_month]

        # Normalize to 0-1 range
        max_val = max(monthly.values())
        normalized = {m: v / max_val if max_val > 0 else 0 for m, v in monthly.items()}

        curve = SeasonalityCurve(
            monthly_index=normalized,
            peak_month=peak_month,
            trough_month=trough_month,
            amplitude=amplitude / max_val if max_val > 0 else 0,
        )
        self._cache[service_name] = curve
        return curve
```

---

## Composing Providers

After all sub-phases, the providers are composed at startup:

```python
# In app startup — composing multiple partial providers into the full interface
from src.clients.census.adapter import CensusCityDataProvider
from src.clients.census.cbp_client import CBPClient
from src.clients.bls.adapter import BLSServiceDataProvider
from src.clients.trends.adapter import TrendsServiceDataProvider


class CompositeCityDataProvider:
    """Combines Census ACS (demographics) + CBP (business density)."""

    def __init__(self, acs: CensusCityDataProvider, cbp: CBPCityDataProvider):
        self._acs = acs
        self._cbp = cbp

    def get_demographics(self, city_id):
        return self._acs.get_demographics(city_id)

    def get_business_density(self, city_id, naics=None):
        return self._cbp.get_business_density(city_id, naics)

    def find_similar_cities(self, reference, limit=10):
        return self._acs.find_similar_cities(reference, limit)


class CompositeServiceDataProvider:
    """Combines BLS (ACV) + Trends (seasonality) + CBP (growth)."""

    def __init__(self, bls: BLSServiceDataProvider, trends: TrendsServiceDataProvider, cbp=None):
        self._bls = bls
        self._trends = trends
        self._cbp = cbp

    def get_acv_estimate(self, naics, city_id):
        return self._bls.get_acv_estimate(naics, city_id)

    def get_seasonality(self, service_name):
        return self._trends.get_seasonality(service_name)

    def get_establishment_growth(self, naics, city_id):
        return self._cbp.get_establishment_growth(naics, city_id) if self._cbp else None


# Wire into DiscoveryService
discovery_service = DiscoveryService(
    market_service=market_service,
    city_provider=CompositeCityDataProvider(acs_provider, cbp_provider),
    service_provider=CompositeServiceDataProvider(bls_provider, trends_provider),
    market_store=market_store,
)
```

---

## Validation (entire Phase 7)

```bash
# Run all provider tests
python -m pytest tests/clients/census/ -v
python -m pytest tests/clients/bls/ -v
python -m pytest tests/clients/trends/ -v

# Verify architecture
python scripts/check_domain_imports.py

# Verify lenses that were previously non-functional now work
python -c "
from src.domain.lenses import BLUE_OCEAN, SEASONAL_ARBITRAGE, EXPAND_CONQUER, CASH_COW
print('Blue Ocean requires:', BLUE_OCEAN.required_signals)
print('Seasonal Arbitrage requires:', SEASONAL_ARBITRAGE.required_signals)
print('Expand & Conquer requires:', EXPAND_CONQUER.required_signals)
print('Cash Cow filters:', [(f.signal, f.operator, f.value) for f in CASH_COW.filters])
"

# Integration test: run a discovery query with real data
python -c "
import asyncio
from src.domain.queries import MarketQuery, CityFilter
from src.domain.lenses import BLUE_OCEAN

query = MarketQuery(
    city_filters=[CityFilter('population', '>', 200_000)],
    lens=BLUE_OCEAN,
    limit=10,
)
# results = asyncio.run(discovery_service.discover(query))
# print(f'Found {len(results)} Blue Ocean opportunities')
"
```

**Done criteria per sub-phase:**
- 7A: City entities have demographics; find_similar_cities works; Expand & Conquer lens functional
- 7B: City entities have business_density; establishment_growth signal available; Blue Ocean lens functional
- 7C: Service entities have acv_estimate; Cash Cow lens fully functional with ACV filter
- 7D: Service entities have seasonality; Seasonal Arbitrage lens functional with timing signal

**Done criteria for all of Phase 7:**
- All 9 lenses are functional (4 from Phase 4 + 4 new + Portfolio Builder)
- CompositeCity/ServiceDataProvider compose sub-providers cleanly
- Reference tables created in Supabase
- Architecture lint still passes
- All tests pass
