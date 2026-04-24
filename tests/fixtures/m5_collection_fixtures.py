"""Shared fixtures and fake client for M5 unit tests."""

from __future__ import annotations

from typing import Any

from src.clients.dataforseo.types import APIResponse


SAMPLE_KEYWORDS = [
    {"keyword": "plumber phoenix", "tier": 1, "intent": "transactional"},
    {"keyword": "emergency plumber phoenix", "tier": 2, "intent": "commercial"},
    {"keyword": "how to fix a leaking faucet", "tier": 3, "intent": "informational"},
]

SAMPLE_METROS = [
    {"metro_id": "38060", "location_code": 1012873, "principal_city": "Phoenix"},
    {"metro_id": "49740", "location_code": 1023191, "principal_city": "Wilmington"},
]


class FakeDataForSEOClient:
    """Simple async fake client for deterministic tests."""

    def __init__(self, fail_task_type: str | None = None) -> None:
        self.fail_task_type = fail_task_type
        self.calls: list[tuple[str, Any]] = []

    async def keyword_volume(self, keywords: list[str], location_code: int) -> APIResponse:
        self.calls.append(("keyword_volume", {"keywords": keywords, "location_code": location_code}))
        if self.fail_task_type == "keyword_volume":
            return APIResponse(status="error", error="keyword_volume failed")
        return APIResponse(status="ok", data=[{"keyword": keywords[0], "search_volume": 500}], cost=0.05)

    async def serp_organic(self, keyword: str, location_code: int) -> APIResponse:
        self.calls.append(("serp_organic", {"keyword": keyword, "location_code": location_code}))
        if self.fail_task_type == "serp_organic":
            return APIResponse(status="error", error="serp_organic failed")
        return APIResponse(
            status="ok",
            data=[
                {
                    "keyword": keyword,
                    "items": [
                        {"domain": "example.com", "url": "https://example.com"},
                        {"domain": "foo.com", "url": "https://foo.com"},
                    ],
                }
            ],
            cost=0.0006,
        )

    async def serp_maps(self, keyword: str, location_code: int) -> APIResponse:
        self.calls.append(("serp_maps", {"keyword": keyword, "location_code": location_code}))
        if self.fail_task_type == "serp_maps":
            return APIResponse(status="error", error="serp_maps failed")
        return APIResponse(
            status="ok",
            data=[{
                "keyword": keyword,
                "items": [
                    {
                        "type": "maps_search",
                        "title": "Local Biz",
                        "rating": {"value": 4.3, "votes_count": 42},
                    },
                ],
            }],
            cost=0.0006,
        )

    async def business_listings(self, category: str, location_code: int) -> APIResponse:
        self.calls.append(("business_listings", {"category": category, "location_code": location_code}))
        if self.fail_task_type == "business_listings":
            return APIResponse(status="error", error="business_listings failed")
        return APIResponse(
            status="ok",
            data=[{
                "total_count": 1,
                "items": [
                    {
                        "type": "business_listing",
                        "title": "Business",
                        "phone": "+15551234",
                        "address": "123 Main St",
                        "domain": "biz.com",
                        "rating": {"value": 4.0, "votes_count": 20},
                    },
                ],
            }],
            cost=0.01,
        )

    async def google_reviews(self, keyword: str, location_code: int) -> APIResponse:
        self.calls.append(("google_reviews", {"keyword": keyword, "location_code": location_code}))
        if self.fail_task_type == "google_reviews":
            return APIResponse(status="error", error="google_reviews failed")
        return APIResponse(
            status="ok",
            data=[{
                "rating": {"value": 4.4, "votes_count": 31},
                "reviews_count": 31,
                "items": [
                    {"timestamp": "2026-01-15 10:00:00 +00:00", "rating": {"value": 5}},
                    {"timestamp": "2026-02-15 10:00:00 +00:00", "rating": {"value": 4}},
                ],
            }],
            cost=0.005,
        )

    async def google_my_business_info(self, keyword: str, location_code: int) -> APIResponse:
        self.calls.append(("gbp_info", {"keyword": keyword, "location_code": location_code}))
        if self.fail_task_type == "gbp_info":
            return APIResponse(status="error", error="gbp_info failed")
        return APIResponse(
            status="ok",
            data=[{
                "items": [
                    {
                        "type": "google_business_info",
                        "phone": "+15551234",
                        "url": "https://biz.com",
                        "description": "A business",
                        "work_time": {"work_hours": {"timetable": {"monday": []}}},
                        "total_photos": 8,
                        "category": "Service",
                        "attributes": {"available_attributes": []},
                    },
                ],
            }],
            cost=0.004,
        )

    async def backlinks_summary(self, target: str) -> APIResponse:
        self.calls.append(("backlinks", {"target": target}))
        if self.fail_task_type == "backlinks":
            return APIResponse(status="error", error="backlinks failed")
        return APIResponse(status="ok", data=[{"referring_domains": 12}], cost=0.002)

    async def lighthouse(self, url: str) -> APIResponse:
        self.calls.append(("lighthouse", {"url": url}))
        if self.fail_task_type == "lighthouse":
            return APIResponse(status="error", error="lighthouse failed")
        return APIResponse(status="ok", data=[{"performance": 52}], cost=0.002)

