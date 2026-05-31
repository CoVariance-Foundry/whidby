"""Tests for the pure seo_benchmarks repository contract."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from src.scoring.benchmark_repository import SeoBenchmarkCell


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "niche_normalized": "plumber",
        "naics_code": "238220",
        "population_class": "metro_1m_5m",
        "p25_total_volume_per_capita": Decimal("0.001000"),
        "median_total_volume_per_capita": Decimal("0.002500"),
        "p75_total_volume_per_capita": Decimal("0.004000"),
        "p25_avg_cpc": Decimal("8.25"),
        "median_avg_cpc": Decimal("12.50"),
        "p75_avg_cpc": Decimal("18.75"),
        "median_top3_review_count_min": 42,
        "median_top3_review_velocity": Decimal("3.75"),
        "pct_with_local_pack": Decimal("0.7500"),
        "median_aggregator_count": Decimal("2.50"),
        "median_local_biz_count": Decimal("5.00"),
        "median_establishments_per_100k": Decimal("64.50"),
        "median_lsa_present_rate": Decimal("0.2500"),
        "median_ads_present_rate": Decimal("0.5000"),
        "median_aio_trigger_rate": Decimal("0.1250"),
        "sample_size_metros": 12,
        "sample_size_observations": 144,
        "confidence_label": "medium",
        "fact_window_start": "2026-01-01",
        "fact_window_end": "2026-05-01",
        "benchmark_run_id": "11111111-1111-4111-8111-111111111111",
        "benchmark_mode": "pooled_population",
        "formula_version": "2.1",
        "sample_frame_version": "coverage-hardening-v2",
        "metric_confidence_rollup": {
            "demand": {"confidence_label": "high"},
            "local_pack": {"confidence_label": "low"},
        },
    }
    row.update(overrides)
    return row


def test_from_mapping_coerces_supabase_numeric_values() -> None:
    cell = SeoBenchmarkCell.from_mapping(_row())

    assert cell.niche_normalized == "plumber"
    assert cell.naics_code == "238220"
    assert cell.population_class == "metro_1m_5m"
    assert cell.median_total_volume_per_capita == 0.0025
    assert cell.median_avg_cpc == 12.5
    assert cell.median_top3_review_count_min == 42
    assert cell.median_top3_review_velocity == 3.75
    assert cell.sample_size_metros == 12
    assert cell.sample_size_observations == 144
    assert cell.confidence_label == "medium"
    assert cell.is_undersampled is False


def test_from_mapping_parses_benchmark_lineage_fields() -> None:
    cell = SeoBenchmarkCell.from_mapping(_row())

    assert cell.benchmark_run_id == "11111111-1111-4111-8111-111111111111"
    assert cell.benchmark_mode == "pooled_population"
    assert cell.formula_version == "2.1"
    assert cell.sample_frame_version == "coverage-hardening-v2"
    assert dict(cell.metric_confidence_rollup) == {
        "demand": {"confidence_label": "high"},
        "local_pack": {"confidence_label": "low"},
    }


def test_from_mapping_defaults_missing_lineage_fields_for_legacy_rows() -> None:
    row = _row()
    for key in (
        "benchmark_run_id",
        "benchmark_mode",
        "formula_version",
        "sample_frame_version",
        "metric_confidence_rollup",
    ):
        row.pop(key)

    cell = SeoBenchmarkCell.from_mapping(row)

    assert cell.benchmark_run_id is None
    assert cell.benchmark_mode == "exact"
    assert cell.formula_version is None
    assert cell.sample_frame_version is None
    assert dict(cell.metric_confidence_rollup) == {}


def test_from_mapping_preserves_nullable_benchmark_columns() -> None:
    cell = SeoBenchmarkCell.from_mapping(
        _row(
            naics_code=None,
            median_top3_review_count_min=None,
            median_top3_review_velocity=None,
            median_establishments_per_100k=None,
        )
    )

    assert cell.naics_code is None
    assert cell.median_top3_review_count_min is None
    assert cell.median_top3_review_velocity is None
    assert cell.median_establishments_per_100k is None


def test_low_and_insufficient_cells_are_undersampled() -> None:
    low = SeoBenchmarkCell.from_mapping(_row(sample_size_metros=3, confidence_label="low"))
    insufficient = SeoBenchmarkCell.from_mapping(
        _row(sample_size_metros=1, confidence_label="insufficient")
    )

    assert low.is_undersampled is True
    assert insufficient.is_undersampled is True


def test_cells_with_small_metro_sample_are_undersampled() -> None:
    cell = SeoBenchmarkCell.from_mapping(_row(sample_size_metros=7, confidence_label="medium"))

    assert cell.is_undersampled is True


def test_invalid_confidence_label_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unsupported benchmark confidence"):
        SeoBenchmarkCell.from_mapping(_row(confidence_label="experimental"))


def test_invalid_benchmark_mode_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unsupported benchmark mode"):
        SeoBenchmarkCell.from_mapping(_row(benchmark_mode="nearest_neighbor"))


def test_empty_benchmark_mode_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unsupported benchmark mode"):
        SeoBenchmarkCell.from_mapping(_row(benchmark_mode=" "))


def test_non_mapping_metric_confidence_rollup_raises_value_error() -> None:
    with pytest.raises(ValueError, match="metric_confidence_rollup must be a mapping"):
        SeoBenchmarkCell.from_mapping(_row(metric_confidence_rollup=["demand"]))


def test_whi126_migration_adds_lineage_and_metric_sufficiency_schema() -> None:
    migration = (
        Path(__file__).parents[2]
        / "supabase/migrations/20260524133000_whi126_benchmark_lineage.sql"
    ).read_text()

    assert "CREATE TABLE IF NOT EXISTS public.seo_benchmark_runs" in migration
    assert "CREATE TABLE IF NOT EXISTS public.seo_benchmark_metric_sufficiency" in migration
    assert "benchmark_run_id UUID" in migration
    assert "seo_benchmark_runs(id)" in migration
    assert "ON DELETE SET NULL" in migration
    assert "metric_confidence_rollup JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "FROM pg_constraint" in migration
    assert "conname = 'seo_benchmarks_benchmark_mode_check'" in migration
    assert "conrelid = 'public.seo_benchmarks'::regclass" in migration
    assert "jsonb_typeof(source_mix) = 'object'" in migration
    assert "jsonb_typeof(acquisition_flags) = 'object'" in migration
    assert "jsonb_typeof(pool_definition) = 'object'" in migration
    assert "jsonb_typeof(cost_summary) = 'object'" in migration
    assert "jsonb_typeof(metric_confidence_rollup) = 'object'" in migration
    for metric_family in (
        "demand",
        "organic_serp",
        "organic_authority",
        "lighthouse_site_quality",
        "local_pack",
        "review_velocity",
        "gbp_profile",
        "monetization",
        "ai_serp_displacement",
    ):
        assert metric_family in migration
    assert "CHECK (non_null_metros <= attempted_metros)" in migration
    assert "CHECK (non_null_observations <= attempted_observations)" in migration
