"""Supabase-backed repository for V2 seo_benchmarks cells."""
from __future__ import annotations

import os
from typing import Any, Protocol

from src.scoring.benchmark_repository import SeoBenchmarkCell


class _SupabaseLike(Protocol):
    def table(self, name: str) -> Any:
        """Return a PostgREST query builder."""
        ...


_BENCHMARK_COLUMNS = (
    "niche_normalized,naics_code,population_class,"
    "p25_total_volume_per_capita,median_total_volume_per_capita,p75_total_volume_per_capita,"
    "p25_avg_cpc,median_avg_cpc,p75_avg_cpc,"
    "median_top3_review_count_min,median_top3_review_velocity,pct_with_local_pack,"
    "median_aggregator_count,median_local_biz_count,"
    "median_establishments_per_100k,median_lsa_present_rate,median_ads_present_rate,"
    "median_aio_trigger_rate,sample_size_metros,sample_size_observations,"
    "confidence_label,fact_window_start,fact_window_end,"
    "benchmark_run_id,benchmark_mode,formula_version,sample_frame_version,"
    "metric_confidence_rollup"
)


class SupabaseSeoBenchmarkRepository:
    """Reads `seo_benchmarks` through a narrow repository boundary."""

    def __init__(self, *, client: _SupabaseLike | None = None) -> None:
        if client is None:
            from supabase import create_client

            url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            if not url or not key:
                missing = [
                    name
                    for name in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
                    if not os.environ.get(name)
                ]
                raise RuntimeError(
                    "Cannot read seo_benchmarks; missing env var(s): "
                    + ", ".join(missing)
                )
            client = create_client(url, key)
        self._client = client

    def get(
        self,
        *,
        niche_normalized: str,
        population_class: str,
    ) -> SeoBenchmarkCell | None:
        response = (
            self._client.table("seo_benchmarks")
            .select(_BENCHMARK_COLUMNS)
            .eq("niche_normalized", niche_normalized)
            .eq("population_class", population_class)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if not rows:
            return None
        return SeoBenchmarkCell.from_mapping(rows[0])
