"""Test fixtures for observation store and query hash tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

SAMPLE_ENDPOINT = "serp/google/organic/task_post"
SAMPLE_PARAMS = {"keyword": "plumber", "location_code": 1012873, "depth": 10}
SAMPLE_PARAMS_REORDERED = {"location_code": 1012873, "keyword": "plumber", "depth": 10}
SAMPLE_PARAMS_WITH_EXCLUDED = {
    "keyword": "plumber",
    "location_code": 1012873,
    "depth": 10,
    "tag": "run-123",
    "postback_url": "https://example.com/callback",
}
SAMPLE_PARAMS_WITH_NONE = {
    "keyword": "plumber",
    "location_code": 1012873,
    "depth": 10,
    "language_code": None,
}

SAMPLE_QUERY_HASH = (
    "placeholder"  # computed dynamically in tests via compute_query_hash
)

SAMPLE_API_RESPONSE_DATA = {
    "tasks": [
        {
            "id": "04051234-5678-abcd-ef01-234567890abc",
            "status_code": 20000,
            "status_message": "Ok.",
            "result": [
                {
                    "keyword": "plumber",
                    "type": "organic",
                    "items": [
                        {"rank_group": 1, "domain": "example-plumber.com", "title": "Best Plumber"},
                        {"rank_group": 2, "domain": "plumber-reviews.com", "title": "Top Plumbers"},
                    ],
                }
            ],
        }
    ]
}


def fresh_observation_row(
    query_hash: str = "abc123",
    ttl_category: str = "serp",
    minutes_old: int = 30,
) -> dict:
    """Build a sample observation index row that is still within TTL."""
    now = datetime.now(timezone.utc)
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "endpoint": SAMPLE_ENDPOINT,
        "query_params": SAMPLE_PARAMS,
        "query_hash": query_hash,
        "observed_at": (now - timedelta(minutes=minutes_old)).isoformat(),
        "source": "pipeline",
        "run_id": None,
        "cost_usd": 0.0006,
        "api_queue_mode": "standard",
        "storage_path": f"observations/serp_organic/2026/04/05/{query_hash}_550e8400.json.gz",
        "payload_size_bytes": 1024,
        "ttl_category": ttl_category,
        "expires_at": (now + timedelta(hours=23, minutes=30)).isoformat(),
        "status": "ok",
        "error_message": None,
        "payload_purged": False,
    }


def expired_observation_row(query_hash: str = "abc123") -> dict:
    """Build a sample observation index row that has expired."""
    now = datetime.now(timezone.utc)
    return {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "endpoint": SAMPLE_ENDPOINT,
        "query_params": SAMPLE_PARAMS,
        "query_hash": query_hash,
        "observed_at": (now - timedelta(hours=25)).isoformat(),
        "source": "pipeline",
        "run_id": None,
        "cost_usd": 0.0006,
        "api_queue_mode": "standard",
        "storage_path": f"observations/serp_organic/2026/04/04/{query_hash}_550e8400.json.gz",
        "payload_size_bytes": 1024,
        "ttl_category": "serp",
        "expires_at": (now - timedelta(hours=1)).isoformat(),
        "status": "ok",
        "error_message": None,
        "payload_purged": False,
    }


def error_observation_row(query_hash: str = "abc123") -> dict:
    """Build a sample observation with status='error'."""
    now = datetime.now(timezone.utc)
    return {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "endpoint": SAMPLE_ENDPOINT,
        "query_params": SAMPLE_PARAMS,
        "query_hash": query_hash,
        "observed_at": (now - timedelta(minutes=10)).isoformat(),
        "source": "pipeline",
        "run_id": None,
        "cost_usd": 0.0006,
        "api_queue_mode": "standard",
        "storage_path": None,
        "payload_size_bytes": None,
        "ttl_category": "serp",
        "expires_at": (now + timedelta(hours=23, minutes=50)).isoformat(),
        "status": "error",
        "error_message": "DataForSEO returned 500",
        "payload_purged": False,
    }


def partial_observation_row(query_hash: str = "abc123") -> dict:
    """Build a sample observation with status='partial' (Storage upload failed)."""
    now = datetime.now(timezone.utc)
    return {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "endpoint": SAMPLE_ENDPOINT,
        "query_params": SAMPLE_PARAMS,
        "query_hash": query_hash,
        "observed_at": (now - timedelta(minutes=5)).isoformat(),
        "source": "pipeline",
        "run_id": None,
        "cost_usd": 0.0006,
        "api_queue_mode": "standard",
        "storage_path": None,
        "payload_size_bytes": None,
        "ttl_category": "serp",
        "expires_at": (now + timedelta(hours=23, minutes=55)).isoformat(),
        "status": "partial",
        "error_message": "Storage upload failed",
        "payload_purged": False,
    }


TTL_CATEGORY_MAPPING = {
    "serp/google/organic/task_post": "serp",
    "serp/google/maps/task_post": "serp",
    "keywords_data/google/search_volume/task_post": "keyword",
    "dataforseo_labs/google/keyword_suggestions/live": "keyword",
    "business_data/business_listings/search/live": "business",
    "business_data/google/my_business_info/live": "business",
    "business_data/google/reviews/task_post": "review",
    "backlinks/summary/live": "technical",
    "on_page/lighthouse/task_post": "technical",
    "serp/google/locations": "reference",
}
