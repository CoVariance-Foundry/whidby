"""Tests for the Supabase-backed seo_benchmarks repository."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.clients.seo_benchmark_repository import (
    _BENCHMARK_COLUMNS,
    SupabaseSeoBenchmarkRepository,
)


def _benchmark_row() -> dict[str, object]:
    return {
        "niche_normalized": "plumber",
        "naics_code": "238220",
        "population_class": "metro_1m_5m",
        "p25_total_volume_per_capita": 0.001,
        "median_total_volume_per_capita": 0.0025,
        "p75_total_volume_per_capita": 0.004,
        "p25_avg_cpc": 8.25,
        "median_avg_cpc": 12.5,
        "p75_avg_cpc": 18.75,
        "median_top3_review_count_min": 42,
        "median_top3_review_velocity": 3.75,
        "pct_with_local_pack": 0.75,
        "median_aggregator_count": 2.5,
        "median_local_biz_count": 5.0,
        "median_establishments_per_100k": 64.5,
        "median_lsa_present_rate": 0.25,
        "median_ads_present_rate": 0.5,
        "median_aio_trigger_rate": 0.125,
        "sample_size_metros": 12,
        "sample_size_observations": 144,
        "confidence_label": "medium",
        "fact_window_start": "2026-01-01",
        "fact_window_end": "2026-05-01",
        "benchmark_run_id": "11111111-1111-4111-8111-111111111111",
        "benchmark_mode": "manual",
        "formula_version": "2.1",
        "sample_frame_version": "coverage-hardening-v2",
        "metric_confidence_rollup": {"monetization": {"confidence_label": "medium"}},
    }


def _fake_client(data: list[dict[str, object]]) -> MagicMock:
    client = MagicMock()
    response = MagicMock(data=data)
    query = client.table.return_value.select.return_value
    query.eq.return_value.eq.return_value.limit.return_value.execute.return_value = response
    return client


def test_get_queries_seo_benchmarks_by_niche_and_population_class() -> None:
    client = _fake_client([_benchmark_row()])
    repo = SupabaseSeoBenchmarkRepository(client=client)

    cell = repo.get(niche_normalized="plumber", population_class="metro_1m_5m")

    assert cell is not None
    assert cell.niche_normalized == "plumber"
    assert cell.population_class == "metro_1m_5m"
    assert cell.median_avg_cpc == 12.5
    assert cell.benchmark_run_id == "11111111-1111-4111-8111-111111111111"
    assert cell.benchmark_mode == "manual"
    assert cell.formula_version == "2.1"
    assert cell.sample_frame_version == "coverage-hardening-v2"
    assert dict(cell.metric_confidence_rollup) == {
        "monetization": {"confidence_label": "medium"}
    }
    client.table.assert_called_once_with("seo_benchmarks")
    select_arg = client.table.return_value.select.call_args.args[0]
    assert "median_total_volume_per_capita" in select_arg
    assert "confidence_label" in select_arg
    first_eq = client.table.return_value.select.return_value.eq
    first_eq.assert_called_once_with("niche_normalized", "plumber")
    second_eq = first_eq.return_value.eq
    second_eq.assert_called_once_with("population_class", "metro_1m_5m")


def test_get_returns_none_when_no_benchmark_cell_exists() -> None:
    client = _fake_client([])
    repo = SupabaseSeoBenchmarkRepository(client=client)

    assert repo.get(niche_normalized="roofing", population_class="large_300k_1m") is None


def test_benchmark_columns_select_lineage_fields() -> None:
    for column in (
        "benchmark_run_id",
        "benchmark_mode",
        "formula_version",
        "sample_frame_version",
        "metric_confidence_rollup",
    ):
        assert column in _BENCHMARK_COLUMNS
