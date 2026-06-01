from __future__ import annotations

import asyncio
from argparse import ArgumentTypeError, Namespace
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.benchmarks import run_pilot
from scripts.benchmarks.run_pilot import (
    NicheExpansionCache,
    RunStats,
    build_pairs,
    collect_keyword_volume,
    persistence_niche_key,
    select_metros,
    select_niches,
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


class _FakeHTTPResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_exc_info):
        return False

    def read(self) -> bytes:
        return self._body


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


def test_paid_budget_estimate_includes_acquisition_add_ons() -> None:
    args = Namespace(
        collect_organic_telemetry=True,
        collect_review_velocity=True,
        collect_gbp_profile=True,
        organic_telemetry_limit=2,
    )
    pairs = [
        ("tree service", {"cbsa_code": "36540"}),
        ("tree service", {"cbsa_code": "28940"}),
    ]

    estimate = run_pilot.estimate_dfs_paid_cost_usd(pairs, args)

    assert estimate > 0
    assert estimate == pytest.approx(0.252)


def test_paid_budget_estimate_counts_multi_code_keyword_volume_calls() -> None:
    args = Namespace(
        collect_organic_telemetry=False,
        collect_review_velocity=False,
        collect_gbp_profile=False,
        organic_telemetry_limit=2,
    )
    pairs = [("tree service", _metro("36540", "large_300k_1m", [1, 2, 3]))]

    estimate = run_pilot.estimate_dfs_paid_cost_usd(pairs, args)

    assert estimate == pytest.approx(0.208)


def test_paid_acquisition_flags_require_budget() -> None:
    with pytest.raises(SystemExit) as excinfo:
        run_pilot.validate_paid_run_budget(
            estimated_cost_usd=0.25,
            paid_budget_usd=None,
            dfs_balance_usd=10.0,
            paid_acquisition_enabled=True,
        )

    assert excinfo.value.code == 2


def test_preflight_only_does_not_require_paid_budget_for_acquisition_flags() -> None:
    args = Namespace(
        preflight_only=True,
        paid_budget_usd=None,
        collect_organic_telemetry=True,
        collect_review_velocity=True,
        collect_gbp_profile=True,
    )

    assert run_pilot.paid_budget_required(args) is False
    assert run_pilot.paid_calls_enabled(args) is False


def test_preflight_only_with_budget_enables_paid_keyword_volume_validation() -> None:
    args = Namespace(preflight_only=True, paid_budget_usd=1.0)

    assert run_pilot.paid_budget_required(args) is False
    assert run_pilot.paid_calls_enabled(args) is True


def test_paid_budget_rejects_non_finite_values() -> None:
    with pytest.raises(ArgumentTypeError, match="finite positive"):
        run_pilot.positive_float("nan")


def test_paid_budget_guard_rejects_negative_dfs_balance() -> None:
    with pytest.raises(SystemExit) as excinfo:
        run_pilot.validate_paid_run_budget(
            estimated_cost_usd=0.25,
            paid_budget_usd=1.0,
            dfs_balance_usd=-0.09,
            paid_acquisition_enabled=True,
        )

    assert excinfo.value.code == 2


def test_core_project_services_are_selectable_for_benchmark_acquisition() -> None:
    selected = select_niches([
        "roofing",
        "plumbing",
        "hvac",
        "tree service",
        "auto repair",
        "water damage restoration",
        "electrician",
        "locksmith",
    ])

    assert selected == [
        "roofing",
        "plumbing",
        "hvac",
        "tree service",
        "auto repair",
        "water damage restoration",
        "electrician",
        "locksmith",
    ]


def test_requested_niche_aliases_are_canonicalized_and_deduped() -> None:
    selected = select_niches([
        "plumber",
        "plumbing",
        "roofing contractor",
        "roofing",
    ])

    assert selected == ["plumbing", "roofing"]


def test_persistence_niche_key_uses_project_service_keys() -> None:
    assert persistence_niche_key("plumber") == "plumbing"
    assert persistence_niche_key("plumbing") == "plumbing"
    assert persistence_niche_key("roofing contractor") == "roofing"
    assert persistence_niche_key("roofing") == "roofing"
    assert persistence_niche_key("tree service") == "tree service"
    assert persistence_niche_key("tree services") == "tree service"


def test_fetch_metros_by_cbsa_reads_live_metros_in_requested_order(monkeypatch) -> None:
    requests = []

    def fake_urlopen(req, timeout):  # noqa: ANN001
        requests.append((req, timeout))
        return _FakeHTTPResponse(
            """
            [
              {
                "cbsa_code": "43620",
                "cbsa_name": "Sioux Falls, SD-MN",
                "state": "SD",
                "population": 285000,
                "population_class": "medium_100_300k",
                "dataforseo_location_codes": [21167]
              },
              {
                "cbsa_code": "30980",
                "cbsa_name": "Longview, TX",
                "state": "TX",
                "population": 286000,
                "population_class": "medium_100_300k",
                "dataforseo_location_codes": [1026201]
              }
            ]
            """
        )

    monkeypatch.setattr(run_pilot, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(run_pilot, "SUPABASE_KEY", "service-key")
    monkeypatch.setattr("scripts.benchmarks.run_pilot.urlreq.urlopen", fake_urlopen)

    fetch_metros_by_cbsa = getattr(run_pilot, "fetch_metros_by_cbsa", None)
    assert fetch_metros_by_cbsa is not None

    rows = fetch_metros_by_cbsa(["30980", "43620"], include_low_signal=False)

    assert [row["cbsa_code"] for row in rows] == ["30980", "43620"]
    assert all(row["paid_eligible"] for row in rows)
    assert all(row["_dfs_source"] == "native" for row in rows)
    parsed = parse_qs(urlparse(requests[0][0].full_url).query)
    assert "dataforseo_location_match_confidence" in parsed["select"][0]
    assert parsed["cbsa_code"] == ["in.(30980,43620)"]


def test_fetch_metros_by_cbsa_rejects_malformed_codes(monkeypatch) -> None:
    monkeypatch.setattr(run_pilot, "SUPABASE_KEY", "service-key")

    with pytest.raises(SystemExit) as excinfo:
        run_pilot.fetch_metros_by_cbsa(
            ["30980),cbsa_code=gt.0"],
            include_low_signal=False,
        )

    assert excinfo.value.code == 2


def test_fetch_metros_by_cbsa_fails_on_ineligible_exact_targets(monkeypatch) -> None:
    def fake_urlopen(req, timeout):  # noqa: ANN001
        return _FakeHTTPResponse(
            """
            [
              {
                "cbsa_code": "12345",
                "cbsa_name": "Small Metro",
                "state": "TX",
                "population": 45000,
                "population_class": "micro_under_50k",
                "dataforseo_location_codes": [123],
                "dataforseo_location_match_confidence": "verified"
              },
              {
                "cbsa_code": "23456",
                "cbsa_name": "Ambiguous Metro",
                "state": "TX",
                "population": 250000,
                "population_class": "medium_100_300k",
                "dataforseo_location_codes": [234],
                "dataforseo_location_match_confidence": "ambiguous"
              }
            ]
            """
        )

    monkeypatch.setattr(run_pilot, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(run_pilot, "SUPABASE_KEY", "service-key")
    monkeypatch.setattr("scripts.benchmarks.run_pilot.urlreq.urlopen", fake_urlopen)

    with pytest.raises(SystemExit) as excinfo:
        run_pilot.fetch_metros_by_cbsa(["12345", "23456"], include_low_signal=False)

    assert excinfo.value.code == 2


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
