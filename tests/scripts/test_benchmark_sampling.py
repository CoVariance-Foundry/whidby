from __future__ import annotations

import asyncio

import pytest

from scripts.benchmarks.run_pilot import (
    NicheExpansionCache,
    RunStats,
    build_pairs,
    collect_keyword_volume,
    select_metros,
)
from src.clients.dataforseo.types import APIResponse


def _metro(
    cbsa: str,
    population_class: str,
    codes: list[int] | None,
) -> dict:
    return {
        "cbsa_code": cbsa,
        "cbsa_name": f"Metro {cbsa}",
        "state": "TX",
        "population": 1_000_000,
        "population_class": population_class,
        "dataforseo_location_codes": codes or [],
    }


class _FakeDFS:
    def __init__(self, responses: dict[int, APIResponse]) -> None:
        self.responses = responses
        self.calls: list[int] = []

    async def keyword_volume(self, keywords: list[str], location_code: int) -> APIResponse:
        self.calls.append(location_code)
        return self.responses[location_code]


def test_default_paid_sample_excludes_low_signal_empty_and_borrowed_metros() -> None:
    metros = [
        _metro("mega", "mega_5m_plus", [1]),
        _metro("metro", "metro_1m_5m", [2]),
        _metro("large", "large_300k_1m", [3]),
        _metro("medium_valid", "medium_100_300k", [4]),
        _metro("medium_empty", "medium_100_300k", []),
        _metro("small", "small_50_100k", []),
        _metro("micro", "micro_under_50k", []),
    ]

    selected = select_metros(metros, sample_mode="full")

    assert [m["cbsa_code"] for m in selected] == [
        "mega",
        "metro",
        "large",
        "medium_valid",
    ]
    assert all(m["paid_eligible"] for m in selected)
    assert all(m["_dfs_source"] == "native" for m in selected)


def test_include_low_signal_allows_diagnostic_state_borrowed_metros() -> None:
    metros = [
        _metro("donor", "metro_1m_5m", [20]),
        _metro("small", "small_50_100k", []),
    ]

    selected = select_metros(metros, sample_mode="full", include_low_signal=True)

    small = next(m for m in selected if m["cbsa_code"] == "small")
    assert small["paid_eligible"] is True
    assert small["_dfs_source"] == "state_borrow"
    assert small["keyword_volume_location_codes"] == [20]


def test_population_class_filter_sees_only_valid_medium_metros_by_default() -> None:
    metros = [
        _metro("medium_valid", "medium_100_300k", [4]),
        _metro("medium_empty", "medium_100_300k", []),
        _metro("small", "small_50_100k", []),
    ]

    selected = [
        metro
        for metro in select_metros(metros, sample_mode="full")
        if metro.get("population_class") == "medium_100_300k"
    ]

    assert [m["cbsa_code"] for m in selected] == ["medium_valid"]


def test_build_pairs_interleaves_niches_for_limited_preflights() -> None:
    metros = [_metro("a", "mega_5m_plus", [1]), _metro("b", "mega_5m_plus", [2])]

    pairs = build_pairs(["plumber", "concrete contractor"], metros)

    assert [(niche, metro["cbsa_code"]) for niche, metro in pairs] == [
        ("plumber", "a"),
        ("concrete contractor", "a"),
        ("plumber", "b"),
        ("concrete contractor", "b"),
    ]


@pytest.mark.asyncio
async def test_collect_keyword_volume_records_empty_volume_failure() -> None:
    dfs = _FakeDFS({1: APIResponse(status="ok", data=[])})

    result = await collect_keyword_volume(dfs, ["plumber"], [1])

    assert result.volume_by_kw == {}
    assert result.valid_location_codes == []
    assert result.failures[0].reason == "keyword_volume_empty"


@pytest.mark.asyncio
async def test_collect_keyword_volume_records_invalid_location_failure() -> None:
    dfs = _FakeDFS({
        1: APIResponse(status="error", error="Invalid Field: 'location_code'.")
    })

    result = await collect_keyword_volume(dfs, ["plumber"], [1])

    assert result.volume_by_kw == {}
    assert result.failures[0].reason == "invalid_keyword_volume_code"


@pytest.mark.asyncio
async def test_collect_keyword_volume_records_queue_timeout_failure() -> None:
    dfs = _FakeDFS({1: APIResponse(status="error", error="Task In Queue.")})

    result = await collect_keyword_volume(dfs, ["plumber"], [1])

    assert result.volume_by_kw == {}
    assert result.failures[0].reason == "task_queue_timeout"


def test_run_stats_tracks_failure_histogram() -> None:
    stats = RunStats()

    stats.record_failure("plumber", "12345", "keyword_volume_empty", "no usable rows")
    stats.record_failure("plumber", "23456", "keyword_volume_empty", "no usable rows")
    stats.record_failure("plumber", "34567", "invalid_keyword_volume_code", "bad code")

    assert stats.failure_reasons == {
        "keyword_volume_empty": 2,
        "invalid_keyword_volume_code": 1,
    }
    assert "keyword_volume_empty" in stats.failures[0]


@pytest.mark.asyncio
async def test_expansion_cache_shares_inflight_work(monkeypatch) -> None:
    calls = 0

    async def fake_expand_keywords(**kwargs):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return {"expanded_keywords": []}

    monkeypatch.setattr(
        "scripts.benchmarks.run_pilot.expand_keywords",
        fake_expand_keywords,
    )
    cache = NicheExpansionCache(llm=object(), dfs=object())  # type: ignore[arg-type]

    results = await asyncio.gather(
        cache.get("plumber"),
        cache.get("plumber"),
        cache.get("plumber"),
    )

    assert calls == 1
    assert results == [{"expanded_keywords": []}] * 3
