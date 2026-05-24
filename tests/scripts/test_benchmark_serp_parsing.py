import pytest

from scripts.benchmarks.run_pilot import (
    collect_organic_telemetry,
    collect_top3_review_velocity,
    evidence_artifacts_from_dfs_cost_log,
    parse_backlinks_domain_authority,
    parse_lighthouse_performance_score,
    parse_serp_items,
    propagate_head_feature,
    upsert_evidence_artifacts,
)
from src.clients.dataforseo.types import APIResponse, CostRecord


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
        parse_backlinks_domain_authority([
            {"items": [{"rank": 1}]},
            {"domain_rank": 44},
        ])
        == 44
    )
    assert (
        parse_lighthouse_performance_score([
            {"categories": {"performance": {"score": 0.87}}},
        ])
        == 87
    )
    assert parse_lighthouse_performance_score([{"performance_score": 91}]) == 91


def test_propagate_head_feature_updates_all_keyword_rows():
    features_by_kw = {
        "roofing": {"top3_review_velocity_avg": None},
        "roof repair": {},
    }
    head_features = {}

    propagate_head_feature(
        features_by_kw,
        head_features,
        "top3_review_velocity_avg",
        1.25,
    )

    assert head_features["top3_review_velocity_avg"] == 1.25
    assert features_by_kw["roofing"]["top3_review_velocity_avg"] == 1.25
    assert features_by_kw["roof repair"]["top3_review_velocity_avg"] == 1.25


class _FakeDFS:
    def __init__(self) -> None:
        self.backlink_calls = []
        self.review_calls = []
        self.cost_log = []

    async def backlinks_summary(self, target, *, rank_scale=None):
        self.backlink_calls.append({"target": target, "rank_scale": rank_scale})
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
    assert dfs.backlink_calls == [
        {"target": "a.example", "rank_scale": "one_hundred"},
        {"target": "b.example", "rank_scale": "one_hundred"},
    ]


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


@pytest.mark.asyncio
async def test_collect_top3_review_velocity_skips_missing_review_identifiers():
    dfs = _FakeDFS()

    velocity = await collect_top3_review_velocity(
        dfs,
        [
            {},
            {"title": ""},
            {"cid": "cid-a"},
        ],
        location_code=1012873,
        depth=10,
    )

    assert velocity == 1.0
    assert dfs.review_calls == [
        {
            "keyword": None,
            "location_code": 1012873,
            "depth": 10,
            "cid": "cid-a",
            "place_id": None,
            "sort_by": "newest",
        }
    ]


def test_benchmark_pilot_builds_evidence_artifacts_from_dfs_cost_log():
    dfs = _FakeDFS()
    dfs.cost_log = [
        CostRecord(
            endpoint="serp/google/maps/live/advanced",
            task_id="maps-other",
            cost=0.002,
            cached=False,
            latency_ms=120,
            parameters={"keyword": "hvac repair", "location_code": 2000020},
            collected_at="2026-05-24T14:00:00+00:00",
            collection_context_id="pair-other",
            response_hash="other-maps-hash",
        ),
        CostRecord(
            endpoint="serp/google/maps/live/advanced",
            task_id="maps-1",
            cost=0.002,
            cached=False,
            latency_ms=120,
            parameters={"keyword": "roof repair", "location_code": 1000013},
            collected_at="2026-05-24T14:00:01+00:00",
            collection_context_id="pair-current",
            response_hash="maps-hash",
        ),
        CostRecord(
            endpoint="business_data/google/reviews/task_post",
            task_id="reviews-1",
            cost=0.005,
            cached=False,
            latency_ms=400,
            parameters={"cid": "123", "location_code": 1000013, "depth": 10},
            collected_at="2026-05-24T14:00:02+00:00",
            collection_context_id="pair-current",
            response_hash="reviews-hash",
        ),
        CostRecord(
            endpoint="backlinks/summary/live",
            task_id="backlinks-other",
            cost=0.002,
            cached=False,
            latency_ms=80,
            parameters={"target": "other.example", "rank_scale": "one_hundred"},
            collected_at="2026-05-24T14:00:03+00:00",
            collection_context_id="pair-other",
            response_hash="other-backlinks-hash",
        ),
        CostRecord(
            endpoint="backlinks/summary/live",
            task_id="backlinks-1",
            cost=0.002,
            cached=False,
            latency_ms=80,
            parameters={"target": "example.com", "rank_scale": "one_hundred"},
            collected_at="2026-05-24T14:00:04+00:00",
            collection_context_id="pair-current",
            response_hash="backlinks-hash",
        ),
        CostRecord(
            endpoint="on_page/lighthouse/live",
            task_id="lighthouse-1",
            cost=0.006,
            cached=True,
            latency_ms=0,
            parameters={"url": "https://example.com/"},
            collected_at="2026-05-24T14:00:05+00:00",
            collection_context_id="pair-current",
            response_hash="lighthouse-hash",
        ),
        CostRecord(
            endpoint="on_page/lighthouse/live",
            task_id="lighthouse-overlap",
            cost=0.006,
            cached=True,
            latency_ms=0,
            parameters={"url": "https://example.com/"},
            collected_at="2026-05-24T14:00:06+00:00",
            collection_context_id="pair-other",
            response_hash="lighthouse-other-hash",
        ),
    ]

    rows = evidence_artifacts_from_dfs_cost_log(
        dfs,
        collection_context_id="pair-current",
        niche="roof repair",
        location_codes=[1000013],
        keywords=["roof repair"],
        serp_keywords=["roof repair"],
        local_pack_items=[{"title": "A", "cid": "123"}],
        organic_targets=[
            {"domain": "example.com", "url": "https://example.com/"},
        ],
    )

    assert [row["evidence_family"] for row in rows] == [
        "maps",
        "reviews",
        "backlinks",
        "lighthouse",
    ]
    assert rows[0]["cache_status"] == "miss"
    assert rows[0]["request_hash"]
    assert rows[0]["response_hash"] == "maps-hash"
    assert rows[0]["collected_at"] == "2026-05-24T14:00:01+00:00"
    assert rows[1]["normalized_request_params"]["cid"] == "123"
    assert rows[2]["cost_usd"] == 0.002
    assert rows[3]["cache_status"] == "hit"
    assert {row["response_hash"] for row in rows}.isdisjoint(
        {"other-maps-hash", "other-backlinks-hash", "lighthouse-other-hash"}
    )


def test_benchmark_evidence_upsert_ignores_duplicate_artifacts(monkeypatch):
    captured = {}

    class _Response:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b""

    def fake_urlopen(req, timeout):  # noqa: ANN001
        captured["headers"] = dict(req.header_items())
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr("scripts.benchmarks.run_pilot.urlreq.urlopen", fake_urlopen)

    status, _body = upsert_evidence_artifacts(
        [
            {
                "provider": "dataforseo",
                "endpoint_path": "serp/google/maps/live/advanced",
                "request_hash": "hash",
                "evidence_family": "maps",
            }
        ]
    )

    assert status == 201
    assert captured["headers"]["Prefer"] == "resolution=ignore-duplicates,return=minimal"
