"""Fixtures for M6 signal extraction unit tests."""

from __future__ import annotations

from copy import deepcopy


SAMPLE_KEYWORD_EXPANSION = [
    {"keyword": "plumber near me", "tier": 1, "intent": "transactional", "local_fulfillment_required": 1},
    {"keyword": "emergency plumber", "tier": 2, "intent": "transactional"},
    {"keyword": "how to unclog drain", "tier": 3, "intent": "informational"},
]


SAMPLE_RAW_METRO_BUNDLE = {
    "serp_organic": [
        {
            "keyword": "plumber near me",
            "aio_present": True,
            "serp_features": ["ai_overview", "local_pack", "featured_snippet", "ads_top", "local_services_ads"],
            "paa_count": 2,
            "local_pack_position": 2,
            "organic_results": [
                {"url": "https://yelp.com/biz/x", "domain": "yelp.com", "title": "Best plumber near me"},
                {"url": "https://localplumbingco.com", "domain": "localplumbingco.com", "title": "Plumber Near Me"},
            ],
        },
        {
            "keyword": "how to unclog drain",
            "aio_present": False,
            "serp_features": ["people_also_ask"],
            "people_also_ask": ["q1", "q2", "q3"],
            "organic_results": [
                {
                    "url": "https://diyexample.com/drain-guide",
                    "domain": "diyexample.com",
                    "title": "How to unclog drain guide",
                }
            ],
        },
    ],
    "serp_maps": [
        {"business_id": "b1", "rating": 4.5, "review_count": 80},
        {"business_id": "b2", "rating": 4.1, "review_count": 35},
        {"business_id": "b3", "rating": 4.0, "review_count": 20},
    ],
    "keyword_volume": [
        {"keyword": "plumber near me", "search_volume": 5000, "cpc": 20.0},
        {"keyword": "emergency plumber", "search_volume": 3000, "cpc": 18.0},
        {"keyword": "how to unclog drain", "search_volume": 2000, "cpc": 4.0},
    ],
    "business_listings": [
        {"business_id": "b1", "nap_consistency": 0.8},
        {"business_id": "b2", "nap_consistency": 0.7},
        {"business_id": "b3", "nap_consistency": 0.9},
    ],
    "google_reviews": [
        {
            "business_id": "b1",
            "rating": 4.5,
            "review_count": 80,
            "review_timestamps": ["2026-01-01T00:00:00Z", "2026-02-01T00:00:00Z", "2026-03-01T00:00:00Z"],
        },
        {
            "business_id": "b2",
            "rating": 4.1,
            "review_count": 35,
            "review_timestamps": ["2026-01-15T00:00:00Z", "2026-02-15T00:00:00Z"],
        },
    ],
    "gbp_info": [
        {
            "business_id": "b1",
            "phone": "555-0100",
            "hours": True,
            "website": "https://localplumbingco.com",
            "photos": ["a", "b", "c"],
            "description": "Local experts",
            "services": ["drain cleaning"],
            "attributes": ["licensed"],
            "photo_count": 25,
            "has_recent_post": True,
        },
        {
            "business_id": "b2",
            "phone": "555-0101",
            "hours": True,
            "website": "",
            "photos": ["a"],
            "description": "Emergency plumbing",
            "services": ["24/7 service"],
            "attributes": [],
            "photo_count": 10,
            "has_recent_post": False,
        },
    ],
    "backlinks": [
        {"domain": "yelp.com", "domain_authority": 90},
        {"domain": "localplumbingco.com", "domain_authority": 25},
        {"domain": "diyexample.com", "domain_authority": 45},
        {"domain": "cityservices.com", "domain_authority": 35},
        {"domain": "directory.com", "domain_authority": 55},
    ],
    "lighthouse": [
        {"url": "https://localplumbingco.com", "performance_score": 62, "has_localbusiness_schema": True},
        {"url": "https://diyexample.com/drain-guide", "performance_score": 48, "schema_types": ["Article"]},
    ],
}


NO_LOCAL_PACK_RAW_METRO_BUNDLE = {
    **SAMPLE_RAW_METRO_BUNDLE,
    "serp_organic": [
        {
            "keyword": "plumber near me",
            "aio_present": False,
            "serp_features": [],
            "paa_count": 0,
            "organic_results": [{"url": "https://localplumbingco.com", "domain": "localplumbingco.com"}],
        }
    ],
    "serp_maps": [],
    "google_reviews": [],
    "gbp_info": [],
}


def build_sample_bundle() -> dict:
    return deepcopy(SAMPLE_RAW_METRO_BUNDLE)


def build_no_local_pack_bundle() -> dict:
    return deepcopy(NO_LOCAL_PACK_RAW_METRO_BUNDLE)


def build_keyword_expansion() -> list[dict]:
    return deepcopy(SAMPLE_KEYWORD_EXPANSION)
