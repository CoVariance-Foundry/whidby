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


def test_whi9_competitor_intel_migration_adds_fact_and_run_tables() -> None:
    sql = _latest_whi9_migration_sql()

    assert "CREATE TABLE IF NOT EXISTS public.organic_competitor_facts" in sql
    assert "CREATE TABLE IF NOT EXISTS public.competitor_intel_runs" in sql
    assert (
        "UNIQUE (cbsa_code, niche_normalized, keyword, result_rank, snapshot_date)"
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
