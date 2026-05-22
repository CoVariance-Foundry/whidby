"""Schema contract tests for Supabase migrations."""

from __future__ import annotations

from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def test_v2_top5_fact_fields_migration_extends_seo_facts() -> None:
    """V2 facts persist nullable top-5 organic signals for benchmark recompute."""
    sql = (MIGRATIONS_DIR / "022_v2_scoring_persistence_contract.sql").read_text()

    for column in (
        "avg_top5_da",
        "avg_top5_lighthouse",
        "top5_da_coverage",
        "top5_lighthouse_coverage",
        "top5_organic_data_confidence",
    ):
        assert f"ADD COLUMN IF NOT EXISTS {column}" in sql

    assert "ALTER TABLE public.seo_facts" in sql
    assert "CREATE UNIQUE INDEX IF NOT EXISTS idx_score_v2_report_cbsa_unique" in sql
    assert "ON public.metro_score_v2(report_id, cbsa_code)" in sql
    assert "seo_facts_top5_organic_confidence_check" in sql
    assert "top5_organic_data_confidence IN ('high', 'medium', 'low', 'missing')" in sql


def test_billing_operations_hardening_migration_contract() -> None:
    """Billing hardening persists checkout, webhook, and admin issue state."""
    sql = (MIGRATIONS_DIR / "023_billing_operations_hardening.sql").read_text()

    for table in (
        "billing_checkout_sessions",
        "billing_operation_events",
        "billing_webhook_events",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql

    for column in (
        "last_stripe_event_id",
        "last_stripe_event_created_at",
        "billing_operations_admin",
    ):
        assert f"ADD COLUMN IF NOT EXISTS {column}" in sql

    assert "idx_billing_checkout_sessions_one_pending_account" in sql
    assert "WHERE status = 'pending'" in sql
    assert "idx_internal_user_entitlements_billing_ops_admin" in sql
    assert "idx_billing_operation_events_status_severity_created" in sql
    assert "idx_billing_webhook_events_status_created" in sql
    assert "Service role full access on billing checkout sessions" in sql
    assert "Service role full access on billing operation events" in sql
    assert "Service role full access on billing webhook events" in sql
    assert "Authenticated admins can read billing operation events" in sql
    assert "Authenticated admins can resolve billing operation events" in sql
    assert "CREATE OR REPLACE FUNCTION public.list_billing_operation_events" in sql
    assert "CREATE OR REPLACE FUNCTION public.resolve_billing_operation_event" in sql
    assert "FROM public.internal_user_entitlements" in sql
    assert "billing_operations_admin = true" in sql
    assert "role = 'admin'" not in sql
    assert "GET DIAGNOSTICS v_rows_updated = ROW_COUNT" in sql
    assert "billing_event_not_found" in sql
    assert "billing_admin_required" in sql
