"""Test fixtures for canonical reference store and benchmark tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

SAMPLE_METROS = [
    {
        "cbsa_code": "38060",
        "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
        "state": "AZ",
        "region": "Southwest",
        "population": 4946145,
        "population_year": 2023,
        "population_growth_pct": 1.52,
        "principal_cities": ["Phoenix", "Mesa", "Chandler", "Scottsdale"],
        "dataforseo_location_codes": {"Phoenix": 1012873},
        "metro_size_tier": "major",
    },
    {
        "cbsa_code": "46060",
        "cbsa_name": "Tucson, AZ",
        "state": "AZ",
        "region": "Southwest",
        "population": 1043433,
        "population_year": 2023,
        "population_growth_pct": 0.83,
        "principal_cities": ["Tucson"],
        "dataforseo_location_codes": {"Tucson": 1012868},
        "metro_size_tier": "mid",
    },
    {
        "cbsa_code": "22380",
        "cbsa_name": "Flagstaff, AZ",
        "state": "AZ",
        "region": "Southwest",
        "population": 145101,
        "population_year": 2023,
        "population_growth_pct": 0.41,
        "principal_cities": ["Flagstaff"],
        "dataforseo_location_codes": {"Flagstaff": 1012833},
        "metro_size_tier": "small",
    },
]

SAMPLE_NICHES = [
    {
        "niche_keyword": "plumber",
        "dataforseo_category": "Plumbing",
        "parent_vertical": "home_services",
        "requires_physical_fulfillment": True,
        "typical_aio_exposure": "low",
        "modifier_patterns": ["emergency", "24 hour", "near me", "affordable"],
    },
    {
        "niche_keyword": "personal injury lawyer",
        "dataforseo_category": "Personal Injury Attorney",
        "parent_vertical": "legal",
        "requires_physical_fulfillment": True,
        "typical_aio_exposure": "moderate",
        "modifier_patterns": ["best", "free consultation", "near me"],
    },
    {
        "niche_keyword": "dentist",
        "dataforseo_category": "Dentist",
        "parent_vertical": "medical",
        "requires_physical_fulfillment": True,
        "typical_aio_exposure": "moderate",
        "modifier_patterns": ["emergency", "affordable", "pediatric", "cosmetic"],
    },
]

VERTICALS = [
    "home_services",
    "automotive",
    "legal",
    "medical",
    "specialty_services",
]


def fresh_computed_benchmark(
    niche: str = "plumber",
    metric: str = "median_cpc",
    tier: str | None = None,
    value: float = 5.25,
    sample_size: int = 42,
) -> dict:
    """Build a fresh computed benchmark row."""
    now = datetime.now(timezone.utc)
    return {
        "id": "b00c0001-0000-0000-0000-000000000001",
        "niche_keyword": niche,
        "metro_size_tier": tier,
        "metric_name": metric,
        "metric_value": value,
        "sample_size": sample_size,
        "computed_at": now.isoformat(),
        "valid_until": (now + timedelta(days=7)).isoformat(),
        "source": "computed",
    }


def stale_computed_benchmark(
    niche: str = "plumber",
    metric: str = "median_cpc",
    tier: str | None = None,
    value: float = 4.80,
) -> dict:
    """Build a computed benchmark whose valid_until has passed."""
    now = datetime.now(timezone.utc)
    return {
        "id": "b00c0002-0000-0000-0000-000000000002",
        "niche_keyword": niche,
        "metro_size_tier": tier,
        "metric_name": metric,
        "metric_value": value,
        "sample_size": 30,
        "computed_at": (now - timedelta(days=14)).isoformat(),
        "valid_until": (now - timedelta(days=7)).isoformat(),
        "source": "computed",
    }


def fresh_external_benchmark(
    niche: str = "plumber",
    metric: str = "median_cpc",
    tier: str | None = None,
    value: float = 5.00,
) -> dict:
    """Build a fresh externally-seeded benchmark row."""
    now = datetime.now(timezone.utc)
    return {
        "id": "b00c0003-0000-0000-0000-000000000003",
        "niche_keyword": niche,
        "metro_size_tier": tier,
        "metric_name": metric,
        "metric_value": value,
        "sample_size": 1,
        "computed_at": (now - timedelta(days=30)).isoformat(),
        "valid_until": (now + timedelta(days=60)).isoformat(),
        "source": "external",
    }


BENCHMARK_METRICS = [
    "median_cpc",
    "median_search_volume",
    "avg_da_top5",
    "avg_review_count",
    "avg_review_velocity",
    "avg_business_density",
    "aio_trigger_rate",
    "median_aggregator_count",
    "avg_gbp_photo_count",
    "avg_lighthouse_score",
]
