"""Structure tests for the Explore refresh control migration."""

from __future__ import annotations

from pathlib import Path


MIGRATION = Path("supabase/migrations/015_explore_refresh_control.sql")
GRANTS_MIGRATION = Path("supabase/migrations/019_explore_refresh_grants.sql")


def _migration_sql() -> str:
    assert MIGRATION.exists(), f"Missing migration: {MIGRATION}"
    return MIGRATION.read_text()


def test_refresh_schema_has_policy_run_and_snapshot_tables() -> None:
    sql = _migration_sql()

    for table in (
        "explore_refresh_policies",
        "explore_refresh_targets",
        "explore_refresh_runs",
        "explore_refresh_run_items",
        "explore_report_snapshots",
    ):
        assert f"CREATE TABLE IF NOT EXISTS public.{table}" in sql


def test_refresh_policy_defaults_to_30_days() -> None:
    sql = _migration_sql()

    assert "cadence_days INTEGER NOT NULL DEFAULT 30" in sql
    assert "cadence_days BETWEEN 1 AND 365" in sql


def test_refresh_schema_exposes_latest_and_trend_views() -> None:
    sql = _migration_sql()

    assert "CREATE OR REPLACE VIEW public.explore_latest_target_scores" in sql
    assert "CREATE OR REPLACE VIEW public.explore_target_trends" in sql
    assert "LAG(opportunity_score)" in sql


def test_refresh_schema_has_explicit_data_api_grants() -> None:
    sql = _migration_sql()

    for relation in (
        "explore_refresh_policies",
        "explore_refresh_targets",
        "explore_refresh_runs",
        "explore_refresh_run_items",
        "explore_report_snapshots",
        "explore_latest_target_scores",
        "explore_target_trends",
    ):
        assert f"public.{relation}" in sql

    assert "GRANT SELECT ON public.explore_refresh_targets TO authenticated" in sql
    assert "GRANT ALL ON TABLE public.explore_refresh_targets TO service_role" in sql


def test_refresh_grants_migration_is_forward_only_and_idempotent() -> None:
    assert GRANTS_MIGRATION.exists(), f"Missing migration: {GRANTS_MIGRATION}"
    sql = GRANTS_MIGRATION.read_text()

    assert "to_regclass('public.explore_refresh_targets')" in sql
    assert "GRANT SELECT ON TABLE public.explore_refresh_targets TO authenticated" in sql
    assert "GRANT ALL ON TABLE public.explore_refresh_targets TO service_role" in sql
    assert "GRANT SELECT ON TABLE public.explore_target_trends TO authenticated" in sql
