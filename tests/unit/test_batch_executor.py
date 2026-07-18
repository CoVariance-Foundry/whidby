"""Unit tests for M5 execution ordering, dedup, and failure isolation."""

from __future__ import annotations

import asyncio

import pytest

from src.clients.dataforseo.types import APIResponse
from src.pipeline.batch_executor import execute_collection_plan
from src.pipeline.collection_plan import CollectionPlan, build_collection_plan
from src.pipeline.types import CollectionTask, build_collection_request
from tests.fixtures.m5_collection_fixtures import (
    FakeDataForSEOClient,
    SAMPLE_KEYWORDS,
    SAMPLE_METROS,
)


class OrganicResultsClient(FakeDataForSEOClient):
    """Fake client with configurable organic result payloads."""

    def __init__(self, items: list[dict[str, str]]) -> None:
        super().__init__()
        self.items = items

    async def serp_organic(self, keyword: str, location_code: int) -> APIResponse:
        self.calls.append(("serp_organic", {"keyword": keyword, "location_code": location_code}))
        return APIResponse(
            status="ok",
            data=[{"keyword": keyword, "items": self.items}],
            cost=0.0006,
        )


class MapsIdentifierClient(FakeDataForSEOClient):
    async def serp_maps(self, keyword: str, location_code: int) -> APIResponse:
        self.calls.append(("serp_maps", {"keyword": keyword, "location_code": location_code}))
        return APIResponse(
            status="ok",
            data=[
                {
                    "keyword": keyword,
                    "items": [
                        {
                            "type": "maps_search",
                            "rank_group": 1,
                            "title": "CID Biz",
                            "cid": "cid-1",
                            "place_id": "place-1",
                        },
                        {
                            "type": "maps_search",
                            "rank_group": 2,
                            "title": "Place Biz",
                            "place_id": "place-2",
                        },
                        {
                            "type": "maps_search",
                            "rank_group": 3,
                            "title": "Title Biz",
                        },
                    ],
                }
            ],
            cost=0.0006,
        )


class EmptyMapsProfileClient(FakeDataForSEOClient):
    async def serp_maps(self, keyword: str, location_code: int) -> APIResponse:
        self.calls.append(("serp_maps", {"keyword": keyword, "location_code": location_code}))
        return APIResponse(
            status="ok",
            data=[
                {
                    "items": [
                        {
                            "type": "maps_search",
                            "rank_group": 1,
                        },
                    ],
                }
            ],
            cost=0.0006,
        )


@pytest.mark.asyncio
async def test_executor_runs_base_and_dependent_categories() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    client = FakeDataForSEOClient()

    state = await execute_collection_plan(plan, request, client)

    categories = set(state.task_categories.values())
    assert "keyword_volume" in categories
    assert "serp_organic" in categories
    assert "serp_maps" in categories
    assert "backlinks" in categories
    assert "lighthouse" in categories
    assert state.total_api_calls > 0


@pytest.mark.asyncio
async def test_executor_prefers_maps_identifiers_for_reviews_and_preserves_gbp_provenance() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    client = MapsIdentifierClient()

    state = await execute_collection_plan(plan, request, client)

    review_payloads = [payload for name, payload in client.calls if name == "google_reviews"]
    assert review_payloads == [
        {
            "keyword": "cid-1",
            "location_code": 1012873,
            "cid": "cid-1",
            "place_id": None,
        }
    ]
    gbp_payloads = [
        state.task_payloads[task_id]
        for task_id, category in sorted(state.task_categories.items())
        if category == "gbp_info"
    ]
    assert [payload["keyword"] for payload in gbp_payloads] == ["CID Biz"]
    assert [payload["preferred_identifier_mode"] for payload in gbp_payloads] == ["cid"]
    assert [payload["gbp_retrieval_mode"] for payload in gbp_payloads] == ["keyword"]


@pytest.mark.asyncio
async def test_executor_skips_reviews_when_maps_profile_has_no_query_or_identifier() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    client = EmptyMapsProfileClient()

    state = await execute_collection_plan(plan, request, client)

    assert [call for call in client.calls if call[0] == "google_reviews"] == []
    assert "google_reviews" not in state.task_categories.values()


@pytest.mark.asyncio
async def test_executor_materializes_top5_backlinks_domains_with_dedupe_cap() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    client = OrganicResultsClient(
        [
            {"domain": "first.com", "url": "https://first.com"},
            {"domain": "second.com", "url": "https://second.com"},
            {"domain": "first.com", "url": "https://first.com/duplicate"},
            {"domain": "www.second.com:443", "url": "https://www.second.com/variant"},
            {"domain": "", "url": "https://missing-domain.com"},
            {"domain": "third.com", "url": "https://third.com"},
            {"domain": "fourth.com", "url": "https://fourth.com"},
            {"domain": "fifth.com", "url": "https://fifth.com"},
            {"domain": "sixth.com", "url": "https://sixth.com"},
        ]
    )

    await execute_collection_plan(plan, request, client)

    targets = [payload["target"] for name, payload in client.calls if name == "backlinks"]
    assert targets == ["first.com", "second.com", "third.com", "fourth.com", "fifth.com"]


@pytest.mark.asyncio
async def test_executor_excludes_aggregator_domains_from_paid_backlinks() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    client = OrganicResultsClient(
        [
            {"domain": "first.com", "url": "https://first.com"},
            {"domain": "yelp.com", "url": "https://www.yelp.com/biz/example"},
            {"domain": "second.com", "url": "https://second.com"},
            {"domain": "angi.com", "url": "https://www.angi.com/companylist/example"},
            {"domain": "third.com", "url": "https://third.com"},
            {"domain": "fourth.com", "url": "https://fourth.com"},
            {"domain": "fifth.com", "url": "https://fifth.com"},
            {"domain": "sixth.com", "url": "https://sixth.com"},
        ]
    )

    await execute_collection_plan(plan, request, client)

    targets = [payload["target"] for name, payload in client.calls if name == "backlinks"]
    assert targets == ["first.com", "second.com", "third.com", "fourth.com", "fifth.com"]


@pytest.mark.asyncio
async def test_executor_materializes_top5_lighthouse_urls_with_dedupe_cap() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    client = OrganicResultsClient(
        [
            {"domain": "first.com", "url": "https://first.com"},
            {"domain": "second.com", "url": "https://second.com"},
            {"domain": "third.com", "url": "https://first.com"},
            {"domain": "fourth.com", "url": ""},
            {"domain": "fifth.com", "url": "https://third.com"},
            {"domain": "sixth.com", "url": "https://fourth.com"},
            {"domain": "seventh.com", "url": "https://fifth.com"},
            {"domain": "eighth.com", "url": "https://sixth.com"},
        ]
    )

    await execute_collection_plan(plan, request, client)

    urls = [payload["url"] for name, payload in client.calls if name == "lighthouse"]
    assert urls == [
        "https://first.com",
        "https://second.com",
        "https://third.com",
        "https://fourth.com",
        "https://fifth.com",
    ]


@pytest.mark.asyncio
async def test_executor_canonicalizes_lighthouse_urls_for_dedupe_only() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    client = OrganicResultsClient(
        [
            {"domain": "example.com", "url": "https://Example.com"},
            {"domain": "www.example.com", "url": "https://www.example.com"},
            {"domain": "example.com", "url": "https://example.com/"},
            {"domain": "example.com", "url": "https://example.com/#reviews"},
            {"domain": "example.com", "url": "https://example.com/?service=roofing#reviews"},
            {"domain": "example.com", "url": "https://example.com/?service=plumbing"},
            {"domain": "second.com", "url": "HTTPS://Second.com/services/"},
            {"domain": "second.com", "url": "https://second.com/services#map"},
            {"domain": "third.com", "url": "https://third.com"},
        ]
    )

    await execute_collection_plan(plan, request, client)

    urls = [payload["url"] for name, payload in client.calls if name == "lighthouse"]
    assert urls == [
        "https://Example.com",
        "https://example.com/?service=roofing#reviews",
        "https://example.com/?service=plumbing",
        "HTTPS://Second.com/services/",
        "https://third.com",
    ]


@pytest.mark.asyncio
async def test_executor_excludes_aggregator_urls_from_paid_lighthouse() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    client = OrganicResultsClient(
        [
            {"domain": "first.com", "url": "https://first.com"},
            {"domain": "yelp.com", "url": "https://www.yelp.com/biz/example"},
            {"domain": "second.com", "url": "https://second.com"},
            {"domain": "angi.com", "url": "https://www.angi.com/companylist/example"},
            {"domain": "third.com", "url": "https://third.com"},
            {"domain": "fourth.com", "url": "https://fourth.com"},
            {"domain": "fifth.com", "url": "https://fifth.com"},
            {"domain": "sixth.com", "url": "https://sixth.com"},
        ]
    )

    await execute_collection_plan(plan, request, client)

    urls = [payload["url"] for name, payload in client.calls if name == "lighthouse"]
    assert urls == [
        "https://first.com",
        "https://second.com",
        "https://third.com",
        "https://fourth.com",
        "https://fifth.com",
    ]


@pytest.mark.asyncio
async def test_executor_skips_empty_organic_dependents() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    client = OrganicResultsClient(
        [
            {"domain": "", "url": ""},
            {"domain": "   ", "url": "   "},
            {},
        ]
    )

    await execute_collection_plan(plan, request, client)

    assert [call for call in client.calls if call[0] == "backlinks"] == []
    assert [call for call in client.calls if call[0] == "lighthouse"] == []


@pytest.mark.asyncio
async def test_executor_applies_partial_failure_isolation() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, [SAMPLE_METROS[0]], "balanced")
    plan = build_collection_plan(request)
    client = FakeDataForSEOClient(fail_task_type="serp_organic")

    state = await execute_collection_plan(plan, request, client)

    assert any(error.task_type == "serp_organic" for error in state.failures)
    assert state.total_api_calls > 0


@pytest.mark.asyncio
async def test_executor_maintains_multi_metro_state_partition() -> None:
    request = build_collection_request(SAMPLE_KEYWORDS, SAMPLE_METROS, "balanced")
    plan = build_collection_plan(request)
    client = FakeDataForSEOClient()

    state = await execute_collection_plan(plan, request, client)

    assert {"38060", "49740"}.issubset(set(state.task_metros.values()))


@pytest.mark.asyncio
async def test_executor_caps_provider_concurrency_at_eight() -> None:
    release = asyncio.Event()
    at_limit = asyncio.Event()

    class ConcurrencyClient:
        active = 0
        peak = 0

        async def serp_organic(self, keyword: str, location_code: int) -> APIResponse:
            self.active += 1
            self.peak = max(self.peak, self.active)
            if self.active == 8:
                at_limit.set()
            await release.wait()
            self.active -= 1
            return APIResponse(status="ok", data=[{"keyword": keyword, "items": []}])

    request = build_collection_request(
        [{"keyword": "service", "tier": 1, "intent": "transactional"}],
        [SAMPLE_METROS[0]],
        "balanced",
    )
    plan = CollectionPlan(
        base_tasks=[
            CollectionTask(
                task_id=f"task-{index}",
                metro_id="38060",
                task_type="serp_organic",
                payload={"keyword": f"service-{index}", "location_code": 1012873},
            )
            for index in range(12)
        ],
        dependent_templates=[],
    )
    client = ConcurrencyClient()

    running = asyncio.create_task(execute_collection_plan(plan, request, client))
    await asyncio.wait_for(at_limit.wait(), timeout=0.1)
    await asyncio.sleep(0)
    assert client.peak == 8
    release.set()
    state = await running
    assert state.total_api_calls == 12


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("slow_task_type", "fast_task_type"),
    [("keyword_volume", "serp_organic"), ("serp_organic", "keyword_volume")],
)
async def test_executor_converts_task_timeout_to_failure_and_keeps_siblings(
    monkeypatch: pytest.MonkeyPatch,
    slow_task_type: str,
    fast_task_type: str,
) -> None:
    monkeypatch.setattr("src.pipeline.batch_executor.M5_LIVE_TASK_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr("src.pipeline.batch_executor.M5_QUEUED_TASK_TIMEOUT_SECONDS", 0.01)

    class TimeoutClient:
        async def keyword_volume(self, keywords: list[str], location_code: int) -> APIResponse:
            if slow_task_type == "keyword_volume":
                await asyncio.Event().wait()
            return APIResponse(status="ok", data=[{"keywords": keywords}])

        async def serp_organic(self, keyword: str, location_code: int) -> APIResponse:
            if slow_task_type == "serp_organic":
                await asyncio.Event().wait()
            return APIResponse(status="ok", data=[{"keyword": keyword, "items": []}])

    request = build_collection_request(
        [{"keyword": "service", "tier": 1, "intent": "transactional"}],
        [SAMPLE_METROS[0]],
        "balanced",
    )
    plan = CollectionPlan(
        base_tasks=[
            CollectionTask(
                task_id="queued",
                metro_id="38060",
                task_type="keyword_volume",
                payload={"keywords": ["service"], "location_code": 1012873},
            ),
            CollectionTask(
                task_id="live",
                metro_id="38060",
                task_type="serp_organic",
                payload={"keyword": "service", "location_code": 1012873},
            ),
        ],
        dependent_templates=[],
    )

    state = await asyncio.wait_for(
        execute_collection_plan(plan, request, TimeoutClient()),
        timeout=0.1,
    )

    assert any(failure.task_type == slow_task_type for failure in state.failures)
    assert fast_task_type in state.task_categories.values()
