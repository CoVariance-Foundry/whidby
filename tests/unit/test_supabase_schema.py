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
            "015_explore_refresh_control.sql",
            "016_consumer_onboarding.sql",
            "017_strategy_discovery_system.sql",
            "018_internal_user_entitlements.sql",
            "019_explore_refresh_grants.sql",
            "020_explore_market_cells.sql",
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
        assert "Account members can update own reports" not in sql

    def test_account_bootstrap_is_serialized_per_user(self, sql: str):
        assert "idx_account_memberships_one_account_per_user" in sql
        assert "cannot add one-account-per-user constraint" in sql
        assert "GROUP BY user_id" in sql
        assert "HAVING count(*) > 1" in sql
        assert "pg_advisory_xact_lock(" in sql
        assert "replace(v_user_id::TEXT, '-', '')" in sql

    def test_report_archive_uses_scoped_rpc(self, sql: str):
        assert "public.archive_account_report" in sql
        assert "GRANT EXECUTE ON FUNCTION public.archive_account_report(UUID)" in sql
        assert "SET archived_at = now()" in sql
        assert "AND archived_at IS NULL" in sql

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


class TestInternalUserEntitlementsSchema:
    @pytest.fixture
    def sql(self) -> str:
        return (
            MIGRATIONS_DIR / "018_internal_user_entitlements.sql"
        ).read_text()

    @pytest.fixture
    def normalized_sql(self, sql: str) -> str:
        return " ".join(sql.split())

    def test_internal_user_entitlements_table(self, sql: str, normalized_sql: str):
        assert "CREATE TABLE IF NOT EXISTS public.internal_user_entitlements" in sql
        assert (
            "user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE"
            in normalized_sql
        )
        assert (
            "fresh_report_quota_exempt BOOLEAN NOT NULL DEFAULT false"
            in normalized_sql
        )
        assert "reason TEXT NOT NULL" in normalized_sql
        assert (
            "granted_by UUID REFERENCES auth.users(id) ON DELETE SET NULL"
            in normalized_sql
        )
        assert "expires_at TIMESTAMPTZ" in normalized_sql
        assert "created_at TIMESTAMPTZ NOT NULL DEFAULT now()" in normalized_sql
        assert "updated_at TIMESTAMPTZ NOT NULL DEFAULT now()" in normalized_sql
        assert "idx_internal_user_entitlements_active_quota_exempt" in sql
        assert (
            "ON public.internal_user_entitlements (user_id, expires_at)"
            in normalized_sql
        )
        assert "WHERE fresh_report_quota_exempt = true" in normalized_sql

    def test_internal_user_entitlements_rls_is_service_role_only(
        self, sql: str, normalized_sql: str
    ):
        assert (
            "ALTER TABLE public.internal_user_entitlements "
            "ENABLE ROW LEVEL SECURITY"
        ) in normalized_sql
        assert "Service role full access on internal_user_entitlements" in sql
        assert (
            "ON public.internal_user_entitlements FOR ALL TO service_role"
            in normalized_sql
        )
        assert (
            "ON public.internal_user_entitlements FOR ALL TO authenticated"
            not in normalized_sql
        )
        assert (
            "ON public.internal_user_entitlements FOR SELECT TO authenticated"
            not in normalized_sql
        )
        assert (
            "ON public.internal_user_entitlements FOR INSERT TO authenticated"
            not in normalized_sql
        )
        assert (
            "ON public.internal_user_entitlements FOR UPDATE TO authenticated"
            not in normalized_sql
        )
        assert (
            "ON public.internal_user_entitlements FOR DELETE TO authenticated"
            not in normalized_sql
        )

    def test_get_account_entitlement_includes_internal_override(
        self, normalized_sql: str
    ):
        assert "DROP FUNCTION IF EXISTS public.get_account_entitlement()" in (
            normalized_sql
        )
        assert "fresh_report_quota_exempt BOOLEAN" in normalized_sql
        assert "cancel_at_period_end BOOLEAN" in normalized_sql
        assert "COALESCE(s.cancel_at_period_end, false)" in normalized_sql
        assert "public.internal_user_entitlements iue" in normalized_sql
        assert "COALESCE(iue.fresh_report_quota_exempt, false)" in normalized_sql
        assert (
            "(iue.expires_at IS NULL OR iue.expires_at > now())"
            in normalized_sql
        )
        assert (
            "REVOKE EXECUTE ON FUNCTION public.get_account_entitlement() "
            "FROM PUBLIC"
        ) in normalized_sql
        assert (
            "REVOKE EXECUTE ON FUNCTION public.get_account_entitlement() "
            "FROM anon"
        ) in normalized_sql
        assert (
            "GRANT EXECUTE ON FUNCTION public.get_account_entitlement() "
            "TO authenticated"
        ) in normalized_sql

    def test_admin_account_bootstrap_rpc(self, normalized_sql: str):
        assert (
            "DROP FUNCTION IF EXISTS public.ensure_account_for_user_admin("
            "UUID, TEXT, TEXT, TEXT)"
        ) in normalized_sql
        assert "ensure_account_for_user_admin" in normalized_sql
        assert "p_member_role TEXT DEFAULT 'admin'" in normalized_sql
        assert "p_plan_key TEXT DEFAULT 'free'" in normalized_sql
        assert "p_overwrite_existing BOOLEAN DEFAULT false" in normalized_sql
        assert "role IN ('owner', 'member', 'admin')" in normalized_sql
        assert "plan_key IN ('free', 'plus', 'pro')" in normalized_sql
        assert "email = COALESCE(EXCLUDED.email, user_profiles.email)" in (
            normalized_sql
        )
        assert normalized_sql.count("WHERE p_overwrite_existing") == 2

    def test_admin_account_bootstrap_execute_is_service_role_only(
        self, normalized_sql: str
    ):
        assert (
            "REVOKE EXECUTE ON FUNCTION public.ensure_account_for_user_admin"
            in normalized_sql
        )
        assert (
            "GRANT EXECUTE ON FUNCTION public.ensure_account_for_user_admin("
            "UUID, TEXT, TEXT, TEXT, BOOLEAN) TO service_role"
        ) in normalized_sql
        assert (
            "GRANT EXECUTE ON FUNCTION public.ensure_account_for_user_admin("
            "UUID, TEXT, TEXT, TEXT, BOOLEAN) TO authenticated"
        ) not in normalized_sql
        assert (
            "GRANT EXECUTE ON FUNCTION public.ensure_account_for_user_admin("
            "UUID, TEXT, TEXT, TEXT, BOOLEAN) TO anon"
        ) not in normalized_sql


class TestConsumerOnboardingSchema:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "016_consumer_onboarding.sql").read_text()

    def test_onboarding_tables_created(self, sql: str):
        assert "CREATE TABLE IF NOT EXISTS onboarding_profiles" in sql
        assert "CREATE TABLE IF NOT EXISTS onboarding_targets" in sql

    def test_rls_enabled_on_onboarding_tables(self, sql: str):
        for table in ["onboarding_profiles", "onboarding_targets"]:
            assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql, (
                f"RLS not enabled for {table}"
            )

    def test_account_member_policies_exist(self, sql: str):
        assert "public.is_account_member(account_id)" in sql
        assert "public.is_account_member(op.account_id)" in sql

    def test_policy_creation_is_idempotent(self, sql: str):
        policies = [
            ("Account members can read onboarding profiles", "onboarding_profiles"),
            ("Users can update own onboarding profile", "onboarding_profiles"),
            ("Users can insert own onboarding profile", "onboarding_profiles"),
            ("Account members can read onboarding targets", "onboarding_targets"),
            ("Users can upsert own onboarding targets", "onboarding_targets"),
            ("Service role full access on onboarding_profiles", "onboarding_profiles"),
            ("Service role full access on onboarding_targets", "onboarding_targets"),
        ]
        for name, table in policies:
            assert f'DROP POLICY IF EXISTS "{name}"\n    ON {table};' in sql
            assert f'CREATE POLICY "{name}"' in sql

    def test_updated_at_triggers_exist(self, sql: str):
        for table in ["onboarding_profiles", "onboarding_targets"]:
            assert f"DROP TRIGGER IF EXISTS {table}_set_updated_at ON {table};" in sql
            assert f"CREATE TRIGGER {table}_set_updated_at" in sql
            assert f"BEFORE UPDATE ON {table}" in sql
        assert "EXECUTE FUNCTION public.set_updated_at();" in sql

    def test_own_user_write_checks_exist(self, sql: str):
        assert "USING (user_id = (SELECT auth.uid())" in sql
        assert "WITH CHECK (user_id = (SELECT auth.uid())" in sql
        assert "AND op.user_id = (SELECT auth.uid())" in sql

    def test_expected_status_values_exist(self, sql: str):
        for status in [
            "profile_started",
            "profile_completed",
            "strategy_recommended",
            "target_selected",
            "report_queued",
            "cached_route_selected",
            "upgrade_required",
            "report_ready",
        ]:
            assert f"'{status}'" in sql

    def test_expected_geo_scope_values_exist(self, sql: str):
        for geo_scope in ["city", "state", "region", "nationwide"]:
            assert f"'{geo_scope}'" in sql


class TestStrategyDiscoverySchema:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "017_strategy_discovery_system.sql").read_text()

    def test_strategy_discovery_run_tables(self, sql: str):
        assert "CREATE TABLE IF NOT EXISTS public.strategy_runs" in sql
        assert "CREATE TABLE IF NOT EXISTS public.strategy_run_items" in sql
        assert "account_id UUID" in sql
        assert "strategy_id TEXT NOT NULL" in sql
        assert "result_count INTEGER NOT NULL DEFAULT 0" in sql

    def test_strategy_discovery_evidence_tables(self, sql: str):
        assert "CREATE TABLE IF NOT EXISTS public.local_pack_listing_facts" in sql
        assert "CREATE TABLE IF NOT EXISTS public.metro_feature_vectors" in sql
        assert "CREATE TABLE IF NOT EXISTS public.strategy_score_cache" in sql
        assert "exact_match_name BOOLEAN NOT NULL DEFAULT FALSE" in sql
        assert "feature_vector JSONB NOT NULL" in sql

    def test_strategy_discovery_rls_enabled_on_all_tables(self, sql: str):
        for table in [
            "strategy_runs",
            "strategy_run_items",
            "local_pack_listing_facts",
            "metro_feature_vectors",
            "strategy_score_cache",
        ]:
            assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY" in sql

    def test_strategy_discovery_service_role_policies_exist(self, sql: str):
        for policy in [
            "Service role manages strategy runs",
            "Service role manages strategy run items",
            "Service role manages local pack listing facts",
            "Service role manages metro feature vectors",
            "Service role manages strategy score cache",
        ]:
            assert policy in sql

    def test_strategy_discovery_account_member_read_policies(self, sql: str):
        assert "Account members can read strategy runs" in sql
        assert "ON public.strategy_runs FOR SELECT TO authenticated" in sql
        assert "public.is_account_member(account_id)" in sql
        assert "Account members can read strategy run items" in sql
        assert "ON public.strategy_run_items FOR SELECT TO authenticated" in sql
        assert "EXISTS (" in sql
        assert "FROM public.strategy_runs sr" in sql
        assert "WHERE sr.id = strategy_run_items.run_id" in sql
        assert "public.is_account_member(sr.account_id)" in sql

    def test_strategy_discovery_report_linked_reads_respect_report_visibility(
        self, sql: str
    ):
        assert "Authenticated users can read local pack listing facts" in sql
        assert "report_id IS NULL" in sql
        assert "WHERE r.id = local_pack_listing_facts.report_id" in sql
        assert "Authenticated users can read strategy score cache" in sql
        assert "source_report_id IS NULL" in sql
        assert "WHERE r.id = strategy_score_cache.source_report_id" in sql
        assert "r.access_scope = 'cached'" in sql
        assert "public.is_account_member(r.owner_account_id)" in sql
        assert (
            "ON public.local_pack_listing_facts FOR SELECT TO authenticated "
            "USING (true)"
        ) not in sql
        assert (
            "ON public.strategy_score_cache FOR SELECT TO authenticated "
            "USING (true)"
        ) not in sql

    def test_strategy_discovery_strategy_checks_apply_to_result_tables(
        self, sql: str
    ):
        assert sql.count("strategy_id TEXT NOT NULL CHECK (strategy_id IN (") == 3
        assert "UNIQUE (run_id, rank)" in sql
        assert "CREATE INDEX IF NOT EXISTS idx_strategy_score_cache_scored_at" in sql
        assert "ON public.strategy_score_cache(strategy_id, scored_at DESC)" in sql
