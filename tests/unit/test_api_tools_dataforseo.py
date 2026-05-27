"""Tests for DataForSEO api_tools wrapper parity with benchmark acquisition."""

from __future__ import annotations

import json
from typing import Any

import pytest

from src.clients.dataforseo.types import APIResponse
from src.research_agent.tools import api_tools


class _FakeDFSClient:
    def __init__(self) -> None:
        self.review_calls: list[dict[str, Any]] = []
        self.backlink_calls: list[dict[str, Any]] = []

    async def google_reviews(
        self,
        keyword: str | None = None,
        location_code: int | None = None,
        depth: int = 20,
        *,
        cid: str | int | None = None,
        place_id: str | None = None,
        sort_by: str | None = None,
    ) -> APIResponse:
        self.review_calls.append(
            {
                "keyword": keyword,
                "location_code": location_code,
                "depth": depth,
                "cid": cid,
                "place_id": place_id,
                "sort_by": sort_by,
            }
        )
        return APIResponse(
            status="ok",
            data=[{"rating": 5}],
            cost=0.005,
            cached=False,
            latency_ms=12,
            task_id="reviews-task-1",
        )

    async def backlinks_summary(
        self,
        target: str,
        *,
        rank_scale: str | None = None,
    ) -> APIResponse:
        self.backlink_calls.append({"target": target, "rank_scale": rank_scale})
        return APIResponse(
            status="ok",
            data=[{"rank": 77}],
            cost=0.002,
            cached=True,
            latency_ms=0,
        )


@pytest.fixture
def fake_dfs(monkeypatch: pytest.MonkeyPatch) -> _FakeDFSClient:
    client = _FakeDFSClient()
    monkeypatch.setattr(api_tools, "_get_dfs_client", lambda: client)
    return client


@pytest.mark.parametrize(
    ("kwargs", "expected_identifier"),
    [
        ({"cid": "cid-123"}, {"cid": "cid-123", "place_id": None}),
        ({"place_id": "place-123"}, {"cid": None, "place_id": "place-123"}),
    ],
)
def test_fetch_google_reviews_supports_place_identifiers_with_newest_sort(
    fake_dfs: _FakeDFSClient,
    kwargs: dict[str, str],
    expected_identifier: dict[str, str | None],
) -> None:
    raw = api_tools.fetch_google_reviews(
        location_code=1012873,
        depth=10,
        **kwargs,
    )

    assert fake_dfs.review_calls == [
        {
            "keyword": None,
            "location_code": 1012873,
            "depth": 10,
            "sort_by": "newest",
            **expected_identifier,
        }
    ]
    payload = json.loads(raw)
    assert payload["status"] == "ok"
    assert payload["cost"] == 0.005
    assert payload["cost_usd"] == 0.005
    assert payload["task_id"] == "reviews-task-1"
    assert payload["cached"] is False
    assert payload["source"] == {
        "provider": "dataforseo",
        "endpoint_path": "business_data/google/reviews/task_post",
        "mode": "queued",
        "cache_status": "miss",
        "request_params": {
            "location_code": 1012873,
            "depth": 10,
            "sort_by": "newest",
            **{key: value for key, value in expected_identifier.items() if value},
        },
    }


def test_fetch_google_reviews_preserves_keyword_call_path(
    fake_dfs: _FakeDFSClient,
) -> None:
    raw = api_tools.fetch_google_reviews(
        keyword="plumber",
        location_code=1012873,
        depth=10,
    )

    assert fake_dfs.review_calls == [
        {
            "keyword": "plumber",
            "location_code": 1012873,
            "depth": 10,
            "cid": None,
            "place_id": None,
            "sort_by": "newest",
        }
    ]
    payload = json.loads(raw)
    assert payload["source"]["request_params"] == {
        "keyword": "plumber",
        "location_code": 1012873,
        "depth": 10,
        "sort_by": "newest",
    }


def test_fetch_google_reviews_requires_identifier(fake_dfs: _FakeDFSClient) -> None:
    with pytest.raises(ValueError, match="keyword, cid, or place_id"):
        api_tools.fetch_google_reviews(location_code=1012873)

    assert fake_dfs.review_calls == []


def test_fetch_backlinks_summary_defaults_to_one_hundred_rank_scale(
    fake_dfs: _FakeDFSClient,
) -> None:
    raw = api_tools.fetch_backlinks_summary("example.com")

    assert fake_dfs.backlink_calls == [
        {"target": "example.com", "rank_scale": "one_hundred"}
    ]
    payload = json.loads(raw)
    assert payload["status"] == "ok"
    assert payload["cached"] is True
    assert payload["source"] == {
        "provider": "dataforseo",
        "endpoint_path": "backlinks/summary/live",
        "mode": "live",
        "cache_status": "hit",
        "request_params": {
            "target": "example.com",
            "rank_scale": "one_hundred",
        },
    }
