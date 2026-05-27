"""Schema contract tests for Supabase migrations."""

from __future__ import annotations

from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def _latest_whi9_migration_sql() -> str:
    matches = sorted(MIGRATIONS_DIR.glob("*_whi9_competitor_intel_schema_quota.sql"))
    assert matches, "WHI-9 competitor intel migration is missing"
    return matches[-1].read_text()


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


def test_whi130_warning_codes_read_model_contract() -> None:
    """V2 score and Explore read models persist canonical warning codes."""
    migration_sql = (
        MIGRATIONS_DIR / "20260524153000_whi130_warning_codes_read_models.sql"
    ).read_text()
    v2_sql = (MIGRATIONS_DIR / "010_v2_benchmarks.sql").read_text()
    explore_sql = (MIGRATIONS_DIR / "020_explore_market_cells.sql").read_text()

    assert "ADD COLUMN IF NOT EXISTS warning_codes TEXT[]" in migration_sql
    assert "COMMENT ON COLUMN public.metro_score_v2.warning_codes" in migration_sql
    assert "metric_undersampled" in migration_sql
    assert "coalesce(v2.warning_codes, ARRAY[]::text[]) AS warning_codes" in migration_sql
    assert "cell.warning_codes" in migration_sql

    assert "warning_codes                TEXT[] NOT NULL DEFAULT '{}'::text[]" in v2_sql
    assert "coalesce(v2.warning_codes, ARRAY[]::text[]) AS warning_codes" in explore_sql
    assert "ARRAY[]::text[] AS warning_codes" in explore_sql


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


def test_repair_migration_keeps_v2_top5_schema_idempotent() -> None:
    matches = sorted(MIGRATIONS_DIR.glob("*_repair_v2_top5_schema.sql"))
    assert matches, "V2 top-5 repair migration is missing"
    sql = matches[-1].read_text()

    for expected in (
        "ADD COLUMN IF NOT EXISTS avg_top5_da",
        "ADD COLUMN IF NOT EXISTS avg_top5_lighthouse",
        "ADD COLUMN IF NOT EXISTS top5_da_coverage",
        "ADD COLUMN IF NOT EXISTS top5_lighthouse_coverage",
        "ADD COLUMN IF NOT EXISTS top5_organic_data_confidence",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_score_v2_report_cbsa_unique",
        "seo_facts_top5_organic_confidence_check",
        "top5_organic_data_confidence IN ('high', 'medium', 'low', 'missing')",
    ):
        assert expected in sql


def test_metro_dfs_readiness_migration_adds_provenance_fields() -> None:
    """DFS enrichment must leave reviewable provenance on canonical metro rows."""
    sql = (MIGRATIONS_DIR / "024_metro_dfs_readiness_provenance.sql").read_text()

    for column in (
        "dataforseo_location_match_name",
        "dataforseo_location_match_confidence",
        "dataforseo_location_match_source",
        "dataforseo_location_verified_at",
        "dataforseo_location_review_reason",
    ):
        assert f"ADD COLUMN IF NOT EXISTS {column}" in sql

    assert "ALTER TABLE public.metros" in sql
    assert "metros_dfs_location_match_confidence_check" in sql
    assert "'exact'" in sql
    assert "'strong'" in sql
    assert "idx_metros_dfs_verified_at" in sql


def test_whi9_competitor_intel_migration_adds_fact_and_run_tables() -> None:
    sql = _latest_whi9_migration_sql()

    assert "CREATE TABLE IF NOT EXISTS public.organic_competitor_facts" in sql
    assert "CREATE TABLE IF NOT EXISTS public.competitor_intel_runs" in sql
    assert (
        "UNIQUE (cbsa_code, niche_normalized, keyword, result_rank, result_type, snapshot_date)"
        in sql
    )
    assert "account_id UUID REFERENCES public.accounts(id) ON DELETE SET NULL" in sql
    assert "created_by_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL" in sql
    assert "report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL" in sql
    assert "backlinks_count INTEGER" in sql
    assert "referring_domains_count INTEGER" in sql
    assert "has_localbusiness_schema BOOLEAN" in sql
    assert "schema_types TEXT[] NOT NULL DEFAULT '{}'::text[]" in sql
    assert "title_keyword_match BOOLEAN" in sql
    assert "service TEXT" in sql
    assert "scan_cost_usd NUMERIC(10,4) NOT NULL DEFAULT 0" in sql
    assert "quota_consumed INTEGER NOT NULL DEFAULT 0" in sql
    assert "status TEXT NOT NULL DEFAULT 'queued'" in sql
    assert "result_summary JSONB NOT NULL DEFAULT '{}'::jsonb" in sql
    assert "errors JSONB NOT NULL DEFAULT '[]'::jsonb" in sql
    assert "CREATE TABLE IF NOT EXISTS public.local_pack_listing_facts" not in sql


def test_whi9_competitor_intel_migration_enables_rls_and_grants_access() -> None:
    sql = _latest_whi9_migration_sql()

    assert "ALTER TABLE public.organic_competitor_facts ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE public.competitor_intel_runs ENABLE ROW LEVEL SECURITY" in sql
    assert "FOR SELECT TO authenticated" in sql
    assert "FOR ALL TO service_role" in sql
    assert "public.is_account_member(account_id)" in sql
    assert "REVOKE ALL ON TABLE public.organic_competitor_facts FROM authenticated" in sql
    assert "REVOKE ALL ON TABLE public.local_pack_listing_facts FROM authenticated" in sql
    assert "GRANT SELECT ON TABLE public.organic_competitor_facts TO authenticated" not in sql
    assert "DROP POLICY IF EXISTS \"Authenticated users can read local pack listing facts\"" in sql
    assert "GRANT ALL ON TABLE public.organic_competitor_facts TO service_role" in sql
    assert "GRANT SELECT ON TABLE public.competitor_intel_runs TO authenticated" in sql
    assert "GRANT ALL ON TABLE public.competitor_intel_runs TO service_role" in sql
    assert "GRANT ALL ON TABLE public.local_pack_listing_facts TO service_role" in sql


def test_whi9_competitor_intel_migration_adds_multi_unit_quota_rpcs() -> None:
    sql = _latest_whi9_migration_sql()

    assert "CREATE OR REPLACE FUNCTION public.consume_usage_quota" in sql
    assert "p_metric_key TEXT" in sql
    assert "p_units INT" in sql
    assert "p_units IS NULL OR p_units <= 0" in sql
    assert "RAISE EXCEPTION 'p_units must be a positive integer'" in sql
    assert "used_count = usage_counters.used_count + p_units" in sql
    assert "WHERE usage_counters.used_count + p_units <= v_limit" in sql
    assert "CREATE OR REPLACE FUNCTION public.refund_usage_quota" in sql
    assert "used_count = GREATEST(used_count - p_units, 0)" in sql
    assert "IF auth.role() <> 'service_role' AND NOT public.is_account_member(p_account_id)" in sql
    assert "SELECT public.consume_usage_quota(p_account_id, 'fresh_report', 1)" in sql
    assert "SELECT public.refund_usage_quota(p_account_id, 'fresh_report', 1)" in sql
    assert "GRANT EXECUTE ON FUNCTION public.consume_usage_quota(UUID, TEXT, INT)" in sql
    assert "REVOKE EXECUTE ON FUNCTION public.refund_usage_quota(UUID, TEXT, INT) FROM authenticated" in sql
    assert "GRANT EXECUTE ON FUNCTION public.refund_usage_quota(UUID, TEXT, INT) TO service_role" in sql
    assert "REVOKE EXECUTE ON FUNCTION public.refund_report_quota(UUID) FROM authenticated" in sql
    assert "GRANT EXECUTE ON FUNCTION public.refund_report_quota(UUID) TO service_role" in sql
