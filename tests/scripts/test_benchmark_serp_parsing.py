import pytest

from scripts.benchmarks.run_pilot import (
    collect_organic_telemetry,
    collect_top3_review_velocity,
    parse_backlinks_domain_authority,
    parse_lighthouse_performance_score,
    parse_serp_items,
)
from src.clients.dataforseo.types import APIResponse


def test_parse_serp_items_extracts_top3_review_floor_and_rating():
    serp = [{
        "items": [{
            "type": "local_pack",
            "rank_absolute": 1,
            "items": [
                {"title": "A", "rating": {"value": 4.8, "votes_count": 120}},
                {"title": "B", "rating": {"value": 4.5, "votes_count": 80}},
                {"title": "C", "rating": {"value": 4.1, "votes_count": 40}},
            ],
        }]
    }]

    parsed = parse_serp_items(serp)

    assert parsed["local_pack_present"] is True
    assert parsed["top3_review_count_min"] == 40
    assert parsed["top3_review_count_avg"] == 80
    assert parsed["top3_rating_avg"] == 4.47


def test_parse_serp_items_extracts_non_aggregator_organic_targets():
    serp = [{
        "items": [
            {"type": "organic", "url": "https://www.yelp.com/biz/a", "title": "Yelp"},
            {
                "type": "organic",
                "url": "https://local-roof.example/services",
                "title": "Local Roof",
                "rank_absolute": 2,
            },
            {"type": "organic", "url": "", "title": "Missing URL"},
            {
                "type": "organic",
                "url": "https://www.plumber.example/",
                "title": "Plumber Example",
                "rank_absolute": 4,
            },
        ],
    }]

    parsed = parse_serp_items(serp)

    assert parsed["aggregator_count_top10"] == 1
    assert parsed["local_biz_count_top10"] == 2
    assert parsed["organic_targets"] == [
        {
            "url": "https://local-roof.example/services",
            "domain": "local-roof.example",
            "title": "Local Roof",
            "rank_absolute": 2,
        },
        {
            "url": "https://www.plumber.example/",
            "domain": "plumber.example",
            "title": "Plumber Example",
            "rank_absolute": 4,
        },
    ]


def test_parse_backlinks_and_lighthouse_values_from_dfs_shapes():
    assert parse_backlinks_domain_authority([{"rank": 42}]) == 42
    assert parse_backlinks_domain_authority([{"domain_from_rank": "33.5"}]) == 33.5
    assert (
        parse_lighthouse_performance_score([
            {"categories": {"performance": {"score": 0.87}}},
        ])
        == 87
    )
    assert parse_lighthouse_performance_score([{"performance_score": 91}]) == 91


class _FakeDFS:
    def __init__(self) -> None:
        self.review_calls = []

    async def backlinks_summary(self, target):
        return APIResponse(status="ok", data=[{"rank": 40 if target == "a.example" else 50}])

    async def lighthouse(self, url):
        score = 0.8 if "a.example" in url else 0.9
        return APIResponse(status="ok", data=[{"categories": {"performance": {"score": score}}}])

    async def google_reviews(
        self,
        keyword=None,
        location_code=None,
        depth=10,
        *,
        cid=None,
        place_id=None,
        sort_by=None,
    ):
        self.review_calls.append({
            "keyword": keyword,
            "location_code": location_code,
            "depth": depth,
            "cid": cid,
            "place_id": place_id,
            "sort_by": sort_by,
        })
        return APIResponse(
            status="ok",
            data=[
                {
                    "items": [
                        {
                            "review_id": "r1",
                            "timestamp": "2026-01-01 00:00:00 +00:00",
                        }
                    ]
                }
            ],
        )


@pytest.mark.asyncio
async def test_collect_organic_telemetry_aggregates_top5_fields():
    dfs = _FakeDFS()

    result = await collect_organic_telemetry(
        dfs,
        [
            {"domain": "a.example", "url": "https://a.example/"},
            {"domain": "b.example", "url": "https://b.example/"},
        ],
    )

    assert result.fields == {
        "avg_top5_da": 45.0,
        "avg_top5_lighthouse": 85.0,
        "top5_da_coverage": 0.4,
        "top5_lighthouse_coverage": 0.4,
        "top5_organic_data_confidence": "low",
    }
    assert result.failures == []


@pytest.mark.asyncio
async def test_collect_top3_review_velocity_uses_place_identifiers():
    dfs = _FakeDFS()

    velocity = await collect_top3_review_velocity(
        dfs,
        [
            {"title": "A", "cid": "cid-a"},
            {"title": "B", "place_id": "place-b"},
        ],
        location_code=1012873,
        depth=10,
    )

    assert velocity == 1.0
    assert dfs.review_calls == [
        {
            "keyword": "A",
            "location_code": 1012873,
            "depth": 10,
            "cid": "cid-a",
            "place_id": None,
            "sort_by": "newest",
        },
        {
            "keyword": "B",
            "location_code": 1012873,
            "depth": 10,
            "cid": None,
            "place_id": "place-b",
            "sort_by": "newest",
        },
    ]
