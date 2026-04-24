"""Unit tests for DataForSEO response normalizers."""
from __future__ import annotations

from src.pipeline.dfs_normalizers import (
    normalize_business_listings_rows,
    normalize_gbp_info_rows,
    normalize_google_reviews_rows,
    normalize_serp_maps_rows,
)


# --- serp_maps ---


def test_normalize_serp_maps_unpacks_items_and_flattens_rating() -> None:
    raw = [
        {
            "keyword": "plumber near me",
            "se_domain": "google.com",
            "items_count": 2,
            "items": [
                {
                    "type": "maps_search",
                    "title": "Joe's Plumbing",
                    "rating": {"value": 4.5, "votes_count": 80},
                    "place_id": "abc123",
                    "phone": "+16025551234",
                    "total_photos": 12,
                },
                {
                    "type": "maps_search",
                    "title": "Quick Fix Plumbing",
                    "rating": {"value": 4.1, "votes_count": 35},
                    "place_id": "def456",
                    "phone": None,
                    "total_photos": 5,
                },
            ],
        }
    ]
    result = normalize_serp_maps_rows(raw)

    assert len(result) == 2
    assert result[0]["rating"] == 4.5
    assert result[0]["review_count"] == 80
    assert result[0]["title"] == "Joe's Plumbing"
    assert result[1]["rating"] == 4.1
    assert result[1]["review_count"] == 35


def test_normalize_serp_maps_handles_already_flat_rows() -> None:
    flat = [
        {"business_id": "b1", "rating": 4.5, "review_count": 80},
    ]
    result = normalize_serp_maps_rows(flat)
    assert len(result) == 1
    assert result[0]["rating"] == 4.5
    assert result[0]["review_count"] == 80


def test_normalize_serp_maps_handles_empty_list() -> None:
    assert normalize_serp_maps_rows([]) == []


def test_normalize_serp_maps_handles_missing_rating_object() -> None:
    raw = [{"items": [{"type": "maps_search", "title": "No Rating Biz"}]}]
    result = normalize_serp_maps_rows(raw)
    assert len(result) == 1
    assert result[0]["rating"] == 0.0
    assert result[0]["review_count"] == 0


# --- google_reviews ---


def test_normalize_google_reviews_extracts_timestamps_and_aggregate_rating() -> None:
    raw = [
        {
            "keyword": "plumber phoenix",
            "type": "google_reviews",
            "rating": {"value": 4.5, "votes_count": 120},
            "reviews_count": 120,
            "items_count": 3,
            "items": [
                {
                    "type": "google_reviews_search",
                    "timestamp": "2026-01-15 10:30:00 +00:00",
                    "rating": {"value": 5, "votes_count": 0},
                    "review_text": "Great service!",
                },
                {
                    "type": "google_reviews_search",
                    "timestamp": "2026-02-20 14:00:00 +00:00",
                    "rating": {"value": 4, "votes_count": 0},
                    "review_text": "Good work.",
                },
                {
                    "type": "google_reviews_search",
                    "timestamp": "2026-03-10 09:15:00 +00:00",
                    "rating": {"value": 5, "votes_count": 0},
                    "review_text": "Highly recommend!",
                },
            ],
        }
    ]
    result = normalize_google_reviews_rows(raw)

    assert len(result) == 1
    assert result[0]["rating"] == 4.5
    assert result[0]["review_count"] == 120
    assert len(result[0]["review_timestamps"]) == 3
    assert result[0]["review_timestamps"][0] == "2026-01-15 10:30:00 +00:00"


def test_normalize_google_reviews_handles_already_flat_rows() -> None:
    flat = [{"rating": 4.5, "review_count": 80, "review_timestamps": ["2026-01-01T00:00:00Z"]}]
    result = normalize_google_reviews_rows(flat)
    assert len(result) == 1
    assert result[0]["review_count"] == 80


def test_normalize_google_reviews_handles_empty_items() -> None:
    raw = [{"rating": {"value": 4.0, "votes_count": 10}, "reviews_count": 10, "items": []}]
    result = normalize_google_reviews_rows(raw)
    assert result[0]["review_count"] == 10
    assert result[0]["review_timestamps"] == []


# --- gbp_info ---


def test_normalize_gbp_info_unpacks_items_and_maps_fields() -> None:
    raw = [
        {
            "keyword": "plumber phoenix",
            "items_count": 1,
            "items": [
                {
                    "type": "google_business_info",
                    "title": "Joe's Plumbing",
                    "phone": "+16025551234",
                    "url": "https://joesplumbing.com",
                    "description": "Licensed plumber serving Phoenix",
                    "work_time": {
                        "work_hours": {
                            "timetable": {
                                "monday": [{"open": {"hour": 8}, "close": {"hour": 17}}]
                            },
                        },
                        "current_status": "opened",
                    },
                    "total_photos": 25,
                    "category": "Plumber",
                    "additional_categories": ["Water Heater Repair"],
                    "attributes": {
                        "available_attributes": [
                            {"attribute": "Online appointments", "category": "service_options"},
                        ],
                    },
                },
            ],
        }
    ]
    result = normalize_gbp_info_rows(raw)

    assert len(result) == 1
    row = result[0]
    assert row["phone"] == "+16025551234"
    assert row["website"] == "https://joesplumbing.com"
    assert row["hours"] is True
    assert row["photo_count"] == 25
    assert isinstance(row["photos"], list) or row["photos"]
    assert row["description"] == "Licensed plumber serving Phoenix"
    assert len(row["services"]) >= 1
    assert len(row["attributes"]) >= 1
    assert row["has_recent_post"] is False


def test_normalize_gbp_info_handles_already_flat_rows() -> None:
    flat = [
        {
            "phone": "555-1234",
            "hours": True,
            "website": "https://x.com",
            "photos": ["a"],
            "description": "desc",
            "services": ["s1"],
            "attributes": ["a1"],
            "photo_count": 5,
            "has_recent_post": False,
        }
    ]
    result = normalize_gbp_info_rows(flat)
    assert result[0]["phone"] == "555-1234"


def test_normalize_gbp_info_handles_missing_fields_gracefully() -> None:
    raw = [{"items": [{"type": "google_business_info", "title": "Bare Listing"}]}]
    result = normalize_gbp_info_rows(raw)
    assert len(result) == 1
    assert result[0]["phone"] == ""
    assert result[0]["hours"] is False
    assert result[0]["photo_count"] == 0


# --- business_listings ---


def test_normalize_business_listings_unpacks_items_and_computes_nap() -> None:
    raw = [
        {
            "total_count": 2,
            "count": 2,
            "items": [
                {
                    "type": "business_listing",
                    "title": "Joe's Plumbing",
                    "phone": "+16025551234",
                    "address": "123 Main St, Phoenix, AZ 85001",
                    "domain": "joesplumbing.com",
                    "url": "https://joesplumbing.com",
                    "rating": {"value": 4.5, "votes_count": 89},
                },
                {
                    "type": "business_listing",
                    "title": "Quick Fix",
                    "phone": None,
                    "address": "456 Oak Ave",
                    "domain": "",
                    "url": None,
                    "rating": {"value": 3.8, "votes_count": 12},
                },
            ],
        }
    ]
    result = normalize_business_listings_rows(raw)

    assert len(result) == 2
    assert result[0]["nap_consistency"] == 1.0
    assert result[1]["nap_consistency"] < 1.0
    assert result[0]["rating"] == 4.5
    assert result[0]["review_count"] == 89


def test_normalize_business_listings_handles_already_flat_rows() -> None:
    flat = [{"business_id": "b1", "nap_consistency": 0.8}]
    result = normalize_business_listings_rows(flat)
    assert result[0]["nap_consistency"] == 0.8


def test_normalize_business_listings_handles_empty_items() -> None:
    raw = [{"total_count": 0, "items": []}]
    result = normalize_business_listings_rows(raw)
    assert result == []
