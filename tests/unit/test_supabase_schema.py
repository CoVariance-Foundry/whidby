"""Schema contract tests for Supabase migrations."""

from __future__ import annotations

from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def test_v2_top5_fact_fields_migration_extends_seo_facts() -> None:
    """V2 facts persist nullable top-5 organic signals for benchmark recompute."""
    sql = (MIGRATIONS_DIR / "021_v2_top5_fact_fields.sql").read_text()

    for column in (
        "avg_top5_da",
        "avg_top5_lighthouse",
        "top5_da_coverage",
        "top5_lighthouse_coverage",
        "top5_organic_data_confidence",
    ):
        assert f"ADD COLUMN IF NOT EXISTS {column}" in sql

    assert "ALTER TABLE public.seo_facts" in sql
    assert "seo_facts_top5_organic_confidence_check" in sql
    assert "top5_organic_data_confidence IN ('high', 'medium', 'low', 'missing')" in sql
