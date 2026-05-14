"""Unit tests for Supabase schema migrations (M2).

No live database — validates migration files exist, are non-empty,
and contain the expected table definitions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "supabase" / "migrations"


class TestMigrationFiles:
    def test_all_migration_files_exist(self):
        expected = [
            "001_core_schema.sql",
            "002_experiment_schema.sql",
            "003_shared_tables.sql",
            "004_rls_policies.sql",
            "007_kb_schema.sql",
            "008_kb_rls_and_lifecycle.sql",
            "014_user_management_billing.sql",
        ]
        for name in expected:
            path = MIGRATIONS_DIR / name
            assert path.exists(), f"Missing migration: {name}"
            assert path.stat().st_size > 0, f"Empty migration: {name}"


class TestCoreSchema:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "001_core_schema.sql").read_text()

    def test_reports_table(self, sql: str):
        assert "CREATE TABLE" in sql
        assert "reports" in sql
        assert "niche_keyword" in sql

    def test_feedback_log_table(self, sql: str):
        assert "feedback_log" in sql
        assert "context" in sql
        assert "outcome" in sql

    def test_metro_scores_table(self, sql: str):
        assert "metro_scores" in sql
        assert "opportunity_score" in sql
        assert "serp_archetype" in sql


class TestExperimentSchema:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "002_experiment_schema.sql").read_text()

    def test_experiments_table(self, sql: str):
        assert "experiments" in sql
        assert "niche_keyword" in sql

    def test_rentability_signals_table(self, sql: str):
        assert "rentability_signals" in sql
        assert "UNIQUE(niche_keyword, cbsa_code)" in sql

    def test_outreach_events_table(self, sql: str):
        assert "outreach_events" in sql
        assert "event_type" in sql

    def test_foreign_keys(self, sql: str):
        assert "REFERENCES experiments(id)" in sql
        assert "REFERENCES experiment_businesses(id)" in sql


class TestSharedTables:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "003_shared_tables.sql").read_text()

    def test_api_usage_log(self, sql: str):
        assert "api_usage_log" in sql
        assert "endpoint" in sql
        assert "cost" in sql

    def test_metro_location_cache(self, sql: str):
        assert "metro_location_cache" in sql
        assert "dataforseo_location_codes" in sql

    def test_suppression_list(self, sql: str):
        assert "suppression_list" in sql


class TestRLSPolicies:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "004_rls_policies.sql").read_text()

    def test_rls_enabled_on_all_tables(self, sql: str):
        tables = [
            "reports", "report_keywords", "metro_signals", "metro_scores",
            "feedback_log", "experiments", "experiment_variants",
            "experiment_businesses", "outreach_events", "reply_classifications",
            "rentability_signals", "api_usage_log", "metro_location_cache",
            "suppression_list",
        ]
        for table in tables:
            assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql, (
                f"RLS not enabled for {table}"
            )

    def test_service_role_policies_exist(self, sql: str):
        assert "CREATE POLICY" in sql
        assert "service_role" in sql


class TestKBSchema:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "007_kb_schema.sql").read_text()

    def test_kb_entities_table(self, sql: str):
        assert "kb_entities" in sql
        assert "niche_keyword_normalized" in sql
        assert "geo_target_normalized" in sql

    def test_kb_snapshots_table(self, sql: str):
        assert "kb_snapshots" in sql
        assert "is_current" in sql
        assert "superseded_by" in sql
        assert "input_hash" in sql

    def test_kb_evidence_artifacts_table(self, sql: str):
        assert "kb_evidence_artifacts" in sql
        assert "artifact_type" in sql
        assert "payload_hash" in sql

    def test_api_response_cache_table(self, sql: str):
        assert "api_response_cache" in sql
        assert "params_hash" in sql
        assert "expires_at" in sql

    def test_feedback_events_table(self, sql: str):
        assert "feedback_events" in sql
        assert "snapshot_id" in sql
        assert "entity_id" in sql

    def test_current_snapshot_unique_constraint(self, sql: str):
        assert "idx_kb_snapshots_current" in sql
        assert "WHERE is_current = true" in sql


class TestKBRLSAndLifecycle:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "008_kb_rls_and_lifecycle.sql").read_text()

    def test_rls_enabled_on_kb_tables(self, sql: str):
        for table in ["kb_entities", "kb_snapshots", "kb_evidence_artifacts",
                       "api_response_cache", "feedback_events"]:
            assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql, (
                f"RLS not enabled for {table}"
            )

    def test_service_role_policies_for_kb(self, sql: str):
        for table in ["kb_entities", "kb_snapshots", "kb_evidence_artifacts",
                       "api_response_cache", "feedback_events"]:
            assert f"Service role full access on {table}" in sql

    def test_reports_soft_delete_column(self, sql: str):
        assert "archived_at" in sql

    def test_reports_entity_and_snapshot_fk(self, sql: str):
        assert "entity_id" in sql
        assert "snapshot_id" in sql


class TestUserManagementBillingSchema:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "014_user_management_billing.sql").read_text()

    def test_account_and_billing_tables(self, sql: str):
        for table in [
            "user_profiles",
            "accounts",
            "account_memberships",
            "subscriptions",
            "billing_customers",
            "usage_counters",
        ]:
            assert f"CREATE TABLE IF NOT EXISTS {table}" in sql

    def test_plan_catalog_seed_matches_tiers(self, sql: str):
        assert "('free', 'Free', 0, 0, NULL)" in sql
        assert "('plus', 'Plus', 4900, 10, 'STRIPE_PLUS_PRICE_ID')" in sql
        assert "('pro', 'Pro', 10000, 50, 'STRIPE_PRO_PRICE_ID')" in sql

    def test_reports_get_ownership_columns(self, sql: str):
        assert "owner_account_id" in sql
        assert "created_by_user_id" in sql
        assert "access_scope TEXT NOT NULL DEFAULT 'cached'" in sql
        assert "reports_scope_owner_consistency" in sql

    def test_broad_authenticated_report_policies_are_removed(self, sql: str):
        assert 'DROP POLICY IF EXISTS "Authenticated users can read reports"' in sql
        assert 'DROP POLICY IF EXISTS "Authenticated users can delete reports"' in sql
        assert "Authenticated users can read visible reports" in sql
        assert "public.is_account_member(owner_account_id)" in sql

    def test_child_report_tables_inherit_parent_visibility(self, sql: str):
        for policy in [
            "Authenticated users can read visible report_keywords",
            "Authenticated users can read visible metro_signals",
            "Authenticated users can read visible metro_scores",
        ]:
            assert policy in sql
        assert "WHERE r.id = report_keywords.report_id" in sql
        assert "WHERE r.id = metro_signals.report_id" in sql
        assert "WHERE r.id = metro_scores.report_id" in sql

    def test_quota_functions_exist(self, sql: str):
        assert "FUNCTION public.get_account_entitlement()" in sql
        assert "FUNCTION public.consume_report_quota(p_account_id UUID)" in sql
        assert "FUNCTION public.refund_report_quota(p_account_id UUID)" in sql
        assert "ON CONFLICT (account_id, metric_key, period_start, period_end)" in sql
        assert "WHERE usage_counters.used_count < v_limit" in sql
